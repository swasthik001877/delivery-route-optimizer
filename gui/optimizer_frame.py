"""
Optimizer Frame — configure and run the Genetic Algorithm
"""

import threading
import time
import customtkinter as ctk
from tkinter import messagebox
from gui.theme import c, FONT_MD_B, FONT_SM, FONT_SM_B, FONT_XS, FONT_LG, card_style, btn_primary, btn_danger, btn_secondary, entry_style
from algorithms.genetic_algorithm import GAConfig
from services.optimization_service import run_optimization_threaded
from services.delivery_service import get_all_deliveries
from services.auth_service import get_current_user_id


class OptimizerFrame(ctk.CTkFrame):
    def __init__(self, parent, navigate_callback=None):
        super().__init__(parent, fg_color=c("bg_primary"), corner_radius=0)
        self._stop_event = None
        self._running = False
        self._selected_ids = []
        self._navigate = navigate_callback
        self._build()
        self.refresh()

    def _build(self):
        # ── Toolbar ──
        toolbar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=60)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        ctk.CTkLabel(toolbar, text="  🚀 Route Optimizer",
                     font=FONT_MD_B, text_color=c("accent"), anchor="w").pack(side="left", fill="y")

        # Two-column layout
        main = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        main.pack(fill="both", expand=True, padx=16, pady=12)
        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        self._build_config_panel(main).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_monitor_panel(main).grid(row=0, column=1, sticky="nsew")

    def _build_config_panel(self, parent):
        panel = ctk.CTkFrame(parent, **card_style())

        ctk.CTkLabel(panel, text="  ⚙ Configuration",
                     font=FONT_SM_B, text_color=c("accent"), anchor="w").pack(fill="x", padx=12, pady=(12, 4))

        scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent", height=460)
        scroll.pack(fill="both", expand=True, padx=8)

        def lbl(txt):
            ctk.CTkLabel(scroll, text=txt, font=FONT_XS,
                         text_color=c("text_secondary"), anchor="w").pack(fill="x", pady=(8, 1))

        def slider_row(label, var, from_, to, steps=100):
            lbl(label)
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x")
            val_lbl = ctk.CTkLabel(row, text=str(var.get()), font=FONT_XS,
                                   text_color=c("accent"), width=50)
            sl = ctk.CTkSlider(
                row, variable=var, from_=from_, to=to, number_of_steps=steps,
                button_color=c("accent"), progress_color=c("accent"),
                fg_color=c("bg_secondary"),
                command=lambda v: val_lbl.configure(text=f"{float(v):.3f}" if isinstance(v, float) and from_ < 1 else str(int(v)))
            )
            sl.pack(side="left", fill="x", expand=True)
            val_lbl.pack(side="left", padx=(6, 0))
            return sl

        lbl("Run Name")
        self.run_name_entry = ctk.CTkEntry(scroll, placeholder_text="e.g. Monday AM Route",
                                           height=34, **entry_style())
        self.run_name_entry.pack(fill="x")

        self.pop_var = ctk.IntVar(value=100)
        slider_row("Population Size", self.pop_var, 20, 500, 48)

        self.gen_var = ctk.IntVar(value=500)
        slider_row("Max Generations", self.gen_var, 50, 2000, 197)

        self.mut_var = ctk.DoubleVar(value=0.02)
        slider_row("Mutation Rate", self.mut_var, 0.001, 0.2, 200)

        self.cross_var = ctk.DoubleVar(value=0.85)
        slider_row("Crossover Rate", self.cross_var, 0.5, 1.0, 50)

        # ── Parameter help cards ──────────────────────────────────────────
        ctk.CTkLabel(scroll, text="ⓘ  What do these mean?",
                     font=FONT_SM_B, text_color=c("accent"), anchor="w").pack(fill="x", pady=(12, 4))

        _help = [
            ("👥  Population Size",
             "Number of random routes created each generation.\n"
             "More = better results but slower.\n"
             "Recommended: 50–150"),
            ("🔁  Max Generations",
             "How many evolution rounds to run.\n"
             "More = more refined route, takes longer.\n"
             "Recommended: 200–500"),
            ("🧬  Mutation Rate",
             "Chance of randomly swapping two stops.\n"
             "Prevents getting stuck. Keep it low.\n"
             "Recommended: 0.01–0.05 (1–5%)"),
            ("✂️  Crossover Rate",
             "Chance two routes combine to make a child.\n"
             "Higher = more breeding from good parents.\n"
             "Recommended: 0.80–0.95 (80–95%)"),
        ]

        for title, desc in _help:
            card = ctk.CTkFrame(scroll, fg_color=c("bg_secondary"), corner_radius=8)
            card.pack(fill="x", pady=3)
            ctk.CTkLabel(card, text=title, font=FONT_SM_B,
                         text_color=c("accent"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(card, text=desc, font=FONT_XS,
                         text_color=c("text_secondary"), anchor="w",
                         justify="left", wraplength=200).pack(fill="x", padx=10, pady=(0, 8))

        # Delivery selector
        lbl("Select Deliveries")
        self.select_all_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll, text="Select All Geocoded", variable=self.select_all_var,
            font=FONT_XS, text_color=c("text_secondary"),
            checkbox_width=16, checkbox_height=16,
            fg_color=c("accent"), hover_color=c("accent_hover"),
            checkmark_color=c("bg_primary"),
            command=self._toggle_select_all,
        ).pack(anchor="w", pady=4)

        self.delivery_list_frame = ctk.CTkScrollableFrame(scroll, fg_color=c("bg_secondary"),
                                                          height=160, corner_radius=8)
        self.delivery_list_frame.pack(fill="x")

        # Buttons
        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=10)

        self.run_btn = ctk.CTkButton(
            btn_row, text="▶  START OPTIMIZATION", command=self._start,
            height=44, **btn_primary()
        )
        self.run_btn.pack(fill="x", pady=(0, 6))

        self.stop_btn = ctk.CTkButton(
            btn_row, text="⏹  STOP", command=self._stop,
            height=36, state="disabled",
            fg_color=c("danger"), hover_color="#CC3355",
            text_color="white", font=FONT_SM_B, corner_radius=8,
        )
        self.stop_btn.pack(fill="x")

        return panel

    def _build_monitor_panel(self, parent):
        panel = ctk.CTkFrame(parent, **card_style())

        ctk.CTkLabel(panel, text="  📡 Optimization Monitor",
                     font=FONT_SM_B, text_color=c("accent"), anchor="w").pack(fill="x", padx=12, pady=(12, 4))

        # KPI row
        kpi_row = ctk.CTkFrame(panel, fg_color=c("bg_secondary"), corner_radius=8)
        kpi_row.pack(fill="x", padx=12, pady=4)

        self.kpi_labels = {}
        for key, label in [("gen", "Generation"), ("dist", "Best Distance"), ("time", "Elapsed"), ("status", "Status")]:
            col = ctk.CTkFrame(kpi_row, fg_color="transparent")
            col.pack(side="left", expand=True, padx=8, pady=8)
            ctk.CTkLabel(col, text=label, font=FONT_XS, text_color=c("text_muted")).pack()
            lbl = ctk.CTkLabel(col, text="—", font=FONT_SM_B, text_color=c("accent"))
            lbl.pack()
            self.kpi_labels[key] = lbl

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(panel, height=8, corner_radius=4,
                                               fg_color=c("bg_secondary"), progress_color=c("accent"))
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=12, pady=4)

        # Live log
        ctk.CTkLabel(panel, text="  Terminal Log",
                     font=FONT_XS, text_color=c("text_muted"), anchor="w").pack(fill="x", padx=12, pady=(4, 0))

        self.log_box = ctk.CTkTextbox(
            panel, height=200, font=("Courier New", 11),
            fg_color=c("bg_secondary"), text_color=c("accent3"),
            wrap="word", border_width=1, border_color=c("border"),
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=4)

        # Result table
        ctk.CTkLabel(panel, text="  Optimized Route",
                     font=FONT_XS, text_color=c("text_muted"), anchor="w").pack(fill="x", padx=12, pady=(4, 0))

        self.result_scroll = ctk.CTkScrollableFrame(panel, fg_color=c("bg_secondary"),
                                                    height=200, corner_radius=8)
        self.result_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        return panel

    def refresh(self):
        self._deliveries = get_all_deliveries(geocoded_only=True)
        self._render_delivery_list()

    def _render_delivery_list(self):
        for w in self.delivery_list_frame.winfo_children():
            w.destroy()
        self._check_vars = []
        for d in self._deliveries:
            var = ctk.BooleanVar(value=True)
            self._check_vars.append((var, d.delivery_id))
            ctk.CTkCheckBox(
                self.delivery_list_frame,
                text=f"{d.delivery_id} — {d.customer_name[:22]}",
                variable=var, font=FONT_XS, text_color=c("text_primary"),
                checkbox_width=14, checkbox_height=14,
                fg_color=c("accent"), hover_color=c("accent_hover"),
                checkmark_color=c("bg_primary"),
            ).pack(anchor="w", pady=1)

    def _toggle_select_all(self):
        val = self.select_all_var.get()
        for var, _ in self._check_vars:
            var.set(val)

    def _get_selected_ids(self):
        return [did for var, did in self._check_vars if var.get()]

    def _start(self):
        if self._running:
            return

        selected = self._get_selected_ids()
        if len(selected) < 2:
            messagebox.showwarning("Selection", "Select at least 2 geocoded deliveries.")
            return

        config = GAConfig(
            population_size=self.pop_var.get(),
            mutation_rate=self.mut_var.get(),
            crossover_rate=self.cross_var.get(),
            num_generations=self.gen_var.get(),
        )

        run_name = self.run_name_entry.get().strip() or None
        self._running = True
        self._start_time = time.time()
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.log_box.delete("1.0", "end")
        self._log(f"Starting optimization: {len(selected)} stops, pop={config.population_size}, gen={config.num_generations}")
        self.kpi_labels["status"].configure(text="Running", text_color=c("accent3"))

        def _progress(gen, dist, fit):
            pct = gen / config.num_generations
            self.after(0, lambda: self.progress_bar.set(pct))
            self.after(0, lambda: self.kpi_labels["gen"].configure(text=str(gen)))
            self.after(0, lambda: self.kpi_labels["dist"].configure(text=f"{dist:.2f} km"))
            elapsed = time.time() - self._start_time
            self.after(0, lambda: self.kpi_labels["time"].configure(text=f"{elapsed:.1f}s"))
            if gen % 25 == 0:
                self.after(0, lambda: self._log(f"Gen {gen:4d} | Best: {dist:.3f} km | Fitness: {fit:.6f}"))

        def _done(result, error):
            self._running = False
            self.after(0, lambda: self.run_btn.configure(state="normal"))
            self.after(0, lambda: self.stop_btn.configure(state="disabled"))
            self.after(0, lambda: self.progress_bar.set(1.0))

            if error:
                self.after(0, lambda: self._log(f"ERROR: {error}"))
                self.after(0, lambda: self.kpi_labels["status"].configure(text="Failed", text_color=c("danger")))
            elif result:
                self.after(0, lambda: self._log(
                    f"\n✔ Complete! Best: {result.best_distance:.3f} km | Time: {result.execution_time:.2f}s | Gen: {result.generations_completed}"
                ))
                self.after(0, lambda: self.kpi_labels["status"].configure(text="Done ✔", text_color=c("success")))
                self.after(0, lambda: self._show_result(result, selected))
                # Auto-generate map in background, then switch to Maps tab
                def _gen_map():
                    from services.optimization_service import get_run_routes, get_optimization_history
                    from maps.map_service import generate_route_map
                    history = get_optimization_history(limit=1)
                    if history:
                        run = history[0]
                        routes = get_run_routes(run.id)
                        generate_route_map(routes, run.id, run.best_distance_km or 0, open_browser=False)
                        if self._navigate:
                            self.after(500, lambda: self._navigate("maps"))
                threading.Thread(target=_gen_map, daemon=True).start()

        self._stop_event = run_optimization_threaded(
            delivery_ids=selected,
            config=config,
            run_name=run_name,
            user_id=get_current_user_id(),
            progress_callback=_progress,
            completion_callback=_done,
        )

    def _stop(self):
        if self._stop_event:
            self._stop_event.set()
        self._log("⏹ Stop requested by user…")
        self.kpi_labels["status"].configure(text="Stopping…", text_color=c("warning"))

    def _log(self, msg: str):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def _show_result(self, result, selected_ids):
        from services.optimization_service import get_run_routes, get_optimization_history
        # Find the latest run
        history = get_optimization_history(limit=1)
        if not history:
            return
        run = history[0]
        routes = get_run_routes(run.id)

        for w in self.result_scroll.winfo_children():
            w.destroy()

        header = ctk.CTkFrame(self.result_scroll, fg_color=c("bg_primary"), height=24)
        header.pack(fill="x")
        for col, w in [("#", 30), ("Customer", 160), ("Address", 220), ("Dist", 70)]:
            ctk.CTkLabel(header, text=col, font=FONT_XS,
                         text_color=c("text_muted"), width=w, anchor="w").pack(side="left", padx=2)

        for i, r in enumerate(routes):
            bg = c("table_row_odd") if i % 2 == 0 else c("table_row_even")
            row = ctk.CTkFrame(self.result_scroll, fg_color=bg, height=28)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            vals = [
                (str(r.stop_order + 1), 30),
                (r.customer_name[:20], 160),
                (r.address[:30], 220),
                (f"{r.distance_from_prev_km:.2f}", 70),
            ]
            for val, w in vals:
                ctk.CTkLabel(row, text=val, font=FONT_XS,
                             text_color=c("text_primary"), width=w, anchor="w").pack(side="left", padx=2)

        # Map + export buttons
        btn_row = ctk.CTkFrame(self.result_scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=6)

        ctk.CTkButton(btn_row, text="🗺 View Map", height=30,
                      command=lambda: self._open_map(run),
                      **btn_primary()).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📤 Export CSV", height=30,
                      command=lambda: self._export(run, "csv"),
                      **btn_secondary()).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📤 PDF", height=30,
                      command=lambda: self._export(run, "pdf"),
                      **btn_secondary()).pack(side="left", padx=4)

    def _open_map(self, run):
        from maps.map_service import generate_route_map
        from services.optimization_service import get_run_routes
        routes = get_run_routes(run.id)
        def _gen():
            path = generate_route_map(routes, run.id, run.best_distance_km or 0, open_browser=True)
        threading.Thread(target=_gen, daemon=True).start()

    def _export(self, run, fmt):
        from exports.export_service import export_routes_csv, export_routes_pdf
        if fmt == "csv":
            path = export_routes_csv(run)
        else:
            path = export_routes_pdf(run)
        messagebox.showinfo("Exported", f"File saved:\n{path}")
