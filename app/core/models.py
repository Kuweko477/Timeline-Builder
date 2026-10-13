from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Scene:
    number: int
    text: str
    start: float = 0.0
    end: float = 0.0
    image: Path | None = None
    interpolated: bool = False
    match: float = 1.0          # share of script words found in the transcript
    edited: bool = False
    auto_start: float = 0.0     # start computed automatically (for "reset")

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def flags(self) -> list[str]:
        out = []
        if self.image is None:
            out.append("No image")
        if self.interpolated:
            out.append("Interpolated")
        elif self.match < 0.6:
            out.append("Low match")
        return out

    @property
    def needs_attention(self) -> bool:
        return bool(self.flags)
