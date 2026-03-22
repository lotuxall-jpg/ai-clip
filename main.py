
import os
import sys
import json
import time
import random
import logging
import textwrap
import argparse
import subprocess
from pathlib import Path

# ═══════════════════════════════════════════════════════════════

# AUTO INSTALL DEPENDENCIES

# ═══════════════════════════════════════════════════════════════

REQUIRED_PACKAGES = {
“anthropic”:             “anthropic”,
“openai”:                “openai”,
“yt_dlp”:                “yt-dlp”,
“feedparser”:            “feedparser”,
“requests”:              “requests”,
“whisper”:               “openai-whisper”,
“dotenv”:                “python-dotenv”,
“googleapiclient”:       “google-api-python-client”,
“google_auth_oauthlib”:  “google-auth-oauthlib”,
}

def install_dependencies():
print(”\n📦 Checking dependencies…\n”)
for import_name, pip_name in REQUIRED_PACKAGES.items():
try:
**import**(import_name.split(”.”)[0])
print(f”  ✅ {pip_name}”)
except ImportError:
print(f”  ⬇️  Installing {pip_name}…”)
subprocess.run([sys.executable, “-m”, “pip”, “install”, pip_name, “-q”], check=True)
print(f”  ✅ {pip_name} installed”)
print(”\n✅ All dependencies ready.\n”)

# ═══════════════════════════════════════════════════════════════

# FIRST-TIME SETUP  (python main.py –setup)

# ═══════════════════════════════════════════════════════════════

ENV_TEMPLATE = “””\

# ─────────────────────────────────────────────────────────

# AI Clip Generator — Environment Variables

# Fill in your keys, then run:  python main.py

# ─────────────────────────────────────────────────────────

# AI Provider — “claude” or “chatgpt”

AI_PROVIDER=claude

# Anthropic (Claude) API Key → https://console.anthropic.com/

ANTHROPIC_API_KEY=your_anthropic_key_here

# OpenAI (ChatGPT) API Key → https://platform.openai.com/api-keys

OPENAI_API_KEY=your_openai_key_here

# Telegram Bot (alerts/logging only) → https://t.me/BotFather

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# TikTok API Access Token → https://developers.tiktok.com/

TIKTOK_ACCESS_TOKEN=your_tiktok_access_token

# Auto-posting toggles

AUTO_POST_TIKTOK=true
AUTO_POST_YOUTUBE=true

# Videos to process per run (avoids rate limits)

MAX_VIDEOS_PER_RUN=2
“””

REQUIREMENTS_TEMPLATE = “””  
anthropic
openai
yt-dlp
feedparser
requests
openai-whisper
python-dotenv
google-api-python-client
google-auth-oauthlib
google-auth
“””

README_TEMPLATE = “””\

# 🎬 AI Clip Generator

Automatically downloads YouTube videos, extracts viral highlights using AI,
adds animated captions + effects, and posts to TikTok & YouTube Shorts.

-----

## 🚀 Quick Start

### 1. Install system dependency (ffmpeg)

```
macOS:   brew install ffmpeg
Ubuntu:  sudo apt install ffmpeg
Windows: https://ffmpeg.org/download.html
```

### 2. First-time project setup

```
python main.py --setup
```

Creates your `.env`, all folders, `requirements.txt`, and this README.

### 3. Fill in your API keys

Edit `.env` with:

- Claude API key  → https://console.anthropic.com/
- ChatGPT API key → https://platform.openai.com/api-keys
- TikTok token    → https://developers.tiktok.com/
- YouTube OAuth   → Google Cloud Console → YouTube Data API v3

### 4. (YouTube) Add OAuth credentials

Download `client_secrets.json` from Google Cloud Console and place it here.

### 5. Run

```
python main.py
```

-----

## 📁 Project Structure

```
project/
├── main.py                ← This file (everything in one)
├── .env                   ← Your API keys
├── requirements.txt
├── client_secrets.json    ← YouTube OAuth (you provide)
├── posted_log.json        ← Tracks what's been processed
├── app.log
├── downloads/             ← Raw source videos
├── clips/                 ← Intermediate processing files
├── output/                ← Final clips ready to post
└── assets/
    ├── music/             ← Drop .mp3 background music here
    ├── sfx/               ← Drop .mp3 sound effects here
    └── branding/          ← Optional: intro.mp4 + outro.mp4
```

