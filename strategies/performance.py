"""
Performance Strategy:
    Identify groups with high latency and high hotness.
    Prioritize them using a weighted score.
    Move selected groups from the most loaded server to the least loaded server.

    In each loop:
        Update the most and least loaded servers.
        Find a hot group with high latency on the most loaded server.
        Add the group to the migration plan.
        Simulate the migration and repeat.
"""


def performance(groups):
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

    latency_threshold = calc_75_percentile_latency(groups)
    hotness_threshold = calc_75_percentile_hotness(groups)

    max_latency = max(group.average_latency for group in groups)
    max_hotness = max(group.hotness for group in groups)

    plan = []

    while True:

        most_loaded = max(server_load, key=server_load.get)
        least_loaded = min(server_load, key=server_load.get)

        best_group = None
        best_score = 0

        # Find a hot group with high latency
        for group in groups:

            if group.current_server != most_loaded:
                continue

            if group.average_latency < latency_threshold:
                continue

            if group.hotness < hotness_threshold:
                continue

            latency_score = group.average_latency / max_latency
            hotness_score = group.hotness / max_hotness

            score = 0.6 * latency_score + 0.4 * hotness_score

            if score > best_score:
                best_score = score
                best_group = group

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

        # Remove the group so it is not selected again
        groups.remove(best_group)

    return plan






def calc_75_percentile_latency(groups):
    values = []

    for group in groups:
        values.append(group.average_latency)

    values.sort()

    index = int(len(values) * 0.75) - 1

    return values[index]


def calc_75_percentile_hotness(groups):
    values = []

    for group in groups:
        values.append(group.hotness)

    values.sort()

    index = int(len(values) * 0.75) - 1

    return values[index]