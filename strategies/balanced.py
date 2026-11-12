"""
Balanced Strategy:
    Distribute request load more evenly between servers.
    Ignore groups with low activity.
    Move active groups from overloaded servers.
    Continue moving groups while the balance improves.
"""

from strategies.strategy_utils import calc_75_percentile

def balanced(groups):
    """
        input: all groups
        output: migration plan
    """

    server_load = {
        "slave1": 0,
        "slave2": 0,
        "slave3": 0
    }

    # Calculate request load for each server
    for group in groups:
        server_load[group.current_server] += group.request_count

    threshold = calc_75_percentile(groups)
    plan = []

    while True:

        most_loaded = max(server_load, key=server_load.get)
        least_loaded = min(server_load, key=server_load.get)

        current_difference = (server_load[most_loaded] - server_load[least_loaded])

        best_group = None
        best_difference = current_difference

        # Find the group that improves the balance the most
        for group in groups:

            if group.current_server != most_loaded:
                continue

            if group.request_count < threshold:
                continue

            new_difference = abs((server_load[most_loaded] - group.request_count) - (server_load[least_loaded] + group.request_count))

            if new_difference < best_difference:
                best_difference = new_difference
                best_group = group

        # Stop if no group can improve the balance
        if best_group is None:
            break

        plan.append({
            "group_id": best_group.group_id,
            "table": best_group.table,
            "current_server": best_group.current_server,
            "target_server": least_loaded,
            "migration_cost": best_group.size
        })

        # Simulate the migration
        server_load[most_loaded] -= best_group.request_count
        server_load[least_loaded] += best_group.request_count

        # Remove the group so it cannot be selected again
        groups.remove(best_group)

    return plan