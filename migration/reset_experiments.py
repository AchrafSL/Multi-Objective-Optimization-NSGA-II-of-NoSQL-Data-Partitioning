#!/usr/bin/env python3

import subprocess
import sys
import time

# CONFIGURATION
POLL_INTERVAL = 3
MAX_WAIT_SECONDS = 120

# HBASE
def run_hbase(command):
    """Execute an HBase shell command."""

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

# REGION PARSING
def extract_encoded_region_name(region_name):
    """Extract encoded HBase Region ID."""

    region_name = region_name.strip().rstrip(".")

    if "." not in region_name:
        raise ValueError(
            f"Cannot extract encoded Region name: "
            f"{region_name}"
        )

    encoded = region_name.rsplit(".", 1)[1].strip()

    if not encoded:
        raise ValueError(
            f"Empty encoded Region name: "
            f"{region_name}"
        )

    return encoded


def parse_regions(output, table):

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
            x.strip()
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

        if not region_name.startswith(table + ","):
            continue

        try:
            encoded_name = extract_encoded_region_name(region_name)
        except ValueError:
            continue

        try:
            size_mb = float(size)
        except ValueError:
            size_mb = 0.0

        regions.append({
            "table": table,
            "region_name": region_name,
            "encoded_name": encoded_name,
            "start_key": start_key,
            "end_key": end_key,
            "size_mb": size_mb,
            "server": server,
        })

    return regions


# GET REGIONS
def get_regions(table):

    output = run_hbase(f"list_regions \'{table}\'")

    regions = parse_regions(output, table)

    if not regions:
        raise RuntimeError(
            f"No Regions found for table '{table}'"
        )

    return regions


# FIND PHYSICAL REGION
def get_group_region(group_id, table):
    """
    The 90 physical Regions were already materialized
    in the same order as the DataGroups.

    Therefore:
        G1 -> Region 1
        G2 -> Region 2
        ...
    """

    prefix = table + "_G"

    if not group_id.startswith(prefix):
        raise ValueError(
            f"Invalid group ID: {group_id}"
        )

    group_number = int(
        group_id.split("_G")[1]
    )

    regions = get_regions(table)

    regions.sort(
        key=lambda r: r["start_key"]
    )

    index = group_number - 1

    if index < 0 or index >= len(regions):
        raise RuntimeError(
            f"Cannot find Region for {group_id}"
        )

    return regions[index]


# GET LIVE SERVER NAMES
def get_live_servers():

    servers = {}

    for table in [
        "customer",
        "product",
        "transactions",
        "click_stream",
    ]:

        regions = get_regions(table)

        for region in regions:

            server_name = region["server"]

            hostname = server_name.split(",", 1)[0]

            servers[hostname] = server_name

    return servers


# WAIT FOR MOVE
def wait_for_move(table, encoded_region, target_server):

    print(
        "[WAIT] Waiting for Region migration..."
    )

    start = time.time()

    while time.time() - start < MAX_WAIT_SECONDS:

        regions = get_regions(table)

        for region in regions:

            if region["encoded_name"] == encoded_region:

                print(
                    f"[CHECK] {region['server']}"
                )

                if region["server"] == target_server:

                    print(
                        "[OK] Region verified on target."
                    )

                    return True

                break

        time.sleep(POLL_INTERVAL)

    return False


# MOVE ONE GROUP BACK
def reset_group(group_id, table, source, target, live_servers):

    region = get_group_region(group_id, table)

    encoded = region["encoded_name"]
    current_server = region["server"]

    print()
    print("=" * 70)
    print(f"RESET: {group_id}")
    print("=" * 70)

    print(f"Region : {encoded}")
    print(f"Size   : {region['size_mb']} MB")
    print(f"Current: {current_server}")
    print(f"Target : {target}")

    # Already reset
    if current_server.startswith(target + ","):

        print(
            "[SKIP] Region is already on "
            f"{target}."
        )

        return True

    # Safety check
    if not current_server.startswith(source + ","):

        raise RuntimeError(
            f"Unexpected physical server for "
            f"{group_id}.\n"
            f"Expected: {source}\n"
            f"Actual: {current_server}"
        )

    target_server = live_servers.get(target)

    if target_server is None:

        raise RuntimeError(
            f"Could not find live ServerName "
            f"for {target}"
        )

    print()
    print(
        f"[MOVE] {encoded}"
    )

    print(
        f"       {current_server}"
    )

    print(
        f"       -> {target_server}"
    )

    run_hbase(f"move \'{encoded}\', \'{target_server}\'")

    verified = wait_for_move(table, encoded, target_server)

    if not verified:

        raise RuntimeError(
            f"Could not verify reset of "
            f"{group_id}"
        )

    print(
        f"[SUCCESS] {group_id} "
        f"reset to {target}"
    )

    return True


