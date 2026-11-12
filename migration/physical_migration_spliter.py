#!/usr/bin/env python3

"""
Physical HBase Region Migration

Responsibilities
----------------
1. Discover physical HBase Regions.
2. Materialize logical DataGroups as physical Regions.
3. Move Regions between RegionServers.
4. Wait for HBase Region transitions to finish.
5. Verify the final Region location.
6. Record migration statistics.
7. Synchronize DataGroup.current_server only after success.

HBase version tested conceptually:
    HBase 2.6.x

Cluster:
    master
    slave1
    slave2
    slave3
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# CONFIGURATION
HBASE_CMD = os.environ.get("HBASE_CMD", "hbase")

WAIT_INTERVAL = 1.0
DEFAULT_TIMEOUT = 300

OUTPUT_DIR = Path("migration_results")
OUTPUT_DIR.mkdir(exist_ok=True)

MIGRATION_LOG = OUTPUT_DIR / "migration_log.csv"
REGION_MAPPING_FILE = OUTPUT_DIR / "region_mapping.json"



SERVER_ALIASES = {
    "slave1": "slave1",
    "slave2": "slave2",
    "slave3": "slave3",
}

# DATA STRUCTURES
@dataclass
class HBaseRegion:
    table: str
    region_name: str
    encoded_name: str
    start_key: str
    end_key: str
    size_mb: float
    server: str


@dataclass
class MigrationResult:
    timestamp: str
    group_id: str
    table: str
    encoded_region: str
    source_server: str
    target_server: str
    size_mb: float
    duration_seconds: float
    success: bool
    error: str = ""

# HBASE SHELL
def run_hbase(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Execute one HBase shell command non-interactively.

    Example:
        run_hbase("list_regions 'transactions'")
    """

    process = subprocess.run(
        [
            HBASE_CMD,
            "shell",
            "-n",
        ],
        input=command + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )

    output = process.stdout

    if process.returncode != 0:
        raise RuntimeError(
            f"HBase command failed:\n"
            f"COMMAND: {command}\n"
            f"OUTPUT:\n{output}"
        )

    return output

# REGION DISCOVERY
def _clean(value: str) -> str:
    return value.strip().strip("|").strip()


def parse_list_regions(output: str, table: str) -> List[HBaseRegion]:
    """
    Parse HBase shell `list_regions` output.

    Expected columns:

        SERVER_NAME
        REGION_NAME
        START_KEY
        END_KEY
        SIZE
        REQ
        LOCALITY

    Compatible with HBase output both with and without
    leading/trailing pipe characters.
    """

    regions = []

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        # Ignore HBase shell prompts
        if line.startswith("hbase:"):
            continue

        # Ignore table headers
        if "SERVER_NAME" in line and "REGION_NAME" in line:
            continue

        # Ignore separator lines such as:
        # ---------------- | ----------------
        if set(line.replace("|", "").replace(" ", "")) <= {"-"}:
            continue

        # list_regions data rows are pipe-separated
        if "|" not in line:
            continue

        columns = [
            _clean(x)
            for x in line.split("|")
        ]

        # With no leading pipe we expect exactly 7 columns.
        # With a leading pipe there can be 8 because of the
        # empty element before the first column.
        if len(columns) >= 7:

            # Remove empty first/last elements caused by
            # leading/trailing pipes.
            while columns and not columns[0]:
                columns.pop(0)

            while columns and not columns[-1]:
                columns.pop()

        if len(columns) < 7:
            continue

        server = columns[0]
        region_name = columns[1]
        start_key = columns[2]
        end_key = columns[3]
        size = columns[4]

        # Ignore invalid/header rows
        if not server or not region_name:
            continue

        if server == "SERVER_NAME":
            continue

        if region_name == "REGION_NAME":
            continue

        # Make sure this Region belongs to the requested table.
        #
        # Example:
        # transactions,,timestamp.encoded.
        #
        if not region_name.startswith(table + ","):
            continue

        try:
            encoded_name = extract_encoded_region_name(
                region_name
            )
        except ValueError:
            continue

        try:
            size_mb = float(size)
        except ValueError:
            continue

        regions.append(
            HBaseRegion(
                table=table,
                region_name=region_name,
                encoded_name=encoded_name,
                start_key=start_key,
                end_key=end_key,
                size_mb=size_mb,
                server=server,
            )
        )

    return regions


