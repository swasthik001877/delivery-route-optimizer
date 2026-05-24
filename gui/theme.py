"""
GUI Theme — color palette, fonts, and style constants for all CTk widgets
"""

# ── Color Palette ──────────────────────────────────────────────────────────────
DARK = {
    "bg_primary":    "#080818",
    "bg_secondary":  "#0d0d28",
    "bg_card":       "#111130",
    "bg_sidebar":    "#080820",
    "accent":        "#00D4FF",
    "accent_hover":  "#00A8D0",
    "accent2":       "#7B61FF",
    "accent3":       "#A8FF78",
    "danger":        "#FF4C6A",
    "warning":       "#FFB347",
    "success":       "#4CFFAB",
    "text_primary":  "#F0F0FF",
    "text_secondary":"#8888BB",
    "text_muted":    "#4A4A7A",
    "border":        "#1E1E4A",
    "border_accent": "#1A4A5A",
    "input_bg":      "#0a0a22",
    "table_row_odd": "#0f0f2a",
    "table_row_even":"#13133a",
    "scrollbar":     "#2A2A5A",
}

LIGHT = {
    "bg_primary":    "#F4F6FB",
    "bg_secondary":  "#EAECF5",
    "bg_card":       "#FFFFFF",
    "bg_sidebar":    "#1E2A4A",
    "accent":        "#2563EB",
    "accent_hover":  "#1D4ED8",
    "accent2":       "#7C3AED",
    "accent3":       "#059669",
    "danger":        "#DC2626",
    "warning":       "#D97706",
    "success":       "#16A34A",
    "text_primary":  "#111827",
    "text_secondary":"#6B7280",
    "text_muted":    "#9CA3AF",
    "border":        "#E5E7EB",
    "border_accent": "#93C5FD",
    "input_bg":      "#F9FAFB",
    "table_row_odd": "#F9FAFB",
    "table_row_even":"#FFFFFF",
    "scrollbar":     "#CBD5E1",
}

_active_theme = DARK


def get_theme():
    return _active_theme


def set_theme(name: str):
    global _active_theme
    _active_theme = DARK if name == "dark" else LIGHT


def c(key: str) -> str:
    """Shorthand: get color from active theme."""
    return _active_theme.get(key, "#FF00FF")


# ── Font sizes ─────────────────────────────────────────────────────────────────
import sys as _sys
_FONT = "Segoe UI" if _sys.platform == "win32" else "Helvetica Neue" if _sys.platform == "darwin" else "DejaVu Sans"

FONT_XL    = (_FONT, 26, "bold")
FONT_LG    = (_FONT, 20, "bold")
FONT_MD    = (_FONT, 16)
FONT_MD_B  = (_FONT, 16, "bold")
FONT_SM    = (_FONT, 14)
FONT_SM_B  = (_FONT, 14, "bold")
FONT_XS    = (_FONT, 13)

# ── Widget style dicts ─────────────────────────────────────────────────────────
def btn_primary():
    return dict(
        fg_color=c("accent"),
        hover_color=c("accent_hover"),
        text_color="#000000",
        font=FONT_SM_B,
        corner_radius=8,
    )

def btn_danger():
    return dict(
        fg_color=c("danger"),
        hover_color="#CC3355",
        text_color="#FFFFFF",
        font=FONT_SM_B,
        corner_radius=8,
    )

def btn_secondary():
    return dict(
        fg_color=c("bg_card"),
        hover_color=c("border"),
        border_color=c("accent"),
        border_width=1,
        text_color=c("text_primary"),
        font=FONT_SM,
        corner_radius=8,
    )

def entry_style():
    return dict(
        fg_color=c("input_bg"),
        border_color=c("border"),
        text_color=c("text_primary"),
        placeholder_text_color=c("text_muted"),
        font=FONT_SM,
        corner_radius=8,
    )

def card_style():
    return dict(
        fg_color=c("bg_card"),
        corner_radius=12,
        border_width=1,
        border_color=c("border"),
    )
