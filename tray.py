"""System tray icon and context menu using pystray + Pillow."""

from __future__ import annotations

import math
import threading

import pystray
from PIL import Image, ImageDraw

from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

import autostart
import settings

# ── Icon generation ──────────────────────────────────────────────────────────

def _make_icon(state: str) -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)

    if state == "golden":
        d.ellipse([4, 4, 60, 60], fill=(255, 200, 50, 255))
        for angle_deg in range(0, 360, 45):
            a = math.radians(angle_deg)
            cx, cy = 32, 32
            x1 = cx + 20 * math.cos(a)
            y1 = cy + 20 * math.sin(a)
            x2 = cx + 28 * math.cos(a)
            y2 = cy + 28 * math.sin(a)
            d.line([(x1, y1), (x2, y2)], fill=(255, 230, 100, 200), width=3)
        d.ellipse([26, 26, 38, 38], fill=(255, 255, 180, 255))
    elif state == "peak":
        d.ellipse([4, 4, 60, 60], fill=(100, 120, 200, 230))
        d.ellipse([14, 14, 50, 50], outline=(200, 210, 255, 200), width=2)
        d.line([(32, 32), (32, 20)], fill=(200, 210, 255, 255), width=2)
        d.line([(32, 32), (43, 38)], fill=(200, 210, 255, 255), width=2)
    else:
        d.ellipse([4, 4, 60, 60], fill=(90, 90, 100, 180))
        d.ellipse([20, 20, 44, 44], outline=(160, 160, 170, 180), width=2)

    return img


# ── Tray runner ──────────────────────────────────────────────────────────────

_tray_icon: pystray.Icon | None = None


def _show_widget(widget) -> None:
    QMetaObject.invokeMethod(widget, "setVisible", Qt.QueuedConnection, Q_ARG(bool, True))


def _toggle_widget(widget) -> None:
    visible = widget.isVisible()
    QMetaObject.invokeMethod(widget, "setVisible", Qt.QueuedConnection, Q_ARG(bool, not visible))


def _quit_app(widget) -> None:
    from PyQt5.QtWidgets import QApplication
    QMetaObject.invokeMethod(widget, "hide", Qt.QueuedConnection)
    QApplication.instance().quit()


def _build_menu(widget, on_settings) -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem("Показать / Скрыть", lambda icon, item: _toggle_widget(widget)),
        pystray.MenuItem("Настройки", lambda icon, item: on_settings()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Выход", lambda icon, item: _quit_app(widget)),
    )


def run_tray(widget, on_settings_cb) -> None:
    """Run the pystray loop (call this on a daemon thread)."""
    global _tray_icon
    icon_img = _make_icon("inactive")
    _tray_icon = pystray.Icon(
        "ClaudeHappyHours",
        icon_img,
        "Claude Happy Hours",
        _build_menu(widget, on_settings_cb),
    )

    def on_state_changed(new_state: str):
        if _tray_icon:
            _tray_icon.icon  = _make_icon(new_state)
            _tray_icon.title = _state_title(new_state)

    widget.state_changed.connect(on_state_changed)

    _tray_icon.run()


def _state_title(state: str) -> str:
    return {
        "golden":   "Claude: Золотые часы!",
        "peak":     "Claude: Пиковые часы",
        "inactive": "Claude Happy Hours",
    }.get(state, "Claude Happy Hours")


def update_tray_state(state: str) -> None:
    if _tray_icon:
        _tray_icon.icon  = _make_icon(state)
        _tray_icon.title = _state_title(state)
