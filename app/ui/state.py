from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..core.models import Scene


@dataclass
class Project:
    images_dir: str = ""
    script_path: str = ""
    audio_path: str = ""
    audio_duration: float = 0.0
    images: dict = field(default_factory=dict)
    lines: list = field(default_factory=list)
    skip_title: bool = True
    api_key: str = ""
    model: str = "whisper-large-v3"
    language: str = "auto"
    scenes: list[Scene] = field(default_factory=list)

    @property
    def audio(self) -> Path:
        return Path(self.audio_path)


class Task(QThread):
    """Run fn(report) off the UI thread. report(message) emits progress text."""
    progress = Signal(str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(self._fn(self.progress.emit))
        except Exception as exc:  # surfaced to the UI
            self.failed.emit(str(exc) or exc.__class__.__name__)
