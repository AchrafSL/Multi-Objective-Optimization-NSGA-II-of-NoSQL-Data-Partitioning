#!/usr/bin/env python3

import subprocess
import sys
import time
from dataclasses import dataclass
from collections import Counter

from workload.workload_utils import (
    create_customer_groups,
    create_product_groups,
    create_transactions_groups,
    create_clickStream_groups,
)

TABLES = [
    "customer",
    "product",
    "transactions",
    "click_stream",
]

POLL_INTERVAL = 3
MAX_WAIT_SECONDS = 120

@dataclass
class HBaseRegion:
    table: str
    region_name: str
    encoded_name: str
    start_key: str
    end_key: str
    size_mb: float
    server: str

def run_hbase(command: str) -> str:
    """
    Execute a command through HBase shell.
    """

    result = subprocess.run(
        ["hbase", "shell", "-n"],
        input=command + "\n",
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print("\n[ERROR] HBase command failed:")
        print(command)
        print("\nSTDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)

        raise RuntimeError(
            f"HBase command failed: {command}"
        )

    return result.stdout

def clean(value: str) -> str:
    return value.strip()

def extract_encoded_region_name(region_name: str) -> str:
    """
    Extract the HBase encoded region name from:
        customer,,1789304327816.3c0eef92957c87c8ade16fd539105349.
    or:
        customer,18999,1789304449043.a746b51280d9cd3702abd8ff8bcd022e.
    """
    region_name = region_name.strip().rstrip(".")

    if "." not in region_name:
        raise ValueError(
            f"Cannot extract encoded region name from: {region_name}"
        )

    encoded = region_name.rsplit(".", 1)[1].strip()

    if not encoded:
        raise ValueError(
            f"Empty encoded region name extracted from: {region_name}"
        )

    return encoded

def parse_list_regions(output: str, table: str):

    regions = []

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("hbase:"):
            continue

        if (
            "REGION_NAME" in line
            and "SERVER_NAME" in line
        ):
            continue

        if set(
            line.replace("|", "").replace(" ", "")
        ) <= {"-"}:
            continue

        if "|" not in line:
            continue

        columns = [
            clean(x)
            for x in line.split("|")
        ]

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

        if not server or not region_name:
            continue

        if server == "SERVER_NAME":
            continue

        if region_name == "REGION_NAME":
            continue

        if not region_name.startswith(
            table + ","
        ):
            continue

        try:
            encoded_name = (
                extract_encoded_region_name(
                    region_name
                )
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

def get_regions(table: str):

    output = run_hbase(
        f"list_regions '{table}'"
    )

    regions = parse_list_regions(output, table)

    if not regions:
        raise RuntimeError(
            f"No physical Regions found for {table}"
        )

    return regions

def get_all_physical_regions():

    physical = {}

    print()
    print("=" * 70)
    print("READING PHYSICAL HBASE REGIONS")
    print("=" * 70)

    for table in TABLES:

        regions = get_regions(table)

        physical[table] = regions
        print(f"{table:<15} : {len(regions)} Regions")

    total = sum(len(regions) for regions in physical.values())

    print("-" * 70)
    print(f"TOTAL           : {total} Regions")

    if total != 90:
        raise RuntimeError(
            f"Expected 90 Regions, found {total}"
        )

    return physical

def get_logical_groups():

    groups = []

    groups.extend(create_customer_groups())
    groups.extend(create_product_groups())
    groups.extend(create_transactions_groups())
    groups.extend(create_clickStream_groups())

    return groups

def show_logical_distribution(groups):

    counts = Counter(group.current_server for group in groups)

    print()
    print("=" * 70)
    print("LOGICAL DISTRIBUTION")
    print("=" * 70)

    for server in [
        "slave1",
        "slave2",
        "slave3",
    ]:
        print(
            f"{server:<10}: {counts[server]} groups"
        )

    print("-" * 70)
    print(f"TOTAL     : {len(groups)} groups")

def build_mapping(groups, physical):

    mapping = []

    print()
    print("=" * 70)
    print("MATCHING LOGICAL GROUPS TO PHYSICAL REGIONS")
    print("=" * 70)

    for table in TABLES:

        table_groups = [g for g in groups if g.table == table]

        table_regions = physical[table]

        table_groups.sort(
            key=lambda g: g.key_start
        )

        table_regions.sort(
            key=lambda r: r.start_key
        )

        print()
        print(
            f"[{table}] "
            f"logical={len(table_groups)}, "
            f"physical={len(table_regions)}"
        )

        if len(table_groups) != len(table_regions):

            raise RuntimeError(
                f"\nCOUNT MISMATCH for {table}:\n"
                f"  Logical groups : {len(table_groups)}\n"
                f"  Physical Regions: {len(table_regions)}"
            )

        for group, region in zip(table_groups, table_regions):

            mapping.append(
                (group, region)
            )

            print(
                f"  {group.group_id:<22} "
                f"{region.start_key or '<EMPTY>':<40} "
                f"-> "
                f"{region.server.split(',')[0]}"
            )

    if len(mapping) != 90:
        raise RuntimeError(f"Expected 90 mappings, created {len(mapping)}")

    print()
    print(
        f"[SUCCESS] Successfully mapped "
        f"{len(mapping)} / 90 groups."
    )

    return mapping

def show_physical_distribution(
    mapping,
):

    counts = Counter()

    for group, region in mapping:

        server = region.server.split(",")[0]

        counts[server] += 1

    print()
    print("=" * 70)
    print("CURRENT PHYSICAL DISTRIBUTION")
    print("=" * 70)

    for server in [
        "slave1",
        "slave2",
        "slave3",
    ]:

        print(
            f"{server:<10}: "
            f"{counts[server]} Regions"
        )

def find_mismatches(mapping):

    mismatches = []

    for group, region in mapping:

        physical_server = region.server.split(",")[0]
        logical_server = group.current_server

        if physical_server != logical_server:

            mismatches.append(
                (
                    group,
                    region,
                )
            )

    return mismatches

def show_migration_plan(
    mismatches,
):

    print()
    print("=" * 100)
    print("PHYSICAL CORRECTION PLAN")
    print("=" * 100)

    if not mismatches:

        print(
            "[SUCCESS] "
            "Physical placement already matches logical placement."
        )

        return

    print(
        f"{'GROUP':<24}"
        f"{'TABLE':<16}"
        f"{'FROM':<10}"
        f"{'TO':<10}"
        f"{'SIZE(MB)':<12}"
        f"{'REGION':<35}"
    )

    print("-" * 110)

    for group, region in mismatches:

        source = region.server.split(",")[0]

        print(
            f"{group.group_id:<24}"
            f"{group.table:<16}"
            f"{source:<10}"
            f"{group.current_server:<10}"
            f"{region.size_mb:<12.2f}"
            f"{region.encoded_name:<35}"
        )

    print()
    print(
        f"Total physical moves required: "
        f"{len(mismatches)}"
    )

def get_live_servers(
    physical,
):

    servers = {}

    for table_regions in physical.values():
        for region in table_regions:

            hostname = region.server.split(",")[0]
            servers[hostname] = region.server

    return servers

def move_region(
    region,
    target_server,
):

    command = f"move '{region.encoded_name}', '{target_server}'"

    print()
    print(
        f"[MOVE] {region.encoded_name}"
    )

    print(
        f"       {region.server}"
        f" -> {target_server}"
    )

    output = run_hbase(command)
    print(output)

    return True

def wait_for_move(
    table,
    encoded_name,
    target_server,
):

    print(
        "[WAIT] Waiting for Region "
        "migration..."
    )

    start = time.time()

    while (
        time.time() - start
        < MAX_WAIT_SECONDS
    ):

        regions = get_regions(table)

        for region in regions:

            if (
                region.encoded_name
                == encoded_name
            ):

                current_server = (
                    region.server
                )

                print(
                    f"[CHECK] "
                    f"{current_server}"
                )

                if (
                    current_server
                    == target_server
                ):

                    print(
                        "[OK] Region verified "
                        "on target."
                    )

                    return True

                break

        time.sleep(POLL_INTERVAL)

    print(
        "[ERROR] Timeout waiting for "
        f"{encoded_name}"
    )

    return False

def verify_final_distribution(
    groups,
):

    print()
    print("=" * 70)
    print("FINAL VERIFICATION")
    print("=" * 70)

    physical = get_all_physical_regions()
    mapping = build_mapping(groups, physical)

    remaining = []

    counts = Counter()

    for group, region in mapping:

        physical_server = (
            region.server.split(",")[0]
        )

        counts[physical_server] += 1

        if (
            physical_server
            != group.current_server
        ):

            remaining.append(
                (
                    group.group_id,
                    physical_server,
                    group.current_server,
                )
            )

    print()
    print("Final physical distribution:")

    for server in [
        "slave1",
        "slave2",
        "slave3",
    ]:

        print(
            f"  {server}: "
            f"{counts[server]} Regions"
        )

    print()

    if remaining:

        print(
            "[FAILED] Remaining mismatches:"
        )

        for (
            group_id,
            physical_server,
            logical_server,
        ) in remaining:

            print(
                f"  {group_id}: "
                f"{physical_server} -> "
                f"{logical_server}"
            )

        return False

    print(
        "[SUCCESS] Every physical Region "
        "matches its logical DataGroup."
    )

    if all(
        counts[s] == 30
        for s in [
            "slave1",
            "slave2",
            "slave3",
        ]
    ):

        print(
            "[SUCCESS] Distribution is exactly "
            "30 / 30 / 30."
        )

    else:

        print(
            "[WARNING] Counts are not "
            "30 / 30 / 30."
        )

    return True

def main():

    execute = (
        "--execute"
        in sys.argv
    )

    print()
    print("=" * 70)
    print("HBASE INITIAL DISTRIBUTION CORRECTION")
    print("=" * 70)

    if execute:

        print(
            "MODE: EXECUTE"
        )

    else:

        print(
            "MODE: DRY RUN"
        )

        print(
            "No Regions will be moved."
        )

        print(
            "Use --execute to perform "
            "the correction."
        )

    # LOGICAL GROUPS

    groups = get_logical_groups()

    print()
    print(f"[INFO] Logical groups loaded: {len(groups)}")

    if len(groups) != 90:

        raise RuntimeError(
            f"Expected 90 logical groups, "
            f"found {len(groups)}"
        )

    show_logical_distribution(groups)

    # PHYSICAL REGIONS

    physical = get_all_physical_regions()

    # MATCH

    mapping = build_mapping(groups, physical)

    show_physical_distribution(mapping)

    # MISMATCHES

    mismatches = find_mismatches(mapping)
    show_migration_plan(mismatches)

    if not mismatches:

        print()
        print(
            "Nothing to correct."
        )

        return

    # DRY RUN

    if not execute:

        print()
        print("=" * 70)
        print("DRY RUN COMPLETE")
        print("=" * 70)

        print()
        print(
            "If the migration plan looks correct,"
        )

        print(
            "run:"
        )

        print()
        print(
            "python3 fix_initial_distribution.py "
            "--execute"
        )

        return

    # LIVE SERVERS

    servers = get_live_servers(physical)

    print()
    print("=" * 70)
    print("LIVE HBASE SERVERS")
    print("=" * 70)

    for hostname, server_name in sorted(
        servers.items()
    ):

        print(
            f"{hostname:<10} -> "
            f"{server_name}"
        )

    # EXECUTE MOVES

    successful = 0
    failed = 0

    print()
    print("=" * 70)
    print("STARTING PHYSICAL CORRECTION")
    print("=" * 70)

    for index, (
        group,
        region,
    ) in enumerate(
        mismatches,
        start=1,
    ):

        print()
        print(
            f"[{index}/{len(mismatches)}] "
            f"{group.group_id}"
        )

        target_server = servers.get(
            group.current_server
        )

        if target_server is None:

            print(
                f"[ERROR] Cannot find live "
                f"ServerName for "
                f"{group.current_server}"
            )

            failed += 1
            break

        try:

            move_region(region, target_server)

            verified = wait_for_move(group.table, region.encoded_name, target_server)

            if not verified:

                print(
                    "[STOP] Migration could "
                    "not be verified."
                )

                failed += 1
                break

            successful += 1

        except Exception as e:

            print()
            print(
                f"[ERROR] {group.group_id}: "
                f"{e}"
            )

            failed += 1

            print(
                "[STOP] Stopping to avoid "
                "an uncertain physical state."
            )

            break

    # FINAL CHECK

    print()
    print("=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)

    print(
        f"Successful moves : {successful}"
    )

    print(
        f"Failed moves     : {failed}"
    )

    success = verify_final_distribution(groups)

    print()

    if success:

        print("=" * 70)
        print(
            "SUCCESS: LOGICAL = PHYSICAL"
        )
        print("=" * 70)

    else:

        print("=" * 70)
        print(
            "WARNING: CORRECTION NOT COMPLETE"
        )
        print("=" * 70)

        sys.exit(1)

if __name__ == "__main__":
    main()
