from __future__ import annotations

from PySide6.QtCore import (QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QSize, Qt, QUrl, Signal)
from PySide6.QtGui import QColor, QImageReader, QKeySequence, QPixmap, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QAbstractItemView, QDoubleSpinBox, QGridLayout, QHBoxLayout, QHeaderView,
                               QLineEdit, QPushButton, QTableView, QVBoxLayout, QWidget)

from ..core.util import fmt_time
from . import theme
from .state import Project
from .widgets import ImageView, PageHeader, TimelineBar, button, card, label

THUMB = QSize(80, 45)
MIN_LEN = 0.05


class SceneModel(QAbstractTableModel):
    HEAD = ["#", "", "SCRIPT LINE", "START", "LENGTH", "STATUS"]

    def __init__(self):
        super().__init__()
        self.scenes = []
        self._thumbs: dict[str, QPixmap] = {}

    def set_scenes(self, scenes):
        self.beginResetModel()
        self.scenes = scenes
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.scenes)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEAD)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEAD[section]
        if orientation == Qt.Horizontal and role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter)

    def _thumb(self, path) -> QPixmap:
        key = str(path)
        if key not in self._thumbs:
            r = QImageReader(key)
            sz = r.size()
            if sz.isValid():
                r.setScaledSize(sz.scaled(THUMB * 2, Qt.KeepAspectRatio))
            img = r.read()
            pm = QPixmap.fromImage(img) if not img.isNull() else QPixmap()
            self._thumbs[key] = pm.scaled(THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pm.isNull() else pm
        return self._thumbs[key]

    def data(self, index, role=Qt.DisplayRole):
        s = self.scenes[index.row()]
        c = index.column()
        if role == Qt.UserRole:
            return index.row()
        if role == Qt.DisplayRole:
            return {0: f"{s.number:03d}", 2: s.text, 3: fmt_time(s.start), 4: f"{s.duration:.2f}s",
                    5: ", ".join(s.flags) if s.flags else ("Edited" if s.edited else "Aligned")}.get(c)
        if role == Qt.DecorationRole and c == 1 and s.image:
            return self._thumb(s.image)
        if role == Qt.ForegroundRole:
            if c == 5:
                return QColor(theme.WARN if s.flags else (theme.ACCENT if s.edited else theme.SUCCESS))
            if c in (0, 3, 4):
                return QColor(theme.MUTED)
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter)

    def touched(self, i):
        for r in (i - 1, i, i + 1):
            if 0 <= r < len(self.scenes):
                self.dataChanged.emit(self.index(r, 0), self.index(r, len(self.HEAD) - 1))


class SceneFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.only_flagged = False
        self.query = ""

    def set_filters(self, only_flagged=None, query=None):
        if only_flagged is not None:
            self.only_flagged = only_flagged
        if query is not None:
            self.query = query.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        s = self.sourceModel().scenes[row]
        if self.only_flagged and not s.needs_attention:
            return False
        return not self.query or self.query in s.text.lower() or self.query == str(s.number)