def extract_encoded_region_name(region_name: str) -> str:
    """
    Extract the encoded Region identifier from:

    transactions,start,timestamp.9f105d....

    -> 9f105d....
    """

    match = re.search(r"\.([0-9a-fA-F]{32})\.$", region_name)

    if match:
        return match.group(1)

    # Fallback
    if "." in region_name:
        value = region_name.rsplit(".", 2)[-2]
        return value

    raise ValueError(
        f"Cannot extract encoded Region name from:\n{region_name}"
    )


def get_regions(table: str) -> List[HBaseRegion]:
    output = run_hbase(f"list_regions '{table}'")

    regions = parse_list_regions(
        output,
        table,
    )

    print(f"[DEBUG] Parsed {len(regions)} regions for {table}")

    for r in regions:
        print(
            f"[DEBUG] {r.region_name} | "
            f"{r.start_key} -> {r.end_key} | "
            f"{r.server} | {r.size_mb} MB"
        )

    if not regions:
        raise RuntimeError(
            f"No Regions found for table '{table}'.\n"
            f"HBase output:\n{output}"
        )

    return regions

# REGION LOCATION
def find_region_containing_key(regions: List[HBaseRegion], key: str,) -> Optional[HBaseRegion]:

    for region in regions:

        # Empty start = negative infinity
        start_ok = (
            not region.start_key
            or key >= region.start_key
        )

        # Empty end = positive infinity
        end_ok = (
            not region.end_key
            or key < region.end_key
        )

        if start_ok and end_ok:
            return region

    return None

# REGIONS IN TRANSITION
def get_regions_in_transition() -> List[str]:
    """
    Return Regions currently in transition.

    `status 'detailed'` prints:

        0 regionsInTransition

    when the cluster is stable.
    """

    output = run_hbase("status 'detailed'")

    match = re.search(
        r"(\d+)\s+regionsInTransition",
        output,
    )

    if not match:
        raise RuntimeError(
            "Could not determine regionsInTransition.\n"
            f"Output:\n{output}"
        )

    count = int(match.group(1))

    if count == 0:
        return []

    # The detailed status output can vary between versions.
    # Return a non-empty marker; location verification is done
    # independently after the transition.
    return [f"{count} region(s) in transition"]



def wait_for_stable(timeout: int = DEFAULT_TIMEOUT):
    """
    Wait until HBase reports 0 regionsInTransition.
    """

    start = time.time()

    while True:

        transitions = get_regions_in_transition()

        if not transitions:
            return

        if time.time() - start > timeout:
            raise TimeoutError(
                "HBase did not become stable within "
                f"{timeout} seconds.\n"
                f"Current state: {transitions}"
            )

        time.sleep(WAIT_INTERVAL)


# BALANCER
def disable_balancer() -> bool:
    """
    Disable HBase balancer.

    Returns the previous state.

    If:
        Previous balancer state : true

    then the balancer was enabled and is now disabled.
    """

    output = run_hbase("balance_switch false")

    match = re.search(
        r"Previous balancer state\s*:\s*(true|false)",
        output,
        re.IGNORECASE,
    )

    if not match:
        raise RuntimeError(
            "Could not determine previous balancer state.\n"
            f"Output:\n{output}"
        )

    previous = match.group(1).lower() == "true"

    print(
        f"[BALANCER] Previous state: "
        f"{'ENABLED' if previous else 'DISABLED'}"
    )

    print("[BALANCER] Current state: DISABLED")

    return previous



