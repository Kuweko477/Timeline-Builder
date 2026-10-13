from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from ..core import media
from . import theme
from .export_page import ExportPage
from .import_page import ImportPage
from .process_page import ProcessPage
from .review_page import ReviewPage
from .state import Project
from .widgets import StepButton, label

STEPS = [("Import", "Scenes, script, voiceover"), ("Build", "Transcribe and align"),
         ("Review", "Check and adjust"), ("Export", "Create the CapCut draft")]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timeline Builder")
        self.resize(1360, 860)
        self.setMinimumSize(1120, 720)
        self.project = Project()
        self.reached = 0

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(260)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 28, 14, 20)
        sl.setSpacing(2)
        head = QVBoxLayout()
        head.setContentsMargins(14, 0, 0, 22)
        head.setSpacing(2)
        head.addWidget(label("Timeline Builder", "appName"))
        head.addWidget(label("Voiceover to CapCut timeline", "appTag"))
        sl.addLayout(head)
        self.steps = []
        for i, (t, s) in enumerate(STEPS):
            b = StepButton(i + 1, t, s)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            self.steps.append(b)
            sl.addWidget(b)
        sl.addStretch(1)
        sl.addWidget(label("Groq Whisper  |  CapCut", "faint"))
        lay.addWidget(side)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.import_page = ImportPage(self.project)
        self.process_page = ProcessPage(self.project)
        self.review_page = ReviewPage(self.project)
        self.export_page = ExportPage(self.project)
        for pg in (self.import_page, self.process_page, self.review_page, self.export_page):
            self.stack.addWidget(pg)

        self.import_page.build_requested.connect(self._build)
        self.process_page.finished.connect(lambda: self._advance(2))
        self.process_page.back_requested.connect(lambda: self.go(0))
        self.review_page.continue_requested.connect(lambda: self._advance(3))
        self.go(0)

    def _build(self):
        if not media.has_ffmpeg():
            QMessageBox.warning(self, "FFmpeg required",
                                "FFmpeg and FFprobe were not found in your PATH.\n"
                                "Install FFmpeg and restart the app.")
            return
        self.import_page.commit()
        self.reached = 1
        self.go(1)
        self.process_page.start()

    def _advance(self, i: int):
        self.reached = max(self.reached, i)
        self.go(i)

    def go(self, i: int):
        if i == 2:
            self.review_page.load()
        elif i == 3:
            self.export_page.load()
        self.stack.setCurrentIndex(i)
        for n, b in enumerate(self.steps):
            if n == i:
                b.set_state("active")
            elif n < self.reached or (n < i):
                b.set_state("done")
            elif n <= self.reached:
                b.set_state("todo")
            else:
                b.set_state("locked")