-----

## ⚙️ Configuration (edit CONFIG block in main.py)

|Setting                |Default|Description                         |
|-----------------------|-------|------------------------------------|
|AI_PROVIDER            |claude |“claude” or “chatgpt”               |
|CLIPS_PER_VIDEO        |3      |Clips extracted per video           |
|CLIP_MAX_SECONDS       |59     |Max clip length                     |
|FAST_CUT_THRESHOLD     |0.7    |Min AI engagement score to keep clip|
|ENABLE_CAPTIONS        |True   |Animated subtitles                  |
|ENABLE_BACKGROUND_MUSIC|True   |Requires files in assets/music/     |
|ENABLE_ZOOM_EFFECTS    |True   |Punch-in zoom                       |
|ENABLE_COLOR_GRADING   |True   |Cinematic colour grade              |
|ENABLE_INTRO_OUTRO     |True   |Branding overlay                    |

-----

## 🔔 Telegram

Used for monitoring only — not for posting clips.
You get alerts when clips are posted, errors occur, or a run completes.

-----

## ❓ Troubleshooting

- **FFmpeg not found** → Make sure ffmpeg is installed and in your PATH
- **Whisper is slow** → Change `"base"` to `"tiny"` in transcribe_video()
- **TikTok fails** → Ensure your token has `video.publish` scope
- **YouTube OAuth** → First run opens a browser to authorise (normal)
  “””

def run_setup():
print(”\n🛠️  Running first-time setup…\n”)
for folder in [“downloads”, “clips”, “output”, “assets/music”, “assets/sfx”, “assets/branding”]:
Path(folder).mkdir(parents=True, exist_ok=True)
print(f”  📁 {folder}/”)

```
if not Path(".env").exists():
    Path(".env").write_text(ENV_TEMPLATE)
    print("\n  📝 .env created  ← FILL IN YOUR API KEYS")
else:
    print("\n  ⏭️  .env already exists — skipping")

Path("requirements.txt").write_text(REQUIREMENTS_TEMPLATE)
print("  📝 requirements.txt created")
Path("README.md").write_text(README_TEMPLATE)
print("  📝 README.md created")

print("\n" + "═"*55)
print("  ✅ Setup complete!")
print("═"*55)
print("\n  👉 Next steps:")
print("  1. Open .env and fill in your API keys")
print("  2. Install ffmpeg if not already installed")
print("  3. Run:  python main.py\n")
```

# ═══════════════════════════════════════════════════════════════

# LOAD .ENV + BUILD CONFIG

# ═══════════════════════════════════════════════════════════════

