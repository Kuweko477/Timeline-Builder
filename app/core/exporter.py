from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import Scene
from .media import PipelineError


def default_drafts_dir() -> str:
    return str(Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft")


def _us(seconds: float) -> int:
    return int(round(seconds * 1_000_000))


def _black_frame(w: int, h: int) -> Path:
    from PIL import Image
    p = Path(tempfile.gettempdir()) / "TimelineBuilder" / f"black_{w}x{h}.png"
    p.parent.mkdir(exist_ok=True)
    if not p.exists():
        Image.new("RGB", (w, h), (0, 0, 0)).save(p)
    return p


def export_capcut(scenes: list[Scene], audio: Path, drafts_dir: str, name: str,
                  width: int, height: int, fps: int, missing_mode: str, report=lambda *_: None) -> str:
    try:
        import pycapcut as cc
        from pycapcut import trange
    except ImportError:
        raise PipelineError("The 'pycapcut' package is not installed (pip install pycapcut).")
    if not Path(drafts_dir).is_dir():
        raise PipelineError(f"CapCut drafts folder not found:\n{drafts_dir}")

    folder = cc.DraftFolder(drafts_dir)
    script = folder.create_draft(name, width, height, fps=fps, allow_replace=True)
    script.add_track(cc.TrackType.video, "Scenes")
    script.add_track(cc.TrackType.audio, "Voiceover")

    last_img: Path | None = None
    total = len(scenes)
    for i, sc in enumerate(scenes):
        img = sc.image
        if img is not None:
            last_img = img
        elif missing_mode == "previous" and last_img is not None:
            img = last_img
        else:
            img = _black_frame(width, height)
        s, e = _us(sc.start), _us(sc.end)
        script.add_segment(cc.VideoSegment(str(img), trange(s, max(e - s, 1))), "Scenes")
        if i % 25 == 0:
            report(f"Adding scenes ({i + 1}/{total})")
    report("Adding voiceover")
    script.add_segment(cc.AudioSegment(str(audio), trange(0, _us(scenes[-1].end))), "Voiceover")
    report("Saving project")
    script.save()
    return str(Path(drafts_dir) / name)


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(scenes: list[Scene], path: Path) -> None:
    blocks = [f"{i}\n{_srt_time(s.start)} --> {_srt_time(s.end)}\n{s.text}\n" for i, s in enumerate(scenes, 1)]
    path.write_text("\n".join(blocks), encoding="utf-8")


def write_json(scenes: list[Scene], audio: Path, path: Path) -> None:
    data = {"audio": str(audio), "duration": scenes[-1].end if scenes else 0, "scenes": [
        {"scene": s.number, "start": round(s.start, 3), "end": round(s.end, 3),
         "image": str(s.image) if s.image else None, "text": s.text,
         "interpolated": s.interpolated, "edited": s.edited} for s in scenes]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
