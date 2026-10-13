from __future__ import annotations

import bisect
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QImageReader)
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from . import theme
from .theme import qcolor


# ---------------------------------------------------------------- icons
def icon_pixmap(kind: str, color: str = theme.ACCENT, size: int = 44) -> QPixmap:
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    s = size
    if kind == "folder":
        path = QPainterPath()
        path.moveTo(s * .14, s * .30)
        path.lineTo(s * .14, s * .76)
        path.quadTo(s * .14, s * .82, s * .20, s * .82)
        path.lineTo(s * .80, s * .82)
        path.quadTo(s * .86, s * .82, s * .86, s * .76)
        path.lineTo(s * .86, s * .38)
        path.quadTo(s * .86, s * .32, s * .80, s * .32)
        path.lineTo(s * .50, s * .32)
        path.lineTo(s * .42, s * .22)
        path.lineTo(s * .20, s * .22)
        path.quadTo(s * .14, s * .22, s * .14, s * .30)
        p.drawPath(path)
    elif kind == "doc":
        path = QPainterPath()
        path.moveTo(s * .24, s * .14)
        path.lineTo(s * .60, s * .14)
        path.lineTo(s * .78, s * .32)
        path.lineTo(s * .78, s * .82)
        path.lineTo(s * .24, s * .82)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(s * .60, s * .14), QPointF(s * .60, s * .32))
        p.drawLine(QPointF(s * .60, s * .32), QPointF(s * .78, s * .32))
        for y in (.46, .58, .70):
            p.drawLine(QPointF(s * .34, s * y), QPointF(s * .68, s * y))
    elif kind == "wave":
        heights = [.18, .38, .62, .44, .74, .50, .30, .56, .22]
        n = len(heights)
        for i, hh in enumerate(heights):
            x = s * (.14 + .72 * i / (n - 1))
            p.drawLine(QPointF(x, s * (.5 - hh / 2)), QPointF(x, s * (.5 + hh / 2)))
    p.end()
    return pm


# ---------------------------------------------------------------- basic building blocks
def card(flat: bool = False) -> QFrame:
    f = QFrame()
    f.setObjectName("cardFlat" if flat else "card")
    return f


def label(text: str = "", name: str = "", wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def button(text: str, name: str = "", on_click=None) -> QPushButton:
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    b.setCursor(Qt.PointingHandCursor)
    if on_click:
        b.clicked.connect(on_click)
    return b


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(label(title, "pageTitle"))
        lay.addWidget(label(subtitle, "pageSub", wrap=True))


# ---------------------------------------------------------------- drop card
class DropCard(QFrame):
    changed = Signal(str)

    def __init__(self, icon: str, title: str, hint: str, mode: str, file_filter: str = ""):
        super().__init__()
        self.setObjectName("dropCard")
        self.setAcceptDrops(True)
        self.mode = mode
        self.file_filter = file_filter
        self.title = title
        self.path = ""
        self.setMinimumHeight(212)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 20)
        lay.setSpacing(6)
        self.icon = QLabel()
        self.icon.setPixmap(icon_pixmap(icon))
        self.icon.setFixedHeight(48)
        lay.addWidget(self.icon, 0, Qt.AlignLeft)
        lay.addSpacing(4)
        lay.addWidget(label(title, "cardTitle"))
        self.hint = label(hint, "muted", wrap=True)
        lay.addWidget(self.hint)
        lay.addStretch(1)
        self.status = label("", wrap=True)
        self.status.hide()
        lay.addWidget(self.status)
        self.btn = button("Choose folder" if mode == "folder" else "Choose file", on_click=self.browse)
        lay.addWidget(self.btn, 0, Qt.AlignLeft)

    def browse(self):
        if self.mode == "folder":
            p = QFileDialog.getExistingDirectory(self, self.title, self.path or "")
        else:
            p, _ = QFileDialog.getOpenFileName(self, self.title, self.path or "", self.file_filter)
        if p:
            self.set_path(p)

    def set_path(self, p: str):
        self.path = p
        self.changed.emit(p)

    def set_status(self, text: str, level: str = "ok"):
        color = {"ok": theme.SUCCESS, "warn": theme.WARN, "error": theme.DANGER}.get(level, theme.MUTED)
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; font-weight: 500;")
        self.status.setVisible(bool(text))
        self.btn.setText("Change" if self.path else self.btn.text())
        self.setProperty("state", level if text else "")
        repolish(self)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.setProperty("drag", "true")
            repolish(self)

    def dragLeaveEvent(self, e):
        self.setProperty("drag", "false")
        repolish(self)

    def dropEvent(self, e):
        self.setProperty("drag", "false")
        repolish(self)
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if (self.mode == "folder" and p.is_dir()) or (self.mode == "file" and p.is_file()):
                self.set_path(str(p))
                return
        self.set_status("Drop a folder here" if self.mode == "folder" else "Drop a file here", "error")


