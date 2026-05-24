"""
Analytics — simple, clean Matplotlib charts embedded in Tkinter.
All charts use integer/float data properly typed to avoid categorical warnings.
"""

import os
from typing import List
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.figure import Figure
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    FigureCanvasTkAgg = None
from models import OptimizationRun

# ── Theme ──────────────────────────────────────────────────────────────────────
BG      = "#0d0d1a"
PANEL   = "#12122a"
ACCENT  = "#00D4FF"
RED     = "#FF6B6B"
GREEN   = "#4CFFAB"
YELLOW  = "#FFB347"
PURPLE  = "#7B61FF"
TEXT    = "#e0e0e0"
GRID    = "#2a2a4a"

plt.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    PANEL,
    "axes.edgecolor":    GRID,
    "axes.labelcolor":   TEXT,
    "axes.titlecolor":   TEXT,
    "axes.titlesize":    13,
    "axes.labelsize":    11,
    "xtick.color":       TEXT,
    "ytick.color":       TEXT,
    "xtick.labelsize":   10,
    "ytick.labelsize":   10,
    "grid.color":        GRID,
    "grid.linewidth":    0.5,
    "text.color":        TEXT,
    "lines.linewidth":   2.5,
    "font.family":       "DejaVu Sans",
})


def _new_fig(w=8, h=4):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    return fig, ax


# ── 1. Distance improvement per generation ────────────────────────────────────
def plot_distance_improvement(fitness_history: List[float], run_id: int) -> Figure:
    """
    Shows how total route distance dropped over generations.
    Easy to understand: lower = better, flat = converged.
    """
    fig, ax = _new_fig(8, 4)

    # Convert fitness → distance (km) — cast to float explicitly
    distances = [float(1.0 / f) if f > 0 else 0.0 for f in fitness_history]
    gens = list(range(len(distances)))  # integers

    ax.plot(gens, distances, color=ACCENT, linewidth=2)
    ax.fill_between(gens, distances, alpha=0.12, color=ACCENT)

    # Mark best point
    best_idx = int(np.argmin(distances))
    best_val = distances[best_idx]
    ax.scatter([best_idx], [best_val], color=GREEN, s=80, zorder=5)
    ax.annotate(f"Best: {best_val:.2f} km",
                xy=(best_idx, best_val),
                xytext=(best_idx + max(1, len(gens)//10), best_val * 1.02),
                color=GREEN, fontsize=9,
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2))

    ax.set_xlabel("Generation")
    ax.set_ylabel("Route Distance (km)")
    ax.set_title(f"Route Distance Improvement  —  Run #{run_id}")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()
    return fig


# ── 2. Run comparison bar chart ───────────────────────────────────────────────
def plot_run_comparison(runs: List[OptimizationRun]) -> Figure:
    """Bar chart: each run's best distance. Shortest bar highlighted green."""
    fig, ax = _new_fig(9, 4)

    labels    = [f"Run #{r.id}" for r in runs]
    distances = [float(r.best_distance_km or 0) for r in runs]
    colors    = [GREEN if d == min(distances) else ACCENT for d in distances]

    x = np.arange(len(labels))
    bars = ax.bar(x, distances, color=colors, width=0.55, edgecolor=GRID, linewidth=0.5)

    for bar, dist in zip(bars, distances):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(distances) * 0.01,
                f"{dist:.1f} km",
                ha="center", va="bottom", fontsize=9, color=TEXT)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Total Route Distance (km)")
    ax.set_title("Best Distance per Optimization Run  (green = shortest)")
    ax.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    return fig


