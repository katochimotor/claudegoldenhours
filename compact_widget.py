"""Compact strip widget — thin bar above the taskbar with countdown."""

from __future__ import annotations

import gc
import math
from datetime import datetime

from PyQt5.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt5.QtGui import (
    QColor, QFont, QFontDatabase, QLinearGradient, QPainter,
    QPainterPath, QBrush, QPen, QRadialGradient, QPixmap,
)
from PyQt5.QtWidgets import QApplication, QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem, QWidget

import logic

STRIP_H = 36
STRIP_W = 340
RADIUS = 12


class CompactStripWidget(QWidget):
    """Thin Liquid Glass bar that sits above the taskbar."""

    def __init__(self):
        super().__init__()
        self._anim_phase: float = 0.0
        self._status: dict = {}
        self._bg_blur: QPixmap | None = None

        self._setup_window()
        self._setup_fonts()
        self._setup_timers()

    def _setup_window(self):
        self.setFixedSize(STRIP_W, STRIP_H)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._reposition()

    def _reposition(self):
        """Place the strip centered above the taskbar."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        full = screen.geometry()
        # Taskbar height = full height - available height
        taskbar_h = full.height() - avail.height()
        if taskbar_h < 10:
            taskbar_h = 48  # fallback if taskbar is hidden/auto-hide

        x = avail.right() - STRIP_W - 12
        y = avail.bottom() - STRIP_H - 6
        self.move(x, y)

    def _setup_fonts(self):
        self._font_status = QFont("Segoe UI", 9, QFont.DemiBold)
        self._font_cd = QFont("Cascadia Mono", 13, QFont.Bold)
        if "Cascadia Mono" not in QFontDatabase().families():
            self._font_cd = QFont("Consolas", 13, QFont.Bold)
        self._font_label = QFont("Segoe UI", 8)

    def _setup_timers(self):
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(500)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim)
        self._anim_timer.start(33)

        self._bg_timer = QTimer(self)
        self._bg_timer.timeout.connect(self._grab_background)
        self._bg_timer.start(2000)

        self._on_tick()
        QTimer.singleShot(100, self._grab_background)

    def _on_tick(self):
        self._status = logic.get_status()
        self.update()

    def _on_anim(self):
        self._anim_phase += 0.04
        if self._anim_phase > math.tau:
            self._anim_phase -= math.tau
        self.update()

    # ── Background blur ──────────────────────────────────────────────────

    def _grab_background(self):
        if not self.isVisible():
            return
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = self.geometry()
        grab = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        if grab.isNull():
            return
        old = self._bg_blur
        self._bg_blur = self._blur_pixmap(grab, radius=30)
        del old, grab
        gc.collect(0)

    @staticmethod
    def _blur_pixmap(src: QPixmap, radius: int = 30) -> QPixmap:
        from PyQt5.QtGui import QImage
        small = src.scaled(
            src.width() // 4, src.height() // 4,
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )
        medium = small.scaled(
            src.width(), src.height(),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(medium)
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(radius)
        item.setGraphicsEffect(blur)
        scene.addItem(item)

        result = QImage(src.size(), QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        scene.render(painter)
        painter.end()

        # Explicitly clean up Qt objects to prevent memory leaks
        scene.removeItem(item)
        item.setGraphicsEffect(None)
        del blur, item, scene

        return QPixmap.fromImage(result)

    # ── Painting ─────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        state = self._status.get("state", "inactive")
        ending = self._status.get("ending_soon", False)
        pulse = 0.5 + 0.5 * math.sin(self._anim_phase)
        w, h = STRIP_W, STRIP_H

        # ── Clip ────────────────────────────────────────────────────────
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), RADIUS, RADIUS)
        p.setClipPath(clip)

        # ── Blurred background ──────────────────────────────────────────
        if self._bg_blur:
            p.drawPixmap(0, 0, self._bg_blur)

        # ── Dark tint ───────────────────────────────────────────────────
        p.fillRect(self.rect(), QColor(10, 8, 16, 160))

        # ── Depth gradient ──────────────────────────────────────────────
        depth = QLinearGradient(0, 0, 0, h)
        depth.setColorAt(0.0, QColor(255, 255, 255, 12))
        depth.setColorAt(1.0, QColor(0, 0, 0, 20))
        p.fillRect(self.rect(), QBrush(depth))

        # ── Ambient glow ────────────────────────────────────────────────
        if state == "golden":
            if ending:
                ac = QColor(255, 80, 40, int(40 + 20 * pulse))
            else:
                ac = QColor(255, 180, 40, int(35 + 15 * pulse))
            ambient = QRadialGradient(w * 0.2, -5, w * 0.5)
            ambient.setColorAt(0.0, ac)
            ambient.setColorAt(1.0, QColor(ac.red(), ac.green(), ac.blue(), 0))
            p.fillRect(self.rect(), QBrush(ambient))

        # ── Content ─────────────────────────────────────────────────────
        LM = 14

        # Status dot
        if state == "golden":
            dot_clr = QColor(255, 80, 40) if ending else QColor(255, 200, 50)
        elif state == "peak":
            dot_clr = QColor(100, 150, 255)
        else:
            dot_clr = QColor(120, 120, 130)

        dot_r = 4 + (1.5 * pulse if state == "golden" else 0)
        cy = h / 2
        p.setBrush(QBrush(dot_clr))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(LM, cy - dot_r, dot_r * 2, dot_r * 2))

        # Status text
        if state == "golden":
            if ending:
                status_text = "ЗАКАНЧИВАЕТСЯ"
                status_clr = QColor(255, 100, 60)
            else:
                status_text = "ЗОЛОТЫЕ ЧАСЫ"
                status_clr = QColor(255, 210, 70)
        elif state == "peak":
            status_text = "ПИКОВЫЕ ЧАСЫ"
            status_clr = QColor(140, 170, 255)
        else:
            status_text = "НЕ АКТИВНА"
            status_clr = QColor(160, 160, 175)

        p.setFont(self._font_status)
        p.setPen(QPen(status_clr))
        text_x = LM + dot_r * 2 + 8
        p.drawText(QRectF(text_x, 0, 140, h), Qt.AlignLeft | Qt.AlignVCenter, status_text)

        # Countdown
        cd = self._status.get("countdown_seconds")
        if cd is not None:
            cd_text = logic.format_countdown(cd)
            if state == "golden":
                cd_clr = QColor(255, 220, 100) if not ending else QColor(255, 100, 60)
            elif state == "peak":
                cd_clr = QColor(140, 180, 255)
            else:
                cd_clr = QColor(180, 180, 200)

            p.setFont(self._font_cd)
            p.setPen(QPen(cd_clr))
            p.drawText(QRectF(w - 130, 0, 118, h), Qt.AlignRight | Qt.AlignVCenter, cd_text)

        # ── Border ──────────────────────────────────────────────────────
        p.setClipping(False)

        if state == "golden":
            r, g, b = (255, 80, 40) if ending else (255, 180, 30)
            ga = int(15 + 20 * pulse)
            pen = QPen(QColor(r, g, b, ga), 4.0)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(-1, -1, w + 2, h + 2), RADIUS + 1, RADIUS + 1)

        if state == "golden":
            bc = QColor(255, 190, 50, int(50 + 35 * pulse))
        elif state == "peak":
            bc = QColor(100, 140, 230, 40)
        else:
            bc = QColor(150, 150, 180, 25)
        p.setPen(QPen(bc, 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), RADIUS, RADIUS)

        p.end()

    # ── Mouse: click to expand, drag to move ─────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._click_pos = event.globalPos()
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition()
        # Resume timers
        self._anim_timer.start(33)
        self._bg_timer.start(2000)
        QTimer.singleShot(150, self._grab_background)

    def hideEvent(self, event):
        super().hideEvent(event)
        # Pause expensive timers while hidden — saves CPU & memory
        self._anim_timer.stop()
        self._bg_timer.stop()
        self._bg_blur = None  # free cached pixmap
