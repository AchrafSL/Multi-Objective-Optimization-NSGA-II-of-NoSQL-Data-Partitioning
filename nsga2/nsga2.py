import random

from nsga2.population import generate_population
from nsga2.evaluation import evaluate_chromosome
from nsga2.genetic import crossover, mutate
from nsga2.nsga import non_dominated_sort, crowding_distance


def run_nsga2(
    groups,
    plans,
    servers,
    population_size=10,
    generations=10,
    mutation_rate=0.1
):

    population = generate_population(plans)

    while len(population) < population_size:

        parent = random.choice(population)

        child = mutate(
            parent,
            servers,
            mutation_rate
        )

        population.append(child)

    for generation in range(generations):

        # Evaluate population
        scores = []

        for chromosome in population:

            score = evaluate_chromosome(
                chromosome,
                groups
            )

            scores.append(score)

        # Create children
        children = []

        while len(children) < population_size:

            parent1 = random.choice(population)
            parent2 = random.choice(population)

            child = crossover(
                parent1,
                parent2
            )

            child = mutate(
                child,
                servers,
                mutation_rate
            )

            children.append(child)

        # Combine parents and children
        combined_population = population + children

        combined_scores = []

        for chromosome in combined_population:

            score = evaluate_chromosome(
                chromosome,
                groups
            )

            combined_scores.append(score)

        # Non-dominated sorting
        fronts = non_dominated_sort(
            combined_population,
            combined_scores
        )

        # Select next generation
        new_population = []

        for front in fronts:

            if len(new_population) + len(front) <= population_size:

                for index in front:
                    new_population.append(
                        combined_population[index]
                    )

            else:

                distances = crowding_distance(
                    front,
                    combined_scores
                )

                sorted_front = sorted(
                    front,
                    key=lambda index: distances[index],
                    reverse=True
                )

                remaining = (
                    population_size
                    - len(new_population)
                )

                for index in sorted_front[:remaining]:
                    new_population.append(
                        combined_population[index]
                    )

                break

        population = new_population

        print(
            f"Generation {generation + 1}/{generations}"
        )

    # Final evaluation
    final_scores = []

    for chromosome in population:

        score = evaluate_chromosome(
            chromosome,
            groups
        )

        final_scores.append(score)

    final_fronts = non_dominated_sort(
        population,
        final_scores
    )

    pareto_front = []

    for index in final_fronts[0]:

        pareto_front.append({
            "chromosome": population[index],
            "score": final_scores[index]
        })

    return pareto_front