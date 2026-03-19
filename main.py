"""Claude Happy Hours — entry point."""

from __future__ import annotations

import logging
import os
import sys
import threading

# Log to file next to exe (or script) for debugging
_log_dir = os.path.dirname(os.path.abspath(sys.argv[0] if not getattr(sys, 'frozen', False) else sys.executable))
logging.basicConfig(
    filename=os.path.join(_log_dir, "claude_golden_hours.log"),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("main")

def _excepthook(exc_type, exc_value, exc_tb):
    log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

log.info("=== Starting Claude Golden Hours ===")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import glass
import settings
import tray
import widget
from compact_widget import CompactStripWidget
from settings_dialog import SettingsDialog


def main():
    log.info("main() entered")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    log.info("QApplication created")

    build = glass.get_windows_build()
    log.info("Windows build: %d", build)

    w = widget.GoldenHoursWidget(build_number=build)
    log.info("Widget created, pos=(%d,%d)", w.pos().x(), w.pos().y())
    w.show()
    w.apply_glass()
    log.info("Widget shown")

    # Compact strip widget
    compact = CompactStripWidget()
    log.info("Compact widget created")

    # Settings dialog (created once, shown/hidden)
    dlg = SettingsDialog()
    log.info("Settings dialog created")

    def on_settings_changed():
        w.reload_settings()
        cfg = settings.load()
        if not cfg.get("compact_mode", True):
            compact.hide()
        elif not w.isVisible():
            compact.show()

    dlg.settings_changed.connect(on_settings_changed)

    def show_settings():
        dlg.refresh()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    # Show compact strip when main widget is hidden (if enabled)
    def on_main_visibility(visible: bool):
        cfg = settings.load()
        if not cfg.get("compact_mode", True):
            compact.hide()
            return
        if visible:
            compact.hide()
        else:
            compact.show()

    w.visibility_changed.connect(on_main_visibility)

    # Double-click on compact strip → expand main widget
    def on_compact_dblclick(event):
        w.show()
        w.raise_()
        w.activateWindow()

    compact.mouseDoubleClickEvent = on_compact_dblclick

    # Auto-popup handler
    def on_popup_request():
        if getattr(w, '_settings_requested', False):
            w._settings_requested = False
            show_settings()
            return
        if not w.isVisible():
            w.show()
        w.raise_()
        w.activateWindow()

    w.request_popup.connect(on_popup_request)

    initial_state = w._current_state or "inactive"
    tray.update_tray_state(initial_state)

    tray_thread = threading.Thread(
        target=tray.run_tray,
        args=(w, show_settings),
        daemon=True,
    )
    tray_thread.start()
    log.info("Tray thread started, entering event loop")

    ret = app.exec_()
    log.info("Event loop exited with code %d", ret)
    sys.exit(ret)


if __name__ == "__main__":
    main()
