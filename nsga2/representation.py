"""
    Convert strategies plans to chromosome format:
    Group -> ServerTarget
"""


def plan_to_chromosome(plan):
    chromosome = []

    for action in plan:
        chromosome.append( (action["group_id"], action["target_server"]) )

    return chromosome




def chromosome_to_plan(chromosome, groups):

    plan = []

    for group_id, target_server in chromosome:

        for group in groups:

            if group.group_id == group_id:

                if group.current_server != target_server:

                    plan.append({
                        "group_id": group.group_id,
                        "table": group.table,
                        "current_server": group.current_server,
                        "target_server": target_server,
                        "migration_cost": group.size
                    })

                break

    return plan