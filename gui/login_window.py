"""
Login & Registration Window
"""

import customtkinter as ctk
from gui.theme import c, FONT_XL, FONT_LG, FONT_MD, FONT_SM, FONT_SM_B, btn_primary, entry_style
from services.auth_service import login, register


class LoginWindow(ctk.CTkToplevel):
    """Standalone login/register dialog."""

    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.on_success = on_success
        self.title("Last-Mile Delivery Optimizer — Login")
        self.geometry("480x580")
        self.resizable(False, False)
        self.configure(fg_color=c("bg_primary"))
        self._mode = "login"
        self._build()
        self.grab_set()
        self.lift()
        self.focus_force()

    def _build(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=120)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🚚", font=("Courier New", 40)
        ).pack(pady=(20, 0))
        ctk.CTkLabel(
            header, text="Route Optimizer", font=FONT_LG,
            text_color=c("accent")
        ).pack()

        # ── Tab buttons ──
        tab_frame = ctk.CTkFrame(self, fg_color=c("bg_primary"), height=44)
        tab_frame.pack(fill="x", padx=30, pady=(16, 0))

        self.login_tab_btn = ctk.CTkButton(
            tab_frame, text="LOGIN", command=lambda: self._switch("login"),
            fg_color=c("accent"), hover_color=c("accent_hover"),
            text_color="#000", font=FONT_SM_B, corner_radius=8, height=36,
        )
        self.login_tab_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.register_tab_btn = ctk.CTkButton(
            tab_frame, text="REGISTER", command=lambda: self._switch("register"),
            fg_color=c("bg_card"), hover_color=c("border"),
            text_color=c("text_secondary"), font=FONT_SM_B, corner_radius=8, height=36,
        )
        self.register_tab_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ── Form frame ──
        self.form_frame = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        self.form_frame.pack(fill="both", expand=True, padx=30, pady=16)

        self._build_login_form()

    def _switch(self, mode: str):
        self._mode = mode
        for widget in self.form_frame.winfo_children():
            widget.destroy()

        if mode == "login":
            self.login_tab_btn.configure(fg_color=c("accent"), text_color="#000")
            self.register_tab_btn.configure(fg_color=c("bg_card"), text_color=c("text_secondary"))
            self._build_login_form()
        else:
            self.register_tab_btn.configure(fg_color=c("accent"), text_color="#000")
            self.login_tab_btn.configure(fg_color=c("bg_card"), text_color=c("text_secondary"))
            self._build_register_form()

    def _label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=FONT_SM, text_color=c("text_secondary"),
                     anchor="w").pack(fill="x", pady=(8, 2))

    def _entry(self, parent, placeholder="", show=""):
        e = ctk.CTkEntry(parent, placeholder_text=placeholder, show=show,
                         height=40, **entry_style())
        e.pack(fill="x")
        return e

    def _build_login_form(self):
        f = self.form_frame
        self._label(f, "Username")
        self.login_user_entry = self._entry(f, "Enter username")

        self._label(f, "Password")
        self.login_pass_entry = self._entry(f, "Enter password", show="•")

        self.remember_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            f, text="Remember me", variable=self.remember_var,
            font=FONT_SM, text_color=c("text_secondary"),
            checkbox_width=18, checkbox_height=18,
            checkmark_color=c("bg_primary"), fg_color=c("accent"),
            hover_color=c("accent_hover"),
        ).pack(anchor="w", pady=8)

        self.login_status = ctk.CTkLabel(f, text="", font=FONT_SM, text_color=c("danger"))
        self.login_status.pack()

        ctk.CTkButton(
            f, text="LOGIN  →", command=self._do_login,
            height=44, **btn_primary()
        ).pack(fill="x", pady=(8, 0))

        # Demo hint
        ctk.CTkLabel(
            f, text="Demo: admin / admin123", font=("Courier New", 9),
            text_color=c("text_muted")
        ).pack(pady=(12, 0))

    def _build_register_form(self):
        f = self.form_frame
        self._label(f, "Full Name")
        self.reg_name_entry = self._entry(f, "Your full name")

        self._label(f, "Username")
        self.reg_user_entry = self._entry(f, "Choose a username")

        self._label(f, "Email")
        self.reg_email_entry = self._entry(f, "you@example.com")

        self._label(f, "Password")
        self.reg_pass_entry = self._entry(f, "Min 6 characters", show="•")

        self.reg_status = ctk.CTkLabel(f, text="", font=FONT_SM, text_color=c("danger"))
        self.reg_status.pack(pady=(6, 0))

        ctk.CTkButton(
            f, text="CREATE ACCOUNT  →", command=self._do_register,
            height=44, **btn_primary()
        ).pack(fill="x", pady=(8, 0))

    def _do_login(self):
        user = self.login_user_entry.get().strip()
        pwd = self.login_pass_entry.get().strip()
        remember = self.remember_var.get()

        if not user or not pwd:
            self.login_status.configure(text="Please fill in all fields.")
            return

        ok, msg, uid = login(user, pwd, remember)
        if ok:
            self.destroy()
            self.on_success(uid)
        else:
            self.login_status.configure(text=f"✗ {msg}")

    def _do_register(self):
        name = self.reg_name_entry.get().strip()
        user = self.reg_user_entry.get().strip()
        email = self.reg_email_entry.get().strip()
        pwd = self.reg_pass_entry.get().strip()

        ok, msg = register(user, email, pwd, name)
        if ok:
            self.reg_status.configure(text_color=c("success"), text=f"✓ {msg} Please login.")
            self.after(1500, lambda: self._switch("login"))
        else:
            self.reg_status.configure(text_color=c("danger"), text=f"✗ {msg}")
