import numpy as np

"""
    Calculer les metriques 
"""


def workload_imbalance(chromosome, groups):
    """
    Calculate workload imbalance after applying the migration plan.
    """

    server_load = {
        "slave1": 0,
        "slave2": 0,
        "slave3": 0
    }

    for group in groups:

        server = group.current_server

        for group_id, target_server in chromosome:

            if group.group_id == group_id:
                server = target_server
                break

        server_load[server] += group.request_count

    values = list(server_load.values())

    if np.sum(values) == 0:
        return 0

    return np.std(values) / np.mean(values)











def migration_cost(chromosome, groups):
    """
    Calculate the total amount of data that will be migrated.
    """

    total_cost = 0

    for group_id, target_server in chromosome:

        for group in groups:

            if group.group_id == group_id:

                if group.current_server != target_server:
                    total_cost += group.size

                break

    return total_cost












def evaluate_chromosome(chromosome, groups):
    """
    Evaluate one migration plan.
    """

    return {
        "migration_cost": migration_cost(chromosome, groups),
        "workload_imbalance": workload_imbalance(chromosome, groups)
    }