from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QVBoxLayout,
                               QWidget)

from ..core import media
from ..core.util import compact_ranges, fmt_time, parse_script, scan_images
from . import theme
from .state import Project
from .widgets import DropCard, PageHeader, button, card, label

MODELS = [("Whisper Large v3  (most accurate)", "whisper-large-v3"),
          ("Whisper Large v3 Turbo  (faster)", "whisper-large-v3-turbo")]
LANGUAGES = [("Auto-detect", "auto"), ("French", "fr"), ("English", "en"), ("Spanish", "es"),
             ("German", "de"), ("Italian", "it"), ("Portuguese", "pt"), ("Dutch", "nl"),
             ("Arabic", "ar"), ("Japanese", "ja")]


def _env_key() -> str:
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    for base in (Path.cwd(), Path(__file__).resolve().parents[2]):
        env = base / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("GROQ_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    return ""


class ImportPage(QWidget):
    build_requested = Signal()

    def __init__(self, project: Project):
        super().__init__()
        self.setObjectName("page")
        self.p = project
        self.settings = QSettings("TimelineBuilder", "TimelineBuilder")

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 34, 40, 28)
        root.setSpacing(22)
        root.addWidget(PageHeader("Import your project",
                                  "Drop in your generated scenes, the script and the voiceover. "
                                  "Each script line is one scene, matched to the image with the same number."))

        row = QHBoxLayout()
        row.setSpacing(18)
        self.c_scenes = DropCard("folder", "Scenes", "A folder of images numbered 0001, 0002, ... "
                                 "matching the script lines.", "folder")
        self.c_script = DropCard("doc", "Script", "A text file with one scene per line (.txt).", "file",
                                 "Text files (*.txt *.md);;All files (*)")
        self.c_audio = DropCard("wave", "Voiceover", "The narration audio file (mp3, wav, m4a ...).", "file",
                                "Audio files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg);;All files (*)")
        for c in (self.c_scenes, self.c_script, self.c_audio):
            row.addWidget(c, 1)
        root.addLayout(row)

        # --- transcription settings
        st = card()
        g = QGridLayout(st)
        g.setContentsMargins(22, 18, 22, 18)
        g.setHorizontalSpacing(18)
        g.setVerticalSpacing(8)
        g.addWidget(label("TRANSCRIPTION", "sectionTitle"), 0, 0, 1, 3)
        g.addWidget(label("Groq API key", "muted"), 1, 0)
        g.addWidget(label("Model", "muted"), 1, 1)
        g.addWidget(label("Spoken language", "muted"), 1, 2)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("gsk_...")
        reveal = QAction(self.key)
        reveal.setText("Show")
        reveal.triggered.connect(self._toggle_key)
        self.reveal = reveal
        self.key.addAction(reveal, QLineEdit.TrailingPosition)
        self.model = QComboBox()
        for t, v in MODELS:
            self.model.addItem(t, v)
        self.lang = QComboBox()
        for t, v in LANGUAGES:
            self.lang.addItem(t, v)
        g.addWidget(self.key, 2, 0)
        g.addWidget(self.model, 2, 1)
        g.addWidget(self.lang, 2, 2)
        g.setColumnStretch(0, 3)
        g.setColumnStretch(1, 2)
        g.setColumnStretch(2, 2)
        opts = QHBoxLayout()
        self.remember = QCheckBox("Remember the key on this computer")
        self.skip_title = QCheckBox("First script line is a title (skip it)")
        opts.addWidget(self.remember)
        opts.addSpacing(24)
        opts.addWidget(self.skip_title)
        opts.addStretch(1)
        g.addLayout(opts, 3, 0, 1, 3)
        root.addWidget(st)

        # --- validation + action
        bottom = QHBoxLayout()
        self.summary = label("", wrap=True)
        bottom.addWidget(self.summary, 1)
        self.build_btn = button("Build timeline", "primary", self.build_requested.emit)
        self.build_btn.setEnabled(False)
        bottom.addWidget(self.build_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
        root.addLayout(bottom)
        root.addStretch(1)

        saved = self.settings.value("api_key", "")
        self.key.setText(saved or _env_key())
        self.remember.setChecked(bool(saved))
        self.model.setCurrentIndex(max(0, self.model.findData(self.settings.value("model", "whisper-large-v3"))))
        self.lang.setCurrentIndex(max(0, self.lang.findData(self.settings.value("language", "auto"))))

        self.c_scenes.changed.connect(self._set_scenes)
        self.c_script.changed.connect(self._set_script)
        self.c_audio.changed.connect(self._set_audio)
        self.key.textChanged.connect(self._validate)
        self.skip_title.toggled.connect(self._reparse_script)
        self.skip_title.setChecked(True)

    # -------------------------------------------------- handlers
    def _toggle_key(self):
        shown = self.key.echoMode() == QLineEdit.Normal
        self.key.setEchoMode(QLineEdit.Password if shown else QLineEdit.Normal)
        self.reveal.setText("Show" if shown else "Hide")

    def _set_scenes(self, path):
        self.p.images_dir = path
        try:
            self.p.images = scan_images(path)
        except OSError as e:
            self.p.images = {}
            self.c_scenes.set_status(str(e), "error")
            return self._validate()
        if not self.p.images:
            self.c_scenes.set_status("No numbered images found in this folder", "error")
        else:
            nums = sorted(self.p.images)
            self.c_scenes.set_status(f"{len(nums)} images  |  {nums[0]} to {nums[-1]}", "ok")
        self._validate()

    def _set_script(self, path):
        self.p.script_path = path
        self._reparse_script()

    def _reparse_script(self):
        if not self.p.script_path:
            return
        try:
            title, lines, detected = parse_script(self.p.script_path, self.skip_title.isChecked())
        except OSError as e:
            self.c_script.set_status(str(e), "error")
            self.p.lines = []
            return self._validate()
        self.p.lines = lines
        self.p.skip_title = self.skip_title.isChecked()
        note = "  |  title skipped" if title else ""
        self.c_script.set_status(f"{len(lines)} scenes{note}" if lines else "The script is empty",
                                 "ok" if lines else "error")
        self._validate()

    def _set_audio(self, path):
        self.p.audio_path = path
        if not media.has_ffmpeg():
            self.c_audio.set_status("FFmpeg not found in PATH", "error")
            self.p.audio_duration = 0
            return self._validate()
        try:
            self.p.audio_duration = media.probe_duration(path)
            mb = Path(path).stat().st_size / 1_048_576
            self.c_audio.set_status(f"{fmt_time(self.p.audio_duration, False)}  |  {mb:.1f} MB", "ok")
        except Exception as e:
            self.p.audio_duration = 0
            self.c_audio.set_status(str(e), "error")
        self._validate()

    # -------------------------------------------------- validation
    def _validate(self, *_):
        p = self.p
        msgs, level = [], "ok"
        ready = bool(p.images and p.lines and p.audio_duration > 0)
        if p.images and p.lines:
            missing = [n for n in range(1, len(p.lines) + 1) if n not in p.images]
            extra = sorted(n for n in p.images if n > len(p.lines))
            if missing:
                msgs.append(f"{len(missing)} scene(s) have no image ({compact_ranges(missing)}). "
                            "You will choose how to fill them at export.")
                level = "warn"
            if extra:
                msgs.append(f"{len(extra)} image(s) beyond the last script line will be ignored.")
                level = "warn"
            if not missing and not extra:
                msgs.append(f"All {len(p.lines)} scenes have a matching image.")
        elif not ready:
            msgs.append("Add the scenes folder, the script and the voiceover to continue.")
            level = "muted"
        if ready and not self.key.text().strip():
            msgs.append("Enter your Groq API key to transcribe the voiceover.")
            level = "warn"
            ready = False
        color = {"ok": theme.SUCCESS, "warn": theme.WARN}.get(level, theme.MUTED)
        self.summary.setText("  ".join(msgs))
        self.summary.setStyleSheet(f"color: {color};")
        self.build_btn.setEnabled(ready)

    def commit(self):
        """Copy UI settings into the project; persist preferences."""
        self.p.api_key = self.key.text().strip()
        self.p.model = self.model.currentData()
        self.p.language = self.lang.currentData()
        self.settings.setValue("model", self.p.model)
        self.settings.setValue("language", self.p.language)
        if self.remember.isChecked():
            self.settings.setValue("api_key", self.p.api_key)
        else:
            self.settings.remove("api_key")
