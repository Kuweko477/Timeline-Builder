from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_LIMIT = 24 * 1024 * 1024  # stay under the 25 MB upload limit
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class PipelineError(Exception):
    pass


def has_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def probe_duration(path: str | Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, creationflags=_NOWIN, timeout=60)
        return float(out.stdout.strip())
    except Exception as exc:
        raise PipelineError(f"Could not read audio duration: {exc}")


def compress_audio(src: str | Path, duration: float) -> Path:
    """Mono 16 kHz MP3, small enough for Groq's upload limit."""
    dst_dir = Path(tempfile.gettempdir()) / "TimelineBuilder"
    dst_dir.mkdir(exist_ok=True)
    dst = dst_dir / "voiceover_16k.mp3"
    for kbps in (48, 32, 24):
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn",
             "-ac", "1", "-ar", "16000", "-b:a", f"{kbps}k", str(dst)],
            check=True, creationflags=_NOWIN)
        if dst.stat().st_size <= GROQ_LIMIT:
            return dst
    raise PipelineError("The voiceover is too long to fit Groq's 25 MB upload limit, even compressed.")


def _cache_path(audio: Path, model: str, language: str) -> Path:
    st = audio.stat()
    key = hashlib.sha1(f"{audio.resolve()}|{st.st_size}|{st.st_mtime_ns}|{model}|{language}".encode()).hexdigest()
    base = Path(os.environ.get("APPDATA", Path.home())) / "TimelineBuilder" / "cache"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{key}.json"


def transcribe(audio: Path, api_key: str, model: str, language: str) -> dict:
    body = []
    boundary = uuid.uuid4().hex

    def field(name, value):
        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())

    field("model", model)
    if language and language != "auto":
        field("language", language)
    field("response_format", "verbose_json")
    field("temperature", "0")
    field("timestamp_granularities[]", "word")
    field("timestamp_granularities[]", "segment")
    body.append((f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                 f'filename="audio.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n').encode())
    body.append(audio.read_bytes())
    body.append(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        GROQ_URL, data=b"".join(body),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}",
                 "User-Agent": "timeline-builder/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            pass
        hint = {401: "Invalid API key.", 413: "File too large.", 429: "Rate limit reached, try again shortly."}.get(e.code, "")
        raise PipelineError(f"Groq error {e.code}. {hint} {detail}".strip())
    except urllib.error.URLError as e:
        raise PipelineError(f"Network error: {e.reason}")


def get_transcript(audio: Path, duration: float, api_key: str, model: str, language: str, report) -> dict:
    cache = _cache_path(audio, model, language)
    if cache.exists():
        report("Using cached transcription")
        return json.loads(cache.read_text(encoding="utf-8"))
    report("Compressing audio")
    small = compress_audio(audio, duration)
    report("Transcribing with Groq Whisper")
    data = transcribe(small, api_key, model, language)
    if not data.get("words"):
        raise PipelineError("Groq returned no word-level timestamps.")
    data["duration"] = data.get("duration") or duration
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data
