"""Colour palettes and the global Qt stylesheet."""
from __future__ import annotations

from PySide6.QtGui import QColor

DARK = {
    "name": "dark",
    "bg": "#0E1017",
    "bg_alt": "#12151F",
    "sidebar": "#101320",
    "card": "#171B27",
    "card_alt": "#1E2333",
    "card_hover": "#232940",
    "border": "#242B3D",
    "border_soft": "#1C2231",
    "text": "#ECEEF7",
    "muted": "#8B93AB",
    "faint": "#5A6175",
    "accent": "#7B6CFF",
    "accent_hover": "#8F82FF",
    "accent_soft": "#272350",
    "accent_text": "#FFFFFF",
    "mint": "#2EE6A8",
    "mint_soft": "#12352C",
    "blue": "#4EA8FF",
    "warn": "#FFB84D",
    "warn_soft": "#3A2C15",
    "danger": "#FF5D7A",
    "danger_soft": "#3A1A24",
    "grid": "#242B3D",
    "shadow": "#05060A",
    "is_dark": True,
}

LIGHT = {
    "name": "light",
    "bg": "#F2F5FB",
    "bg_alt": "#E9EDF6",
    "sidebar": "#FFFFFF",
    "card": "#FFFFFF",
    "card_alt": "#F4F6FC",
    "card_hover": "#EDF0F9",
    "border": "#DCE3F0",
    "border_soft": "#E7ECF6",
    "text": "#1A1F30",
    "muted": "#6B738A",
    "faint": "#98A0B4",
    "accent": "#5B4BE0",
    "accent_hover": "#4B3BD0",
    "accent_soft": "#EBE8FF",
    "accent_text": "#FFFFFF",
    "mint": "#0FB37E",
    "mint_soft": "#E1F7EF",
    "blue": "#2C7BE5",
    "warn": "#C98209",
    "warn_soft": "#FFF3DC",
    "danger": "#E23A57",
    "danger_soft": "#FDE8EC",
    "grid": "#E4E9F3",
    "shadow": "#B9C2D6",
    "is_dark": False,
}

PALETTES = {"dark": DARK, "light": LIGHT}

FONT_STACK = '"Segoe UI Variable Display", "Segoe UI", "Inter", "Noto Sans", "Helvetica Neue", Arial, sans-serif'


def palette(name: str) -> dict:
    return PALETTES.get(name, DARK)


def qcolor(p: dict, key: str, alpha: int | None = None) -> QColor:
    color = QColor(p[key])
    if alpha is not None:
        color.setAlpha(alpha)
    return color


def build_stylesheet(p: dict) -> str:
    return f"""
* {{
    font-family: {FONT_STACK};
    outline: none;
}}
QWidget {{
    color: {p['text']};
    background: transparent;
    font-size: 13px;
}}
QMainWindow, #Root {{
    background: {p['bg']};
}}
#Sidebar {{
    background: {p['sidebar']};
    border-right: 1px solid {p['border_soft']};
}}
#TopBar {{
    background: {p['bg']};
}}
#Card, #Panel {{
    background: {p['card']};
    border: 1px solid {p['border_soft']};
    border-radius: 16px;
}}
#CardFlat {{
    background: {p['card']};
    border: none;
    border-radius: 14px;
}}
#InnerCard {{
    background: {p['card_alt']};
    border: 1px solid {p['border_soft']};
    border-radius: 12px;
}}
#Title {{
    font-size: 25px;
    font-weight: 700;
    color: {p['text']};
}}
#PageTitle {{
    font-size: 21px;
    font-weight: 700;
}}
#CardTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {p['text']};
}}
#Subtitle {{
    font-size: 12px;
    color: {p['muted']};
}}
#Muted {{
    color: {p['muted']};
}}
#Faint {{
    color: {p['faint']};
    font-size: 11px;
}}
#StatValue {{
    font-size: 24px;
    font-weight: 700;
}}
#Mono {{
    font-family: "Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}}
QLabel#Chip {{
    background: {p['card_alt']};
    border: 1px solid {p['border_soft']};
    border-radius: 10px;
    padding: 4px 9px;
    color: {p['muted']};
    font-size: 11px;
}}
QLabel#BadgeAccent {{
    background: {p['accent_soft']};
    color: {p['accent']};
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 600;
}}
QPushButton {{
    background: {p['card_alt']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 8px 14px;
    color: {p['text']};
    font-size: 12px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {p['card_hover']};
    border-color: {p['border']};
}}
QPushButton:pressed {{
    background: {p['card']};
}}
QPushButton:disabled {{
    color: {p['faint']};
    background: {p['card_alt']};
}}
QPushButton#Primary {{
    font-size: 13px;
    font-weight: 700;
    background: {p['accent']};
    color: {p['accent_text']};
    border: 1px solid {p['accent']};
}}
QPushButton#Primary:hover {{
    background: {p['accent_hover']};
    border-color: {p['accent_hover']};
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {p['muted']};
    padding: 6px 10px;
}}
QPushButton#Ghost:hover {{
    background: {p['card_alt']};
    color: {p['text']};
}}
QPushButton#Danger {{
    background: {p['danger_soft']};
    border: 1px solid {p['danger_soft']};
    color: {p['danger']};
}}
QPushButton#Danger:hover {{
    background: {p['danger']};
    color: #FFFFFF;
}}
QPushButton#Link {{
    background: transparent;
    border: none;
    color: {p['accent']};
    padding: 2px 4px;
    font-weight: 600;
}}
QPushButton#IconButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 5px;
}}
QPushButton#IconButton:hover {{
    background: {p['card_alt']};
    border-color: {p['border_soft']};
}}
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {p['card_alt']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 9px 12px;
    color: {p['text']};
    selection-background-color: {p['accent']};
    selection-color: #FFFFFF;
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {p['accent']};
    background: {p['card']};
}}
QLineEdit#Search {{
    padding-left: 36px;
    background: {p['card']};
}}
QComboBox {{
    background: {p['card_alt']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 7px 12px;
    min-width: 110px;
}}
QComboBox:hover {{
    border-color: {p['accent']};
}}
QComboBox QAbstractItemView {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 8px;
    selection-background-color: {p['accent_soft']};
    selection-color: {p['text']};
    padding: 4px;
    outline: none;
}}
QToolTip {{
    background: {p['card']};
    color: {p['text']};
    border: 1px solid {p['border']};
    border-radius: 8px;
    padding: 6px 9px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {p['border']};
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['faint']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: none;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {p['border']};
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}
QMenu {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 22px 7px 14px;
    border-radius: 7px;
    color: {p['text']};
}}
QMenu::item:selected {{
    background: {p['accent_soft']};
    color: {p['accent']};
}}
QMenu::separator {{
    height: 1px;
    background: {p['border_soft']};
    margin: 5px 8px;
}}
QDialog {{
    background: {p['bg']};
}}
QMessageBox {{
    background: {p['bg']};
}}
"""


CURRENT: dict = DARK


def set_current(name: str) -> dict:
    """Select the palette used by hand-painted widgets and return it."""
    global CURRENT
    CURRENT = palette(name)
    return CURRENT
