"""
Simulate DataGroup migration between HBase servers.

The migration is logical only.
No physical HBase Region is moved.


we were debuging for 6h+ no solution so we changed our plan to logical simulation.
"""

def migrate_group(group, target_server):

    print(f"\nMigrating {group.group_id}: "
        f"{group.current_server} -> {target_server}"
    )

    group.current_server = target_server

    print(f"{group.group_id} successfully migrated.")

    return True



def execute_migration(plan, groups):

    for action in plan:

        group = None

        for item in groups:
            if item.group_id == action["group_id"]:
                group = item
                break

        if group is None:
            print(f"Group {action['group_id']} not found.")
            continue

        target_server = action["target_server"]

        if group.current_server == target_server:
            continue

        success = migrate_group(group, target_server)

        if not success:
            print(f"Migration failed for {group.group_id}")

    return groups