def restore_balancer(previous_state: bool):
    if previous_state:
        run_hbase("balance_switch true")
        print("[BALANCER] Restored to ENABLED")
    else:
        print("[BALANCER] Remains DISABLED")


# REGION SPLITTING
def split_region_at_key(table: str, split_key: str,
    max_retries: int = 3,):
    print(f"[SPLIT] {table} at key: {split_key}")

    for attempt in range(1, max_retries + 1):

        regions = get_regions(table)

        # Already split
        if boundary_already_exists(regions, split_key):
            print(f"[SKIP] Boundary already exists: {split_key}")
            return

        region = find_region_containing_key(regions, split_key)

        if region is None:
            raise RuntimeError(
                f"No Region contains split key: {split_key}"
            )

        print(
            f"[SPLIT] Attempt {attempt}/{max_retries} | "
            f"Region={region.encoded_name}"
        )

        try:
            run_hbase(f"split '{table}', '{split_key}'")

        except RuntimeError as e:

            if "NOT splittable" not in str(e):
                raise

            print(
                f"[AUTO] Region {region.encoded_name} "
                f"is not splittable."
            )

            print(f"[AUTO] Compacting {region.encoded_name}...")

            run_hbase(f"compact '{region.encoded_name}'")

            time.sleep(3)

            wait_for_stable()

            print("[AUTO] Retrying split...")

            continue

        # Split command succeeded
        wait_for_stable()

        # Verify boundary really exists
        verification_start = time.time()

        while time.time() - verification_start < DEFAULT_TIMEOUT:

            regions = get_regions(table)

            if boundary_already_exists(regions, split_key):
                print(f"[SUCCESS] Boundary created: {split_key}")
                return

            time.sleep(WAIT_INTERVAL)

        raise TimeoutError(
            f"Split completed but boundary "
            f"did not appear: {split_key}"
        )

    raise RuntimeError(
        f"Failed to split {table} at {split_key} "
        f"after {max_retries} attempts."
    )


def boundary_already_exists(regions: List[HBaseRegion], boundary: str,) -> bool:

    for region in regions:
        if region.start_key == boundary:
            return True

    return False


# DATAGROUP VALIDATION
def validate_datagroups(groups) -> None:
    """
    Validate DataGroup ranges.

    Keys are compared lexicographically because HBase row keys
    are byte arrays.

    We do NOT convert keys to integers.
    """

    by_table: Dict[str, List] = {}

    for group in groups:
        by_table.setdefault(
            group.table,
            []
        ).append(group)

    for table, table_groups in by_table.items():

        ordered = sorted(
            table_groups,
            key=lambda g: g.key_start
        )

        print(
            f"[VALIDATE] {table}: "
            f"{len(ordered)} DataGroups"
        )

        for i in range(len(ordered) - 1):

            current = ordered[i]
            nxt = ordered[i + 1]

            if current.key_start >= current.key_end:
                raise ValueError(
                    f"Invalid range: {current.group_id}\n"
                    f"{current.key_start} -> {current.key_end}"
                )

            # This is deliberately lexical.
            if current.key_start >= nxt.key_start:
                raise ValueError(
                    f"Invalid DataGroup ordering:\n"
                    f"{current.group_id}\n"
                    f"{nxt.group_id}"
                )

        last = ordered[-1]

        if last.key_start >= last.key_end:
            raise ValueError(
                f"Invalid final range: {last.group_id}"
            )

        