def load_env():
env_path = Path(”.env”)
if env_path.exists():
try:
from dotenv import load_dotenv
load_dotenv()
except ImportError:
for line in env_path.read_text().splitlines():
line = line.strip()
if line and not line.startswith(”#”) and “=” in line:
k, _, v = line.partition(”=”)
os.environ.setdefault(k.strip(), v.strip())

load_env()

CONFIG = {
# ── AI Provider ─────────────────────────────────────────
“AI_PROVIDER”:        os.getenv(“AI_PROVIDER”, “claude”),

```
# ── API Keys ────────────────────────────────────────────
"ANTHROPIC_API_KEY":  os.getenv("ANTHROPIC_API_KEY", ""),
"OPENAI_API_KEY":     os.getenv("OPENAI_API_KEY", ""),

# ── Source Channels ─────────────────────────────────────
"YOUTUBE_CHANNEL_IDS": [
    "UCWsDFclhY2DBi3GB5uykGXA",  # IShowSpeed
    "UCjiXtODGCCulmhwypZAWSag",  # Jynxzi
    "UCoEmptob-eEGKk18c2VpIJg",  # Kai Cenat
    "UCGRryxFxjXbVAtBPE9EbyMg",  # Joe Bartolozzi
    "UCKDBMEtklUsdH-xJlyrBG7A",  # Plaqueboy Max
],

# ── Telegram (alerts only) ───────────────────────────────
"TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
"TELEGRAM_CHAT_ID":   os.getenv("TELEGRAM_CHAT_ID", ""),

# ── YouTube OAuth ────────────────────────────────────────
"YOUTUBE_CLIENT_SECRETS": "client_secrets.json",
"YOUTUBE_TOKEN_FILE":     "youtube_token.json",

# ── TikTok ───────────────────────────────────────────────
"TIKTOK_ACCESS_TOKEN": os.getenv("TIKTOK_ACCESS_TOKEN", ""),

# ── Clip Settings ────────────────────────────────────────
"CLIP_MIN_SECONDS":  20,
"CLIP_MAX_SECONDS":  59,
"CLIPS_PER_VIDEO":   3,
"OUTPUT_WIDTH":      1080,
"OUTPUT_HEIGHT":     1920,

# ── Feature Flags ────────────────────────────────────────
"ENABLE_CAPTIONS":         True,
"ENABLE_BACKGROUND_MUSIC": True,
"ENABLE_ZOOM_EFFECTS":     True,
"ENABLE_COLOR_GRADING":    True,
"ENABLE_INTRO_OUTRO":      True,
"ADD_HOOK_TEXT":           True,

# ── Engagement ───────────────────────────────────────────
"FAST_CUT_THRESHOLD": 0.7,

# ── Directories ──────────────────────────────────────────
"DOWNLOAD_DIR": "downloads",
"CLIPS_DIR":    "clips",
"OUTPUT_DIR":   "output",
"MUSIC_DIR":    "assets/music",
"SFX_DIR":      "assets/sfx",
"BRANDING_DIR": "assets/branding",

# ── Misc ─────────────────────────────────────────────────
"LOG_FILE":           "posted_log.json",
"APP_LOG_FILE":       "app.log",
"AUTO_POST_TIKTOK":   os.getenv("AUTO_POST_TIKTOK",  "true").lower() == "true",
"AUTO_POST_YOUTUBE":  os.getenv("AUTO_POST_YOUTUBE", "true").lower() == "true",
"MAX_VIDEOS_PER_RUN": int(os.getenv("MAX_VIDEOS_PER_RUN", "2")),
```

}

# ═══════════════════════════════════════════════════════════════

# LOGGING

# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
level=logging.INFO,
format=”%(asctime)s [%(levelname)s] %(message)s”,
handlers=[
logging.FileHandler(CONFIG[“APP_LOG_FILE”]),
logging.StreamHandler(),
]
)
log = logging.getLogger(**name**)

# ═══════════════════════════════════════════════════════════════

# HELPERS

# ═══════════════════════════════════════════════════════════════

def setup_directories():
for d in [CONFIG[“DOWNLOAD_DIR”], CONFIG[“CLIPS_DIR”], CONFIG[“OUTPUT_DIR”],
CONFIG[“MUSIC_DIR”], CONFIG[“SFX_DIR”], CONFIG[“BRANDING_DIR”]]:
Path(d).mkdir(parents=True, exist_ok=True)
log.info(“Directories ready ✅”)

def load_log() -> list:
if not os.path.exists(CONFIG[“LOG_FILE”]):
return []
with open(CONFIG[“LOG_FILE”]) as f:
return json.load(f)

def save_log(data: list):
with open(CONFIG[“LOG_FILE”], “w”) as f:
json.dump(data, f, indent=2)

def telegram_alert(msg: str):
token, chat = CONFIG[“TELEGRAM_BOT_TOKEN”], CONFIG[“TELEGRAM_CHAT_ID”]
if not token or not chat:
return
try:
import requests as req
req.post(f”https://api.telegram.org/bot{token}/sendMessage”,
data={“chat_id”: chat, “text”: msg}, timeout=10)
except Exception as e:
log.warning(f”Telegram: {e}”)

def _ffmpeg(args: list, label: str) -> bool:
try:
subprocess.run([“ffmpeg”, “-y”] + args, check=True, capture_output=True)
return True
except subprocess.CalledProcessError as e:
log.warning(f”  ffmpeg [{label}]: {e.stderr.decode()[:250]}”)
return False
except FileNotFoundError:
log.error(”  ffmpeg not found! brew install ffmpeg  /  sudo apt install ffmpeg”)
return False

# ═══════════════════════════════════════════════════════════════

# AI CLIENT  (Claude / ChatGPT — switchable)

# ═══════════════════════════════════════════════════════════════

