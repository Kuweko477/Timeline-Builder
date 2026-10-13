"""Aligne chaque ligne de formated_script.txt (= scene N) sur transcript.json -> timeline.json"""
import json, re, os, unicodedata, difflib

def norm(w):
    w = unicodedata.normalize("NFD", w.lower().replace("œ", "oe").replace("æ", "ae"))
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)

def tokens(text):
    # l'apostrophe sépare les mots comme Whisper : l'ecriture -> l ecriture ; on garde les 2 conventions
    out = []
    for raw in re.split(r"\s+", text.strip()):
        for part in re.split(r"['’\-]", raw):
            n = norm(part)
            if n:
                out.append(n)
    return out

lines = [l.strip() for l in open("formated_script.txt", encoding="utf-8-sig")]
lines = [l for l in lines if l]
title, scenes = lines[0], lines[1:]
print("scenes:", len(scenes))

tr = json.load(open("transcript.json", encoding="utf-8"))
words = tr["words"]
duration = tr["duration"]
w_tok, w_idx = [], []   # tokens Whisper -> index du mot
for i, w in enumerate(words):
    for t in tokens(w["word"]):
        w_tok.append(t); w_idx.append(i)

s_tok, s_scene = [], []
for n, line in enumerate(scenes):
    for t in tokens(line):
        s_tok.append(t); s_scene.append(n)

sm = difflib.SequenceMatcher(None, s_tok, w_tok, autojunk=False)
s2w = {}
for a, b, size in sm.get_matching_blocks():
    for k in range(size):
        s2w[a + k] = b + k
print(f"tokens script appariés: {len(s2w)}/{len(s_tok)}")

first_tok = {}; last_tok = {}
for i, n in enumerate(s_scene):
    first_tok.setdefault(n, i); last_tok[n] = i

def first_word(n):
    for i in range(first_tok[n], last_tok[n] + 1):
        if i in s2w: return w_idx[s2w[i]]
def last_word(n):
    for i in range(last_tok[n], first_tok[n] - 1, -1):
        if i in s2w: return w_idx[s2w[i]]

N = len(scenes)
fw = [first_word(n) for n in range(N)]
lw = [last_word(n) for n in range(N)]
unmatched = [n + 1 for n in range(N) if fw[n] is None]

# début de scène (secondes) ; interpolation pour les scènes sans appariement
start = [None] * N
for n in range(N):
    if fw[n] is not None:
        start[n] = words[fw[n]]["start"]
        # frontière : milieu de la pause avec la scène précédente, max 0.3s avant le mot
        if n > 0 and lw[n - 1] is not None:
            pe = words[lw[n - 1]]["end"]
            gap = start[n] - pe
            if gap > 0:
                start[n] = start[n] - min(gap / 2, 0.3) if gap < 0.6 else start[n] - 0.3
for n in range(N):
    if start[n] is None:
        p = max((k for k in range(n) if start[k] is not None), default=None)
        q = min((k for k in range(n + 1, N) if start[k] is not None), default=None)
        t0 = start[p] if p is not None else 0.0
        t1 = start[q] if q is not None else duration
        p = -1 if p is None else p; q = N if q is None else q
        start[n] = t0 + (t1 - t0) * (n - p) / (q - p)
start[0] = 0.0
for n in range(1, N):                      # monotone
    start[n] = max(start[n], start[n - 1] + 0.05)

have = {int(f[:4]) for f in os.listdir("scenes") if f.lower().endswith(".jpg")}
timeline, missing = [], []
last_img = None
for n in range(N):
    end = start[n + 1] if n + 1 < N else duration
    num = n + 1
    img = f"scenes/{num:04d}.jpg"
    miss = num not in have
    if miss:
        missing.append(num); img_used = last_img
    else:
        img_used = img; last_img = img
    timeline.append({"scene": num, "start": round(start[n], 3), "end": round(end, 3),
                     "duration": round(end - start[n], 3), "image": img_used,
                     "image_missing": miss, "interpolated": fw[n] is None, "text": scenes[n]})

json.dump({"title": title, "audio": "voiceover.mp3", "duration": duration, "scenes": timeline},
          open("timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
d = [t["duration"] for t in timeline]
print("interpolées (non appariées):", unmatched)
print("images manquantes:", missing)
print(f"durée scène min/moy/max: {min(d):.2f}/{sum(d)/len(d):.2f}/{max(d):.2f}")
