"""
Analytics Frame — simple embedded charts with export buttons on each chart.
"""

import os
import time
import customtkinter as ctk
from tkinter import messagebox
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from gui.theme import c, FONT_MD_B, FONT_SM_B, FONT_SM, FONT_XS, card_style, btn_primary, btn_secondary
from services.optimization_service import get_optimization_history
from services.delivery_service import get_all_deliveries
from analytics.charts import (
    plot_distance_improvement, plot_run_comparison,
    plot_delivery_stats, plot_runtime_analysis,
    plot_run_summary, save_figure
)


class AnalyticsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=c("bg_primary"), corner_radius=0)
        self._runs = []
        self._deliveries = []
        self._current_fig = None
        self._current_title = "chart"
        self._build()
        self.refresh()

    def _build(self):
        # ── Toolbar ──
        toolbar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=60)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        ctk.CTkLabel(toolbar, text="  📊 Analytics",
                     font=FONT_MD_B, text_color=c("accent"), anchor="w").pack(side="left", fill="y")
        ctk.CTkButton(toolbar, text="🔄 Refresh", command=self.refresh,
                      height=36, **btn_secondary()).pack(side="right", padx=8, pady=12)

        # ── Main layout ──
        main = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        main.pack(fill="both", expand=True, padx=16, pady=12)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        self._build_selector(main).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_chart_area(main).grid(row=0, column=1, sticky="nsew")

    def _build_selector(self, parent):
        panel = ctk.CTkFrame(parent, **card_style())

        ctk.CTkLabel(panel, text="  Charts", font=FONT_SM_B,
                     text_color=c("accent"), anchor="w").pack(fill="x", padx=12, pady=(12, 8))

        # ── Global chart buttons ──
        ctk.CTkLabel(panel, text="Overview", font=FONT_XS,
                     text_color=c("text_muted"), anchor="w").pack(fill="x", padx=14, pady=(4, 2))

        for icon, label, cmd in [
            ("📦", "Delivery Status",   self._show_delivery_stats),
            ("📊", "Compare All Runs",  self._show_run_comparison),
            ("⏱",  "Runtime per Run",   self._show_runtime),
        ]:
            ctk.CTkButton(
                panel, text=f"  {icon}  {label}", anchor="w",
                command=cmd,
                fg_color=c("bg_secondary"), hover_color=c("border"),
                text_color=c("text_primary"), font=FONT_SM,
                corner_radius=6, height=38,
            ).pack(fill="x", padx=12, pady=2)

        # ── Per-run charts ──
        ctk.CTkLabel(panel, text="\nPer-Run Charts", font=FONT_XS,
                     text_color=c("text_muted"), anchor="w").pack(fill="x", padx=14)

        self.run_scroll = ctk.CTkScrollableFrame(
            panel, fg_color=c("bg_secondary"), height=320, corner_radius=8
        )
        self.run_scroll.pack(fill="x", padx=12, pady=4)

        return panel

    def _build_chart_area(self, parent):
        panel = ctk.CTkFrame(parent, **card_style())

        # ── Chart toolbar ──
        self.chart_toolbar = ctk.CTkFrame(panel, fg_color=c("bg_secondary"), height=44, corner_radius=0)
        self.chart_toolbar.pack(fill="x")
        self.chart_toolbar.pack_propagate(False)

        self.chart_title_label = ctk.CTkLabel(
            self.chart_toolbar, text="  No chart selected",
            font=FONT_SM, text_color=c("text_muted"), anchor="w"
        )
        self.chart_title_label.pack(side="left", fill="y")

        # Export buttons in toolbar
        for fmt, ext in [("PNG", "png"), ("PDF", "pdf")]:
            ctk.CTkButton(
                self.chart_toolbar,
                text=f"💾 {fmt}",
                command=lambda e=ext: self._export_chart(e),
                height=30, width=70,
                fg_color=c("accent2"), hover_color="#5A3FCC",
                text_color="white", font=FONT_XS, corner_radius=6,
            ).pack(side="right", padx=4, pady=7)

        ctk.CTkLabel(self.chart_toolbar, text="Export:",
                     font=FONT_XS, text_color=c("text_muted")).pack(side="right", padx=4)

        # ── Canvas area ──
        self.canvas_frame = ctk.CTkFrame(panel, fg_color=c("bg_primary"), corner_radius=0)
        self.canvas_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.canvas_frame,
            text="👈  Select a chart from the left panel",
            font=FONT_SM, text_color=c("text_muted")
        ).pack(expand=True)

        return panel

    def refresh(self):
        self._runs = get_optimization_history(limit=30)
        self._deliveries = get_all_deliveries()
        self._render_run_list()

    def _render_run_list(self):
        for w in self.run_scroll.winfo_children():
            w.destroy()

        if not self._runs:
            ctk.CTkLabel(self.run_scroll, text="No completed runs yet.",
                         font=FONT_XS, text_color=c("text_muted")).pack(pady=12)
            return

        for run in self._runs:
            card = ctk.CTkFrame(self.run_scroll, fg_color=c("bg_primary"), corner_radius=6)
            card.pack(fill="x", pady=2)

            ctk.CTkLabel(card,
                         text=f"Run #{run.id}  {(run.run_name or '')[:14]}",
                         font=FONT_XS, text_color=c("text_primary"), anchor="w").pack(fill="x", padx=8, pady=(4, 0))
            ctk.CTkLabel(card,
                         text=f"{run.best_distance_km:.1f} km  ·  {run.num_deliveries} stops",
                         font=FONT_XS, text_color=c("accent"), anchor="w").pack(fill="x", padx=8)

            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(fill="x", padx=6, pady=(2, 6))

            ctk.CTkButton(
                btn_row, text="📉 Distance", width=90, height=26,
                fg_color=c("accent"), hover_color=c("accent_hover"),
                text_color="#000", font=FONT_XS, corner_radius=4,
                command=lambda r=run: self._show_run_distance(r)
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_row, text="📋 Summary", width=80, height=26,
                fg_color=c("accent2"), hover_color="#5A3FCC",
                text_color="white", font=FONT_XS, corner_radius=4,
                command=lambda r=run: self._show_run_summary(r)
            ).pack(side="left", padx=2)

    # ── Chart display ─────────────────────────────────────────────────────────

    def _embed(self, fig, title: str):
        """Clear canvas and embed new figure."""
        for w in self.canvas_frame.winfo_children():
            w.destroy()
        self._current_fig = fig
        self._current_title = title
        self.chart_title_label.configure(text=f"  {title}", text_color=c("text_primary"))

        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def _show_run_distance(self, run):
        history = run.get_fitness_history()
        if not history:
            messagebox.showwarning("No Data", "No history saved for this run.")
            return
        fig = plot_distance_improvement(history, run.id)
        self._embed(fig, f"Distance Improvement — Run #{run.id}")

    def _show_run_summary(self, run):
        history = run.get_fitness_history()
        if not history:
            messagebox.showwarning("No Data", "No history saved for this run.")
            return
        fig = plot_run_summary(history, run.id,
                               run.best_distance_km or 0,
                               run.num_deliveries)
        self._embed(fig, f"Summary — Run #{run.id}")

    def _show_delivery_stats(self):
        if not self._deliveries:
            messagebox.showwarning("No Data", "No deliveries in database.")
            return
        fig = plot_delivery_stats(self._deliveries)
        self._embed(fig, "Delivery Status Overview")

    def _show_run_comparison(self):
        if not self._runs:
            messagebox.showwarning("No Data", "No completed runs.")
            return
        fig = plot_run_comparison(self._runs[:12])
        self._embed(fig, "Run Distance Comparison")

    def _show_runtime(self):
        if not self._runs:
            messagebox.showwarning("No Data", "No completed runs.")
            return
        fig = plot_runtime_analysis(self._runs[:12])
        self._embed(fig, "Runtime per Run")

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_chart(self, ext: str):
        if not self._current_fig:
            messagebox.showwarning("No Chart", "Display a chart first.")
            return
        safe_title = self._current_title.replace(" ", "_").replace("/", "-").replace("#", "")
        filename = f"{safe_title}_{int(time.time())}.{ext}"
        path = save_figure(self._current_fig, filename)
        messagebox.showinfo("Exported", f"Saved to:\n{path}")
