from __future__ import annotations

import random
import threading

from PySide6.QtCore import QRectF, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QLabel, QStyle, QStyledItemDelegate, QWidget


class EqualizerWidget(QWidget):
    def __init__(self, bars: int = 18, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("eqWidget")
        self._bar_count = bars
        self._bars = [0.28 for _ in range(bars)]
        self._bars_lock = threading.Lock()
        self._active = False
        self._animation_running = False
        self._animation_thread = None
        self._a = QColor("#ff6bc7")
        self._b = QColor("#ff9b4c")

        # Low-frequency timer (220ms) - animation in background thread
        self._timer = QTimer(self)
        self._timer.setInterval(220)
        self._timer.timeout.connect(self.update)

    def set_active(self, active: bool) -> None:
        """Set equalizer active state - ANIMATION DISABLED FOR NOW."""
        self._active = active
        
        # Animation paused - just set static bar values
        if active:
            self._bars = [0.45 for _ in range(self._bar_count)]
        else:
            self._bars = [0.28 for _ in range(self._bar_count)]
        
        self.update()

    def set_palette(self, a: QColor, b: QColor) -> None:
        self._a = a
        self._b = b
        self.update()

    def _animate_background(self) -> None:
        """Background thread animation - minimal locking for performance."""
        while self._animation_running:
            # Compute new values WITHOUT holding lock
            new_bars = []
            for i in range(self._bar_count):
                # Read current values
                with self._bars_lock:
                    current = self._bars[i] if i < len(self._bars) else 0.28
                # Compute new value
                target = random.uniform(0.16, 1.0) if self._active else 0.26
                new_val = current * 0.56 + target * 0.44
                new_bars.append(new_val)
            
            # Atomic swap of entire bar array (minimal lock hold)
            with self._bars_lock:
                self._bars = new_bars
            
            threading.Event().wait(0.22)

    def _tick(self) -> None:
        pass

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        if not rect.width() or not rect.height():
            return

        count = len(self._bars)
        gap = 4.0
        usable = max(1.0, rect.width() - (count - 1) * gap)
        bar_w = usable / count

        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0.0, self._a)
        grad.setColorAt(1.0, self._b)
        p.setBrush(grad)
        p.setPen(Qt.NoPen)

        # Read bars from background thread (minimal lock hold time)
        with self._bars_lock:
            bars_snapshot = self._bars[:]
        
        for i, magnitude in enumerate(bars_snapshot):
            h = rect.height() * magnitude
            x = i * (bar_w + gap)
            y = rect.height() - h
            p.drawRect(QRectF(x, y, bar_w, h))

        p.end()


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class GradientSelectedTextDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:  # noqa: N802
        painter.save()

        selected = bool(option.state & QStyle.State_Selected)

        title = str(index.data(Qt.DisplayRole) or "")
        artist = str(index.data(Qt.UserRole + 1) or "")
        left = option.rect.left() + 10
        right = option.rect.right() - 10

        title_font = option.font
        title_font.setBold(selected)
        painter.setFont(title_font)

        title_rect = option.rect.adjusted(0, 5, 0, -option.rect.height() // 2)
        title_rect.setLeft(left)
        title_rect.setRight(right)

        if selected:
            grad = QLinearGradient(title_rect.left(), title_rect.top(), title_rect.right(), title_rect.top())
            grad.setColorAt(0.0, QColor("#f38843"))
            grad.setColorAt(0.56, QColor("#f85fbe"))
            grad.setColorAt(1.0, QColor("#a643d5"))
            painter.setPen(QPen(QBrush(grad), 1))
        else:
            painter.setPen(option.palette.text().color())

        painter.drawText(title_rect, int(Qt.AlignLeft | Qt.AlignVCenter), title)

        if artist:
            artist_font = option.font
            artist_font.setPointSize(max(9, artist_font.pointSize() - 2))
            artist_font.setBold(False)
            painter.setFont(artist_font)
            painter.setPen(QColor(240, 240, 245, 170) if selected else QColor(200, 200, 210, 150))
            artist_rect = option.rect.adjusted(0, option.rect.height() // 2 - 2, 0, -3)
            artist_rect.setLeft(left)
            artist_rect.setRight(right)
            painter.drawText(artist_rect, int(Qt.AlignLeft | Qt.AlignVCenter), artist)

        painter.restore()

    def sizeHint(self, option, index):  # noqa: N802
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(46, base.height() + 14))


class BoldSelectedItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:  # noqa: N802
        opt = option
        if option.state & QStyle.State_Selected:
            opt.font.setBold(True)
        super().paint(painter, opt, index)