class AIClient:
def **init**(self):
self.provider = CONFIG[“AI_PROVIDER”].lower()
if self.provider == “claude”:
import anthropic as _a
self._c = _a.Anthropic(api_key=CONFIG[“ANTHROPIC_API_KEY”])
log.info(“AI: Claude (Anthropic) ✅”)
elif self.provider == “chatgpt”:
from openai import OpenAI as _O
self._c = _O(api_key=CONFIG[“OPENAI_API_KEY”])
log.info(“AI: ChatGPT (OpenAI) ✅”)
else:
raise ValueError(f”Unknown AI_PROVIDER ‘{self.provider}’. Use ‘claude’ or ‘chatgpt’.”)

```
def chat(self, system: str, user: str) -> str:
    if self.provider == "claude":
        r = self._c.messages.create(
            model="claude-opus-4-5", max_tokens=1500,
            system=system, messages=[{"role": "user", "content": user}]
        )
        return r.content[0].text.strip()
    else:
        r = self._c.chat.completions.create(
            model="gpt-4o", max_tokens=1500,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}]
        )
        return r.choices[0].message.content.strip()
```

# ═══════════════════════════════════════════════════════════════

# YOUTUBE  — Feed + Download

# ═══════════════════════════════════════════════════════════════

def get_latest_videos(channel_id: str) -> list:
import feedparser
try:
feed = feedparser.parse(f”https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}”)
return feed.entries
except Exception as e:
log.error(f”Feed error {channel_id}: {e}”)
return []

def download_video(url: str, out: str) -> bool:
from yt_dlp import YoutubeDL
opts = {
“format”:             “bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best”,
“outtmpl”:            out,
“noplaylist”:         True,
“quiet”:              False,
“nocheckcertificate”: True,
“ignoreerrors”:       True,
“extractor_args”:     {“youtube”: {“player_client”: [“android”]}},
}
try:
with YoutubeDL(opts) as ydl:
ydl.download([url])
return os.path.exists(out)
except Exception as e:
log.error(f”Download failed: {e}”)
return False

# ═══════════════════════════════════════════════════════════════

# TRANSCRIPTION

# ═══════════════════════════════════════════════════════════════

def transcribe_video(path: str) -> dict:
try:
import whisper
log.info(”  Transcribing with Whisper…”)
result = whisper.load_model(“base”).transcribe(path)
log.info(”  Transcription done ✅”)
return result
except ImportError:
log.warning(”  Whisper not available — skipping”)
return {“text”: “”, “segments”: []}
except Exception as e:
log.error(f”  Transcription error: {e}”)
return {“text”: “”, “segments”: []}

# ═══════════════════════════════════════════════════════════════

# AI CLIP ANALYSIS

# ═══════════════════════════════════════════════════════════════

