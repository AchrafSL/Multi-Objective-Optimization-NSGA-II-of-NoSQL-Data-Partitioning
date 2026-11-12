def normalize(value, minimum, maximum):

    if maximum == minimum:
        return 0

    return (value - minimum) / (maximum - minimum)


def choose_solution(pareto_front):

    costs = []
    imbalances = []

    for solution in pareto_front:
        costs.append(solution["score"]["migration_cost"])
        imbalances.append(
            solution["score"]["workload_imbalance"]
        )

    min_cost = min(costs)
    max_cost = max(costs)

    min_imbalance = min(imbalances)
    max_imbalance = max(imbalances)

    best_solution = None
    best_score = float("inf")

    for solution in pareto_front:

        cost = solution["score"]["migration_cost"]
        imbalance = solution["score"]["workload_imbalance"]

        cost_score = normalize(
            cost,
            min_cost,
            max_cost
        )

        imbalance_score = normalize(
            imbalance,
            min_imbalance,
            max_imbalance
        )

        score = (
            0.5 * cost_score
            + 0.5 * imbalance_score
        )

        if score < best_score:
            best_score = score
            best_solution = solution

    return best_solution