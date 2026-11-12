import random
import numpy as np

random.seed(40)
np.random.seed(40)

from strategies.cost_efficient import cost_efficient
from strategies.balanced import balanced
from strategies.performance import performance

from strategies.strategy_utils import load_execution, update_group_stats

from nsga2.nsga2 import run_nsga2
from nsga2.decision import choose_solution
from nsga2.representation import chromosome_to_plan

from migration.save_plan import save_migration_plan


def run(groups, servers, workload_type):

    print("\n" + "=" * 60)
    print(f" {workload_type.upper()} WORKLOAD")
    print("=" * 60)

    print("\nInitial distribution:")

    for server in servers:
        count = sum(1 for group in groups if group.current_server == server)
        print(f"{server}: {count}")

    print("\nInitial workload:")

    for server in servers:
        workload = sum(group.request_count for group in groups if group.current_server == server)
        print(f"{server}: {workload}")

    print("\n1. Generate strategy plans:")

    cost_plan = cost_efficient(groups.copy())
    balanced_plan = balanced(groups.copy())
    performance_plan = performance(groups.copy())

    plans = [cost_plan, balanced_plan, performance_plan]

    print(f"Generated {len(plans)} plans.")

    print("\n2. Run NSGA-II:")

    pareto_front = run_nsga2(
        groups,
        plans,
        servers,
        population_size=10,
        generations=10,
        mutation_rate=0.1
    )

    print(f"Pareto solutions: {len(pareto_front)}")

    print("\nPareto front:")

    for i, solution in enumerate(pareto_front, 1):
        print(
            f"{i}. "
            f"Migration cost = "
            f"{solution['score']['migration_cost']}, "
            f"Workload imbalance = "
            f"{solution['score']['workload_imbalance']}"
        )

    print("\n3. Choose solution:")

    solution = choose_solution(pareto_front)

    if solution is None:
        print("No solution found.")
        return groups

    print("Selected solution:")
    print(solution["score"])

    chromosome = solution["chromosome"]

    plan = chromosome_to_plan(chromosome, groups)

    print("\n4. Migration plan:")
    print(f"{len(plan)} migrations")

    if not plan:
        print("No migration required.")
        return groups

    for action in plan:
        print(
            f"{action['group_id']} : "
            f"{action['current_server']} -> "
            f"{action['target_server']}"
        )

    print("\n5. Save migration plan:")

    output_file = save_migration_plan(plan, solution, workload_type)

    print("[SUCCESS] Plan saved to:")
    print(f"          {output_file}")

    print("\n6. Physical migration:")
    print("NOT EXECUTED.")
    print("The plan will be executed separately by the")
    print("physical HBase migration executor.")

    print("\nResults:")

    print(f"Migrations: {len(plan)}")

    print(
        f"Migration cost: "
        f"{solution['score']['migration_cost']}"
    )

    print(
        f"Workload imbalance: "
        f"{solution['score']['workload_imbalance']}"
    )

    return groups


if __name__ == "__main__":

    from workload.workload_utils import (
        create_customer_groups,
        create_clickStream_groups,
        create_product_groups,
        create_transactions_groups
    )

    servers = ["slave1", "slave2", "slave3"]

    groups = (
        create_transactions_groups()
        + create_product_groups()
        + create_clickStream_groups()
        + create_customer_groups()
    )

    requests = load_execution("workload/workloadOutput/normal_execution.csv")

    groups = update_group_stats(groups, requests)

    run(groups, servers, "normal")

    groups = (
        create_transactions_groups()
        + create_product_groups()
        + create_clickStream_groups()
        + create_customer_groups()
    )

    requests = load_execution("workload/workloadOutput/skewed_execution.csv")

    groups = update_group_stats(groups, requests)

    run(groups, servers, "skewed")