class ReviewPage(QWidget):
    continue_requested = Signal()

    def __init__(self, project: Project):
        super().__init__()
        self.setObjectName("page")
        self.p = project
        self.cur = -1
        self.stop_at: float | None = None

        self.audio_out = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_out)
        self.player.positionChanged.connect(self._on_position)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 24)
        root.setSpacing(16)

        head = QHBoxLayout()
        head.addWidget(PageHeader("Review the timeline",
                                  "Listen to any scene and fine-tune its start. Scenes that need a closer look are highlighted."), 1)
        self.chip_all = QPushButton("All scenes")
        self.chip_flag = QPushButton("Needs review")
        for c in (self.chip_all, self.chip_flag):
            c.setObjectName("chip")
            c.setCheckable(True)
            c.setCursor(Qt.PointingHandCursor)
        self.chip_all.setChecked(True)
        self.chip_all.clicked.connect(lambda: self._set_filter(False))
        self.chip_flag.clicked.connect(lambda: self._set_filter(True))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search scenes")
        self.search.setFixedWidth(200)
        self.search.textChanged.connect(lambda t: self.proxy.set_filters(query=t))
        box = QHBoxLayout()
        box.setSpacing(8)
        box.addWidget(self.chip_all)
        box.addWidget(self.chip_flag)
        box.addSpacing(6)
        box.addWidget(self.search)
        head.addLayout(box)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(18)
        # ---- table
        tcard = card()
        tl = QVBoxLayout(tcard)
        tl.setContentsMargins(4, 4, 4, 4)
        self.model = SceneModel()
        self.proxy = SceneFilter()
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.setIconSize(THUMB)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        for col, w in ((0, 50), (1, 96), (3, 86), (4, 66), (5, 104)):
            self.table.setColumnWidth(col, w)
            if col > 2:
                hh.setSectionResizeMode(col, QHeaderView.Fixed)
        tl.addWidget(self.table)
        body.addWidget(tcard, 1)

        # ---- detail panel
        side = card()
        side.setFixedWidth(360)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(18, 18, 18, 18)
        sl.setSpacing(12)
        self.preview = ImageView()
        self.preview.setMinimumSize(200, 120)
        sl.addWidget(self.preview, 1)
        self.scene_title = label("Scene", "cardTitle")
        self.scene_flags = label("", wrap=True)
        sl.addWidget(self.scene_title)
        self.scene_text = label("", "muted", wrap=True)
        self.scene_text.setMaximumHeight(44)
        sl.addWidget(self.scene_text)
        sl.addWidget(self.scene_flags)

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.addWidget(label("Start (s)", "faint"), 0, 0)
        g.addWidget(label("End (s)", "faint"), 0, 1)
        self.sp_start = self._spin()
        self.sp_end = self._spin()
        self.sp_start.editingFinished.connect(lambda: self._set_start(self.cur, self.sp_start.value()))
        self.sp_end.editingFinished.connect(lambda: self._set_start(self.cur + 1, self.sp_end.value()))
        g.addWidget(self.sp_start, 1, 0)
        g.addWidget(self.sp_end, 1, 1)
        nudge = QHBoxLayout()
        nudge.setSpacing(6)
        for txt, d in (("-0.25s", -.25), ("-0.05s", -.05), ("+0.05s", .05), ("+0.25s", .25)):
            b = button(txt, on_click=lambda _=False, d=d: self._nudge(d))
            b.setStyleSheet("padding: 6px 4px;")
            nudge.addWidget(b)
        g.addLayout(nudge, 2, 0, 1, 2)
        sl.addLayout(g)

        tr = QHBoxLayout()
        tr.setSpacing(8)
        self.btn_scene = button("Play scene", "primary", self.play_scene)
        self.btn_from = button("Play from here", on_click=self.play_from)
        self.btn_stop = button("Stop", on_click=self.stop)
        self.btn_scene.setStyleSheet("padding: 9px 14px;")
        tr.addWidget(self.btn_scene, 2)
        tr.addWidget(self.btn_from, 2)
        tr.addWidget(self.btn_stop, 1)
        sl.addLayout(tr)
        self.btn_reset = button("Reset to automatic timing", "ghost", self._reset)
        sl.addWidget(self.btn_reset)
        body.addWidget(side)
        root.addLayout(body, 1)

        # ---- timeline + continue
        self.bar = TimelineBar()
        self.bar.sceneClicked.connect(self.select_scene)
        bcard = card(flat=True)
        bl = QVBoxLayout(bcard)
        bl.setContentsMargins(14, 8, 14, 8)
        bl.addWidget(self.bar)
        root.addWidget(bcard)

        foot = QHBoxLayout()
        self.stats = label("", "muted")
        foot.addWidget(self.stats, 1)
        self.next_btn = button("Continue to export", "primary", self.continue_requested.emit)
        foot.addWidget(self.next_btn)
        root.addLayout(foot)

        self.table.selectionModel().currentRowChanged.connect(self._on_row)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self._toggle_play)

    @staticmethod
    def _spin():
        s = QDoubleSpinBox()
        s.setDecimals(3)
        s.setRange(0, 99999)
        s.setSingleStep(0.05)
        s.setKeyboardTracking(False)
        return s

    # ------------------------------------------------------ data
    def load(self):
        sc = self.p.scenes
        self.model.set_scenes(sc)
        self.bar.set_scenes(sc)
        self.player.setSource(QUrl.fromLocalFile(self.p.audio_path))
        self._update_stats()
        self.cur = -1
        first = next((i for i, s in enumerate(sc) if s.needs_attention), 0)
        self.select_scene(first)

    def _update_stats(self):
        sc = self.p.scenes
        flagged = sum(1 for s in sc if s.needs_attention)
        edited = sum(1 for s in sc if s.edited)
        self.stats.setText(f"{len(sc)} scenes   |   {flagged} need review   |   {edited} edited by you   |   "
                           f"{fmt_time(sc[-1].end, False) if sc else '00:00'} total")
        self.chip_flag.setText(f"Needs review ({flagged})")

    def _set_filter(self, flagged: bool):
        self.chip_all.setChecked(not flagged)
        self.chip_flag.setChecked(flagged)
        self.proxy.set_filters(only_flagged=flagged)

    # ------------------------------------------------------ selection
    def select_scene(self, i: int):
        if not self.p.scenes:
            return
        i = max(0, min(i, len(self.p.scenes) - 1))
        src = self.model.index(i, 0)
        idx = self.proxy.mapFromSource(src)
        if not idx.isValid():  # hidden by the filter
            self._show(i)
            return
        self.table.selectRow(idx.row())
        self.table.setCurrentIndex(idx)
        self.table.scrollTo(idx, QAbstractItemView.PositionAtCenter)

    def _on_row(self, current, _prev):
        if current.isValid():
            self._show(self.proxy.mapToSource(current).row())

    def _show(self, i: int):
        self.cur = i
        s = self.p.scenes[i]
        self.bar.set_current(i)
        self.preview.set_image(s.image, "No image for this scene")
        self.scene_title.setText(f"Scene {s.number}")
        self.scene_text.setText(s.text)
        if s.flags:
            self.scene_flags.setText("Needs review: " + ", ".join(s.flags))
            self.scene_flags.setStyleSheet(f"color: {theme.WARN};")
        else:
            self.scene_flags.setText("Matched to the narration")
            self.scene_flags.setStyleSheet(f"color: {theme.SUCCESS};")
        self._refresh_spins()

    def _refresh_spins(self):
        if self.cur < 0:
            return
        s = self.p.scenes[self.cur]
        last = self.cur == len(self.p.scenes) - 1
        for sp in (self.sp_start, self.sp_end):
            sp.blockSignals(True)
        self.sp_start.setValue(s.start)
        self.sp_end.setValue(s.end)
        self.sp_start.setEnabled(self.cur > 0)
        self.sp_end.setEnabled(not last)
        for sp in (self.sp_start, self.sp_end):
            sp.blockSignals(False)
        self.btn_reset.setEnabled(s.edited)

    # ------------------------------------------------------ editing
    def _set_start(self, i: int, t: float):
        sc = self.p.scenes
        if i <= 0 or i >= len(sc):
            return self._refresh_spins()
        lo, hi = sc[i - 1].start + MIN_LEN, sc[i].end - MIN_LEN
        t = max(lo, min(t, hi))
        sc[i - 1].end = t
        sc[i].start = t
        sc[i].edited = True
        self._after_edit(i)

    def _nudge(self, d: float):
        if self.cur > 0:
            self._set_start(self.cur, self.p.scenes[self.cur].start + d)

    def _reset(self):
        sc = self.p.scenes
        i = self.cur
        if i > 0 and sc[i].edited:
            self._set_start(i, sc[i].auto_start)
            sc[i].edited = False
            self._after_edit(i)

    def _after_edit(self, i):
        self.model.touched(i)
        self.bar.refresh()
        self._refresh_spins()
        self._update_stats()

    # ------------------------------------------------------ playback
    def play_scene(self):
        if self.cur < 0:
            return
        s = self.p.scenes[self.cur]
        self.stop_at = s.end
        self.player.setPosition(int(s.start * 1000))
        self.player.play()

    def play_from(self):
        if self.cur < 0:
            return
        self.stop_at = None
        self.player.setPosition(int(self.p.scenes[self.cur].start * 1000))
        self.player.play()

    def stop(self):
        self.player.pause()
        self.stop_at = None
        self.bar.set_playhead(-1)

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.stop()
        else:
            self.play_scene()

    def _on_position(self, ms: int):
        t = ms / 1000
        if self.player.playbackState() != QMediaPlayer.PlayingState:
            return
        self.bar.set_playhead(t)
        if self.stop_at is not None and t >= self.stop_at:
            self.stop()
            return
        if self.stop_at is None:  # continuous playback: selection follows the audio
            import bisect
            i = max(0, bisect.bisect_right([s.start for s in self.p.scenes], t) - 1)
            if i != self.cur:
                self.select_scene(i)

    def hideEvent(self, e):
        self.player.pause()
        super().hideEvent(e)
