"""
Last-Mile Delivery Route Optimizer
MCA Final Year Major Project

Entry point: python main.py
"""

import sys
import os
import warnings

# Suppress requests/urllib3 version mismatch warning — cosmetic only, doesn't affect functionality
warnings.filterwarnings("ignore", category=Warning, module="requests")
warnings.filterwarnings("ignore", message=".*urllib3.*")
warnings.filterwarnings("ignore", message=".*chardet.*")
warnings.filterwarnings("ignore", message=".*charset_normalizer.*")

# ── Add project root to path ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.helpers import print_banner, log_info, log_error
from models import init_engine


def bootstrap():
    """Initialize database and seed demo account."""
    log_info("Initializing database…")
    init_engine()

    # Create demo account if not exists
    from services.auth_service import register
    from models import get_session
    from models.models import User
    session = get_session()
    try:
        if not session.query(User).filter_by(username="admin").first():
            ok, msg = register("admin", "admin@routeopt.local", "admin123", "Administrator")
            if ok:
                log_info("Demo account created: admin / admin123")
    finally:
        session.close()


def main():
    print_banner()
    bootstrap()

    # ── Handle CLI mode (headless) ──
    if "--cli" in sys.argv:
        _run_cli()
        return

    # ── GUI mode ──
    log_info("Starting GUI…")
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    from gui.main_app import _launch_login
    _launch_login()


def _run_cli():
    """Minimal CLI mode for testing without display."""
    from rich.console import Console
    from rich.prompt import Prompt
    console = Console()

    console.print("\n[cyan]CLI Mode — Route Optimizer[/cyan]")
    console.print("Commands: list, add, geocode, optimize, history, exit\n")

    while True:
        cmd = Prompt.ask("[cyan]>[/cyan]").strip().lower()

        if cmd == "exit":
            break
        elif cmd == "list":
            from services.delivery_service import get_all_deliveries
            from utils.helpers import print_delivery_table
            deliveries = get_all_deliveries()
            if deliveries:
                print_delivery_table(deliveries)
            else:
                console.print("[yellow]No deliveries found.[/yellow]")
        elif cmd == "add":
            name = Prompt.ask("Customer name")
            addr = Prompt.ask("Address")
            contact = Prompt.ask("Contact", default="")
            from services.delivery_service import add_delivery
            ok, msg, d = add_delivery(name, addr, contact)
            console.print(f"[{'green' if ok else 'red'}]{msg}[/]")
        elif cmd == "geocode":
            from services.geocoding import geocode_all_pending
            console.print("[cyan]Geocoding pending addresses…[/cyan]")
            s, f = geocode_all_pending()
            console.print(f"[green]Done: {s} success, {f} failed[/green]")
        elif cmd == "optimize":
            from services.delivery_service import get_all_deliveries
            from algorithms.genetic_algorithm import GAConfig
            from services.optimization_service import run_optimization
            deliveries = get_all_deliveries(geocoded_only=True)
            if len(deliveries) < 2:
                console.print("[yellow]Need at least 2 geocoded deliveries.[/yellow]")
                continue
            ids = [d.delivery_id for d in deliveries]
            config = GAConfig(population_size=50, num_generations=200)
            console.print(f"[cyan]Running GA on {len(ids)} stops…[/cyan]")
            run_id = run_optimization(ids, config, run_name="CLI Run")
            console.print(f"[green]✔ Completed — Run ID: {run_id}[/green]")
        elif cmd == "history":
            from services.optimization_service import get_optimization_history
            from utils.helpers import print_run_summary
            runs = get_optimization_history(limit=5)
            for r in runs:
                console.print(f"  Run #{r.id} | {r.run_name} | {r.best_distance_km:.2f} km | {r.num_deliveries} stops")
        else:
            console.print("[yellow]Unknown command. Try: list, add, geocode, optimize, history, exit[/yellow]")


if __name__ == "__main__":
    main()
