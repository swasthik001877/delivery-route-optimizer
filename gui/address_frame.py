"""
Address Management Frame — add, edit, delete, import, search, geocode deliveries
Supports checkbox multi-select for bulk delete.
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from gui.theme import c, FONT_MD, FONT_MD_B, FONT_SM, FONT_SM_B, FONT_XS, card_style, btn_primary, btn_danger, btn_secondary, entry_style
from services.delivery_service import (
    add_delivery, delete_delivery, update_delivery,
    get_all_deliveries, search_deliveries, import_csv, import_json
)
from services.geocoding import geocode_all_pending
from services.auth_service import get_current_user_id


class AddressFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=c("bg_primary"), corner_radius=0)
        self._deliveries = []
        self._check_vars = []   # list of (BooleanVar, delivery_id)
        self._select_all_var = ctk.BooleanVar(value=False)
        self._build()
        self.refresh()

    def _build(self):
        # ── Top toolbar ──
        toolbar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=60)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        ctk.CTkLabel(toolbar, text="  📦 Address Management",
                     font=FONT_MD_B, text_color=c("accent"), anchor="w").pack(side="left", fill="y")

        for text, cmd, style in [
            ("+ Add",           self._show_add_dialog, btn_primary()),
            ("📥 Import CSV",   self._import_csv,      btn_secondary()),
            ("📥 Import JSON",  self._import_json,     btn_secondary()),
            ("🌍 Geocode All",  self._geocode_all,     btn_secondary()),
            ("🗺️ Map View",     self._show_map,        btn_secondary()),
        ]:
            ctk.CTkButton(toolbar, text=text, command=cmd, height=36, width=120, **style).pack(
                side="right", padx=4, pady=12
            )

        # ── Selection action bar ──
        self.sel_bar = ctk.CTkFrame(self, fg_color=c("bg_secondary"), height=40)
        self.sel_bar.pack(fill="x", padx=20, pady=(6, 0))
        self.sel_bar.pack_propagate(False)

        # Select-all checkbox
        self.sel_all_chk = ctk.CTkCheckBox(
            self.sel_bar, text="Select All", variable=self._select_all_var,
            command=self._toggle_select_all,
            font=FONT_XS, text_color=c("text_secondary"),
            checkbox_width=16, checkbox_height=16,
            fg_color=c("accent"), hover_color=c("accent_hover"),
            checkmark_color=c("bg_primary"),
        )
        self.sel_all_chk.pack(side="left", padx=10)

        self.sel_count_label = ctk.CTkLabel(
            self.sel_bar, text="", font=FONT_XS, text_color=c("text_muted")
        )
        self.sel_count_label.pack(side="left", padx=8)

        self.del_sel_btn = ctk.CTkButton(
            self.sel_bar, text="🗑 Delete Selected", command=self._delete_selected,
            height=28, width=140,
            fg_color=c("danger"), hover_color="#CC3355",
            text_color="white", font=FONT_XS, corner_radius=6,
            state="disabled",
        )
        self.del_sel_btn.pack(side="right", padx=10, pady=6)

        # ── Search bar ──
        search_frame = ctk.CTkFrame(self, fg_color=c("bg_primary"), height=50)
        search_frame.pack(fill="x", padx=20, pady=(6, 0))
        search_frame.pack_propagate(False)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        self.search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var,
            placeholder_text="🔍 Search by name, address, or ID…",
            height=38, **entry_style()
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.count_label = ctk.CTkLabel(search_frame, text="0 records",
                                        font=FONT_XS, text_color=c("text_muted"))
        self.count_label.pack(side="right")

        # ── Table header ──
        col_widths = [30, 100, 150, 260, 90, 90, 110, 80]
        col_names  = ["", "ID", "Customer", "Address", "Latitude", "Longitude", "Contact", "Actions"]
        header = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=32)
        header.pack(fill="x", padx=20, pady=(4, 0))
        header.pack_propagate(False)
        for name, w in zip(col_names, col_widths):
            ctk.CTkLabel(header, text=name, font=FONT_XS, text_color=c("text_muted"),
                         width=w, anchor="w").pack(side="left", padx=4)

        # ── Scrollable table ──
        self.table_frame = ctk.CTkScrollableFrame(
            self, fg_color=c("bg_primary"), scrollbar_button_color=c("scrollbar")
        )
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Status bar
        self.status_bar = ctk.CTkLabel(self, text="", font=FONT_XS,
                                       text_color=c("text_muted"), anchor="w")
        self.status_bar.pack(fill="x", padx=20, pady=(0, 6))

    def refresh(self):
        self._deliveries = get_all_deliveries()
        self._select_all_var.set(False)
        self._render_table(self._deliveries)

    def _render_table(self, deliveries):
        for w in self.table_frame.winfo_children():
            w.destroy()
        self._check_vars = []
        self.count_label.configure(text=f"{len(deliveries)} records")
        self._update_sel_count()

        if not deliveries:
            ctk.CTkLabel(self.table_frame,
                         text="No deliveries found.\nClick '+ Add' or import a file.",
                         font=FONT_SM, text_color=c("text_muted")).pack(pady=40)
            return

        for i, d in enumerate(deliveries):
            bg = c("table_row_odd") if i % 2 == 0 else c("table_row_even")
            row = ctk.CTkFrame(self.table_frame, fg_color=bg, height=36)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            # ── Checkbox ──
            var = ctk.BooleanVar(value=False)
            var.trace_add("write", lambda *_, v=var: self._on_check_change())
            self._check_vars.append((var, d.delivery_id))

            ctk.CTkCheckBox(
                row, text="", variable=var,
                checkbox_width=16, checkbox_height=16,
                fg_color=c("danger"), hover_color="#CC3355",
                checkmark_color="white", width=30,
            ).pack(side="left", padx=6)

            # ── Data columns ──
            values = [
                d.delivery_id,
                d.customer_name[:18],
                d.address[:32],
                f"{d.latitude:.4f}" if d.latitude else "—",
                f"{d.longitude:.4f}" if d.longitude else "—",
                d.contact_number or "—",
            ]
            widths = [100, 150, 260, 90, 90, 110]
            for val, w in zip(values, widths):
                ctk.CTkLabel(row, text=val, font=FONT_XS,
                             text_color=c("text_primary"), width=w, anchor="w").pack(side="left", padx=4)

            dot_color = c("success") if d.is_geocoded else c("warning")
            ctk.CTkLabel(row, text="●", font=FONT_XS, text_color=dot_color, width=8).pack(side="left")

            # ── Edit / Delete buttons ──
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right", padx=4)

            ctk.CTkButton(
                btn_frame, text="✏", width=28, height=24,
                fg_color=c("accent2"), hover_color="#5A3FCC",
                text_color="white", corner_radius=4, font=FONT_XS,
                command=lambda d=d: self._show_edit_dialog(d)
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_frame, text="🗑", width=28, height=24,
                fg_color=c("danger"), hover_color="#CC3355",
                text_color="white", corner_radius=4, font=FONT_XS,
                command=lambda d=d: self._delete_one(d.delivery_id)
            ).pack(side="left", padx=2)

    # ── Checkbox helpers ──────────────────────────────────────────────────────

    def _on_check_change(self):
        self._update_sel_count()

    def _update_sel_count(self):
        selected = sum(1 for v, _ in self._check_vars if v.get())
        total = len(self._check_vars)
        if selected:
            self.sel_count_label.configure(
                text=f"{selected} of {total} selected",
                text_color=c("warning")
            )
            self.del_sel_btn.configure(state="normal")
        else:
            self.sel_count_label.configure(text="", text_color=c("text_muted"))
            self.del_sel_btn.configure(state="disabled")

        # Sync select-all checkbox state
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
        selected = [(v, did) for v, did in self._check_vars if v.get()]
        if not selected:
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete {len(selected)} selected delivery record(s)?\nThis cannot be undone."
        ):
            return
        count = 0
        for _, did in selected:
            ok, _ = delete_delivery(did)
            if ok:
                count += 1
        self.status_bar.configure(
            text=f"✓ Deleted {count} record(s).",
            text_color=c("success")
        )
        self.refresh()

    def _delete_one(self, delivery_id):
        if messagebox.askyesno("Confirm Delete", f"Delete delivery {delivery_id}?"):
            ok, msg = delete_delivery(delivery_id)
            self.status_bar.configure(
                text=f"{'✓' if ok else '✗'} {msg}",
                text_color=c("success") if ok else c("danger")
            )
            if ok:
                self.refresh()

    # ── Search ────────────────────────────────────────────────────────────────

    def _on_search(self):
        query = self.search_var.get().strip()
        results = search_deliveries(query) if query else self._deliveries
        self._render_table(results)

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _show_add_dialog(self):
        AddEditDialog(self, title="Add Delivery", on_save=self._save_new)

    def _show_edit_dialog(self, delivery):
        AddEditDialog(self, title="Edit Delivery", delivery=delivery,
                      on_save=lambda data: self._save_edit(delivery.delivery_id, data))

    def _save_new(self, data):
        ok, msg, _ = add_delivery(
            data["customer_name"], data["address"], data["contact"],
            data["notes"], user_id=get_current_user_id()
        )
        self.status_bar.configure(
            text=f"{'✓' if ok else '✗'} {msg}",
            text_color=c("success") if ok else c("danger")
        )
        if ok:
            self.refresh()

    def _save_edit(self, delivery_id, data):
        ok, msg = update_delivery(delivery_id, **{
            "customer_name": data["customer_name"],
            "address":       data["address"],
            "contact_number": data["contact"],
            "notes":         data["notes"],
        })
        self.status_bar.configure(
            text=f"{'✓' if ok else '✗'} {msg}",
            text_color=c("success") if ok else c("danger")
        )
        if ok:
            self.refresh()

    def _import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            ok, fail, errors = import_csv(path, get_current_user_id())
            messagebox.showinfo("Import Result", f"Added: {ok}\nFailed: {fail}\n" + "\n".join(errors[:5]))
            self.refresh()

    def _import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            ok, fail, errors = import_json(path, get_current_user_id())
            messagebox.showinfo("Import Result", f"Added: {ok}\nFailed: {fail}\n" + "\n".join(errors[:5]))
            self.refresh()

    def _geocode_all(self):
        self.status_bar.configure(text="🌍 Geocoding in background…", text_color=c("accent"))
        def _run():
            succ, fail = geocode_all_pending()
            self.after(0, lambda: self.status_bar.configure(
                text=f"✓ Geocoded: {succ} success, {fail} failed",
                text_color=c("success")
            ))
            self.after(0, self.refresh)
        threading.Thread(target=_run, daemon=True).start()

    def _show_map(self):
        from maps.map_service import generate_delivery_overview_map
        deliveries = [d for d in self._deliveries if d.is_geocoded]
        if not deliveries:
            messagebox.showwarning("No Data", "No geocoded deliveries to map.")
            return
        threading.Thread(
            target=lambda: generate_delivery_overview_map(deliveries, open_browser=True),
            daemon=True
        ).start()


class AddEditDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, on_save, delivery=None):
        super().__init__(parent)
        self.on_save = on_save
        self.title(title)
        self.geometry("460x420")
        self.resizable(False, False)
        self.configure(fg_color=c("bg_primary"))
        self.grab_set()

        ctk.CTkLabel(self, text=title, font=FONT_MD_B,
                     text_color=c("accent")).pack(pady=(16, 8))

        form = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        form.pack(fill="both", expand=True, padx=24)

        def lbl(txt):
            ctk.CTkLabel(form, text=txt, font=FONT_XS,
                         text_color=c("text_secondary"), anchor="w").pack(fill="x", pady=(6, 1))

        def ent(ph="", val=""):
            e = ctk.CTkEntry(form, placeholder_text=ph, height=36, **entry_style())
            if val:
                e.insert(0, val)
            e.pack(fill="x")
            return e

        lbl("Customer Name *")
        self.name_entry    = ent("Full name",          delivery.customer_name  if delivery else "")
        lbl("Full Address *")
        self.addr_entry    = ent("Street, City, Country", delivery.address     if delivery else "")
        lbl("Contact Number")
        self.contact_entry = ent("+91 9876543210",     delivery.contact_number if delivery else "")
        lbl("Notes")
        self.notes_entry   = ent("Optional notes",     delivery.notes          if delivery else "")

        self.status = ctk.CTkLabel(form, text="", font=FONT_XS, text_color=c("danger"))
        self.status.pack(pady=4)

        btn_row = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        btn_row.pack(fill="x", padx=24, pady=12)

        ctk.CTkButton(btn_row, text="Save", command=self._save,
                      height=38, **btn_primary()).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy,
                      height=38, **btn_secondary()).pack(side="right")

    def _save(self):
        name    = self.name_entry.get().strip()
        addr    = self.addr_entry.get().strip()
        contact = self.contact_entry.get().strip()
        notes   = self.notes_entry.get().strip()
        if not name or not addr:
            self.status.configure(text="Name and Address are required.")
            return
        self.on_save({"customer_name": name, "address": addr,
                      "contact": contact, "notes": notes})
        self.destroy()