def analyse_clips(ai: AIClient, transcript: dict, title: str) -> list:
if not transcript.get(“segments”):
return []
segs = “\n”.join(
f”[{s[‘start’]:.1f}s–{s[‘end’]:.1f}s]: {s[‘text’]}”
for s in transcript[“segments”]
)
system = textwrap.dedent(”””
You are a viral short-form video editor for TikTok and YouTube Shorts.
Find the most engaging highlight moments. Look for emotional peaks,
funny moments, shocking moments, high energy, shareable content.
Respond with valid JSON only — no markdown, no explanation.
“””)
user = textwrap.dedent(f”””
Video: {title}
Transcript:
{segs}

```
    Find the {CONFIG['CLIPS_PER_VIDEO']} best clips ({CONFIG['CLIP_MIN_SECONDS']}–{CONFIG['CLIP_MAX_SECONDS']}s each).
    Only include clips with engagement_score > {CONFIG['FAST_CUT_THRESHOLD']}.

    Return JSON array:
    [{{
        "start": 45.2, "end": 78.5,
        "reason": "Peak funny moment",
        "hook": "You won't believe this 😂",
        "engagement_score": 0.92,
        "caption_style": "bold_animated"
    }}]
""")
try:
    clips = json.loads(ai.chat(system, user))
    log.info(f"  AI found {len(clips)} clips ✅")
    return clips
except Exception as e:
    log.error(f"  AI analysis failed: {e}")
    return []
```

def fallback_split(path: str) -> list:
try:
r = subprocess.run(
[“ffprobe”, “-v”, “error”, “-show_entries”, “format=duration”,
“-of”, “default=noprint_wrappers=1:nokey=1”, path],
capture_output=True, text=True
)
dur = float(r.stdout.strip())
except Exception:
dur = 180.0
clip_len = min(CONFIG[“CLIP_MAX_SECONDS”], max(CONFIG[“CLIP_MIN_SECONDS”], dur / CONFIG[“CLIPS_PER_VIDEO”]))
return [
{“start”: i * clip_len, “end”: min((i+1)*clip_len, dur),
“reason”: “Auto segment”, “hook”: “Watch this 🔥”,
“engagement_score”: 0.75, “caption_style”: “bold_animated”}
for i in range(CONFIG[“CLIPS_PER_VIDEO”])
if min((i+1)*clip_len, dur) - i*clip_len >= CONFIG[“CLIP_MIN_SECONDS”]
]

# ═══════════════════════════════════════════════════════════════

# CAPTION GENERATION

# ═══════════════════════════════════════════════════════════════

def generate_captions(ai: AIClient, text: str, style: str = “bold_animated”) -> list:
system = “You are a TikTok caption writer. Max 5 words per line. Return valid JSON only.”
user   = textwrap.dedent(f”””
Style: {style}
Text: {text}
Break into 3–5 word chunks. Return:
[{{“text”: “CAPTION HERE”, “start_offset”: 0.0, “duration”: 1.5}}]
“””)
try:
return json.loads(ai.chat(system, user))
except Exception:
words  = text.split()
chunks = [” “.join(words[i:i+5]) for i in range(0, min(len(words), 25), 5)]
return [{“text”: c, “start_offset”: i*2.0, “duration”: 2.0} for i, c in enumerate(chunks)]

# ═══════════════════════════════════════════════════════════════

# VIDEO PROCESSING STEPS

# ═══════════════════════════════════════════════════════════════

def extract_clip(src: str, start: float, end: float, out: str) -> bool:
return _ffmpeg([”-ss”, str(start), “-i”, src, “-t”, str(end-start),
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “aac”, out], “extract”)

def convert_to_vertical(src: str, out: str) -> bool:
w, h = CONFIG[“OUTPUT_WIDTH”], CONFIG[“OUTPUT_HEIGHT”]
return _ffmpeg([
“-i”, src,
“-filter_complex”,
f”[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,”
f”crop={w}:{h},boxblur=20:20[bg];”
f”[0:v]scale={w}:-2[fg];”
f”[bg][fg]overlay=(W-w)/2:(H-h)/2[out]”,
“-map”, “[out]”, “-map”, “0:a?”,
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “aac”, “-shortest”, out
], “vertical”)

def apply_color_grade(src: str, out: str) -> bool:
if not CONFIG[“ENABLE_COLOR_GRADING”]: return False
return _ffmpeg([”-i”, src,
“-vf”, “eq=contrast=1.15:brightness=0.02:saturation=1.3,”
“colorchannelmixer=rr=1.05:gg=1.0:bb=0.95”,
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “copy”, out], “grade”)

def add_captions_ffmpeg(src: str, caps: list, out: str) -> bool:
if not CONFIG[“ENABLE_CAPTIONS”] or not caps: return False
filters = []
for c in caps:
txt = c[“text”].replace(”’”, “\’”).replace(”:”, “\:”).upper()
t0, t1 = c.get(“start_offset”, 0.0), c.get(“start_offset”, 0.0) + c.get(“duration”, 2.0)
filters.append(
f”drawtext=text=’{txt}’:fontsize=72:fontcolor=white:borderw=4:bordercolor=black”
f”:x=(w-text_w)/2:y=h*0.72:enable=‘between(t,{t0},{t1})’”
)
return _ffmpeg([”-i”, src, “-vf”, “,”.join(filters),
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “copy”, out], “captions”)

def add_background_music(src: str, out: str) -> bool:
if not CONFIG[“ENABLE_BACKGROUND_MUSIC”]: return False
files = list(Path(CONFIG[“MUSIC_DIR”]).glob(”*.mp3”)) + list(Path(CONFIG[“MUSIC_DIR”]).glob(”*.m4a”))
if not files:
log.warning(”  No music in assets/music/ — skipping”)
return False
music = str(random.choice(files))
return _ffmpeg([”-i”, src, “-stream_loop”, “-1”, “-i”, music,
“-filter_complex”, “[1:a]volume=0.15[m];[0:a][m]amix=inputs=2:duration=first[aout]”,
“-map”, “0:v”, “-map”, “[aout]”,
“-c:v”, “copy”, “-c:a”, “aac”, “-shortest”, out], “music”)

def add_zoom_effects(src: str, out: str) -> bool:
if not CONFIG[“ENABLE_ZOOM_EFFECTS”]: return False
return _ffmpeg([”-i”, src,
“-vf”, “zoompan=z=‘if(lte(mod(time,10),0.5),1.05,1)’:d=1”
“:x=‘iw/2-(iw/zoom/2)’:y=‘ih/2-(ih/zoom/2)’”,
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “copy”, out], “zoom”)

def add_hook_overlay(src: str, hook: str, out: str) -> bool:
if not CONFIG[“ADD_HOOK_TEXT”] or not hook: return False
txt = hook.upper().replace(”’”, “\’”).replace(”:”, “\:”)
return _ffmpeg([”-i”, src,
“-vf”, f”drawtext=text=’{txt}’:fontsize=80:fontcolor=yellow”
“:borderw=5:bordercolor=black:x=(w-text_w)/2:y=h*0.15”
“:enable=‘between(t,0,2.5)’”,
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “copy”, out], “hook”)

def add_intro_outro(src: str, out: str, channel: str = “ClipBot”) -> bool:
if not CONFIG[“ENABLE_INTRO_OUTRO”]: return False
intro = Path(CONFIG[“BRANDING_DIR”]) / “intro.mp4”
outro = Path(CONFIG[“BRANDING_DIR”]) / “outro.mp4”
if intro.exists() and outro.exists():
lst = Path(CONFIG[“CLIPS_DIR”]) / “concat.txt”
lst.write_text(f”file ‘{intro.absolute()}’\nfile ‘{Path(src).absolute()}’\nfile ‘{outro.absolute()}’\n”)
return _ffmpeg([”-f”, “concat”, “-safe”, “0”, “-i”, str(lst),
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “aac”, out], “concat”)
brand = channel.upper().replace(”’”, “\’”)
return _ffmpeg([”-i”, src,
“-vf”, f”drawtext=text=’{brand}’:fontsize=40:fontcolor=white:alpha=0.7:x=20:y=20”,
“-c:v”, “libx264”, “-preset”, “fast”, “-c:a”, “copy”, out], “brand”)

# ═══════════════════════════════════════════════════════════════

# FULL CLIP PIPELINE

# ═══════════════════════════════════════════════════════════════

def process_clip(ai: AIClient, source: str, clip: dict, idx: int, title: str):
import shutil
b   = f”clip_{idx}_{int(time.time())}”
cd  = Path(CONFIG[“CLIPS_DIR”])
od  = Path(CONFIG[“OUTPUT_DIR”])

```
raw       = str(cd / f"{b}_1_raw.mp4")
vertical  = str(cd / f"{b}_2_vert.mp4")
graded    = str(cd / f"{b}_3_grade.mp4")
captioned = str(cd / f"{b}_4_cap.mp4")
musiced   = str(cd / f"{b}_5_music.mp4")
zoomed    = str(cd / f"{b}_6_zoom.mp4")
hooked    = str(cd / f"{b}_7_hook.mp4")
final     = str(od / f"{b}_FINAL.mp4")

cur = source

log.info(f"  [1/7] Extract  {clip['start']:.1f}s–{clip['end']:.1f}s")
if not extract_clip(cur, clip["start"], clip["end"], raw): return None
cur = raw

log.info("  [2/7] 9:16 vertical")
if convert_to_vertical(cur, vertical): cur = vertical

log.info("  [3/7] Color grade")
if apply_color_grade(cur, graded): cur = graded

log.info("  [4/7] AI captions")
caps = generate_captions(ai, clip.get("reason", title), clip.get("caption_style", "bold_animated"))
if add_captions_ffmpeg(cur, caps, captioned): cur = captioned

log.info("  [5/7] Background music")
if add_background_music(cur, musiced): cur = musiced

log.info("  [6/7] Zoom effects")
if add_zoom_effects(cur, zoomed): cur = zoomed

log.info("  [7/7] Hook + branding")
if add_hook_overlay(cur, clip.get("hook", "Watch this 🔥"), hooked): cur = hooked
if add_intro_outro(cur, final): cur = final

if cur != final:
    shutil.copy2(cur, final)

log.info(f"  ✅ {final}")
return final
```

# ═══════════════════════════════════════════════════════════════

# AI CONTENT REVIEW

# ═══════════════════════════════════════════════════════════════

def review_clip(ai: AIClient, clip: dict, title: str) -> dict:
system = textwrap.dedent(”””
You are a TikTok/YouTube content moderation and monetisation expert.
Review clips for safety, TOS compliance, and advertiser-friendliness.
Return valid JSON only.
“””)
user = textwrap.dedent(f”””
Source: {title}
Clip reason: {clip.get(‘reason’, ‘N/A’)}
Engagement: {clip.get(‘engagement_score’, 0)}

```
    Return JSON:
    {{
        "approved": true,
        "monetisation_safe": true,
        "issues": [],
        "tiktok_title": "Title under 100 chars",
        "youtube_title": "YouTube Shorts title",
        "description": "Short keyword description",
        "hashtags": ["#viral", "#fyp", "#shorts"],
        "tiktok_hashtags": "#viral #fyp #reaction"
    }}
""")
try:
    return json.loads(ai.chat(system, user))
except Exception as e:
    log.error(f"  AI review failed: {e}")
    return {
        "approved": True, "monetisation_safe": True, "issues": [],
        "tiktok_title": title[:100], "youtube_title": title[:100],
        "description": "Viral clip 🔥 #shorts",
        "hashtags": ["#viral", "#fyp", "#shorts"],
        "tiktok_hashtags": "#viral #fyp #shorts",
    }
```

# ═══════════════════════════════════════════════════════════════

# TIKTOK UPLOAD

# ═══════════════════════════════════════════════════════════════

def post_to_tiktok(path: str, title: str, hashtags: str) -> bool:
if not CONFIG[“AUTO_POST_TIKTOK”]: return False
token = CONFIG[“TIKTOK_ACCESS_TOKEN”]
if not token:
log.warning(”  TikTok token not set — skipping”)
return False
try:
import requests as req
size = os.path.getsize(path)
hdrs = {“Authorization”: f”Bearer {token}”, “Content-Type”: “application/json; charset=UTF-8”}
init = req.post(
“https://open.tiktokapis.com/v2/post/publish/video/init/”, headers=hdrs,
json={“post_info”: {“title”: f”{title} {hashtags}”[:2200],
“privacy_level”: “PUBLIC_TO_EVERYONE”,
“disable_duet”: False, “disable_comment”: False, “disable_stitch”: False},
“source_info”: {“source”: “FILE_UPLOAD”, “video_size”: size, “chunk_size”: size, “total_chunk_count”: 1}},
timeout=30
).json()
if “data” not in init:
log.error(f”  TikTok init failed: {init}”)
return False
pub_id     = init[“data”][“publish_id”]
upload_url = init[“data”][“upload_url”]
with open(path, “rb”) as f:
data = f.read()
up = req.put(upload_url,
headers={“Content-Range”: f”bytes 0-{size-1}/{size}”,
“Content-Length”: str(size), “Content-Type”: “video/mp4”},
data=data, timeout=300)
if up.status_code not in (200, 201, 204):
log.error(f”  TikTok upload failed: {up.text}”)
return False
log.info(f”  TikTok ✅  publish_id={pub_id}”)
return True
except Exception as e:
log.error(f”  TikTok error: {e}”)
return False

# ═══════════════════════════════════════════════════════════════

# YOUTUBE SHORTS UPLOAD

# ═══════════════════════════════════════════════════════════════

def post_to_youtube(path: str, title: str, description: str, tags: list) -> bool:
if not CONFIG[“AUTO_POST_YOUTUBE”]: return False
try:
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

```
    SCOPES  = ["https://www.googleapis.com/auth/youtube.upload"]
    tf, sf  = CONFIG["YOUTUBE_TOKEN_FILE"], CONFIG["YOUTUBE_CLIENT_SECRETS"]
    creds   = None

    if os.path.exists(tf):
        with open(tf, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(sf):
                log.warning("  client_secrets.json missing — skipping YouTube")
                return False
            creds = InstalledAppFlow.from_client_secrets_file(sf, SCOPES).run_local_server(port=0)
        with open(tf, "wb") as f:
            pickle.dump(creds, f)

    yt   = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": f"{title} #shorts"[:100],
                    "description": f"{description}\n\n#shorts",
                    "tags": tags + ["shorts", "viral"], "categoryId": "22"},
        "status":  {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    req  = yt.videos().insert(part=",".join(body.keys()), body=body,
                               media_body=MediaFileUpload(path, mimetype="video/mp4", resumable=True))
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st: log.info(f"  YouTube: {int(st.progress()*100)}%")
    log.info(f"  YouTube ✅  id={resp['id']}")
    return True
except ImportError:
    log.warning("  YouTube API libs not installed — skipping")
    return False
except Exception as e:
    log.error(f"  YouTube error: {e}")
    return False
```

# ═══════════════════════════════════════════════════════════════

# MAIN PIPELINE

# ═══════════════════════════════════════════════════════════════

def main():
log.info(“═”*55)
log.info(”  🎬 AI Clip Generator”)
log.info(f”  Provider : {CONFIG[‘AI_PROVIDER’].upper()}”)
log.info(f”  Channels : {len(CONFIG[‘YOUTUBE_CHANNEL_IDS’])}”)
log.info(“═”*55)

```
setup_directories()
posted = load_log()
telegram_alert("🤖 AI Clip Generator started")

try:
    ai = AIClient()
except Exception as e:
    log.critical(f"AI init failed: {e}")
    telegram_alert(f"❌ AI init failed: {e}")
    return

processed = 0

for channel_id in CONFIG["YOUTUBE_CHANNEL_IDS"]:
    if processed >= CONFIG["MAX_VIDEOS_PER_RUN"]:
        break
    log.info(f"\n📺 Channel: {channel_id}")
    for video in get_latest_videos(channel_id):
        if processed >= CONFIG["MAX_VIDEOS_PER_RUN"]:
            break
        if video.link in posted:
            log.info(f"  Skip (done): {video.title[:60]}")
            continue

        log.info(f"\n▶  {video.title}")
        telegram_alert(f"🎬 Processing: {video.title}")

        ts  = int(time.time())
        src = str(Path(CONFIG["DOWNLOAD_DIR"]) / f"source_{ts}.mp4")
        log.info("  Downloading...")
        if not download_video(video.link, src):
            log.error("  Download failed — skipping")
            continue

        transcript = transcribe_video(src)
        clips      = analyse_clips(ai, transcript, video.title) or fallback_split(src)
        log.info(f"  {len(clips)} clips to process")

        for i, clip in enumerate(clips):
            log.info(f"\n  ── Clip {i+1}/{len(clips)} ──")
            review = review_clip(ai, clip, video.title)
            if not review.get("approved") or not review.get("monetisation_safe"):
                log.warning(f"  ⛔ Rejected: {review.get('issues')}")
                continue

            final = process_clip(ai, src, clip, i, video.title)
            if not final:
                log.error("  Processing failed — skipping")
                continue

            tt = post_to_tiktok(final, review["tiktok_title"], review["tiktok_hashtags"])
            yt = post_to_youtube(final, review["youtube_title"], review["description"],
                                 [h.lstrip("#") for h in review.get("hashtags", [])])

            status = f"{'✅ TikTok' if tt else '⏭ TikTok'} | {'✅ YouTube' if yt else '⏭ YouTube'}"
            log.info(f"  {status}")
            telegram_alert(f"✅ Clip {i+1} posted!\n📹 {video.title[:50]}\n🪝 {clip.get('hook','')}\n{status}")

        posted.append(video.link)
        save_log(posted)
        processed += 1
        time.sleep(3)

log.info("\n" + "═"*55)
log.info(f"  ✅ Done. Processed {processed} video(s).")
log.info("═"*55)
telegram_alert(f"🏁 Done. Processed {processed} video(s).")
```

# ═══════════════════════════════════════════════════════════════

# ENTRY POINT

# ═══════════════════════════════════════════════════════════════

if **name** == “**main**”:
parser = argparse.ArgumentParser(description=“AI Clip Generator”)
parser.add_argument(”–setup”,   action=“store_true”, help=“First-time setup: create .env, folders, README”)
parser.add_argument(”–install”, action=“store_true”, help=“Install Python dependencies only”)
args = parser.parse_args()

```
if args.setup:
    install_dependencies()
    run_setup()
elif args.install:
    install_dependencies()
else:
    install_dependencies()
    main()
```
