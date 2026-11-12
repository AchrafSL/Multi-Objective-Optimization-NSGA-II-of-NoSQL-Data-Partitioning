from strategies.balanced import balanced
from strategies.cost_efficient import cost_efficient
from strategies.performance import performance

from nsga2.representation import plan_to_chromosome



def generate_population(plans):
    population = []

    for plan in plans:
        chromosome = plan_to_chromosome(plan)
        population.append(chromosome)

    return population


"""

if __name__ == '__main__':

    cost_plan = cost_efficient(groups)
    balanced_plan = balanced(groups)
    performance_plan = performance(groups)

    plans = [cost_plan, balanced_plan,performance_plan]

    population  = generate_population()

"""