# NORMAL RESET
def reset_after_normal(live_servers):

    print()
    print("=" * 80)
    print("RESET AFTER NORMAL EXPERIMENT")
    print("=" * 80)

    # Reverse the Normal NSGA-II plan
    moves = [
        ("transactions_G6", "transactions"),
        ("customer_G7", "customer"),
        ("transactions_G7", "transactions"),
        ("transactions_G9", "transactions"),
        ("transactions_G8", "transactions"),
        ("customer_G10", "customer"),
    ]

    execute_reset(
        moves,
        live_servers
    )


# SKEWED RESET
def reset_after_skewed(live_servers):

    print()
    print("=" * 80)
    print("RESET AFTER SKEWED EXPERIMENT")
    print("=" * 80)

    # Reverse the Skewed NSGA-II plan
    moves = [
        ("transactions_G2", "transactions"),
        ("transactions_G3", "transactions"),
        ("transactions_G4", "transactions"),
        ("transactions_G7", "transactions"),
        ("transactions_G8", "transactions"),
        ("customer_G2", "customer"),
    ]

    execute_reset(
        moves,
        live_servers
    )


# EXECUTE RESET
def execute_reset(
    moves,
    live_servers,
):

    successful = 0

    for index, (
        group_id,
        table,
    ) in enumerate(
        moves,
        start=1,
    ):

        print()
        print(
            f"[{index}/{len(moves)}]"
        )

        try:

            reset_group(
                group_id,
                table,
                "slave1",
                "slave3",
                live_servers,
            )

            successful += 1

        except Exception as e:

            print()
            print(
                f"[ERROR] {group_id}"
            )

            print(e)

            print()
            print(
                "[STOP] Reset stopped."
            )

            sys.exit(1)

    print()
    print("=" * 80)
    print("RESET SUMMARY")
    print("=" * 80)

    print(
        f"Successful resets: "
        f"{successful}/{len(moves)}"
    )

    verify_distribution()


# VERIFY 30 / 30 / 30
def verify_distribution():

    counts = {
        "slave1": 0,
        "slave2": 0,
        "slave3": 0,
    }

    for table in [
        "customer",
        "product",
        "transactions",
        "click_stream",
    ]:

        regions = get_regions(table)

        for region in regions:

            server = (
                region["server"]
                .split(",", 1)[0]
            )

            if server in counts:
                counts[server] += 1

    print()
    print("=" * 80)
    print("FINAL APPLICATION REGION DISTRIBUTION")
    print("=" * 80)

    print(
        f"slave1 : {counts['slave1']} Regions"
    )

    print(
        f"slave2 : {counts['slave2']} Regions"
    )

    print(
        f"slave3 : {counts['slave3']} Regions"
    )

    if counts == {
        "slave1": 30,
        "slave2": 30,
        "slave3": 30,
    }:

        print()
        print(
            "[SUCCESS] Initial state restored."
        )

        print(
            "[SUCCESS] Distribution = 30 / 30 / 30"
        )

        return True

    print()
    print(
        "[FAILED] Distribution is NOT "
        "30 / 30 / 30."
    )

    return False


# MAIN
def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "  python3 -m migration.reset_experiment normal"
        )

        print(
            "  python3 -m migration.reset_experiment skewed"
        )

        sys.exit(1)

    experiment = sys.argv[1].lower()

    print()
    print("=" * 80)
    print("HBASE EXPERIMENT RESET")
    print("=" * 80)

    print(
        f"Experiment: {experiment}"
    )

    print()
    print(
        "This will physically move the Regions "
        "back to the initial state."
    )
    # Discover live servers
    print()
    print(
        "[INFO] Discovering live HBase servers..."
    )

    live_servers = get_live_servers()

    for hostname, server in sorted(
        live_servers.items()
    ):

        print(
            f"  {hostname} -> {server}"
        )
    # Reset
    if experiment == "normal":

        reset_after_normal(
            live_servers
        )

    elif experiment == "skewed":

        reset_after_skewed(
            live_servers
        )

    else:

        print(
            f"[ERROR] Unknown experiment: "
            f"{experiment}"
        )

        print(
            "Use 'normal' or 'skewed'."
        )

        sys.exit(1)

        
# ENTRY POINT
if __name__ == "__main__":
    """
        Usage: python3 -m migration.reset_experiment normal
        python3 -m migration.reset_experiment skewed
    """
    main()