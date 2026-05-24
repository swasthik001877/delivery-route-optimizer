"""
History Frame — view, replay, export, delete optimization runs
Supports checkbox multi-select for bulk delete.
"""

import threading
import time
from tkinter import messagebox
import customtkinter as ctk
from gui.theme import c, FONT_MD_B, FONT_SM_B, FONT_SM, FONT_XS, card_style, btn_primary, btn_secondary, btn_danger
from services.optimization_service import get_optimization_history, get_run_routes, delete_run


class HistoryFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=c("bg_primary"), corner_radius=0)
        self._runs = []
        self._selected_run = None
        self._check_vars = []       # list of (BooleanVar, run_id)
        self._select_all_var = ctk.BooleanVar(value=False)
        self._build()
        self.refresh()

    def _build(self):
        toolbar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=60)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        ctk.CTkLabel(toolbar, text="  📂 Optimization History",
                     font=FONT_MD_B, text_color=c("accent"), anchor="w").pack(side="left", fill="y")

        for text, cmd, style in [
            ("🔄 Refresh",     self.refresh,                btn_secondary()),
            ("📤 Export CSV",  lambda: self._export("csv"), btn_secondary()),
            ("📤 Export JSON", lambda: self._export("json"),btn_secondary()),
            ("📤 PDF Report",  lambda: self._export("pdf"), btn_secondary()),
            ("📤 Excel",       lambda: self._export("xlsx"),btn_secondary()),
        ]:
            ctk.CTkButton(toolbar, text=text, command=cmd, height=36, **style).pack(
                side="right", padx=3, pady=12
            )

        main = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        main.pack(fill="both", expand=True, padx=16, pady=12)
        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        self._build_runs_panel(main).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_detail_panel(main).grid(row=0, column=1, sticky="nsew")

    def _build_runs_panel(self, parent):
        panel = ctk.CTkFrame(parent, **card_style())

        # Header row with select-all + delete selected
        top = ctk.CTkFrame(panel, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(top, text="  Completed Runs",
                     font=FONT_SM_B, text_color=c("accent"), anchor="w").pack(side="left")

        self.del_sel_btn = ctk.CTkButton(
            top, text="🗑 Delete Selected", command=self._delete_selected,
            height=26, width=130,
            fg_color=c("danger"), hover_color="#CC3355",
            text_color="white", font=FONT_XS, corner_radius=6,
            state="disabled",
        )
        self.del_sel_btn.pack(side="right")

        self.sel_count_label = ctk.CTkLabel(
            top, text="", font=FONT_XS, text_color=c("warning")
        )
        self.sel_count_label.pack(side="right", padx=8)

        # Column header
        hdr = ctk.CTkFrame(panel, fg_color=c("bg_secondary"), height=26)
        hdr.pack(fill="x", padx=8)
        hdr.pack_propagate(False)

        # Select-all checkbox in header
        self.sel_all_chk = ctk.CTkCheckBox(
            hdr, text="", variable=self._select_all_var,
            command=self._toggle_select_all,
            checkbox_width=14, checkbox_height=14,
            fg_color=c("danger"), hover_color="#CC3355",
            checkmark_color="white", width=24,
        )
        self.sel_all_chk.pack(side="left", padx=6)

        for col, w in [("ID", 40), ("Name", 130), ("Stops", 44), ("Dist (km)", 75), ("Date", 90)]:
            ctk.CTkLabel(hdr, text=col, font=FONT_XS, text_color=c("text_muted"),
                         width=w, anchor="w").pack(side="left", padx=3)

        self.run_scroll = ctk.CTkScrollableFrame(panel, fg_color=c("bg_primary"), height=500)
        self.run_scroll.pack(fill="both", expand=True, padx=8, pady=4)
        return panel

    def _build_detail_panel(self, parent):
        panel = ctk.CTkFrame(parent, **card_style())
        ctk.CTkLabel(panel, text="  Run Details",
                     font=FONT_SM_B, text_color=c("accent"), anchor="w").pack(fill="x", padx=12, pady=(12, 4))

        self.detail_frame = ctk.CTkFrame(panel, fg_color=c("bg_primary"))
        self.detail_frame.pack(fill="both", expand=True, padx=8, pady=4)

        ctk.CTkLabel(self.detail_frame, text="Select a run from the left panel.",
                     font=FONT_SM, text_color=c("text_muted")).pack(expand=True)
        return panel

    def refresh(self):
        self._runs = get_optimization_history(limit=50)
        self._select_all_var.set(False)
        self._render_runs()

    def _render_runs(self):
        for w in self.run_scroll.winfo_children():
            w.destroy()
        self._check_vars = []
        self._update_sel_count()

        if not self._runs:
            ctk.CTkLabel(self.run_scroll, text="No optimization history found.",
                         font=FONT_SM, text_color=c("text_muted")).pack(pady=30)
            return

        for i, run in enumerate(self._runs):
            bg = c("table_row_odd") if i % 2 == 0 else c("table_row_even")
            row = ctk.CTkFrame(self.run_scroll, fg_color=bg, height=34, cursor="hand2")
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            # ── Checkbox ──
            var = ctk.BooleanVar(value=False)
            var.trace_add("write", lambda *_, v=var: self._on_check_change())
            self._check_vars.append((var, run.id))

            ctk.CTkCheckBox(
                row, text="", variable=var,
                checkbox_width=14, checkbox_height=14,
                fg_color=c("danger"), hover_color="#CC3355",
                checkmark_color="white", width=24,
            ).pack(side="left", padx=6)

            # ── Data columns ──
            date_str = run.created_at.strftime("%b %d %H:%M") if run.created_at else "—"
            for val, w in [
                (str(run.id), 40),
                ((run.run_name or f"Run {run.id}")[:16], 130),
                (str(run.num_deliveries), 44),
                (f"{run.best_distance_km:.2f}" if run.best_distance_km else "—", 75),
                (date_str, 90),
            ]:
                ctk.CTkLabel(row, text=val, font=FONT_XS,
                             text_color=c("text_primary"), width=w, anchor="w").pack(side="left", padx=3)

            # ── Individual delete button ──
            ctk.CTkButton(
                row, text="🗑", width=26, height=22,
                fg_color=c("danger"), hover_color="#CC3355",
                text_color="white", corner_radius=4, font=FONT_XS,
                command=lambda rid=run.id: self._delete_one(rid)
            ).pack(side="right", padx=4)

            # Click row to select detail
            row.bind("<Button-1>", lambda e, r=run: self._select_run(r))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, r=run: self._select_run(r))

    # ── Checkbox helpers ──────────────────────────────────────────────────────

    def _on_check_change(self):
        self._update_sel_count()

    def _update_sel_count(self):
        selected = sum(1 for v, _ in self._check_vars if v.get())
        total = len(self._check_vars)
        if selected:
            self.sel_count_label.configure(text=f"{selected} of {total} selected")
            self.del_sel_btn.configure(state="normal")
        else:
            self.sel_count_label.configure(text="")
            self.del_sel_btn.configure(state="disabled")
        if selected == total and total > 0:
            self._select_all_var.set(True)
        elif selected == 0:
            self._select_all_var.set(False)

    def _toggle_select_all(self):
        val = self._select_all_var.get()
        for var, _ in self._check_vars:
            var.set(val)
        self._update_sel_count()

    def _delete_selected(self):
        selected = [(v, rid) for v, rid in self._check_vars if v.get()]
        if not selected:
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete {len(selected)} optimization run(s)?\nThis cannot be undone."
        ):
            return
        count = 0
        for _, rid in selected:
            if delete_run(rid):
                count += 1
        self.refresh()

    def _delete_one(self, run_id):
        if messagebox.askyesno("Confirm Delete", f"Delete Run #{run_id}? This cannot be undone."):
            delete_run(run_id)
            if self._selected_run and self._selected_run.id == run_id:
                self._selected_run = None
                for w in self.detail_frame.winfo_children():
                    w.destroy()
                ctk.CTkLabel(self.detail_frame, text="Select a run from the left panel.",
                             font=FONT_SM, text_color=c("text_muted")).pack(expand=True)
            self.refresh()

    # ── Detail view ───────────────────────────────────────────────────────────

    def _select_run(self, run):
        self._selected_run = run
        self._render_detail(run)

    def _render_detail(self, run):
        for w in self.detail_frame.winfo_children():
            w.destroy()

        kpi_row = ctk.CTkFrame(self.detail_frame, fg_color=c("bg_secondary"), corner_radius=8)
        kpi_row.pack(fill="x", padx=4, pady=4)
        for label, val, color in [
            ("Distance", f"{run.best_distance_km:.3f} km", c("accent")),
            ("Stops",    str(run.num_deliveries),           c("accent3")),
            ("Time",     f"{run.execution_time_sec:.2f}s",  c("accent2")),
            ("Gens",     str(run.generations_completed),    c("warning")),
        ]:
            col = ctk.CTkFrame(kpi_row, fg_color="transparent")
            col.pack(side="left", expand=True, padx=8, pady=8)
            ctk.CTkLabel(col, text=label, font=FONT_XS, text_color=c("text_muted")).pack()
            ctk.CTkLabel(col, text=val,   font=FONT_SM_B, text_color=color).pack()

        params_row = ctk.CTkFrame(self.detail_frame, fg_color=c("bg_secondary"), corner_radius=8)
        params_row.pack(fill="x", padx=4, pady=4)
        for label, val in [("Population", run.population_size),
                           ("Mutation",   run.mutation_rate),
                           ("Crossover",  run.crossover_rate)]:
            col = ctk.CTkFrame(params_row, fg_color="transparent")
            col.pack(side="left", expand=True, padx=8, pady=4)
            ctk.CTkLabel(col, text=label, font=FONT_XS, text_color=c("text_muted")).pack()
            ctk.CTkLabel(col, text=str(val), font=FONT_XS, text_color=c("text_primary")).pack()

        ctk.CTkLabel(self.detail_frame, text="  Route Sequence",
                     font=FONT_XS, text_color=c("text_muted"), anchor="w").pack(fill="x", padx=4, pady=(6, 0))

        route_scroll = ctk.CTkScrollableFrame(self.detail_frame, fg_color=c("bg_secondary"),
                                              height=240, corner_radius=8)
        route_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        routes = get_run_routes(run.id)
        for r in routes:
            row_frame = ctk.CTkFrame(route_scroll, fg_color=c("table_row_odd"), height=28)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)
            ctk.CTkLabel(row_frame, text=f"#{r.stop_order+1}", font=FONT_XS,
                         text_color=c("accent"), width=30, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=r.customer_name[:22], font=FONT_XS,
                         text_color=c("text_primary"), width=150, anchor="w").pack(side="left")
            ctk.CTkLabel(row_frame, text=r.address[:32], font=FONT_XS,
                         text_color=c("text_secondary"), width=200, anchor="w").pack(side="left")
            ctk.CTkLabel(row_frame, text=f"{r.distance_from_prev_km:.2f} km", font=FONT_XS,
                         text_color=c("text_muted"), anchor="e").pack(side="right", padx=4)

        btn_row = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=6)
        ctk.CTkButton(btn_row, text="🗺 View Map",    height=34,
                      command=lambda: self._open_map(run), **btn_primary()).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📊 View Charts", height=34,
                      command=lambda: self._view_charts(run), **btn_secondary()).pack(side="left", padx=4)

    def _open_map(self, run):
        from maps.map_service import generate_route_map
        routes = get_run_routes(run.id)
        threading.Thread(
            target=lambda: generate_route_map(routes, run.id, run.best_distance_km or 0, open_browser=True),
            daemon=True
        ).start()

    def _view_charts(self, run):
        history = run.get_fitness_history()
        if not history:
            messagebox.showwarning("No Data", "No fitness history for this run.")
            return

        from analytics.charts import plot_run_summary, save_figure
        import time

        fig = plot_run_summary(
            history, run.id,
            run.best_distance_km or 0,
            run.num_deliveries
        )

        # ── Open in a proper popup window ──
        popup = ctk.CTkToplevel(self)
        popup.title(f"Charts — Run #{run.id}")
        popup.geometry("820x480")
        popup.configure(fg_color=c("bg_primary"))
        popup.lift()
        popup.focus_force()

        # Toolbar with export
        tb = ctk.CTkFrame(popup, fg_color=c("bg_secondary"), height=44)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        ctk.CTkLabel(tb, text=f"  Run #{run.id} — {run.run_name or ''}",
                     font=FONT_SM_B, text_color=c("accent"), anchor="w").pack(side="left", fill="y")

        def _export(ext):
            fname = f"run{run.id}_chart_{int(time.time())}.{ext}"
            path = save_figure(fig, fname)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

        for fmt in ["PNG", "PDF"]:
            ctk.CTkButton(tb, text=f"💾 {fmt}",
                          command=lambda f=fmt.lower(): _export(f),
                          height=30, width=70,
                          fg_color=c("accent2"), hover_color="#5A3FCC",
                          text_color="white", font=FONT_XS, corner_radius=6,
                          ).pack(side="right", padx=4, pady=7)

        # Embed chart
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas_frame = ctk.CTkFrame(popup, fg_color=c("bg_primary"))
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=8)
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _export(self, fmt):
        run = self._selected_run
        if not run:
            messagebox.showwarning("No Selection", "Select a run first.")
            return
        from exports.export_service import export_routes_csv, export_routes_json, export_routes_pdf, export_excel
        fn = {"csv": export_routes_csv, "json": export_routes_json,
              "pdf": export_routes_pdf, "xlsx": export_excel}.get(fmt)
        if fn:
            path = fn(run)
            if path:
                messagebox.showinfo("Exported", f"Saved to:\n{path}")