# MATERIALIZATION
def materialize_table(
    table: str,
    groups: List,
):
    """
    Convert logical DataGroups into physical Regions.

    For N DataGroups we need N-1 internal boundaries.

    The first DataGroup does not require a split at its own
    start key. The initial Region already starts at the lower
    boundary of the table.

    Existing boundaries are skipped.
    """

    print()
    print("=" * 70)
    print(f"MATERIALIZING TABLE: {table}")
    print("=" * 70)

    groups = sorted(
        groups,
        key=lambda g: g.key_start
    )

    regions = get_regions(table)

    print(
        f"[REGION] Initial physical Regions: "
        f"{len(regions)}"
    )

    expected = len(groups)

    # Internal boundaries only.
    boundaries = [
        group.key_start
        for group in groups[1:]
    ]

    for boundary in boundaries:

        regions = get_regions(table)

        if boundary_already_exists(regions, boundary,):
            print(
                f"[SKIP] Boundary already exists: "
                f"{boundary}"
            )
            continue

        containing = find_region_containing_key(regions, boundary,)

        if containing is None:
            raise RuntimeError(
                f"Could not find a physical Region "
                f"containing boundary:\n"
                f"{boundary}\n"
                f"Table: {table}"
            )

        print(
            f"[SPLIT] Region:\n"
            f"  {containing.region_name}\n"
            f"  Server: {containing.server}\n"
            f"  Range: {containing.start_key} "
            f"-> {containing.end_key}\n"
        )

        split_region_at_key(table, boundary,)

    regions = get_regions(table)

    print()
    print(
        f"[RESULT] {table}: "
        f"{len(regions)} physical Regions"
    )

    if len(regions) != expected:
        raise RuntimeError(
            f"Materialization failed for {table}.\n"
            f"Expected: {expected}\n"
            f"Actual:   {len(regions)}"
        )

    print(
        f"[SUCCESS] {table}: "
        f"{expected} DataGroups = "
        f"{len(regions)} physical Regions"
    )

    return regions


# DATA GROUP → PHYSICAL REGION MAPPING
def map_datagroups_to_regions(
    groups,
    regions_by_table,
):
    """
    Map every DataGroup to its physical Region.

    The DataGroup start key determines which Region contains
    that DataGroup.
    """

    mapping = {}

    for group in groups:

        regions = regions_by_table[group.table]

        region = find_region_containing_key(regions, group.key_start,)

        if region is None:
            raise RuntimeError(
                f"No physical Region found for "
                f"{group.group_id}\n"
                f"Range: {group.key_start} "
                f"-> {group.key_end}"
            )

        mapping[group.group_id] = {
            "group_id": group.group_id,
            "table": group.table,
            "key_start": group.key_start,
            "key_end": group.key_end,
            "region_name": region.region_name,
            "encoded_region_name": region.encoded_name,
            "physical_start_key": region.start_key,
            "physical_end_key": region.end_key,
            "physical_size_mb": region.size_mb,
            "current_server": region.server,
        }

    return mapping


def save_mapping(mapping):
    with open(
        REGION_MAPPING_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            mapping,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"[MAPPING] Saved to "
        f"{REGION_MAPPING_FILE}"
    )


# REGION MIGRATION
def resolve_server(
    target_alias: str,
    regions: List[HBaseRegion],
) -> str:
    """
    Resolve slave1/slave2/slave3 to the CURRENT complete
    HBase ServerName including startcode.

    This avoids hard-coding an old RegionServer startcode.
    """

    prefix = SERVER_ALIASES.get(
        target_alias,
        target_alias,
    )

    candidates = [
        r.server
        for r in regions
        if r.server.startswith(
            prefix + ","
        )
    ]

    if candidates:
        return candidates[0]

    # If the target does not currently host a Region of this
    # table, discover it through the cluster status.
    status = run_hbase("status 'detailed'")

    pattern = re.compile(
        rf"^\s*{re.escape(prefix)}:16020\s+(\d+)",
        re.MULTILINE,
    )

    match = pattern.search(status)

    if match:
        startcode = match.group(1)

        return (
            f"{prefix},16020,{startcode}"
        )

    raise RuntimeError(
        f"Could not resolve target RegionServer "
        f"'{target_alias}'."
    )


def find_current_region(
    group,
):
    regions = get_regions(group.table)

    # Prefer encoded name if the group already knows it.
    encoded = getattr(
        group,
        "encoded_region_name",
        None,
    )

    if encoded:
        for region in regions:
            if region.encoded_name == encoded:
                return region

    # Otherwise map through key range.
    region = find_region_containing_key(regions, group.key_start,)

    if region is None:
        raise RuntimeError(
            f"Cannot resolve physical Region for "
            f"{group.group_id}"
        )

    return region


