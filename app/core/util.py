from __future__ import annotations

import re
from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
TITLE_RE = re.compile(r"^\s*(titre|title)\s*[:：]", re.IGNORECASE)


def fmt_time(t: float, ms: bool = True) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    base = f"{int(m):02d}:{s:06.3f}" if ms else f"{int(m):02d}:{int(s):02d}"
    return f"{int(h)}:{base}" if h >= 1 else base


def read_text(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_script(path: str | Path, skip_title: bool | None = None):
    """Return (title, scene_lines, title_detected). One non-empty line = one scene."""
    lines = [ln.strip() for ln in read_text(path).splitlines()]
    lines = [ln for ln in lines if ln]
    detected = bool(lines) and bool(TITLE_RE.match(lines[0]))
    if skip_title is None:
        skip_title = detected
    if skip_title and lines:
        return lines[0], lines[1:], detected
    return None, lines, detected


def scan_images(folder: str | Path) -> dict[int, Path]:
    """Map scene number -> image path, using the first number found in the file name."""
    found: dict[int, Path] = {}
    for p in sorted(Path(folder).iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_EXT:
            m = re.search(r"\d+", p.stem)
            if m:
                found.setdefault(int(m.group()), p)
    return found


def compact_ranges(nums: list[int], limit: int = 12) -> str:
    shown = ", ".join(str(n) for n in nums[:limit])
    return shown + (f" and {len(nums) - limit} more" if len(nums) > limit else "")
