from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path

from .models import Scene


def _norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower().replace("œ", "oe").replace("æ", "ae"))
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def _tokens(text: str) -> list[str]:
    out = []
    for raw in re.split(r"\s+", text.strip()):
        for part in re.split(r"['’\-]", raw):
            n = _norm(part)
            if n:
                out.append(n)
    return out


def align(lines: list[str], transcript: dict, images: dict[int, Path]) -> list[Scene]:
    """Match each script line to the transcribed words and compute its start/end time."""
    words = transcript["words"]
    duration = float(transcript["duration"])
    n_scenes = len(lines)

    w_tok, w_idx = [], []
    for i, w in enumerate(words):
        for t in _tokens(w["word"]):
            w_tok.append(t)
            w_idx.append(i)

    s_tok, s_scene = [], []
    for n, line in enumerate(lines):
        for t in _tokens(line):
            s_tok.append(t)
            s_scene.append(n)

    sm = difflib.SequenceMatcher(None, s_tok, w_tok, autojunk=False)
    s2w: dict[int, int] = {}
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            s2w[a + k] = b + k

    first_tok: dict[int, int] = {}
    last_tok: dict[int, int] = {}
    for i, n in enumerate(s_scene):
        first_tok.setdefault(n, i)
        last_tok[n] = i

    def first_word(n):
        if n not in first_tok:
            return None
        for i in range(first_tok[n], last_tok[n] + 1):
            if i in s2w:
                return w_idx[s2w[i]]

    def last_word(n):
        if n not in first_tok:
            return None
        for i in range(last_tok[n], first_tok[n] - 1, -1):
            if i in s2w:
                return w_idx[s2w[i]]

    fw = [first_word(n) for n in range(n_scenes)]
    lw = [last_word(n) for n in range(n_scenes)]

    start: list[float | None] = [None] * n_scenes
    for n in range(n_scenes):
        if fw[n] is None:
            continue
        t = words[fw[n]]["start"]
        if n > 0 and lw[n - 1] is not None:
            gap = t - words[lw[n - 1]]["end"]
            if gap > 0:  # cut inside the pause, at most 0.3 s before the word
                t -= gap / 2 if gap < 0.6 else 0.3
        start[n] = t

    for n in range(n_scenes):  # interpolate scenes with no matched word
        if start[n] is None:
            p = max((k for k in range(n) if start[k] is not None), default=None)
            q = min((k for k in range(n + 1, n_scenes) if start[k] is not None), default=None)
            t0 = start[p] if p is not None else 0.0
            t1 = start[q] if q is not None else duration
            pi = -1 if p is None else p
            qi = n_scenes if q is None else q
            start[n] = t0 + (t1 - t0) * (n - pi) / (qi - pi)
    if start:
        start[0] = 0.0
    for n in range(1, n_scenes):
        start[n] = max(start[n], start[n - 1] + 0.05)

    scenes = []
    for n, line in enumerate(lines):
        toks = _tokens(line)
        matched = sum(1 for i in range(first_tok.get(n, 0), last_tok.get(n, -1) + 1) if i in s2w)
        end = start[n + 1] if n + 1 < n_scenes else duration
        scenes.append(Scene(
            number=n + 1, text=line, start=start[n], end=end,
            image=images.get(n + 1), interpolated=fw[n] is None,
            match=(matched / len(toks)) if toks else 1.0, auto_start=start[n],
        ))
    return scenes