def move_region(group, target_server: str,
    timeout: int = DEFAULT_TIMEOUT,) -> MigrationResult:

    started = time.time()

    timestamp = datetime.now().isoformat()

    source_server = ""
    encoded = ""
    size_mb = 0.0

    try:
        # 1. Resolve REAL physical Region
        region = find_current_region(
            group
        )

        encoded = region.encoded_name
        source_server = region.server
        size_mb = region.size_mb

        print()
        print("-" * 70)
        print(f"[MOVE] {group.group_id}")
        print(f"  Region : {encoded}")
        print(f"  Source : {source_server}")
        print(f"  Size   : {size_mb:.2f} MB")
        # 2. Resolve exact target ServerName
        all_regions = get_regions(group.table)

        destination = resolve_server(
            target_server,
            all_regions,
        )

        print(f"  Target : {destination}")
        # 3. Don't move if already there
        if source_server.startswith(
            target_server + ","
        ):
            print(
                "[MOVE] Region is already on "
                f"{target_server}"
            )

            duration = time.time() - started

            return MigrationResult(
                timestamp=timestamp,
                group_id=group.group_id,
                table=group.table,
                encoded_region=encoded,
                source_server=source_server,
                target_server=destination,
                size_mb=size_mb,
                duration_seconds=duration,
                success=True,
            )
        # 4. Make sure cluster is stable BEFORE move
        wait_for_stable(timeout=timeout)
        # 5. Issue REAL HBase move
        command = (
            f"move '{encoded}', "
            f"'{destination}'"
        )

        print(f"[HBASE] {command}")

        run_hbase(
            command,
            timeout=timeout,
        )
        # 6. Wait for transition to finish
        print(
            "[WAIT] Waiting for Region "
            "transition to finish..."
        )

        wait_for_stable(timeout=timeout)
        # 7. Query HBase again
        final_region = None

        verification_start = time.time()

        while (
            time.time() - verification_start
            < timeout
        ):

            current_regions = get_regions(group.table)

            for r in current_regions:
                if r.encoded_name == encoded:
                    final_region = r
                    break

            if final_region is not None:
                break

            time.sleep(
                WAIT_INTERVAL
            )

        if final_region is None:
            raise RuntimeError(
                f"Region {encoded} disappeared "
                f"from the Region listing."
            )
        # 8. Verify physical location
        if final_region.server != destination:
            raise RuntimeError(
                "Physical migration verification failed.\n"
                f"Expected: {destination}\n"
                f"Actual:   {final_region.server}"
            )

        duration = time.time() - started

        print(f"[SUCCESS] {group.group_id}")
        print(
            f"  Region now on: "
            f"{final_region.server}"
        )
        print(f"  Duration: {duration:.2f} seconds")
        #
        # We return success first.
        # execute_migration_plan() updates the object only
        # after this function returns successfully.
        return MigrationResult(
            timestamp=timestamp,
            group_id=group.group_id,
            table=group.table,
            encoded_region=encoded,
            source_server=source_server,
            target_server=destination,
            size_mb=size_mb,
            duration_seconds=duration,
            success=True,
        )

    except Exception as exc:

        duration = time.time() - started

        print(
            f"[FAILED] {group.group_id}: "
            f"{exc}"
        )

        return MigrationResult(
            timestamp=timestamp,
            group_id=group.group_id,
            table=group.table,
            encoded_region=encoded,
            source_server=source_server,
            target_server=target_server,
            size_mb=size_mb,
            duration_seconds=duration,
            success=False,
            error=str(exc),
        )

    
