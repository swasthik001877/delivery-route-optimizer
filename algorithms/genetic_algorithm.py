"""
Genetic Algorithm Engine for TSP Route Optimization
Complete implementation from scratch — no optimization libraries used.

Implements:
  - Random population initialization
  - Fitness evaluation (minimize total Haversine distance)
  - Tournament selection
  - Ordered Crossover (OX)
  - Swap mutation + 2-opt mutation
  - Elitism
  - Stagnation detection
"""

import random
import time
import math
import numpy as np
from typing import List, Tuple, Callable, Optional
from dataclasses import dataclass, field
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

console = Console()


# ─── Data structures ───────────────────────────────────────────────────────────

@dataclass
class GAConfig:
    population_size: int = 100
    mutation_rate: float = 0.02
    crossover_rate: float = 0.85
    num_generations: int = 500
    elitism_count: int = 5          # top N always survive
    tournament_size: int = 5
    stagnation_limit: int = 80      # stop if no improvement for N gens
    two_opt_frequency: int = 50     # apply 2-opt every N generations


@dataclass
class GAResult:
    best_route: List[int] = field(default_factory=list)
    best_distance: float = float("inf")
    fitness_history: List[float] = field(default_factory=list)
    generation_history: List[float] = field(default_factory=list)
    execution_time: float = 0.0
    generations_completed: int = 0
    converged_at: int = 0
    improvement_pct: float = 0.0


# ─── Haversine distance ────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two GPS points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ─── Distance Matrix ──────────────────────────────────────────────────────────

def build_distance_matrix(coords: List[Tuple[float, float]]) -> np.ndarray:
    """
    Build a symmetric NxN distance matrix from a list of (lat, lon) tuples.
    Uses Haversine formula for geodesic accuracy.
    """
    n = len(coords)
    matrix = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


# ─── Route evaluation ─────────────────────────────────────────────────────────

def route_distance(route: List[int], dist_matrix: np.ndarray) -> float:
    """Total round-trip distance for a given route (returns to start)."""
    total = 0.0
    n = len(route)
    for i in range(n):
        total += dist_matrix[route[i]][route[(i + 1) % n]]
    return total


def fitness(route: List[int], dist_matrix: np.ndarray) -> float:
    """Fitness = 1 / total_distance  (higher is better)."""
    d = route_distance(route, dist_matrix)
    return 1.0 / d if d > 0 else float("inf")


# ─── Population initialization ────────────────────────────────────────────────

def init_population(n_cities: int, pop_size: int) -> List[List[int]]:
    """Generate a list of random permutations as initial population."""
    base = list(range(n_cities))
    population = []
    for _ in range(pop_size):
        individual = base[:]
        random.shuffle(individual)
        population.append(individual)
    return population


# ─── Selection ────────────────────────────────────────────────────────────────

def tournament_selection(
    population: List[List[int]],
    fitnesses: List[float],
    tournament_size: int,
) -> List[int]:
    """Select one individual via tournament selection."""
    contestants = random.sample(range(len(population)), min(tournament_size, len(population)))
    winner = max(contestants, key=lambda i: fitnesses[i])
    return population[winner][:]


# ─── Crossover ────────────────────────────────────────────────────────────────

