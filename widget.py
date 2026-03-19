"""Main floating Liquid Glass widget — dark glass, Russian UI, marquee."""

from __future__ import annotations

import math
from datetime import datetime

from PyQt5.QtCore import (
    QPoint, QRectF, QRect, Qt, QTimer, pyqtSignal,
)
from PyQt5.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QImage, QLinearGradient,
    QPainter, QPainterPath, QPixmap, QRadialGradient, QBrush, QPen,
)
from PyQt5.QtWidgets import QApplication, QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem, QMenu, QWidget

import logic
import settings
import sound

WIDGET_W = 330
WIDGET_H = 210
RADIUS   = 22

MARQUEE_SPEED = 0.7    # px per animation frame (~30fps)


class GoldenHoursWidget(QWidget):
    state_changed = pyqtSignal(str)
    request_popup = pyqtSignal()

    def __init__(self, build_number: int = 0):
        super().__init__()
        self._build = build_number
        self._drag_pos: QPoint | None = None
        self._current_state: str | None = None
        self._anim_phase: float = 0.0
        self._status: dict = {}
        self._cfg = settings.load()

        # Marquee: continuous scroll, phrase queue
        self._marquee_text: str = ""
        self._marquee_x: float = WIDGET_W
        self._marquee_text_w: int = 0

        # Background blur cache
        self._bg_blur: QPixmap | None = None

        # Auto-popup flags
        self._popup_golden_fired = False
        self._popup_ending_fired = False

        self._setup_window()
        self._setup_fonts()
        self._setup_timers()
        self._new_marquee_phrase()

    def _setup_window(self):
        self.setFixedSize(WIDGET_W, WIDGET_H)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        x, y = self._cfg.get("pos_x"), self._cfg.get("pos_y")
        if x is None or y is None:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right()  - WIDGET_W - 24
            y = screen.bottom() - WIDGET_H - 24
        self.move(x, y)

    def _setup_fonts(self):
        self._font_title = QFont("Segoe UI", 18, QFont.Bold)
        self._font_sub   = QFont("Segoe UI", 9, QFont.Normal)
        self._font_cd    = QFont("Cascadia Mono", 30, QFont.Bold)
        if "Cascadia Mono" not in QFontDatabase().families():
            self._font_cd = QFont("Consolas", 30, QFont.Bold)
        self._font_label   = QFont("Segoe UI", 9, QFont.DemiBold)
        self._font_info    = QFont("Segoe UI", 8)
        self._font_time    = QFont("Segoe UI", 8)
        self._font_marquee = QFont("Segoe UI", 9)
        self._font_btn     = QFont("Segoe UI", 11)

    def _setup_timers(self):
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(500)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim)
        self._anim_timer.start(33)

        # Grab background every 1.5s
        self._bg_timer = QTimer(self)
        self._bg_timer.timeout.connect(self._grab_background)
        self._bg_timer.start(1500)

        self._on_tick()
        QTimer.singleShot(100, self._grab_background)

    def apply_glass(self):
        # Real glass via screenshot+blur (compatible with Start11 and other shells).
        # DWM Acrylic is incompatible with WS_EX_LAYERED (WA_TranslucentBackground),
        # so we skip DWM calls entirely — they can conflict with Start11.
        pass

    # ── Background blur ──────────────────────────────────────────────────────

    def _grab_background(self):
        """Capture screen area and blur it — no hide/show, no flicker."""
        if not self.isVisible():
            return
        screen = QApplication.primaryScreen()
        if not screen:
            return

        geo = self.geometry()
        # Grab screen including our widget — with heavy blur it's invisible.
        # Use device pixel ratio for HiDPI.
        dpr = screen.devicePixelRatio()
        grab = screen.grabWindow(
            0,
            geo.x(), geo.y(),
            geo.width(), geo.height(),
        )
        if grab.isNull():
            return

        self._bg_blur = self._blur_pixmap(grab, radius=35)

    @staticmethod
    def _blur_pixmap(src: QPixmap, radius: int = 35) -> QPixmap:
        """Fast multi-pass blur using scaled-down image."""
        # Downscale → blur is cheaper and looks smoother
        small = src.scaled(
            src.width() // 4, src.height() // 4,
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )
        # Scale back up — the upscale itself adds blur
        medium = small.scaled(
            src.width(), src.height(),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )
        # Apply QGraphicsBlurEffect for final smooth pass
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
        return QPixmap.fromImage(result)

    # ── Marquee ──────────────────────────────────────────────────────────────

    def _new_marquee_phrase(self):
        state = self._status.get("state", "inactive")
        ending = self._status.get("ending_soon", False)
        self._marquee_text = logic.get_random_phrase(state, ending)
        fm = QFontMetrics(self._font_marquee)
        self._marquee_text_w = fm.horizontalAdvance(self._marquee_text)
        self._marquee_x = float(WIDGET_W)

    # ── Timers ───────────────────────────────────────────────────────────────

    def _on_tick(self):
        self._status = logic.get_status()
        new_state = self._status["state"]

        if new_state != self._current_state:
            old = self._current_state
            self._current_state = new_state
            self._popup_ending_fired = False

            if old is not None:
                snd_on = self._cfg.get("sound_enabled", True)
                sound.play_transition(new_state, snd_on)
                self.state_changed.emit(new_state)

            if new_state == "golden" and old is not None:
                self._popup_golden_fired = True
                if self._cfg.get("popup_on_golden_start", True):
                    self.request_popup.emit()
            else:
                self._popup_golden_fired = False

        ending = self._status.get("ending_soon", False)
        if ending and not self._popup_ending_fired:
            self._popup_ending_fired = True
            if self._cfg.get("popup_before_golden_end", True):
                snd_on = self._cfg.get("sound_enabled", True)
                sound.play_transition("golden", snd_on)
                self.request_popup.emit()

        self.update()

    def _on_anim(self):
        self._anim_phase += 0.035
        if self._anim_phase > math.tau:
            self._anim_phase -= math.tau

        # Continuous marquee scroll: wraps naturally
        if self._cfg.get("marquee_enabled", True) and self._marquee_text:
            self._marquee_x -= MARQUEE_SPEED
            # Only get new phrase AFTER current one fully exits left
            if self._marquee_x < -(self._marquee_text_w + 30):
                self._new_marquee_phrase()

        self.update()

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        state = self._status.get("state", "inactive")
        ending = self._status.get("ending_soon", False)
        pulse = 0.5 + 0.5 * math.sin(self._anim_phase)
        w, h  = WIDGET_W, WIDGET_H

        # ── Clip to rounded rect ─────────────────────────────────────────────
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), RADIUS, RADIUS)
        p.setClipPath(clip)

        # ── Blurred background (real glass!) ─────────────────────────────────
        if self._bg_blur:
            p.drawPixmap(0, 0, self._bg_blur)

        # ── Dark tint over blur ──────────────────────────────────────────────
        p.fillRect(self.rect(), QColor(10, 8, 16, 140))

        # ── Depth gradient ───────────────────────────────────────────────────
        depth = QLinearGradient(0, 0, 0, h)
        depth.setColorAt(0.0, QColor(255, 255, 255, 14))
        depth.setColorAt(0.5, QColor(255, 255, 255, 0))
        depth.setColorAt(1.0, QColor(0, 0, 0, 30))
        p.fillRect(self.rect(), QBrush(depth))

        # ── Ambient glow ─────────────────────────────────────────────────────
        if state == "golden":
            if ending:
                ac = QColor(255, 80, 40, int(50 + 25 * pulse))
            else:
                ac = QColor(255, 180, 40, int(45 + 20 * pulse))
            ambient = QRadialGradient(w * 0.35, -10, w * 0.65)
            ambient.setColorAt(0.0, ac)
            ambient.setColorAt(1.0, QColor(ac.red(), ac.green(), ac.blue(), 0))
        elif state == "peak":
            ambient = QRadialGradient(w * 0.35, -10, w * 0.65)
            ambient.setColorAt(0.0, QColor(80, 120, 255, 30))
            ambient.setColorAt(1.0, QColor(80, 120, 255, 0))
        else:
            ambient = QRadialGradient(w * 0.35, -10, w * 0.65)
            ambient.setColorAt(0.0, QColor(150, 150, 170, 15))
            ambient.setColorAt(1.0, QColor(150, 150, 170, 0))
        p.fillRect(self.rect(), QBrush(ambient))

        # ── Specular highlight ───────────────────────────────────────────────
        spec = QRadialGradient(w * 0.22, h * 0.04, w * 0.45)
        spec.setColorAt(0.0, QColor(255, 255, 255, 35))
        spec.setColorAt(0.4, QColor(255, 255, 255, 6))
        spec.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(self.rect(), QBrush(spec))

        # ── Top edge highlight ───────────────────────────────────────────────
        edge = QLinearGradient(w * 0.1, 0, w * 0.9, 0)
        edge.setColorAt(0.0, QColor(255, 255, 255, 0))
        edge.setColorAt(0.3, QColor(255, 255, 255, 50))
        edge.setColorAt(0.7, QColor(255, 255, 255, 50))
        edge.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(QBrush(edge), 1.0))
        p.drawLine(int(w * 0.1), 1, int(w * 0.9), 1)

        # ── Content ──────────────────────────────────────────────────────────
        self._draw_content(p, state, pulse, ending)

        # ── Border + glow (unclipped) ────────────────────────────────────────
        p.setClipping(False)

        if state == "golden":
            r, g, b = (255, 80, 40) if ending else (255, 180, 30)
            ga = int(18 + 25 * pulse)
            for i in range(3):
                pen = QPen(QColor(r, g, b, max(0, ga - i * 8)), 2 + i * 3.0)
                pen.setJoinStyle(Qt.RoundJoin)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                m = -i * 2
                p.drawRoundedRect(QRectF(m, m, w - 2 * m, h - 2 * m),
                                  RADIUS + i * 2, RADIUS + i * 2)

        if state == "golden":
            bc = QColor(255, 190, 50, int(65 + 45 * pulse))
        elif state == "peak":
            bc = QColor(100, 140, 230, 50)
        else:
            bc = QColor(150, 150, 180, 30)
        p.setPen(QPen(bc, 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), RADIUS, RADIUS)

        p.end()

    def _draw_content(self, p: QPainter, state: str, pulse: float, ending: bool):
        LM = 22
        w  = WIDGET_W

        # ── Title + subtitle ─────────────────────────────────────────────────
        if state == "golden":
            if ending:
                dot_clr   = QColor(255, 80, 40)
                title     = "ЗАКАНЧИВАЕТСЯ!"
                title_clr = QColor(255, 100, 60)
                sub       = "Золотые часы на исходе!"
            else:
                dot_clr   = QColor(255, 200, 50)
                title     = "ЗОЛОТЫЕ ЧАСЫ"
                title_clr = QColor(255, 210, 70)
                sub       = "Лимиты x2 · бонусный режим"
        elif state == "peak":
            dot_clr   = QColor(100, 150, 255)
            title     = "ПИКОВЫЕ ЧАСЫ"
            title_clr = QColor(140, 170, 255)
            sub       = "Обычный режим"
        else:
            dot_clr   = QColor(120, 120, 130)
            title     = "АКЦИЯ НЕ АКТИВНА"
            title_clr = QColor(160, 160, 175)
            sub       = "13–28 марта 2026"

        dot_r = 5 + (2.0 * pulse if state == "golden" else 0)
        p.setBrush(QBrush(dot_clr))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(LM, 20 - dot_r, dot_r * 2, dot_r * 2))

        p.setFont(self._font_title)
        p.setPen(QPen(title_clr))
        p.drawText(QRectF(LM + 18, 8, w - LM - 80, 28), Qt.AlignLeft | Qt.AlignVCenter, title)

        p.setFont(self._font_sub)
        p.setPen(QPen(QColor(180, 180, 200, 150)))
        p.drawText(QRectF(LM + 18, 34, w - LM - 80, 16), Qt.AlignLeft | Qt.AlignVCenter, sub)

        # ── Buttons: — (minimize) and ⚙ (settings) ──────────────────────────
        p.setFont(self._font_btn)

        # Minimize button (—)
        self._close_rect = QRectF(w - 32, 6, 22, 22)
        p.setPen(QPen(QColor(200, 200, 220, 140)))
        p.drawText(self._close_rect, Qt.AlignCenter, "\u2014")

        # Gear button (⚙) — same muted tone
        self._gear_rect = QRectF(w - 58, 6, 22, 22)
        p.setPen(QPen(QColor(200, 200, 220, 140)))
        p.drawText(self._gear_rect, Qt.AlignCenter, "\u2699")

        # ── Divider ──────────────────────────────────────────────────────────
        div = QLinearGradient(LM, 0, w - LM, 0)
        div.setColorAt(0.0, QColor(255, 255, 255, 0))
        div.setColorAt(0.1, QColor(255, 255, 255, 28))
        div.setColorAt(0.9, QColor(255, 255, 255, 28))
        div.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(QBrush(div), 1.0))
        p.drawLine(LM, 55, w - LM, 55)

        # ── "До начала/окончания осталось" label ─────────────────────────────
        cd = self._status.get("countdown_seconds")
        if cd is not None:
            if state == "golden":
                label_text = "До окончания золотых часов:"
                label_clr  = QColor(255, 200, 80, 170)
                cd_clr     = QColor(255, 220, 100) if not ending else QColor(255, 100, 60)
            elif state == "peak":
                label_text = "До начала золотых часов:"
                label_clr  = QColor(140, 170, 255, 170)
                cd_clr     = QColor(140, 180, 255)
            else:
                label_text = ""
                label_clr  = QColor(160, 160, 180, 140)
                cd_clr     = QColor(180, 180, 200)

            # Label
            p.setFont(self._font_label)
            p.setPen(QPen(label_clr))
            p.drawText(QRectF(LM, 60, w - LM * 2, 16), Qt.AlignLeft | Qt.AlignVCenter, label_text)

            # Countdown
            cd_text = logic.format_countdown(cd)
            p.setFont(self._font_cd)
            p.setPen(QPen(cd_clr))
            p.drawText(QRectF(LM, 76, w - LM * 2, 44), Qt.AlignLeft | Qt.AlignVCenter, cd_text)

            # Time hint
            next_et = self._status.get("next_transition_et")
            if next_et:
                hint = next_et.strftime("в %H:%M ET")
                p.setFont(self._font_info)
                p.setPen(QPen(QColor(160, 160, 180, 130)))
                p.drawText(QRectF(LM, 120, w - LM * 2, 14), Qt.AlignLeft, hint)
        else:
            p.setFont(self._font_sub)
            p.setPen(QPen(QColor(160, 160, 180, 150)))
            p.drawText(QRectF(LM, 65, w - LM * 2, 40),
                       Qt.AlignLeft | Qt.AlignVCenter, "Акция не активна")

        # ── Marquee ──────────────────────────────────────────────────────────
        marquee_y = 138
        if self._cfg.get("marquee_enabled", True) and self._marquee_text:
            p.setFont(self._font_marquee)
            if state == "golden":
                mc = QColor(255, 210, 80, 145) if not ending else QColor(255, 120, 70, 155)
            elif state == "peak":
                mc = QColor(150, 170, 230, 130)
            else:
                mc = QColor(150, 150, 170, 110)
            p.setPen(QPen(mc))
            p.drawText(QRectF(self._marquee_x, marquee_y, self._marquee_text_w + 20, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, self._marquee_text)

        # ── Bottom divider ───────────────────────────────────────────────────
        bottom_div_y = WIDGET_H - 32
        bdiv = QLinearGradient(LM, 0, w - LM, 0)
        bdiv.setColorAt(0.0, QColor(255, 255, 255, 0))
        bdiv.setColorAt(0.2, QColor(255, 255, 255, 16))
        bdiv.setColorAt(0.8, QColor(255, 255, 255, 16))
        bdiv.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(QBrush(bdiv), 1.0))
        p.drawLine(LM, bottom_div_y, w - LM, bottom_div_y)

        # ── Bottom bar ───────────────────────────────────────────────────────
        local_time = self._status.get("local_time", datetime.now().astimezone())
        et_time    = self._status.get("et_time")
        p.setFont(self._font_time)
        p.setPen(QPen(QColor(140, 140, 160, 120)))
        bottom_y = WIDGET_H - 20
        p.drawText(QRectF(LM, bottom_y, 80, 14), Qt.AlignLeft | Qt.AlignVCenter,
                   local_time.strftime("%H:%M:%S"))
        if et_time:
            p.drawText(QRectF(w - LM - 70, bottom_y, 70, 14), Qt.AlignRight | Qt.AlignVCenter,
                       et_time.strftime("%H:%M ET"))

    # ── Mouse ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            if hasattr(self, '_close_rect') and self._close_rect.contains(pos.x(), pos.y()):
                self.hide()
                return
            if hasattr(self, '_gear_rect') and self._gear_rect.contains(pos.x(), pos.y()):
                self._open_settings()
                return
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if self._drag_pos:
            self._drag_pos = None
            settings.save_position(self.pos().x(), self.pos().y())
            # Re-grab background after move
            QTimer.singleShot(200, self._grab_background)

    def _show_context_menu(self, gpos):
        m = QMenu(self)
        m.setStyleSheet("""
            QMenu {
                background: rgba(25,25,40,240); color: rgba(220,220,235,220);
                border: 1px solid rgba(120,120,160,60); border-radius: 8px;
                padding: 4px; font-family: 'Segoe UI'; font-size: 9pt;
            }
            QMenu::item { padding: 6px 24px; border-radius: 4px; }
            QMenu::item:selected { background: rgba(255,200,50,50); }
            QMenu::separator { height:1px; background:rgba(120,120,160,40); margin:4px 8px; }
        """)
        m.addAction("Настройки").triggered.connect(self._open_settings)
        m.addSeparator()
        m.addAction("Свернуть в трей").triggered.connect(self.hide)
        m.addAction("Выход").triggered.connect(QApplication.instance().quit)
        m.exec_(gpos)

    def _open_settings(self):
        self._settings_requested = True
        self.request_popup.emit()

    def reload_settings(self):
        self._cfg = settings.load()