# MIGRATION LOG
def save_migration_result(
    result: MigrationResult,
):

    file_exists = MIGRATION_LOG.exists()

    with open(
        MIGRATION_LOG,
        "a",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "group_id",
                "table",
                "encoded_region",
                "source_server",
                "target_server",
                "size_mb",
                "duration_seconds",
                "success",
                "error",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            asdict(result)
        )


# EXECUTE NSGA-II MIGRATION PLAN
def execute_migration_plan(
    plan,
    groups,
):
    """
    Execute the plan generated by NSGA-II.

    Expected plan:

        [
            {
                "group_id": "transactions_G6",
                "target_server": "slave2"
            },
            ...
        ]

    """

    group_by_id = {
        g.group_id: g
        for g in groups
    }

    results = []

    for action in plan:

        group_id = action["group_id"]
        target_server = action["target_server"]

        group = group_by_id.get(
            group_id
        )

        if group is None:
            print(
                f"[SKIP] Unknown group: "
                f"{group_id}"
            )
            continue

        result = move_region(group, target_server,)

        save_migration_result(
            result
        )

        results.append(
            result
        )
        #
        # HBase Region has been verified on the target.
        if result.success:

            group.current_server = (
                target_server
            )

            # Store physical information if the DataGroup
            # class allows dynamic attributes.
            group.encoded_region_name = (
                result.encoded_region
            )

            print(
                f"[STATE] {group_id} "
                f"current_server = "
                f"{target_server}"
            )

        else:

            print(
                f"[STATE] {group_id} "
                f"NOT updated because "
                f"physical migration failed."
            )

    return groups, results


# MATERIALIZE ALL 90 DATAGROUPS
def materialize_all_tables(groups):

    by_table: Dict[str, List] = {}

    for group in groups:
        by_table.setdefault(
            group.table,
            []
        ).append(group)

    regions_by_table = {}

    for table, table_groups in by_table.items():

        regions = materialize_table(
            table,
            table_groups,
        )

        regions_by_table[table] = regions

    mapping = map_datagroups_to_regions(
        groups,
        regions_by_table,
    )

    save_mapping(
        mapping
    )

    return regions_by_table, mapping



# MAIN
def main():

    print("=" * 70)
    print("PHYSICAL HBASE REGION MATERIALIZATION + MIGRATION")
    print("=" * 70)
    #
    from workload.workload_utils import (
        create_customer_groups,
        create_product_groups,
        create_transactions_groups,
        create_clickStream_groups,
    )

    groups = (
        create_customer_groups()
        + create_product_groups()
        + create_transactions_groups()
        + create_clickStream_groups()
    )

    print(f"[DATA] Loaded {len(groups)} DataGroups")

    # Expected:
    #
    # customer       = 10
    # product        = 10
    # transactions   = 30
    # click_stream   = 40
    #
    # total           = 90

    if len(groups) != 90:
        raise RuntimeError(
            f"Expected 90 DataGroups, "
            f"got {len(groups)}"
        )

    validate_datagroups(
        groups
    )

    previous_balancer_state = None

    try:
        # Disable automatic balancing
        previous_balancer_state = (
            disable_balancer()
        )
        # PHASE 1
        #
        # Materialize 90 logical DataGroups into physical
        # HBase Regions.
        regions_by_table, mapping = materialize_all_tables(groups)

        print()
        print("=" * 70)
        print("MATERIALIZATION COMPLETE")
        print("=" * 70)

        total_regions = sum(
            len(x)
            for x in regions_by_table.values()
        )

        print(
            f"Physical Regions: "
            f"{total_regions}"
        )
        #
        # experiment can be launched.
        print()
        print(
            "The 90 logical DataGroups are now mapped "
            "to physical HBase Regions."
        )

        print(
            f"Mapping saved to: "
            f"{REGION_MAPPING_FILE}"
        )

        print()
        print("You can now feed the mapping to NSGA-II.")

    finally:
        # is finished.
        #
        # disabled until the experiment is complete.
        if previous_balancer_state is not None:
            restore_balancer(
                previous_balancer_state
            )


if __name__ == "__main__":
    main()