def ordered_crossover(parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
    """
    Ordered Crossover (OX):
    Preserves relative order of genes from both parents.
    """
    n = len(parent1)
    a, b = sorted(random.sample(range(n), 2))

    def _ox(p1, p2):
        child = [None] * n
        child[a:b] = p1[a:b]
        fill = [x for x in p2 if x not in child[a:b]]
        idx = 0
        for i in list(range(b, n)) + list(range(0, a)):
            child[i] = fill[idx]
            idx += 1
        return child

    return _ox(parent1, parent2), _ox(parent2, parent1)


# ─── Mutation ─────────────────────────────────────────────────────────────────

def swap_mutation(route: List[int], mutation_rate: float) -> List[int]:
    """Randomly swap two genes based on mutation_rate."""
    route = route[:]
    for i in range(len(route)):
        if random.random() < mutation_rate:
            j = random.randint(0, len(route) - 1)
            route[i], route[j] = route[j], route[i]
    return route


def two_opt_improvement(route: List[int], dist_matrix: np.ndarray, max_iter: int = 200) -> List[int]:
    """
    2-opt local search improvement.
    Repeatedly reverses sub-segments when doing so reduces total distance.
    """
    best = route[:]
    best_dist = route_distance(best, dist_matrix)
    improved = True
    iteration = 0
    while improved and iteration < max_iter:
        improved = False
        iteration += 1
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                new_route = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                new_dist = route_distance(new_route, dist_matrix)
                if new_dist < best_dist - 1e-10:
                    best = new_route
                    best_dist = new_dist
                    improved = True
    return best


# ─── Main Genetic Algorithm ───────────────────────────────────────────────────

def run_genetic_algorithm(
    coords: List[Tuple[float, float]],
    config: GAConfig,
    progress_callback: Optional[Callable[[int, float, float], None]] = None,
    stop_event=None,
) -> GAResult:
    """
    Execute the complete Genetic Algorithm for TSP.

    Args:
        coords: List of (lat, lon) tuples for each delivery
        config: GAConfig parameters
        progress_callback: fn(generation, best_distance, best_fitness) — called each generation
        stop_event: threading.Event — set to abort early

    Returns:
        GAResult with best route indices, distances, and history
    """
    n_cities = len(coords)
    if n_cities < 2:
        raise ValueError("Need at least 2 delivery locations.")

    start_time = time.time()

    console.print(f"[cyan]► Building {n_cities}×{n_cities} distance matrix…[/cyan]")
    dist_matrix = build_distance_matrix(coords)

    console.print(f"[cyan]► Initialising population (size={config.population_size})…[/cyan]")
    population = init_population(n_cities, config.population_size)

    fitness_history: List[float] = []
    distance_history: List[float] = []

    best_route: List[int] = []
    best_distance: float = float("inf")
    stagnation_counter: int = 0
    converged_at: int = 0
    initial_distance: float = float("inf")

    console.print(f"[green]► Starting GA: {config.num_generations} generations[/green]")

    for generation in range(config.num_generations):
        # Allow external abort
        if stop_event and stop_event.is_set():
            console.print("[yellow]⚠ Optimisation aborted by user.[/yellow]")
            break

        # ── Evaluate fitness ──
        fitnesses = [fitness(ind, dist_matrix) for ind in population]
        distances = [route_distance(ind, dist_matrix) for ind in population]

        # ── Track best ──
        gen_best_idx = int(np.argmax(fitnesses))
        gen_best_distance = distances[gen_best_idx]

        if generation == 0:
            initial_distance = gen_best_distance

        if gen_best_distance < best_distance:
            best_distance = gen_best_distance
            best_route = population[gen_best_idx][:]
            stagnation_counter = 0
            converged_at = generation
        else:
            stagnation_counter += 1

        fitness_history.append(fitnesses[gen_best_idx])
        distance_history.append(best_distance)

        # ── Progress callback ──
        if progress_callback:
            progress_callback(generation, best_distance, fitnesses[gen_best_idx])

        # ── Stagnation check ──
        if stagnation_counter >= config.stagnation_limit:
            console.print(f"[yellow]✓ Converged at generation {generation} (stagnation limit)[/yellow]")
            converged_at = generation
            break

        # ── Elitism: carry top N directly ──
        sorted_pairs = sorted(zip(fitnesses, population), key=lambda x: x[0], reverse=True)
        elites = [ind[:] for _, ind in sorted_pairs[: config.elitism_count]]

        # ── Build next generation ──
        next_population = elites[:]
        while len(next_population) < config.population_size:
            p1 = tournament_selection(population, fitnesses, config.tournament_size)
            p2 = tournament_selection(population, fitnesses, config.tournament_size)

            if random.random() < config.crossover_rate:
                c1, c2 = ordered_crossover(p1, p2)
            else:
                c1, c2 = p1[:], p2[:]

            c1 = swap_mutation(c1, config.mutation_rate)
            c2 = swap_mutation(c2, config.mutation_rate)

            next_population.append(c1)
            if len(next_population) < config.population_size:
                next_population.append(c2)

        population = next_population

        # ── Periodic 2-opt on best individual ──
        if generation > 0 and generation % config.two_opt_frequency == 0:
            improved = two_opt_improvement(best_route, dist_matrix, max_iter=100)
            imp_dist = route_distance(improved, dist_matrix)
            if imp_dist < best_distance:
                best_distance = imp_dist
                best_route = improved
                population[0] = improved[:]
                console.print(f"  [magenta]2-opt improved → {best_distance:.2f} km[/magenta]")

    # ── Final 2-opt polish ──
    console.print("[cyan]► Final 2-opt pass…[/cyan]")
    best_route = two_opt_improvement(best_route, dist_matrix, max_iter=500)
    best_distance = route_distance(best_route, dist_matrix)

    exec_time = time.time() - start_time
    improvement_pct = ((initial_distance - best_distance) / initial_distance * 100) if initial_distance > 0 else 0

    console.print(f"[bold green]✔ Optimisation complete![/bold green]")
    console.print(f"  Best distance : [bold]{best_distance:.3f} km[/bold]")
    console.print(f"  Improvement   : [bold]{improvement_pct:.1f}%[/bold]")
    console.print(f"  Time elapsed  : [bold]{exec_time:.2f}s[/bold]")

    return GAResult(
        best_route=best_route,
        best_distance=best_distance,
        fitness_history=fitness_history,
        generation_history=distance_history,
        execution_time=exec_time,
        generations_completed=len(fitness_history),
        converged_at=converged_at,
        improvement_pct=improvement_pct,
    )
