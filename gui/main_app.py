"""
Main Application Window — sidebar navigation, frame switching
"""

import customtkinter as ctk
from gui.theme import c, FONT_LG, FONT_MD_B, FONT_SM, FONT_SM_B, FONT_XS, set_theme
from services.auth_service import get_current_user, logout


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Last-Mile Delivery Route Optimizer")
        self.geometry("1280x780")
        self.minsize(1100, 680)
        self.configure(fg_color=c("bg_primary"))
        ctk.set_appearance_mode("dark")
        self._active_frame = None
        self._frames = {}
        self._build()
        self.navigate("dashboard")

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──
        self.sidebar = ctk.CTkFrame(self, fg_color=c("bg_sidebar"), width=210, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color=c("bg_secondary"), height=90, corner_radius=0)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text="🚚", font=("Courier New", 32)).pack(pady=(12, 0))
        ctk.CTkLabel(logo_frame, text="RouteOpt", font=FONT_MD_B, text_color=c("accent")).pack()

        # Nav items
        nav_items = [
            ("dashboard",  "🏠", "Dashboard"),
            ("addresses",  "📦", "Deliveries"),
            ("optimizer",  "🚀", "Optimizer"),
            ("maps",       "🗺️", "Maps"),
            ("analytics",  "📊", "Analytics"),
            ("history",    "📂", "History"),
        ]

        self._nav_buttons = {}
        nav_section = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_section.pack(fill="x", pady=16)

        for key, icon, label in nav_items:
            btn = ctk.CTkButton(
                nav_section,
                text=f"  {icon}  {label}",
                anchor="w",
                command=lambda k=key: self.navigate(k),
                fg_color="transparent",
                hover_color=c("bg_card"),
                text_color=c("text_secondary"),
                font=FONT_SM,
                corner_radius=8,
                height=44,
            )
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = btn

        # Bottom section
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=12)

        # Theme toggle
        self._theme_var = ctk.StringVar(value="dark")
        ctk.CTkLabel(bottom, text="Theme", font=FONT_XS,
                     text_color=c("text_muted")).pack()
        ctk.CTkSegmentedButton(
            bottom,
            values=["dark", "light"],
            variable=self._theme_var,
            command=self._toggle_theme,
            font=FONT_XS,
            selected_color=c("accent"),
            selected_hover_color=c("accent_hover"),
            unselected_color=c("bg_card"),
            unselected_hover_color=c("border"),
            text_color=c("text_primary"),
            fg_color=c("bg_secondary"),
        ).pack(fill="x", padx=10, pady=(2, 10))

        # User info
        user = get_current_user()
        if user:
            user_frame = ctk.CTkFrame(bottom, fg_color=c("bg_card"), corner_radius=8)
            user_frame.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(user_frame, text=f"👤 {user.username}",
                         font=FONT_XS, text_color=c("text_primary"), anchor="w").pack(
                fill="x", padx=8, pady=(6, 0))
            ctk.CTkLabel(user_frame, text=user.email[:24],
                         font=FONT_XS, text_color=c("text_muted"), anchor="w").pack(
                fill="x", padx=8)
            ctk.CTkButton(
                user_frame, text="Logout", command=self._logout,
                height=28, fg_color=c("danger"), hover_color="#CC3355",
                text_color="white", font=FONT_XS, corner_radius=6,
            ).pack(fill="x", padx=8, pady=6)

        # ── Content area ──
        self.content = ctk.CTkFrame(self, fg_color=c("bg_primary"), corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")

    def navigate(self, key: str):
        self._current_page = key
        # Highlight active nav
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=c("bg_card"), text_color=c("accent"), font=FONT_SM_B)
            else:
                btn.configure(fg_color="transparent", text_color=c("text_secondary"), font=FONT_SM)

        # Destroy previous frame
        if self._active_frame:
            self._active_frame.destroy()

        # Build frame
        frame = self._create_frame(key)
        frame.pack(fill="both", expand=True)
        self._active_frame = frame

    def _create_frame(self, key: str):
        from gui.dashboard_frame import DashboardFrame
        from gui.address_frame import AddressFrame
        from gui.optimizer_frame import OptimizerFrame
        from gui.analytics_frame import AnalyticsFrame
        from gui.history_frame import HistoryFrame
        from gui.map_frame import MapFrame

        mapping = {
            "dashboard": lambda: DashboardFrame(self.content, navigate_callback=self.navigate),
            "addresses": lambda: AddressFrame(self.content),
            "optimizer": lambda: OptimizerFrame(self.content, navigate_callback=self.navigate),
            "maps":      lambda: MapFrame(self.content),
            "analytics": lambda: AnalyticsFrame(self.content),
            "history":   lambda: HistoryFrame(self.content),
        }
        factory = mapping.get(key)
        if factory:
            return factory()

        # Fallback
        f = ctk.CTkFrame(self.content, fg_color=c("bg_primary"))
        ctk.CTkLabel(f, text=f"Page '{key}' not found.", font=FONT_SM,
                     text_color=c("text_muted")).pack(expand=True)
        return f

    def _toggle_theme(self, value: str):
        set_theme(value)
        mode = "dark" if value == "dark" else "light"
        ctk.set_appearance_mode(mode)
        # Rebuild the entire window so all widgets pick up new theme colors
        current_page = None
        for k, btn in self._nav_buttons.items():
            try:
                if btn.cget("fg_color") not in ("transparent", c("bg_sidebar")):
                    current_page = k
                    break
            except Exception:
                pass
        # Destroy and rebuild
        for widget in self.winfo_children():
            widget.destroy()
        self._nav_buttons = {}
        self._active_frame = None
        self.configure(fg_color=c("bg_primary"))
        self._build()
        self._theme_var.set(value)
        self.navigate(getattr(self, "_current_page", None) or "dashboard")

    def _logout(self):
        logout()
        self.withdraw()
        def _relaunch():
            login_app = _LoginRoot()
            login_app.mainloop()
        self.after(100, _relaunch)


