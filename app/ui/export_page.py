from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit,
                               QProgressBar, QVBoxLayout, QWidget)

from ..core import exporter
from ..core.util import fmt_time
from . import theme
from .state import Project, Task
from .widgets import PageHeader, button, card, label

RESOLUTIONS = [("1920 x 1080  (16:9 landscape)", (1920, 1080)), ("3840 x 2160  (4K)", (3840, 2160)),
               ("1080 x 1920  (9:16 vertical)", (1080, 1920)), ("1080 x 1080  (square)", (1080, 1080))]


class ExportPage(QWidget):
    def __init__(self, project: Project):
        super().__init__()
        self.setObjectName("page")
        self.p = project
        self.settings = QSettings("TimelineBuilder", "TimelineBuilder")
        self.task: Task | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 34, 40, 28)
        root.setSpacing(20)
        root.addWidget(PageHeader("Export to CapCut",
                                  "Creates a CapCut draft with your scenes on the video track and the "
                                  "voiceover on the audio track."))

        # stats
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_vals = {}
        for key, title in (("scenes", "SCENES"), ("duration", "DURATION"), ("review", "NEED REVIEW"), ("missing", "NO IMAGE")):
            c = card(flat=True)
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 14, 18, 14)
            cl.setSpacing(2)
            cl.addWidget(label(title, "sectionTitle"))
            v = label("-", "bigNumber")
            cl.addWidget(v)
            self.stat_vals[key] = v
            stats.addWidget(c, 1)
        root.addLayout(stats)

        # form
        form = card()
        g = QGridLayout(form)
        g.setContentsMargins(24, 22, 24, 22)
        g.setHorizontalSpacing(18)
        g.setVerticalSpacing(8)
        g.addWidget(label("CAPCUT PROJECT", "sectionTitle"), 0, 0, 1, 3)
        g.addWidget(label("Project name", "muted"), 1, 0)
        g.addWidget(label("Canvas size", "muted"), 1, 1)
        g.addWidget(label("Frame rate", "muted"), 1, 2)
        self.name = QLineEdit()
        self.res = QComboBox()
        for t, v in RESOLUTIONS:
            self.res.addItem(t, v)
        self.fps = QComboBox()
        for f in (24, 25, 30, 50, 60):
            self.fps.addItem(f"{f} fps", f)
        self.fps.setCurrentIndex(2)
        g.addWidget(self.name, 2, 0)
        g.addWidget(self.res, 2, 1)
        g.addWidget(self.fps, 2, 2)

        g.addWidget(label("CapCut drafts folder", "muted"), 3, 0, 1, 2)
        g.addWidget(label("Scenes without an image", "muted"), 3, 2)
        self.drafts = QLineEdit(self.settings.value("drafts_dir", exporter.default_drafts_dir()))
        browse = button("Browse", on_click=self._browse_drafts)
        row = QHBoxLayout()
        row.addWidget(self.drafts, 1)
        row.addWidget(browse)
        g.addLayout(row, 4, 0, 1, 2)
        self.missing = QComboBox()
        self.missing.addItem("Extend the previous image", "previous")
        self.missing.addItem("Insert a black frame", "black")
        g.addWidget(self.missing, 4, 2)

        self.chk_json = QCheckBox("Also save timeline.json")
        self.chk_srt = QCheckBox("Also save subtitles (.srt) from the script lines")
        ex = QHBoxLayout()
        ex.addWidget(self.chk_json)
        ex.addSpacing(24)
        ex.addWidget(self.chk_srt)
        ex.addStretch(1)
        g.addLayout(ex, 5, 0, 1, 3)
        for col in range(3):
            g.setColumnStretch(col, 1)
        root.addWidget(form)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.hide()
        root.addWidget(self.bar)
        self.result = label("", wrap=True)
        self.result.hide()
        root.addWidget(self.result)

        act = QHBoxLayout()
        self.open_btn = button("Open folder", on_click=self._open_folder)
        self.open_btn.hide()
        act.addWidget(self.open_btn)
        act.addStretch(1)
        self.export_btn = button("Export to CapCut", "primary", self.export)
        act.addWidget(self.export_btn)
        root.addLayout(act)
        root.addStretch(1)
        self._out = ""

    def load(self):
        sc = self.p.scenes
        self.stat_vals["scenes"].setText(str(len(sc)))
        self.stat_vals["duration"].setText(fmt_time(sc[-1].end, False) if sc else "-")
        self.stat_vals["review"].setText(str(sum(1 for s in sc if s.needs_attention)))
        self.stat_vals["missing"].setText(str(sum(1 for s in sc if s.image is None)))
        if not self.name.text():
            self.name.setText(f"{Path(self.p.audio_path).stem} timeline")
        self.result.hide()
        self.open_btn.hide()

    def _browse_drafts(self):
        d = QFileDialog.getExistingDirectory(self, "CapCut drafts folder", self.drafts.text())
        if d:
            self.drafts.setText(d)

    def _open_folder(self):
        if self._out and Path(self._out).exists():
            os.startfile(self._out)

    def _show(self, text, color):
        self.result.setText(text)
        self.result.setStyleSheet(f"color: {color};")
        self.result.show()

    def export(self):
        name = self.name.text().strip() or "Timeline"
        drafts = self.drafts.text().strip()
        w, h = self.res.currentData()
        fps, mode = self.fps.currentData(), self.missing.currentData()
        self.settings.setValue("drafts_dir", drafts)
        scenes, audio = self.p.scenes, self.p.audio
        side = Path(self.p.script_path).parent
        want_json, want_srt = self.chk_json.isChecked(), self.chk_srt.isChecked()

        def work(report):
            out = exporter.export_capcut(scenes, audio, drafts, name, w, h, fps, mode, report)
            extra = []
            if want_json:
                exporter.write_json(scenes, audio, side / "timeline.json")
                extra.append("timeline.json")
            if want_srt:
                exporter.write_srt(scenes, side / "scenes.srt")
                extra.append("scenes.srt")
            return out, extra, side

        self.export_btn.setEnabled(False)
        self.result.hide()
        self.open_btn.hide()
        self.bar.show()
        self.task = Task(work, self)
        self.task.progress.connect(lambda m: self._show(m, theme.MUTED))
        self.task.done.connect(self._done)
        self.task.failed.connect(self._failed)
        self.task.start()

    def _done(self, res):
        out, extra, side = res
        self.bar.hide()
        self.export_btn.setEnabled(True)
        self._out = out
        msg = f"Exported to {out}\nRestart CapCut if it is open, then find the project in your drafts."
        if extra:
            msg += f"\nSaved next to your script: {', '.join(extra)}"
        self._show(msg, theme.SUCCESS)
        self.open_btn.show()

    def _failed(self, msg):
        self.bar.hide()
        self.export_btn.setEnabled(True)
        self._show("Export failed: " + msg, theme.DANGER)
