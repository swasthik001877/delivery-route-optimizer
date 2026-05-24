"""
Dashboard Frame — statistics cards, recent history overview
"""

import customtkinter as ctk
from gui.theme import c, FONT_XL, FONT_LG, FONT_MD, FONT_MD_B, FONT_SM, FONT_SM_B, FONT_XS, card_style
from models import get_session, Delivery, OptimizationRun
from services.auth_service import get_current_user


class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent, navigate_callback=None):
        super().__init__(parent, fg_color=c("bg_primary"), corner_radius=0)
        self.navigate = navigate_callback
        self._build()

    def _build(self):
        # ── Top greeting ──
        top = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=80)
        top.pack(fill="x")
        top.pack_propagate(False)

        user = get_current_user()
        name = user.full_name or user.username if user else "User"

        ctk.CTkLabel(
            top, text=f"  Welcome back, {name} 👋",
            font=FONT_LG, text_color=c("text_primary"), anchor="w"
        ).pack(side="left", fill="y", padx=20)

        ctk.CTkLabel(
            top, text="Last-Mile Delivery Route Optimizer",
            font=FONT_SM, text_color=c("text_muted"), anchor="e"
        ).pack(side="right", padx=20)

        # ── Stats cards ──
        stats_row = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        stats_row.pack(fill="x", padx=20, pady=16)

        stats = self._get_stats()
        cards = [
            ("📦", "Total Deliveries",    str(stats["total_deliveries"]),  c("accent")),
            ("🌍", "Geocoded",            str(stats["geocoded"]),           c("accent3")),
            ("🔁", "Routes Optimized",    str(stats["total_runs"]),         c("accent2")),
            ("📏", "Best Distance",       f"{stats['best_dist']:.1f} km",  c("warning")),
        ]

        for icon, label, value, color in cards:
            self._stat_card(stats_row, icon, label, value, color).pack(
                side="left", expand=True, fill="x", padx=6
            )

        # ── Two column layout ──
        columns = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        columns.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        columns.columnconfigure(0, weight=3)
        columns.columnconfigure(1, weight=2)

        self._recent_runs_panel(columns).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._quick_actions_panel(columns).grid(row=0, column=1, sticky="nsew")

    def _stat_card(self, parent, icon, label, value, accent_color):
        card = ctk.CTkFrame(parent, **card_style(), height=100)
        card.pack_propagate(False)

        ctk.CTkLabel(card, text=icon, font=("Courier New", 26)).pack(pady=(12, 0))
        ctk.CTkLabel(card, text=value, font=FONT_LG, text_color=accent_color).pack()
        ctk.CTkLabel(card, text=label, font=FONT_XS, text_color=c("text_muted")).pack()
        return card

    def _recent_runs_panel(self, parent):
        frame = ctk.CTkFrame(parent, **card_style())

        ctk.CTkLabel(
            frame, text="  Recent Optimization Runs",
            font=FONT_MD_B, text_color=c("accent"), anchor="w"
        ).pack(fill="x", padx=12, pady=(12, 4))

        # Header row
        header = ctk.CTkFrame(frame, fg_color=c("bg_secondary"), height=28)
        header.pack(fill="x", padx=8)
        for col, w in [("Run Name", 200), ("Stops", 60), ("Distance", 90), ("Date", 130)]:
            ctk.CTkLabel(header, text=col, font=FONT_XS, text_color=c("text_muted"),
                         width=w, anchor="w").pack(side="left", padx=4)

        # Scrollable runs
        scroll = ctk.CTkScrollableFrame(frame, fg_color=c("bg_primary"), height=280)
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        runs = self._get_recent_runs()
        if not runs:
            ctk.CTkLabel(scroll, text="No optimization runs yet.\nCreate one in the Optimizer tab.",
                         font=FONT_SM, text_color=c("text_muted")).pack(pady=30)
        else:
            for i, run in enumerate(runs):
                bg = c("table_row_odd") if i % 2 == 0 else c("table_row_even")
                row = ctk.CTkFrame(scroll, fg_color=bg, height=32)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                date_str = run.created_at.strftime("%b %d, %H:%M") if run.created_at else "—"
                fields = [
                    (run.run_name or f"Run #{run.id}", 200),
                    (str(run.num_deliveries), 60),
                    (f"{run.best_distance_km:.1f} km" if run.best_distance_km else "—", 90),
                    (date_str, 130),
                ]
                for val, w in fields:
                    ctk.CTkLabel(row, text=val, font=FONT_XS,
                                 text_color=c("text_primary"), width=w, anchor="w").pack(side="left", padx=4)

        return frame

    def _quick_actions_panel(self, parent):
        frame = ctk.CTkFrame(parent, **card_style())

        ctk.CTkLabel(
            frame, text="  Quick Actions",
            font=FONT_MD_B, text_color=c("accent"), anchor="w"
        ).pack(fill="x", padx=12, pady=(12, 8))

        actions = [
            ("➕  Add Delivery",      lambda: self.navigate and self.navigate("addresses")),
            ("🚀  Run Optimizer",      lambda: self.navigate and self.navigate("optimizer")),
            ("🗺️  View Maps",          lambda: self.navigate and self.navigate("maps")),
            ("📊  Analytics",          lambda: self.navigate and self.navigate("analytics")),
            ("📂  Export Data",        lambda: self.navigate and self.navigate("history")),
        ]

        for label, cmd in actions:
            ctk.CTkButton(
                frame, text=label, command=cmd,
                fg_color=c("bg_secondary"), hover_color=c("border"),
                text_color=c("text_primary"), font=FONT_SM, anchor="w",
                corner_radius=8, height=40, border_width=1, border_color=c("border"),
            ).pack(fill="x", padx=12, pady=3)

        # System status
        ctk.CTkLabel(frame, text="", font=FONT_SM).pack()
        status_frame = ctk.CTkFrame(frame, fg_color=c("bg_secondary"), corner_radius=8)
        status_frame.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(status_frame, text="  System Status", font=FONT_XS,
                     text_color=c("text_muted"), anchor="w").pack(fill="x", padx=8, pady=(6, 2))

        for label, ok in [("Database", True), ("Geocoder", True), ("GA Engine", True)]:
            dot = "● " if ok else "○ "
            color = c("success") if ok else c("danger")
            ctk.CTkLabel(status_frame, text=f"  {dot}{label}",
                         font=FONT_XS, text_color=color, anchor="w").pack(fill="x", padx=8)

        ctk.CTkLabel(status_frame, text="", font=FONT_XS).pack(pady=2)
        return frame

    def _get_stats(self) -> dict:
        session = get_session()
        try:
            total = session.query(Delivery).filter_by(is_active=True).count()
            geocoded = session.query(Delivery).filter_by(is_geocoded=True, is_active=True).count()
            runs = session.query(OptimizationRun).filter_by(status="completed").count()
            best_run = session.query(OptimizationRun).filter_by(status="completed").order_by(
                OptimizationRun.best_distance_km
            ).first()
            best_dist = best_run.best_distance_km if best_run else 0.0
            return {"total_deliveries": total, "geocoded": geocoded, "total_runs": runs, "best_dist": best_dist}
        finally:
            session.close()

    def _get_recent_runs(self):
        session = get_session()
        try:
            runs = session.query(OptimizationRun).filter_by(status="completed").order_by(
                OptimizationRun.created_at.desc()
            ).limit(15).all()
            session.expunge_all()
            return runs
        finally:
            session.close()

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()