def _launch_login():
    """Entry point: show login window, then open main app on success."""

    # Use LoginWindow as a proper CTk root (not a hidden parent + Toplevel)
    # This avoids stale after() callbacks firing on a destroyed hidden root.
    login_app = _LoginRoot()
    login_app.mainloop()


class _LoginRoot(ctk.CTk):
    """Login screen as a first-class CTk root window."""

    def __init__(self):
        super().__init__()
        self.title("Last-Mile Delivery Optimizer — Login")
        self.geometry("480x580")
        self.resizable(False, False)
        self.configure(fg_color=c("bg_primary"))
        self._mode = "login"
        self._build()

    def _build(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=c("bg_secondary"), corner_radius=0, height=120)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="🚚", font=("", 38)).pack(pady=(18, 0))
        ctk.CTkLabel(header, text="Route Optimizer", font=FONT_LG,
                     text_color=c("accent")).pack()

        # ── Tab buttons ──
        tab_frame = ctk.CTkFrame(self, fg_color=c("bg_primary"), height=44)
        tab_frame.pack(fill="x", padx=30, pady=(16, 0))

        self.login_tab_btn = ctk.CTkButton(
            tab_frame, text="LOGIN",
            command=lambda: self._switch("login"),
            fg_color=c("accent"), hover_color=c("accent_hover"),
            text_color="#000", font=FONT_SM_B, corner_radius=8, height=36,
        )
        self.login_tab_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.register_tab_btn = ctk.CTkButton(
            tab_frame, text="REGISTER",
            command=lambda: self._switch("register"),
            fg_color=c("bg_card"), hover_color=c("border"),
            text_color=c("text_secondary"), font=FONT_SM_B, corner_radius=8, height=36,
        )
        self.register_tab_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.form_frame = ctk.CTkFrame(self, fg_color=c("bg_primary"))
        self.form_frame.pack(fill="both", expand=True, padx=30, pady=16)
        self._build_login_form()

    def _switch(self, mode: str):
        self._mode = mode
        for w in self.form_frame.winfo_children():
            w.destroy()
        if mode == "login":
            self.login_tab_btn.configure(fg_color=c("accent"), text_color="#000")
            self.register_tab_btn.configure(fg_color=c("bg_card"), text_color=c("text_secondary"))
            self._build_login_form()
        else:
            self.register_tab_btn.configure(fg_color=c("accent"), text_color="#000")
            self.login_tab_btn.configure(fg_color=c("bg_card"), text_color=c("text_secondary"))
            self._build_register_form()

    def _lbl(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=FONT_SM,
                     text_color=c("text_secondary"), anchor="w").pack(fill="x", pady=(8, 2))

    def _ent(self, parent, placeholder="", show=""):
        e = ctk.CTkEntry(parent, placeholder_text=placeholder, show=show,
                         height=40,
                         fg_color=c("input_bg"), border_color=c("border"),
                         text_color=c("text_primary"),
                         placeholder_text_color=c("text_muted"),
                         font=FONT_SM, corner_radius=8)
        e.pack(fill="x")
        return e

    def _build_login_form(self):
        f = self.form_frame
        self._lbl(f, "Username")
        self.login_user = self._ent(f, "Enter username")
        self._lbl(f, "Password")
        self.login_pass = self._ent(f, "Enter password", show="•")

        self.remember_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            f, text="Remember me", variable=self.remember_var,
            font=FONT_SM, text_color=c("text_secondary"),
            checkbox_width=18, checkbox_height=18,
            fg_color=c("accent"), hover_color=c("accent_hover"),
            checkmark_color=c("bg_primary"),
        ).pack(anchor="w", pady=8)

        self.login_status = ctk.CTkLabel(f, text="", font=FONT_SM, text_color=c("danger"))
        self.login_status.pack()

        ctk.CTkButton(f, text="LOGIN  →", command=self._do_login,
                      height=44,
                      fg_color=c("accent"), hover_color=c("accent_hover"),
                      text_color="#000", font=FONT_SM_B, corner_radius=8,
                      ).pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(f, text="Demo: admin / admin123", font=("", 10),
                     text_color=c("text_muted")).pack(pady=(10, 0))

    def _build_register_form(self):
        f = self.form_frame
        self._lbl(f, "Full Name")
        self.reg_name  = self._ent(f, "Your full name")
        self._lbl(f, "Username")
        self.reg_user  = self._ent(f, "Choose a username")
        self._lbl(f, "Email")
        self.reg_email = self._ent(f, "you@example.com")
        self._lbl(f, "Password")
        self.reg_pass  = self._ent(f, "Min 6 characters", show="•")

        self.reg_status = ctk.CTkLabel(f, text="", font=FONT_SM, text_color=c("danger"))
        self.reg_status.pack(pady=(6, 0))

        ctk.CTkButton(f, text="CREATE ACCOUNT  →", command=self._do_register,
                      height=44,
                      fg_color=c("accent"), hover_color=c("accent_hover"),
                      text_color="#000", font=FONT_SM_B, corner_radius=8,
                      ).pack(fill="x", pady=(8, 0))

    def _do_login(self):
        user = self.login_user.get().strip()
        pwd  = self.login_pass.get().strip()
        if not user or not pwd:
            self.login_status.configure(text="Please fill in all fields.")
            return
        from services.auth_service import login
        ok, msg, uid = login(user, pwd, self.remember_var.get())
        if ok:
            self._open_main_app()
        else:
            self.login_status.configure(text=f"✗ {msg}")

    def _open_main_app(self):
        # Withdraw (hide) instead of destroy — avoids CTk internal after()
        # callbacks (update, check_dpi_scaling) firing on a dead widget.
        # The login window is never shown again so it doesn't matter that
        # it still exists in memory; it will be cleaned up when the process exits.
        self.withdraw()
        try:
            app = MainApp()
            app.mainloop()
        finally:
            # Only called after MainApp closes — quit the hidden login root cleanly
            try:
                self.quit()
            except Exception:
                pass

    def _do_register(self):
        name  = self.reg_name.get().strip()
        user  = self.reg_user.get().strip()
        email = self.reg_email.get().strip()
        pwd   = self.reg_pass.get().strip()
        from services.auth_service import register
        ok, msg = register(user, email, pwd, name)
        if ok:
            self.reg_status.configure(text_color=c("success"), text=f"✓ {msg} Please login.")
            self.after(1500, lambda: self._switch("login"))
        else:
            self.reg_status.configure(text_color=c("danger"), text=f"✗ {msg}")