# ---------------------------------------------------------------- sidebar step button
class StepButton(QPushButton):
    def __init__(self, index: int, title: str, subtitle: str):
        super().__init__()
        self.index, self.title, self.subtitle = index, title, subtitle
        self.state = "locked"  # locked | todo | active | done
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(64)
        self.setFlat(True)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def set_state(self, state: str):
        self.state = state
        self.setEnabled(state != "locked")
        self.setCursor(Qt.PointingHandCursor if state != "locked" else Qt.ArrowCursor)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(8, 4, -8, -4)
        if self.state == "active":
            p.setBrush(qcolor("#7c6cff", 36))
            p.setPen(QPen(qcolor("#7c6cff", 90), 1))
            p.drawRoundedRect(r, 11, 11)
        elif self.underMouse() and self.state != "locked":
            p.setBrush(qcolor("#ffffff", 10))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 11, 11)
        cx, cy, rad = r.left() + 26, r.center().y(), 13
        if self.state == "done":
            p.setBrush(qcolor(theme.SUCCESS, 40))
            p.setPen(QPen(qcolor(theme.SUCCESS), 1.4))
            p.drawEllipse(QPointF(cx, cy), rad, rad)
            p.setPen(QPen(qcolor(theme.SUCCESS), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline([QPointF(cx - 5, cy), QPointF(cx - 1.5, cy + 4), QPointF(cx + 5, cy - 4)])
        else:
            active = self.state == "active"
            if active:
                g = QLinearGradient(cx - rad, cy, cx + rad, cy)
                g.setColorAt(0, QColor(theme.ACCENT))
                g.setColorAt(1, QColor(theme.ACCENT_2))
                p.setBrush(QBrush(g))
                p.setPen(Qt.NoPen)
            else:
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(qcolor(theme.BORDER_STRONG), 1.4))
            p.drawEllipse(QPointF(cx, cy), rad, rad)
            f = QFont(self.font())
            f.setPixelSize(12)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("white") if active else qcolor(theme.MUTED if self.state != "locked" else theme.FAINT))
            p.drawText(QRectF(cx - rad, cy - rad, rad * 2, rad * 2), Qt.AlignCenter, str(self.index))
        tx = cx + rad + 14
        locked = self.state == "locked"
        f = QFont(self.font())
        f.setPixelSize(13)
        f.setBold(True)
        p.setFont(f)
        p.setPen(qcolor(theme.FAINT if locked else theme.TEXT))
        p.drawText(QRectF(tx, cy - 20, r.right() - tx, 20), Qt.AlignLeft | Qt.AlignVCenter, self.title)
        f.setBold(False)
        f.setPixelSize(11)
        p.setFont(f)
        p.setPen(qcolor(theme.FAINT if locked else theme.MUTED))
        p.drawText(QRectF(tx, cy + 1, r.right() - tx, 18), Qt.AlignLeft | Qt.AlignVCenter, self.subtitle)

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()


# ---------------------------------------------------------------- image view
class ImageView(QWidget):
    def __init__(self):
        super().__init__()
        self._pm: QPixmap | None = None
        self._src: str | None = None
        self.placeholder = "No image"
        self.setMinimumSize(280, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_image(self, path: Path | None, placeholder: str = "No image for this scene"):
        self.placeholder = placeholder
        if path is None:
            self._pm, self._src = None, None
        elif str(path) != self._src:
            self._pm, self._src = QPixmap(str(path)), str(path)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.setClipPath(path)
        p.fillRect(r, QColor("#0a0c11"))
        if self._pm and not self._pm.isNull():
            sz = self._pm.size().scaled(self.size(), Qt.KeepAspectRatio)
            x, y = (self.width() - sz.width()) / 2, (self.height() - sz.height()) / 2
            p.drawPixmap(QRectF(x, y, sz.width(), sz.height()), self._pm, QRectF(self._pm.rect()))
        else:
            p.setClipping(False)
            p.setPen(QPen(qcolor(theme.BORDER_STRONG), 1.4, Qt.DashLine))
            p.drawRoundedRect(r.adjusted(.7, .7, -.7, -.7), 12, 12)
            p.setPen(qcolor(theme.MUTED))
            p.drawText(r, Qt.AlignCenter, self.placeholder)


# ---------------------------------------------------------------- timeline bar
class TimelineBar(QWidget):
    sceneClicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.scenes = []
        self.starts: list[float] = []
        self.total = 1.0
        self.current = -1
        self.playhead = -1.0
        self.setFixedHeight(54)
        self.setCursor(Qt.PointingHandCursor)

    def set_scenes(self, scenes):
        self.scenes = scenes
        self.starts = [s.start for s in scenes]
        self.total = max(scenes[-1].end, 0.001) if scenes else 1.0
        self.update()

    def refresh(self):
        self.starts = [s.start for s in self.scenes]
        self.update()

    def set_current(self, i: int):
        self.current = i
        self.update()

    def set_playhead(self, t: float):
        self.playhead = t
        self.update()

    def _x(self, t):
        return 1 + (self.width() - 2) * t / self.total

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0, 6, 0, -6)
        clip = QPainterPath()
        clip.addRoundedRect(r, 8, 8)
        p.setClipPath(clip)
        p.fillRect(r, qcolor(theme.SURFACE))
        for i, s in enumerate(self.scenes):
            x0, x1 = self._x(s.start), self._x(s.end)
            rect = QRectF(x0, r.top(), max(x1 - x0 - 0.6, 0.6), r.height())
            if s.needs_attention:
                col = qcolor(theme.WARN, 200)
            else:
                col = qcolor("#7c6cff", 120 if i % 2 else 70)
            if i == self.current:
                col = qcolor("#ffffff", 235)
            p.fillRect(rect, col)
        p.setClipping(False)
        p.setPen(QPen(qcolor(theme.BORDER), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(.5, .5, -.5, -.5), 8, 8)
        if self.playhead >= 0:
            x = self._x(self.playhead)
            p.setPen(QPen(QColor(theme.ACCENT_2), 2))
            p.drawLine(QPointF(x, self.rect().top() + 1), QPointF(x, self.rect().bottom() - 1))

    def mousePressEvent(self, e):
        if not self.scenes:
            return
        t = (e.position().x() - 1) / max(self.width() - 2, 1) * self.total
        i = max(0, bisect.bisect_right(self.starts, t) - 1)
        self.sceneClicked.emit(i)
