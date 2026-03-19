"""Claude Happy Hours — entry point."""

from __future__ import annotations

import sys
import threading

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import glass
import settings
import tray
import widget
from settings_dialog import SettingsDialog


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    build = glass.get_windows_build()

    w = widget.GoldenHoursWidget(build_number=build)
    w.show()
    w.apply_glass()

    # Settings dialog (created once, shown/hidden)
    dlg = SettingsDialog()

    def on_settings_changed():
        w.reload_settings()

    dlg.settings_changed.connect(on_settings_changed)

    def show_settings():
        dlg.refresh()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    # Auto-popup handler
    def on_popup_request():
        # Check if it was a gear-icon settings request
        if getattr(w, '_settings_requested', False):
            w._settings_requested = False
            show_settings()
            return
        # Otherwise it's a golden-hours popup
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

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
