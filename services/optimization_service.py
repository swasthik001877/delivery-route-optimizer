"""
Optimization Service — orchestrates GA execution and result persistence
"""

import threading
import json
from datetime import datetime
from typing import List, Optional, Callable
from rich.console import Console
from models import get_session, OptimizationRun, OptimizedRoute, Delivery
from algorithms.genetic_algorithm import GAConfig, GAResult, run_genetic_algorithm
from services.delivery_service import get_all_deliveries

console = Console()


def run_optimization(
    delivery_ids: List[str],
    config: GAConfig,
    run_name: str = None,
    user_id: int = None,
    progress_callback: Optional[Callable] = None,
    completion_callback: Optional[Callable] = None,
    stop_event: Optional[threading.Event] = None,
) -> int:
    """
    Execute a full optimization run in a background thread.
    Persists the run + route sequence to the database.

    Returns:
        run_id of the created OptimizationRun record (0 on failure)
    """

    # ── Fetch deliveries ──
    session = get_session()
    try:
        deliveries = session.query(Delivery).filter(
            Delivery.delivery_id.in_(delivery_ids),
            Delivery.is_geocoded == True,
            Delivery.is_active == True,
        ).all()
        session.expunge_all()
    finally:
        session.close()

    if len(deliveries) < 2:
        console.print("[red]✗ Need at least 2 geocoded deliveries.[/red]")
        if completion_callback:
            completion_callback(None, "Need at least 2 geocoded deliveries.")
        return 0

    coords = [(d.latitude, d.longitude) for d in deliveries]

    # ── Create run record ──
    session = get_session()
    try:
        run = OptimizationRun(
            run_name=run_name or f"Run {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            user_id=user_id,
            num_deliveries=len(deliveries),
            population_size=config.population_size,
            mutation_rate=config.mutation_rate,
            crossover_rate=config.crossover_rate,
            num_generations=config.num_generations,
            status="running",
        )
        run.set_delivery_ids([d.delivery_id for d in deliveries])
        session.add(run)
        session.commit()
        run_id = run.id
    except Exception as e:
        session.rollback()
        console.print(f"[red]Failed to create run record: {e}[/red]")
        return 0
    finally:
        session.close()

    # ── Execute GA ──
    try:
        result: GAResult = run_genetic_algorithm(
            coords=coords,
            config=config,
            progress_callback=progress_callback,
            stop_event=stop_event,
        )
    except Exception as e:
        _mark_run_failed(run_id, str(e))
        if completion_callback:
            completion_callback(None, str(e))
        return run_id

    # ── Persist results ──
    session = get_session()
    try:
        run = session.query(OptimizationRun).get(run_id)
        run.best_distance_km = result.best_distance
        run.execution_time_sec = result.execution_time
        run.generations_completed = result.generations_completed
        run.converged_at_generation = result.converged_at
        run.set_fitness_history(result.fitness_history)
        run.status = "completed"

        # Delete previous routes for this run (re-run case)
        session.query(OptimizedRoute).filter_by(run_id=run_id).delete()

        prev_dist = 0.0
        for order, city_idx in enumerate(result.best_route):
            d = deliveries[city_idx]
            if order > 0:
                prev_city_idx = result.best_route[order - 1]
                pd = deliveries[prev_city_idx]
                from algorithms.genetic_algorithm import haversine
                dist_from_prev = haversine(pd.latitude, pd.longitude, d.latitude, d.longitude)
            else:
                dist_from_prev = 0.0

            route_entry = OptimizedRoute(
                run_id=run_id,
                stop_order=order,
                delivery_id=d.delivery_id,
                customer_name=d.customer_name,
                address=d.address,
                latitude=d.latitude,
                longitude=d.longitude,
                distance_from_prev_km=dist_from_prev,
            )
            session.add(route_entry)

        session.commit()
        console.print(f"[green]✔ Run {run_id} saved to database.[/green]")
    except Exception as e:
        session.rollback()
        _mark_run_failed(run_id, str(e))
        console.print(f"[red]Failed to save results: {e}[/red]")
    finally:
        session.close()

    if completion_callback:
        completion_callback(result, None)

    return run_id


def run_optimization_threaded(
    delivery_ids: List[str],
    config: GAConfig,
    run_name: str = None,
    user_id: int = None,
    progress_callback: Optional[Callable] = None,
    completion_callback: Optional[Callable] = None,
) -> threading.Event:
    """
    Launch optimization in a daemon thread. Returns a stop_event you can set to abort.
    """
    stop_event = threading.Event()

    def _worker():
        run_optimization(
            delivery_ids=delivery_ids,
            config=config,
            run_name=run_name,
            user_id=user_id,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            stop_event=stop_event,
        )

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return stop_event


def _mark_run_failed(run_id: int, error: str):
    session = get_session()
    try:
        run = session.query(OptimizationRun).get(run_id)
        if run:
            run.status = "failed"
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def get_optimization_history(user_id: int = None, limit: int = 50) -> List[OptimizationRun]:
    session = get_session()
    try:
        q = session.query(OptimizationRun).filter_by(status="completed")
        if user_id:
            q = q.filter_by(user_id=user_id)
        runs = q.order_by(OptimizationRun.created_at.desc()).limit(limit).all()
        session.expunge_all()
        return runs
    finally:
        session.close()


def get_run_routes(run_id: int) -> List[OptimizedRoute]:
    session = get_session()
    try:
        routes = session.query(OptimizedRoute).filter_by(run_id=run_id).order_by(OptimizedRoute.stop_order).all()
        session.expunge_all()
        return routes
    finally:
        session.close()


def delete_run(run_id: int) -> bool:
    session = get_session()
    try:
        run = session.query(OptimizationRun).get(run_id)
        if run:
            session.delete(run)
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()
