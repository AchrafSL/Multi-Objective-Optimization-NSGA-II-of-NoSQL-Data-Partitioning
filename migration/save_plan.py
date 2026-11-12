import json
import os


def save_migration_plan(plan, solution, workload_type):
    """
    Save the migration plan selected by NSGA-II.
    """

    os.makedirs("migration/plans", exist_ok=True)

    output_file = (
        f"migration/plans/{workload_type}_migration_plan.json"
    )

    data = {
        "workload": workload_type,
        "migration_count": len(plan),

        "score": {
            "migration_cost": solution["score"]["migration_cost"],
            "workload_imbalance": solution["score"]["workload_imbalance"]
        },

        "migrations": plan
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)

    print(f"\n[SAVED] Migration plan:")
    print(f"        {output_file}")

    return output_file