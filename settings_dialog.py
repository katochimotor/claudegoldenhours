"""Settings dialog — dark glass styled."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QBrush, QPen, QLinearGradient
from PyQt5.QtWidgets import (
    QCheckBox, QLabel, QVBoxLayout, QWidget, QApplication, QPushButton,
)

import autostart
import settings

DIALOG_W = 300
DIALOG_H = 345
RADIUS   = 18


class _StyledCheckBox(QCheckBox):
    """QCheckBox with light text for dark backgrounds."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QCheckBox {
                color: rgba(220, 220, 235, 210);
                font-family: 'Segoe UI';
                font-size: 10pt;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 1px solid rgba(160,160,180,120);
                border-radius: 4px;
                background: rgba(40,40,55,180);
            }
            QCheckBox::indicator:checked {
                background: rgba(255,200,50,200);
                border-color: rgba(255,180,30,200);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(255,200,50,150);
            }
        """)


class SettingsDialog(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._cfg = settings.load()
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.setFixedSize(DIALOG_W, DIALOG_H)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - DIALOG_W - 340,
            screen.bottom() - DIALOG_H - 24,
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 45, 20, 18)
        layout.setSpacing(12)

        self._cb_sound = _StyledCheckBox("Звуковые уведомления")
        self._cb_sound.setChecked(self._cfg.get("sound_enabled", True))
        self._cb_sound.toggled.connect(lambda v: self._save("sound_enabled", v))

        self._cb_popup_start = _StyledCheckBox("Всплывать при начале золотых часов")
        self._cb_popup_start.setChecked(self._cfg.get("popup_on_golden_start", True))
        self._cb_popup_start.toggled.connect(lambda v: self._save("popup_on_golden_start", v))

        self._cb_popup_end = _StyledCheckBox("Всплывать за 10 мин до конца")
        self._cb_popup_end.setChecked(self._cfg.get("popup_before_golden_end", True))
        self._cb_popup_end.toggled.connect(lambda v: self._save("popup_before_golden_end", v))

        self._cb_marquee = _StyledCheckBox("Бегущая строка с фразами")
        self._cb_marquee.setChecked(self._cfg.get("marquee_enabled", True))
        self._cb_marquee.toggled.connect(lambda v: self._save("marquee_enabled", v))

        self._cb_compact = _StyledCheckBox("Компактная полоса при сворачивании")
        self._cb_compact.setChecked(self._cfg.get("compact_mode", True))
        self._cb_compact.toggled.connect(lambda v: self._save("compact_mode", v))

        self._cb_autostart = _StyledCheckBox("Запускать с Windows")
        self._cb_autostart.setChecked(autostart.is_enabled())
        self._cb_autostart.toggled.connect(self._toggle_autostart)

        layout.addWidget(self._cb_sound)
        layout.addWidget(self._cb_popup_start)
        layout.addWidget(self._cb_popup_end)
        layout.addWidget(self._cb_marquee)
        layout.addWidget(self._cb_compact)
        layout.addWidget(self._cb_autostart)
        layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                color: rgba(200,200,220,200);
                background: rgba(60,60,80,150);
                border: 1px solid rgba(120,120,150,80);
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 9pt;
                padding: 6px 20px;
            }
            QPushButton:hover {
                background: rgba(80,80,110,180);
                border-color: rgba(255,200,50,120);
            }
        """)
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    def _save(self, key: str, value) -> None:
        settings.set_key(key, value)
        self.settings_changed.emit()

    def _toggle_autostart(self, enabled: bool) -> None:
        if enabled:
            autostart.enable()
        else:
            autostart.disable()
        settings.set_key("autostart", enabled)

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = DIALOG_W, DIALOG_H

        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        clip = QPainterPath()
        clip.addRoundedRect(0, 0, w, h, RADIUS, RADIUS)
        p.setClipPath(clip)

        # Dark glass
        p.fillRect(self.rect(), QColor(20, 20, 32, 220))

        # Depth gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(255, 255, 255, 12))
        grad.setColorAt(1.0, QColor(0, 0, 0, 30))
        p.fillRect(self.rect(), QBrush(grad))

        # Border
        p.setClipping(False)
        p.setPen(QPen(QColor(120, 120, 160, 50), 1.0))
        p.setBrush(Qt.NoBrush)
        from PyQt5.QtCore import QRectF
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), RADIUS, RADIUS)
        p.setClipPath(clip)

        # Title
        p.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p.setPen(QPen(QColor(220, 220, 240, 220)))
        from PyQt5.QtCore import QRect
        p.drawText(QRect(20, 12, w - 40, 28), Qt.AlignLeft | Qt.AlignVCenter, "Настройки")

        p.end()

    # ── Drag ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, _event):
        self._drag_pos = None

    def refresh(self):
        self._cfg = settings.load()
        self._cb_sound.setChecked(self._cfg.get("sound_enabled", True))
        self._cb_popup_start.setChecked(self._cfg.get("popup_on_golden_start", True))
        self._cb_popup_end.setChecked(self._cfg.get("popup_before_golden_end", True))
        self._cb_marquee.setChecked(self._cfg.get("marquee_enabled", True))
        self._cb_compact.setChecked(self._cfg.get("compact_mode", True))
        self._cb_autostart.setChecked(autostart.is_enabled())
