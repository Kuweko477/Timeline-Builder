"""timeline.json -> brouillon CapCut (via pycapcut). Usage: python export_capcut.py"""
import json, os
import pycapcut as cc
from pycapcut import trange

ROOT = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.join(os.environ["LOCALAPPDATA"], "CapCut", "User Data", "Projects", "com.lveditor.draft")
NAME = "Timeline_Ecriture"

tl = json.load(open(os.path.join(ROOT, "timeline.json"), encoding="utf-8"))
folder = cc.DraftFolder(DRAFTS)
script = folder.create_draft(NAME, 1920, 1080, fps=30, allow_replace=True)
script.add_track(cc.TrackType.video, "Scenes")
script.add_track(cc.TrackType.audio, "Voix off")

us = lambda s: int(round(s * 1_000_000))
for sc in tl["scenes"]:
    s, e = us(sc["start"]), us(sc["end"])   # bornes en µs : pas de trou ni de chevauchement
    img = os.path.join(ROOT, sc["image"])
    script.add_segment(cc.VideoSegment(img, trange(s, e - s)), "Scenes")

script.add_segment(cc.AudioSegment(os.path.join(ROOT, tl["audio"]), trange(0, us(tl["duration"]))), "Voix off")
script.save()
print("Brouillon créé :", os.path.join(DRAFTS, NAME))
