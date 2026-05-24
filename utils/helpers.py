"""
Utilities — logger, input validators, Rich terminal helpers
"""

import os
import re
import logging
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

# ── Logger setup ──────────────────────────────────────────────────────────────

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True),
        logging.FileHandler(os.path.join(LOGS_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")),
    ],
)
logger = logging.getLogger("route_optimizer")


def log_info(msg: str):
    logger.info(msg)


def log_error(msg: str):
    logger.error(msg)


def log_warn(msg: str):
    logger.warning(msg)


# ── Validators ────────────────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$", email))


def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^[\d\s\+\-\(\)]{7,20}$", phone)) if phone else True


def validate_coords(lat, lon) -> bool:
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
    except (TypeError, ValueError):
        return False


def sanitize_string(s: str, max_len: int = 255) -> str:
    """Strip dangerous characters, trim to max length."""
    s = re.sub(r"[<>\"'%;()&+]", "", s)
    return s[:max_len].strip()


# ── Rich terminal display helpers ─────────────────────────────────────────────

def print_banner():
    console.print(Panel.fit(
        "[bold cyan]🚚 Last-Mile Delivery Route Optimizer[/bold cyan]\n"
        "[dim]MCA Final Year Project — Genetic Algorithm TSP Solver[/dim]",
        border_style="cyan",
    ))


def print_run_summary(result, run_id: int):
    table = Table(title=f"Optimization Result — Run #{run_id}", border_style="cyan")
    table.add_column("Parameter", style="dim")
    table.add_column("Value", style="bold cyan")
    table.add_row("Best Distance", f"{result.best_distance:.4f} km")
    table.add_row("Improvement", f"{result.improvement_pct:.2f}%")
    table.add_row("Generations", str(result.generations_completed))
    table.add_row("Converged At", f"Gen {result.converged_at}")
    table.add_row("Execution Time", f"{result.execution_time:.3f} sec")
    console.print(table)


def print_delivery_table(deliveries):
    table = Table(title="Delivery Records", border_style="cyan", show_lines=True)
    table.add_column("ID", style="dim", width=12)
    table.add_column("Customer", width=20)
    table.add_column("Address", width=40)
    table.add_column("Geocoded", width=10)
    for d in deliveries:
        geo = "[green]✓[/green]" if d.is_geocoded else "[yellow]…[/yellow]"
        table.add_row(d.delivery_id, d.customer_name, d.address[:40], geo)
    console.print(table)
