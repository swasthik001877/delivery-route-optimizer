"""
Unit Tests — Genetic Algorithm, distance functions, delivery service, auth
Run with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import math
from algorithms.genetic_algorithm import (
    haversine, route_distance, build_distance_matrix,
    init_population, ordered_crossover, swap_mutation,
    two_opt_improvement, run_genetic_algorithm, GAConfig, GAResult
)


# ── Haversine tests ────────────────────────────────────────────────────────────

def test_haversine_same_point():
    d = haversine(12.9716, 77.5946, 12.9716, 77.5946)
    assert d == 0.0


def test_haversine_known_distance():
    # Bengaluru to Chennai ≈ 280 km
    d = haversine(12.9716, 77.5946, 13.0827, 80.2707)
    assert 270 < d < 300, f"Expected ~280 km, got {d:.1f}"


def test_haversine_symmetry():
    d1 = haversine(12.9716, 77.5946, 19.0760, 72.8777)
    d2 = haversine(19.0760, 72.8777, 12.9716, 77.5946)
    assert abs(d1 - d2) < 0.001


# ── Distance matrix tests ──────────────────────────────────────────────────────

def test_distance_matrix_shape():
    coords = [(12.9, 77.5), (13.0, 77.6), (12.8, 77.7)]
    mat = build_distance_matrix(coords)
    assert mat.shape == (3, 3)


def test_distance_matrix_diagonal_zero():
    import numpy as np
    coords = [(12.9, 77.5), (13.0, 77.6), (12.8, 77.7)]
    mat = build_distance_matrix(coords)
    for i in range(3):
        assert mat[i][i] == 0.0


def test_distance_matrix_symmetry():
    import numpy as np
    coords = [(12.9, 77.5), (13.0, 77.6), (12.8, 77.7)]
    mat = build_distance_matrix(coords)
    assert np.allclose(mat, mat.T)


# ── Population tests ───────────────────────────────────────────────────────────

def test_init_population_size():
    pop = init_population(5, 20)
    assert len(pop) == 20


def test_init_population_valid_permutations():
    pop = init_population(6, 10)
    for ind in pop:
        assert sorted(ind) == list(range(6))


# ── Crossover tests ────────────────────────────────────────────────────────────

def test_ordered_crossover_valid():
    p1 = [0, 1, 2, 3, 4, 5]
    p2 = [5, 4, 3, 2, 1, 0]
    c1, c2 = ordered_crossover(p1, p2)
    assert sorted(c1) == list(range(6))
    assert sorted(c2) == list(range(6))


def test_ordered_crossover_no_duplicates():
    import random
    random.seed(42)
    for _ in range(20):
        p1 = list(range(10))
        p2 = list(range(10))
        random.shuffle(p1)
        random.shuffle(p2)
        c1, c2 = ordered_crossover(p1, p2)
        assert len(set(c1)) == 10
        assert len(set(c2)) == 10


# ── Mutation tests ─────────────────────────────────────────────────────────────

def test_swap_mutation_preserves_genes():
    route = list(range(10))
    mutated = swap_mutation(route, mutation_rate=1.0)
    assert sorted(mutated) == list(range(10))


def test_swap_mutation_zero_rate():
    route = [0, 1, 2, 3, 4]
    mutated = swap_mutation(route, mutation_rate=0.0)
    assert mutated == route


# ── Route distance tests ───────────────────────────────────────────────────────

def test_route_distance_returns_positive():
    import numpy as np
    coords = [(12.9, 77.5), (13.0, 77.6), (12.8, 77.7), (13.1, 77.4)]
    mat = build_distance_matrix(coords)
    d = route_distance([0, 1, 2, 3], mat)
    assert d > 0


def test_two_opt_improves_or_maintains():
    import numpy as np
    coords = [(12.9, 77.5), (13.0, 77.6), (12.8, 77.7), (13.1, 77.4), (12.7, 77.3)]
    mat = build_distance_matrix(coords)
    route = [0, 1, 2, 3, 4]
    original_dist = route_distance(route, mat)
    improved_route = two_opt_improvement(route, mat)
    improved_dist = route_distance(improved_route, mat)
    assert improved_dist <= original_dist + 0.001


# ── Full GA integration test ───────────────────────────────────────────────────

def test_ga_small_instance():
    coords = [
        (12.9716, 77.5946),
        (13.0827, 80.2707),
        (19.0760, 72.8777),
        (28.6139, 77.2090),
        (22.5726, 88.3639),
    ]
    config = GAConfig(
        population_size=20,
        num_generations=30,
        mutation_rate=0.05,
        crossover_rate=0.8,
        stagnation_limit=10,
    )
    result = run_genetic_algorithm(coords, config)
    assert isinstance(result, GAResult)
    assert result.best_distance > 0
    assert len(result.best_route) == len(coords)
    assert sorted(result.best_route) == list(range(len(coords)))
    assert result.execution_time > 0
    assert len(result.fitness_history) > 0


def test_ga_returns_valid_route_indices():
    import random
    random.seed(0)
    n = 8
    import numpy as np
    coords = [(12 + i * 0.1, 77 + i * 0.1) for i in range(n)]
    config = GAConfig(population_size=15, num_generations=20, stagnation_limit=5)
    result = run_genetic_algorithm(coords, config)
    assert set(result.best_route) == set(range(n))


# ── Auth service tests ─────────────────────────────────────────────────────────

def test_registration_and_login():
    from models import init_engine
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_engine(db_path)
        from services.auth_service import register, login
        ok, msg = register("testuser", "test@test.com", "password123", "Test User")
        assert ok, msg

        ok2, msg2, uid = login("testuser", "password123")
        assert ok2, msg2
        assert uid is not None

        ok3, msg3, _ = login("testuser", "wrongpassword")
        assert not ok3
    finally:
        os.unlink(db_path)


# ── Delivery service tests ─────────────────────────────────────────────────────

def test_add_and_search_delivery():
    from models import init_engine
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_engine(db_path)
        from services.delivery_service import add_delivery, search_deliveries
        ok, msg, d = add_delivery("John Doe", "123 Main St, Bengaluru", "+91 9000000001")
        assert ok, msg
        assert d is not None

        results = search_deliveries("John")
        assert any(r.customer_name == "John Doe" for r in results)
    finally:
        os.unlink(db_path)


def test_duplicate_address_rejected():
    from models import init_engine
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_engine(db_path)
        from services.delivery_service import add_delivery
        add_delivery("Alice", "Same Address, City", "+91 9000000002")
        ok, msg, _ = add_delivery("Bob", "Same Address, City", "+91 9000000003")
        assert not ok
    finally:
        os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
