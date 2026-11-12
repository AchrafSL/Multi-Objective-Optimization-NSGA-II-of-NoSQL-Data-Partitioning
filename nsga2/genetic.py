import random


def crossover(parent1, parent2):
    """
    Create a new migration plan from two parent plans.
    """

    child = {}

    for migration in parent1:

        group_id = migration[0]
        target_server = migration[1]

        if random.random() < 0.5:
            child[group_id] = target_server

    for migration in parent2:

        group_id = migration[0]
        target_server = migration[1]

        if group_id not in child:
            child[group_id] = target_server

    return list(child.items())




def mutate(chromosome, servers, mutation_rate):
    """
    Randomly change the target server of a migration.
    """

    child = list(chromosome)

    for i in range(len(child)):

        if random.random() < mutation_rate:

            group_id, current_server = child[i]

            new_server = random.choice(servers)

            while new_server == current_server:
                new_server = random.choice(servers)

            child[i] = (group_id, new_server)

    return child