"""
Embedded Map Panel — shows Leaflet HTML maps inside the app.

Uses tkinterweb.HtmlFrame when available (requires tkinter + tkinterweb).
Falls back gracefully to an in-app preview panel + "Open in Browser" button.
"""

import os
import threading
import webbrowser
import customtkinter as ctk
from gui.theme import c, FONT_SM, FONT_SM_B, FONT_MD_B, FONT_XS, btn_primary, btn_secondary

# Try importing tkinterweb — optional dependency
try:
    from tkinterweb import HtmlFrame
    _HAS_TKINTERWEB = True
except Exception:
    _HAS_TKINTERWEB = False


class MapPanel(ctk.CTkFrame):
    """
    Embeds a Leaflet HTML map inside a CTkFrame.
    If tkinterweb is available, renders inline.
    Otherwise shows a preview card with an Open in Browser button.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=c("bg_primary"), corner_radius=0, **kwargs)
        self._current_html_path: str = ""
        self._build_placeholder()

    def _build_placeholder(self):
        """Show placeholder before any map is loaded."""
        for w in self.winfo_children():
            w.destroy()

        frame = ctk.CTkFrame(self, fg_color=c("bg_card"), corner_radius=12,
                             border_width=1, border_color=c("border"))
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(frame, text="🗺️", font=("", 48)).pack(pady=(40, 8))
        ctk.CTkLabel(frame, text="No map loaded",
                     font=FONT_MD_B, text_color=c("text_secondary")).pack()
        ctk.CTkLabel(frame, text="Run an optimization to view the route map.",
                     font=FONT_XS, text_color=c("text_muted")).pack(pady=4)

    def load_map(self, html_path: str):
        """Load and display a map from a saved HTML file path."""
        if not html_path or not os.path.exists(html_path):
            self._build_placeholder()
            return

        self._current_html_path = html_path

        for w in self.winfo_children():
            w.destroy()

        if _HAS_TKINTERWEB:
            self._embed_with_tkinterweb(html_path)
        else:
            self._embed_preview_panel(html_path)

    def _embed_with_tkinterweb(self, html_path: str):
        """Render map HTML directly inside the frame using tkinterweb."""
        try:
            frame = HtmlFrame(self, messages_enabled=False)
            frame.pack(fill="both", expand=True)
            frame.load_file(f"file://{os.path.abspath(html_path)}")
            self._add_toolbar(html_path, frame_above=False)
        except Exception as e:
            # tkinterweb failed — fall back to preview panel
            self._embed_preview_panel(html_path)

    def _embed_preview_panel(self, html_path: str):
        """Show a rich preview card when tkinterweb is unavailable."""
        # Toolbar
        toolbar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=48)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        ctk.CTkLabel(toolbar, text="  🗺️ Route Map",
                     font=FONT_SM_B, text_color=c("accent"), anchor="w").pack(side="left", fill="y")

        ctk.CTkButton(
            toolbar, text="🌐 Open in Browser", command=self._open_browser,
            height=34, **btn_primary()
        ).pack(side="right", padx=8, pady=7)

        ctk.CTkButton(
            toolbar, text="📋 Copy Path", command=lambda: self._copy_path(html_path),
            height=34, **btn_secondary()
        ).pack(side="right", padx=(0, 4), pady=7)

        # Preview card
        card = ctk.CTkFrame(self, fg_color=c("bg_card"), corner_radius=12,
                            border_width=1, border_color=c("border_accent"))
        card.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(card, text="🗺️", font=("", 56)).pack(pady=(32, 8))
        ctk.CTkLabel(card, text="Map Generated Successfully",
                     font=FONT_MD_B, text_color=c("accent")).pack()
        ctk.CTkLabel(
            card,
            text="The interactive route map is saved and ready.\n"
                 "It uses Leaflet + OSRM for real road-aligned routing.\n"
                 "Click 'Open in Browser' to view with full interactivity.",
            font=FONT_SM, text_color=c("text_secondary"), justify="center"
        ).pack(pady=12)

        # File info
        info_frame = ctk.CTkFrame(card, fg_color=c("bg_secondary"), corner_radius=8)
        info_frame.pack(pady=8, padx=40)

        fname = os.path.basename(html_path)
        fsize = os.path.getsize(html_path) / 1024
        for label, val in [("File", fname), ("Size", f"{fsize:.1f} KB"), ("Path", (html_path[:55] + "...") if len(html_path) > 55 else html_path)]:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=f"{label}:", font=FONT_XS,
                         text_color=c("text_muted"), width=50, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, font=FONT_XS,
                         text_color=c("text_primary"), anchor="w").pack(side="left", padx=6)

        # Features list
        ctk.CTkLabel(card, text="Map Features:",
                     font=FONT_XS, text_color=c("text_muted")).pack(pady=(12, 4))
        features = [
            "✅ Road-aligned routing via OSRM (needs internet)",
            "✅ Numbered stop markers (green = start/end)",
            "✅ Straight-line fallback when offline",
            "✅ Dark / Light / Street tile switcher",
            "✅ Click markers for stop details",
        ]
        for f in features:
            ctk.CTkLabel(card, text=f, font=FONT_XS, text_color=c("text_secondary")).pack()

        # Big open button
        ctk.CTkButton(
            card, text="🌐  Open Interactive Map in Browser",
            command=self._open_browser, height=46, **btn_primary()
        ).pack(pady=20, padx=60, fill="x")

    def _add_toolbar(self, html_path: str, frame_above: bool = True):
        """Minimal toolbar when embedded with tkinterweb."""
        toolbar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), height=40)
        if frame_above:
            toolbar.pack(fill="x", before=self.winfo_children()[0])
        else:
            toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        ctk.CTkButton(toolbar, text="🌐 Browser", command=self._open_browser,
                      height=30, **btn_primary()).pack(side="right", padx=6, pady=5)
        ctk.CTkLabel(toolbar, text=f"  {os.path.basename(html_path)}",
                     font=FONT_XS, text_color=c("text_muted"), anchor="w").pack(side="left", fill="y")

    def _open_browser(self):
        if self._current_html_path:
            webbrowser.open(f"file://{os.path.abspath(self._current_html_path)}")

    def _copy_path(self, path: str):
        try:
            self.clipboard_clear()
            self.clipboard_append(path)
        except Exception:
            pass


class MapFrame(ctk.CTkFrame):
    """
    Full-page Maps tab — shows all generated route maps, lets user load them,
    and embeds the map using MapPanel.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color=c("bg_primary"), corner_radius=0)
        self._map_files = []
        self._check_vars = []        # list of (BooleanVar, filepath)
        self._select_all_var = ctk.BooleanVar(value=False)
        self._build()
        self.refresh()

    def _build(self):
        # Toolbar
        toolbar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=60)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        ctk.CTkLabel(toolbar, text="  🗺️ Maps",
                     font=FONT_MD_B, text_color=c("accent"), anchor="w").pack(side="left", fill="y")
        ctk.CTkButton(toolbar, text="🔄 Refresh", command=self.refresh,
                      height=36, **btn_secondary()).pack(side="right", padx=12, pady=12)

        # Split layout
        main = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=4)
        main.rowconfigure(0, weight=1)

        # File list panel
        list_panel = ctk.CTkFrame(main, fg_color=c("bg_card"), corner_radius=12,
                                  border_width=1, border_color=c("border"))
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)

        # Header with select-all + delete selected
        top = ctk.CTkFrame(list_panel, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(10, 2))

        self.sel_all_chk = ctk.CTkCheckBox(
            top, text="  Saved Maps", variable=self._select_all_var,
            command=self._toggle_select_all,
            font=FONT_SM_B, text_color=c("accent"),
            checkbox_width=15, checkbox_height=15,
            fg_color=c("danger"), hover_color="#CC3355",
            checkmark_color="white",
        )
        self.sel_all_chk.pack(side="left")

        self.del_sel_btn = ctk.CTkButton(
            top, text="🗑 Delete", command=self._delete_selected,
            height=24, width=80,
            fg_color=c("danger"), hover_color="#CC3355",
            text_color="white", font=FONT_XS, corner_radius=6,
            state="disabled",
        )
        self.del_sel_btn.pack(side="right")

        self.sel_count_label = ctk.CTkLabel(
            list_panel, text="", font=FONT_XS, text_color=c("warning")
        )
        self.sel_count_label.pack(fill="x", padx=8)

        self.file_scroll = ctk.CTkScrollableFrame(list_panel, fg_color="transparent")
        self.file_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # Map display panel
        self.map_panel = MapPanel(main)
        self.map_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

    def refresh(self):
        """Scan maps directory and populate file list."""
        from maps.map_service import MAPS_DIR
        for w in self.file_scroll.winfo_children():
            w.destroy()
        self._check_vars = []
        self._select_all_var.set(False)
        self._update_sel_count()

        try:
            files = sorted(
                [f for f in os.listdir(MAPS_DIR) if f.endswith(".html")],
                reverse=True
            )
        except Exception:
            files = []

        self._map_files = files

        if not files:
            ctk.CTkLabel(self.file_scroll, text="No maps generated yet.\nRun an optimization first.",
                         font=FONT_XS, text_color=c("text_muted")).pack(pady=20)
            return

        for fname in files:
            fpath = os.path.join(MAPS_DIR, fname)
            fsize = os.path.getsize(fpath) / 1024

            card = ctk.CTkFrame(self.file_scroll, fg_color=c("bg_secondary"), corner_radius=8)
            card.pack(fill="x", pady=3)

            # ── Checkbox row ──
            chk_row = ctk.CTkFrame(card, fg_color="transparent")
            chk_row.pack(fill="x", padx=6, pady=(6, 0))

            var = ctk.BooleanVar(value=False)
            var.trace_add("write", lambda *_, v=var: self._on_check_change())
            self._check_vars.append((var, fpath))

            ctk.CTkCheckBox(
                chk_row, text=fname[:26], variable=var,
                font=FONT_XS, text_color=c("text_primary"),
                checkbox_width=14, checkbox_height=14,
                fg_color=c("danger"), hover_color="#CC3355",
                checkmark_color="white",
            ).pack(side="left")

            ctk.CTkLabel(card, text=f"{fsize:.1f} KB",
                         font=FONT_XS, text_color=c("text_muted"), anchor="w").pack(fill="x", padx=8)

            # ── Action buttons ──
            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(fill="x", padx=6, pady=(2, 6))

            ctk.CTkButton(btn_row, text="Load", width=55, height=26,
                          fg_color=c("accent"), hover_color=c("accent_hover"),
                          text_color="#000", font=FONT_XS, corner_radius=6,
                          command=lambda p=fpath: self.map_panel.load_map(p)).pack(side="left", padx=2)

            ctk.CTkButton(btn_row, text="Browser", width=65, height=26,
                          fg_color=c("bg_card"), hover_color=c("border"),
                          text_color=c("text_primary"), font=FONT_XS, corner_radius=6,
                          border_width=1, border_color=c("border"),
                          command=lambda p=fpath: webbrowser.open(
                              f"file:///{os.path.abspath(p).replace(os.sep, '/')}"
                          )).pack(side="left", padx=2)

            ctk.CTkButton(btn_row, text="🗑", width=28, height=26,
                          fg_color=c("danger"), hover_color="#CC3355",
                          text_color="white", font=FONT_XS, corner_radius=6,
                          command=lambda p=fpath, cw=card: self._delete_one(p, cw)).pack(side="right", padx=2)

        # Auto-load the most recent map
        if files:
            newest = os.path.join(MAPS_DIR, files[0])
            self.map_panel.load_map(newest)

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
        from tkinter import messagebox
        selected = [(v, fp) for v, fp in self._check_vars if v.get()]
        if not selected:
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete {len(selected)} map file(s)?\nThis cannot be undone."
        ):
            return
        for _, fp in selected:
            try:
                os.remove(fp)
            except Exception:
                pass
        self.refresh()

    def _delete_one(self, fpath: str, card_widget):
        try:
            os.remove(fpath)
            card_widget.destroy()
            # Remove from check_vars
            self._check_vars = [(v, fp) for v, fp in self._check_vars if fp != fpath]
            self._update_sel_count()
        except Exception:
            pass
