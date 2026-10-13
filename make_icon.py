"""Generate assets/icon.ico (violet-to-blue gradient tile with timeline bars)."""
from pathlib import Path
from PIL import Image, ImageDraw

S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
grad = Image.new("RGBA", (S, S))
px = grad.load()
c1, c2 = (124, 108, 255), (79, 140, 255)
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * S)
        px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((16, 16, S - 16, S - 16), radius=112, fill=255)
img.paste(grad, (0, 0), mask)
d = ImageDraw.Draw(img)
bars = [(112, 120, 232), (112, 232, 376), (200, 232, 400)]  # (x0, y0, x1) clip blocks on two tracks
tracks = [(150, 214, [(100, 220), (232, 330), (342, 412)]), (254, 318, [(100, 160), (172, 292), (304, 412)])]
for y0, y1, clips in tracks:
    for a, b in clips:
        d.rounded_rectangle((a, y0, b, y1), radius=18, fill=(255, 255, 255, 235))
d.rounded_rectangle((250, 100, 262, 400), radius=6, fill=(12, 14, 20, 255))
out = Path(__file__).parent
(out / "assets").mkdir(exist_ok=True)
img.save(out / "assets" / "icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
img.save(out / "assets" / "icon.png")
print("icon ok")
