"""
Low cost Strategy:
    Ignore groups with low activity.
    Look for overloaded servers.
    Move only an active group from an overloaded server.
    Prefer the smallest active group to reduce migration cost.
    Don't move a group if it doesn't actually improve the load situation.
"""

from strategies.strategy_utils import calc_75_percentile

def cost_efficient(groups):
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

    # Find the most and least loaded servers
    most_loaded = max(server_load, key=server_load.get)
    least_loaded = min(server_load, key=server_load.get)

    # Calculate 75th percentile of request count
    threshold = calc_75_percentile(groups)

    plan = []

    # Current load difference
    load_difference = server_load[most_loaded] - server_load[least_loaded]

    # Consider active groups on the most loaded server
    for group in groups:

        if group.current_server == most_loaded and group.request_count >= threshold:

            # Check if moving this group improves the load difference
            new_difference = abs((server_load[most_loaded] - group.request_count) - (server_load[least_loaded] + group.request_count))

            if new_difference < load_difference:
                plan.append({
                    "group_id": group.group_id,
                    "table": group.table,
                    "current_server": group.current_server,
                    "target_server": least_loaded,
                    "migration_cost": group.size
                })

    # Move cheaper groups first
    plan.sort(key=lambda item: item["migration_cost"])

    return plan









