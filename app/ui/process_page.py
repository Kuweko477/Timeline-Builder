from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QVBoxLayout, QWidget)

from ..core import media
from ..core.align import align
from ..core.util import fmt_time
from . import theme
from .state import Project, Task
from .widgets import PageHeader, button, card, label

STAGES = [("Prepare audio", "Compress the voiceover for upload"),
          ("Transcribe speech", "Word-level timestamps from Groq Whisper"),
          ("Align script", "Match every scene to its place in the narration")]
COLORS = {"pending": theme.BORDER_STRONG, "running": theme.ACCENT_2, "done": theme.SUCCESS, "error": theme.DANGER}


class StageRow(QWidget):
    def __init__(self, title: str, detail: str):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(14)
        self.dot = QLabel()
        self.dot.setFixedSize(12, 12)
        lay.addWidget(self.dot)
        col = QVBoxLayout()
        col.setSpacing(1)
        self.title = label(title, "cardTitle")
        self.detail = label(detail, "muted")
        col.addWidget(self.title)
        col.addWidget(self.detail)
        lay.addLayout(col, 1)
        self.state_lbl = label("", "faint")
        lay.addWidget(self.state_lbl)
        self.default_detail = detail
        self.set_state("pending")

    def set_state(self, state: str, detail: str | None = None):
        c = COLORS[state]
        ring = f"border: 2px solid {c};" if state == "pending" else f"background: {c}; border: none;"
        self.dot.setStyleSheet(f"{ring} border-radius: 6px;")
        self.state_lbl.setText({"pending": "Waiting", "running": "In progress", "done": "Done",
                                "error": "Failed"}[state])
        self.title.setStyleSheet(f"color: {theme.FAINT if state == 'pending' else theme.TEXT};")
        self.detail.setText(detail or self.default_detail)


class ProcessPage(QWidget):
    finished = Signal()
    back_requested = Signal()

    def __init__(self, project: Project):
        super().__init__()
        self.setObjectName("page")
        self.p = project
        self.task: Task | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 34, 40, 28)
        root.setSpacing(22)
        root.addWidget(PageHeader("Building your timeline",
                                  "Transcribing the voiceover and placing every scene. "
                                  "This usually takes under a minute."))
        c = card()
        cl = QVBoxLayout(c)
        cl.setContentsMargins(26, 22, 26, 22)
        cl.setSpacing(6)
        self.rows = [StageRow(t, d) for t, d in STAGES]
        for r in self.rows:
            cl.addWidget(r)
        cl.addSpacing(10)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setFixedHeight(8)
        cl.addWidget(self.bar)
        root.addWidget(c)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        root.addWidget(self.log)

        self.error_lbl = label("", wrap=True)
        self.error_lbl.setStyleSheet(f"color: {theme.DANGER};")
        self.error_lbl.hide()
        root.addWidget(self.error_lbl)

        act = QHBoxLayout()
        self.back_btn = button("Back to import", on_click=self.back_requested.emit)
        self.retry_btn = button("Retry", "primary", self.start)
        self.back_btn.hide()
        self.retry_btn.hide()
        act.addWidget(self.back_btn)
        act.addStretch(1)
        act.addWidget(self.retry_btn)
        root.addLayout(act)
        root.addStretch(1)

    def _log(self, msg: str):
        self.log.appendPlainText(msg)

    def start(self):
        p = self.p
        for r in self.rows:
            r.set_state("pending")
        self.log.clear()
        self.error_lbl.hide()
        self.back_btn.hide()
        self.retry_btn.hide()
        self.bar.setRange(0, 0)
        self.rows[0].set_state("running")
        self._log(f"Voiceover: {p.audio.name} ({fmt_time(p.audio_duration, False)})")
        self._log(f"Script: {len(p.lines)} scenes  |  Images: {len(p.images)}")

        def work(report):
            data = media.get_transcript(p.audio, p.audio_duration, p.api_key, p.model, p.language, report)
            report("Aligning script to speech")
            return data, align(p.lines, data, p.images)

        self.task = Task(work, self)
        self.task.progress.connect(self._on_progress)
        self.task.done.connect(self._on_done)
        self.task.failed.connect(self._on_failed)
        self.task.start()

    def _on_progress(self, msg: str):
        self._log(msg)
        if msg.startswith("Compressing"):
            self.rows[0].set_state("running")
        elif msg.startswith("Transcribing") or msg.startswith("Using cached"):
            self.rows[0].set_state("done")
            self.rows[1].set_state("running", "Waiting for Groq ..." if msg.startswith("Trans") else "Loaded from cache")
        elif msg.startswith("Aligning"):
            self.rows[1].set_state("done")
            self.rows[2].set_state("running")

    def _on_done(self, result):
        data, scenes = result
        self.p.scenes = scenes
        for r in self.rows:
            r.set_state("done")
        flagged = sum(1 for s in scenes if s.needs_attention)
        self.rows[2].set_state("done", f"{len(scenes)} scenes placed, {flagged} to review")
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        self._log(f"{len(data['words'])} words transcribed. {flagged} scene(s) flagged for review.")
        QTimer.singleShot(650, self.finished.emit)

    def _on_failed(self, msg: str):
        for r in self.rows:
            if r.state_lbl.text() == "In progress":
                r.set_state("error")
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        self.error_lbl.setText(msg)
        self.error_lbl.show()
        self._log("Error: " + msg)
        self.back_btn.show()
        self.retry_btn.show()
