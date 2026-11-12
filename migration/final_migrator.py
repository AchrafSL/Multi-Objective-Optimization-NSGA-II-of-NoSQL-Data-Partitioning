
import json
import os
import subprocess
import sys
import time
from collections import Counter


TABLES = [
    "customer",
    "product",
    "transactions",
    "click_stream",
]

POLL_INTERVAL = 3
MAX_WAIT_SECONDS = 120


def run_hbase(command):
    """
    Execute one HBase shell command.
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


def extract_encoded_region_name(region_name):
    """
    Extract encoded Region ID.

    Example:
        transactions,,1789304327816.cd4747b3df30bd903671ce078425706d.
    """

    region_name = region_name.strip().rstrip(".")

    if "." not in region_name:

        raise ValueError(f"Cannot extract encoded Region name: {region_name}")

    encoded = region_name.rsplit(".", 1)[1].strip()

    if not encoded:

        raise ValueError(f"Empty encoded Region name: {region_name}")

    return encoded


def parse_regions(output, table):
    """
    Parse HBase list_regions output.
    """

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
            line.replace("|", "")
            .replace(" ", "")
        ) <= {"-"}:
            continue

        if "|" not in line:
            continue

        columns = [x.strip() for x in line.split("|")]

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

            encoded = extract_encoded_region_name(region_name)

        except ValueError:

            continue

        try:

            size_mb = float(size)

        except ValueError:

            size_mb = 0.0

        regions.append({
            "table": table,
            "region_name": region_name,
            "encoded_name": encoded,
            "start_key": start_key,
            "end_key": end_key,
            "size_mb": size_mb,
            "server": server,
        })

    return regions


def get_regions(table):

    output = run_hbase(
        f"list_regions '{table}'"
    )

    regions = parse_regions(
        output,
        table
    )

    if not regions:

        raise RuntimeError(f"No physical Regions found for table '{table}'")

    return regions


def get_group_region(group_id, table):
    """
    Find the physical Region corresponding
    to a DataGroup.

    The project has frozen the physical Region
    boundaries so that the Regions correspond
    positionally to the DataGroups.
    """

    prefix = table + "_G"

    if not group_id.startswith(prefix):

        raise ValueError(
            f"Invalid group ID '{group_id}' "
            f"for table '{table}'"
        )

    try:

        group_number = int(group_id.split("_G")[1])

    except Exception:

        raise ValueError(
            f"Invalid group ID: {group_id}"
        )

    regions = get_regions(table)

    regions.sort(
        key=lambda r: r["start_key"]
    )

    index = group_number - 1

    if (
        index < 0
        or index >= len(regions)
    ):

        raise RuntimeError(f"Cannot find physical Region for {group_id}")

    return regions[index]


def get_live_servers():
    """
    Discover the exact HBase ServerName
    including port and startcode.
    """

    servers = {}

    for table in TABLES:

        regions = get_regions(table)

        for region in regions:

            server_name = region["server"]

            hostname = server_name.split(",", 1)[0]

            servers[hostname] = server_name

    return servers


def wait_for_move(
    table,
    encoded_region,
    target_server,
):
    """
    Wait until the Region is physically
    hosted by target_server.
    """

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
                region["encoded_name"]
                == encoded_region
            ):

                current_server = region["server"]

                print(
                    f"[CHECK] "
                    f"{current_server}"
                )

                if current_server == target_server:

                    print(
                        "[OK] Region verified "
                        "on target."
                    )

                    return True

                break

        time.sleep(POLL_INTERVAL)

    return False


def load_plan(plan_file):

    if not os.path.exists(plan_file):

        raise FileNotFoundError(f"Migration plan not found: {plan_file}")

    with open(plan_file, "r") as f:

        data = json.load(f)

    if "migrations" not in data:

        raise ValueError("Invalid migration plan: 'migrations' field missing.")

    return data


def show_plan(plan):

    print()
    print("=" * 80)
    print("NSGA-II MIGRATION PLAN")
    print("=" * 80)

    print(f"Workload          : {plan.get('workload')}")

    print(f"Migration count   : {plan.get('migration_count')}")

    print(f"Migration cost    : {plan['score']['migration_cost']}")

    print(f"Workload imbalance: {plan['score']['workload_imbalance']}")

    print()
    print(
        f"{'GROUP':<25}"
        f"{'TABLE':<18}"
        f"{'FROM':<10}"
        f"{'TO':<10}"
        f"{'COST':<15}"
    )

    print("-" * 80)

    for migration in plan["migrations"]:

        print(f"{migration['group_id']:<25}{migration['table']:<18}{migration['current_server']:<10}{migration['target_server']:<10}{migration['migration_cost']:<15}")


def execute_migration(
    migration,
    live_servers,
):
    """
    Execute one physical HBase Region move.
    """

    group_id = migration["group_id"]
    table = migration["table"]

    expected_source = (
        migration["current_server"]
    )

    target = (
        migration["target_server"]
    )


    region = get_group_region(
        group_id,
        table
    )

    encoded = region["encoded_name"]

    actual_source = region["server"].split(",", 1)[0]

    print()
    print("=" * 80)
    print(
        f"MIGRATION: {group_id}"
    )
    print("=" * 80)

    print(f"Table          : {table}")

    print(f"Region         : {encoded}")

    print(f"Region size    : {region['size_mb']} MB")

    print(f"Plan source    : {expected_source}")

    print(f"Physical source: {actual_source}")

    print(f"Target         : {target}")


    if actual_source == target:

        print(
            "[SKIP] Region is already "
            "on target."
        )

        return True


    if actual_source != expected_source:

        raise RuntimeError(f"Source mismatch for {group_id}.\nPlan says: {expected_source}\nHBase says: {actual_source}")


    target_server = live_servers.get(target)

    if target_server is None:

        raise RuntimeError(f"Cannot find live HBase ServerName for {target}")

    print()
    print(
        f"[MOVE] {encoded}"
    )

    print(
        f"       {region['server']}"
    )

    print(
        f"       -> {target_server}"
    )


    command = (
        f"move '{encoded}', "
        f"'{target_server}'"
    )

    run_hbase(command)


    verified = wait_for_move(table, encoded, target_server)

    if not verified:

        raise RuntimeError(f"Could not verify migration of {group_id}")

    print()
    print(f"[SUCCESS] {group_id} physically migrated.")

    return True


def get_distribution():

    counts = Counter()

    total = 0

    for table in TABLES:

        regions = get_regions(table)

        for region in regions:

            server = region["server"].split(",", 1)[0]

            counts[server] += 1
            total += 1

    return counts, total


def show_final_distribution():

    counts, total = get_distribution()

    print()
    print("=" * 80)
    print("FINAL PHYSICAL DISTRIBUTION")
    print("=" * 80)

    print(f"Application Regions: {total}")

    print(f"slave1: {counts['slave1']}")

    print(f"slave2: {counts['slave2']}")

    print(f"slave3: {counts['slave3']}")

    return counts


def main():

    if len(sys.argv) != 2:

        print()
        print(
            "Usage:"
        )

        print(
            "python3 -m migration.final_migrator "
            "migration/plans/normal_migration_plan.json"
        )

        print(
            "python3 -m migration.final_migrator "
            "migration/plans/skewed_migration_plan.json"
        )

        sys.exit(1)

    plan_file = sys.argv[1]


    plan = load_plan(plan_file)

    show_plan(plan)

    migrations = plan["migrations"]

    if not migrations:

        print()
        print(
            "[INFO] No physical migration "
            "is required."
        )

        return


    print()
    print("=" * 80)
    print("READING CURRENT HBASE STATE")
    print("=" * 80)

    before_counts, before_total = get_distribution()

    print(
        f"Application Regions: "
        f"{before_total}"
    )

    print(
        f"slave1: "
        f"{before_counts['slave1']}"
    )

    print(
        f"slave2: "
        f"{before_counts['slave2']}"
    )

    print(
        f"slave3: "
        f"{before_counts['slave3']}"
    )

    if before_total != 90:

        raise RuntimeError(f"Expected 90 application Regions, found {before_total}")


    live_servers = get_live_servers()

    print()
    print("=" * 80)
    print("LIVE HBASE SERVERS")
    print("=" * 80)

    for hostname, server in sorted(
        live_servers.items()
    ):

        print(
            f"{hostname:<10} -> {server}"
        )


    successful = 0
    failed = 0
    migrated_mb = 0.0

    start_time = time.time()

    print()
    print("=" * 80)
    print("STARTING PHYSICAL MIGRATION")
    print("=" * 80)

    for index, migration in enumerate(
        migrations,
        start=1
    ):

        print()
        print(
            f"[{index}/{len(migrations)}]"
        )

        try:

            region = get_group_region(migration["group_id"], migration["table"])

            size_mb = region["size_mb"]

            execute_migration(migration, live_servers)

            successful += 1
            migrated_mb += size_mb

        except Exception as e:

            failed += 1

            print()
            print(
                f"[ERROR] Migration failed:"
            )

            print(e)

            print()
            print(
                "[STOP] Migration stopped "
                "to protect physical state."
            )

            break

    elapsed = (
        time.time()
        - start_time
    )


    final_counts = (
        show_final_distribution()
    )


    print()
    print("=" * 80)
    print("PHYSICAL MIGRATION SUMMARY")
    print("=" * 80)

    print(f"Workload          : {plan.get('workload')}")

    print(f"Planned migrations: {len(migrations)}")

    print(f"Successful moves  : {successful}")

    print(f"Failed moves      : {failed}")

    print(f"Migrated data     : {migrated_mb:.2f} MB")

    print(f"Execution time    : {elapsed:.2f} seconds")

    print()
    print("Final distribution:")

    print(f"  slave1: {final_counts['slave1']}")

    print(f"  slave2: {final_counts['slave2']}")

    print(f"  slave3: {final_counts['slave3']}")

    if (
        failed == 0
        and successful == len(migrations)
    ):

        print()
        print(
            "=" * 80
        )

        print(
            "[SUCCESS] ALL NSGA-II MIGRATIONS "
            "WERE PHYSICALLY EXECUTED."
        )

        print(
            "=" * 80
        )

    else:

        print()
        print(
            "[WARNING] Migration plan "
            "was not fully executed."
        )

        sys.exit(1)


if __name__ == "__main__":
    main