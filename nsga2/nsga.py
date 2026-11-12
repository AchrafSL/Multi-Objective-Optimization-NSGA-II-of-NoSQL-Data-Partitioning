def dominates(score_a, score_b):
    """
    Check if solution A dominates solution B.

    All objectives are minimized.  min cost and min workload imbalance
    """

    better_or_equal = True
    strictly_better = False

    for objective in score_a:

        if score_a[objective] > score_b[objective]:
            better_or_equal = False

        if score_a[objective] < score_b[objective]:
            strictly_better = True

    return better_or_equal and strictly_better





def non_dominated_sort(population, scores):

    fronts = [[]]

    domination_count = {}
    dominated_solutions = {}

    for i in range(len(population)):

        domination_count[i] = 0
        dominated_solutions[i] = []

        for j in range(len(population)):

            if i == j:
                continue

            if dominates(scores[i], scores[j]):

                dominated_solutions[i].append(j)

            elif dominates(scores[j], scores[i]):

                domination_count[i] += 1

        if domination_count[i] == 0:
            fronts[0].append(i)

    current_front = 0

    while current_front < len(fronts):

        next_front = []

        for i in fronts[current_front]:

            for j in dominated_solutions[i]:

                domination_count[j] -= 1

                if domination_count[j] == 0:
                    next_front.append(j)

        if next_front:
            fronts.append(next_front)

        current_front += 1

    return fronts











def crowding_distance(front, scores):

    distance = {}

    for index in front:
        distance[index] = 0

    if len(front) <= 2:
        for index in front:
            distance[index] = float("inf")

        return distance

    objectives = list(scores[front[0]].keys())

    for objective in objectives:

        sorted_front = sorted(
            front,
            key=lambda index: scores[index][objective]
        )

        first = sorted_front[0]
        last = sorted_front[-1]

        distance[first] = float("inf")
        distance[last] = float("inf")

        minimum = scores[first][objective]
        maximum = scores[last][objective]

        if maximum == minimum:
            continue

        for i in range(1, len(sorted_front) - 1):

            previous = sorted_front[i - 1]
            current = sorted_front[i]
            next = sorted_front[i + 1]

            distance[current] += (
                scores[next][objective]
                - scores[previous][objective]
            ) / (maximum - minimum)

    return distance











def select_population(population, scores, population_size):

    fronts = non_dominated_sort(
        population,
        scores
    )

    selected = []

    for front in fronts:

        # We can take the whole front
        if len(selected) + len(front) <= population_size:

            for index in front:
                selected.append(population[index])

        # We cannot take the whole front
        else:

            distances = crowding_distance(
                front,
                scores
            )

            sorted_front = sorted(
                front,
                key=lambda index: distances[index],
                reverse=True
            )

            remaining = population_size - len(selected)

            for index in sorted_front[:remaining]:
                selected.append(population[index])

            break

    return selected