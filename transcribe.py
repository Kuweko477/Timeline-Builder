"""Transcrit voiceover_16k.mp3 via Groq Whisper -> transcript.json (timestamps mot + segment)."""
import json, os, uuid, urllib.request

def load_env(path=".env"):
    for line in open(path, encoding="utf-8"):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"').strip("'"))

load_env()
key = os.environ["GROQ_API_KEY"]
audio = open("voiceover_16k.mp3", "rb").read()
b = uuid.uuid4().hex
fields = {
    "model": "whisper-large-v3",
    "language": "fr",
    "response_format": "verbose_json",
    "temperature": "0",
}
parts = []
for k, v in fields.items():
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
for g in ("word", "segment"):
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="timestamp_granularities[]"\r\n\r\n{g}\r\n'.encode())
parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="voiceover_16k.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode())
parts.append(audio)
parts.append(f"\r\n--{b}--\r\n".encode())
req = urllib.request.Request(
    "https://api.groq.com/openai/v1/audio/transcriptions",
    data=b"".join(parts),
    headers={"Authorization": f"Bearer {key}",
             "Content-Type": f"multipart/form-data; boundary={b}",
             "User-Agent": "timeline-builder/1.0"},
)
with urllib.request.urlopen(req, timeout=600) as r:
    data = json.loads(r.read())
json.dump(data, open("transcript.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("duree:", data.get("duration"), "segments:", len(data["segments"]), "mots:", len(data.get("words", [])))