# ── 3. Delivery geocoding status ──────────────────────────────────────────────
def plot_delivery_stats(deliveries) -> Figure:
    """Simple donut showing geocoded vs pending deliveries."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor(BG)

    geocoded     = sum(1 for d in deliveries if d.is_geocoded)
    not_geocoded = len(deliveries) - geocoded

    # Donut chart
    wedges, texts, autotexts = ax1.pie(
        [geocoded, not_geocoded],
        labels=["Geocoded", "Pending"],
        colors=[GREEN, RED],
        autopct="%1.0f%%",
        startangle=90,
        wedgeprops=dict(width=0.55, edgecolor=BG, linewidth=2),
        textprops=dict(color=TEXT, fontsize=11),
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_color(BG)
        at.set_fontweight("bold")
    ax1.set_title(f"Geocoding Status\n({len(deliveries)} total deliveries)", pad=14)

    # Stops per run bar
    if deliveries:
        from collections import Counter
        from services.optimization_service import get_optimization_history
        runs = get_optimization_history(limit=8)
        if runs:
            run_labels = [f"#{r.id}" for r in runs]
            run_stops  = [int(r.num_deliveries) for r in runs]
            x = np.arange(len(run_labels))
            ax2.bar(x, run_stops, color=ACCENT, width=0.5, edgecolor=GRID)
            ax2.set_xticks(x)
            ax2.set_xticklabels(run_labels)
            ax2.set_ylabel("Number of Stops")
            ax2.set_title("Stops per Optimization Run")
            ax2.grid(True, axis="y", alpha=0.25)
            ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        else:
            ax2.set_visible(False)

    plt.tight_layout()
    return fig


# ── 4. Runtime bar chart ──────────────────────────────────────────────────────
def plot_runtime_analysis(runs: List[OptimizationRun]) -> Figure:
    """Simple bar: how long each run took."""
    fig, ax = _new_fig(9, 4)

    labels = [f"Run #{r.id}" for r in runs]
    times  = [float(r.execution_time_sec or 0) for r in runs]
    x = np.arange(len(labels))

    bars = ax.bar(x, times, color=PURPLE, width=0.55, edgecolor=GRID)
    for bar, t in zip(bars, times):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(times) * 0.01,
                f"{t:.1f}s",
                ha="center", va="bottom", fontsize=9, color=TEXT)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Execution Time (seconds)")
    ax.set_title("Optimization Runtime per Run")
    ax.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    return fig


# ── 5. Summary card (fitness + distance side by side) ─────────────────────────
def plot_run_summary(fitness_history: List[float], run_id: int,
                     best_distance: float, num_stops: int) -> Figure:
    """Two-panel summary for a single run."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor(BG)

    # Left: distance improvement
    distances = [float(1.0 / f) if f > 0 else 0.0 for f in fitness_history]
    gens = list(range(len(distances)))
    ax1.plot(gens, distances, color=ACCENT, linewidth=2)
    ax1.fill_between(gens, distances, alpha=0.12, color=ACCENT)
    ax1.set_xlabel("Generation")
    ax1.set_ylabel("Distance (km)")
    ax1.set_title("Distance Over Generations")
    ax1.grid(True, alpha=0.25)
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    # Right: summary stats as text
    ax2.set_facecolor(PANEL)
    ax2.axis("off")
    stats = [
        ("Run ID",          f"#{run_id}"),
        ("Best Distance",   f"{best_distance:.3f} km"),
        ("Generations",     str(len(fitness_history))),
        ("Stops",           str(num_stops)),
        ("Start Distance",  f"{distances[0]:.2f} km" if distances else "—"),
        ("Improvement",     f"{((distances[0]-best_distance)/distances[0]*100):.1f}%" if distances and distances[0] > 0 else "—"),
    ]
    y = 0.88
    for label, val in stats:
        ax2.text(0.08, y, label + ":", color=TEXT,      fontsize=11, transform=ax2.transAxes, va="top")
        ax2.text(0.55, y, val,         color=ACCENT,    fontsize=11, transform=ax2.transAxes, va="top", fontweight="bold")
        y -= 0.14
    ax2.set_title(f"Run #{run_id} Summary")

    plt.tight_layout()
    return fig


# ── Embed / save helpers ──────────────────────────────────────────────────────

def embed_figure(fig: Figure, parent_frame) -> FigureCanvasTkAgg:
    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    return canvas


def save_figure(fig: Figure, filename: str) -> str:
    from exports.export_service import EXPORTS_DIR
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    filepath = os.path.join(EXPORTS_DIR, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return filepath


# Keep old names as aliases so nothing else breaks
def plot_fitness_history(fitness_history, run_id, ax=None):
    return plot_distance_improvement(fitness_history, run_id)

def plot_distance_history(distance_history, run_id, ax=None):
    fig, axis = _new_fig(8, 4)
    gens = list(range(len(distance_history)))
    dists = [float(d) for d in distance_history]
    axis.plot(gens, dists, color=RED, linewidth=2)
    axis.fill_between(gens, dists, alpha=0.1, color=RED)
    axis.set_xlabel("Generation")
    axis.set_ylabel("Distance (km)")
    axis.set_title(f"Distance History — Run #{run_id}")
    axis.grid(True, alpha=0.25)
    axis.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()
    return fig
