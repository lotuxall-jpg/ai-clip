import os
import sys
import json
import time
import random
import logging
import argparse
import subprocess
from pathlib import Path

REQUIRED_PACKAGES = {
    "anthropic": "anthropic",
    "openai": "openai",
    "yt_dlp": "yt-dlp",
    "feedparser": "feedparser",
    "requests": "requests",
    "whisper": "openai-whisper",
    "dotenv": "python-dotenv",
    "googleapiclient": "google-api-python-client",
    "google_auth_oauthlib": "google-auth-oauthlib",
}

def install_dependencies():
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name.split(".")[0])
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", pip_name, "-q"], check=True)

def load_env():
    env_path = Path(".env")
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

CONFIG = {
    "AI_PROVIDER": os.getenv("AI_PROVIDER", "claude"),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "YOUTUBE_CHANNEL_IDS": [
        "UCWsDFclhY2DBi3GB5uykGXA",
        "UCjiXtODGCCulmhwypZAWSag",
        "UCoEmptob-eEGKk18c2VpIJg",
        "UCGRryxFxjXbVAtBPE9EbyMg",
        "UCKDBMEtklUsdH-xJlyrBG7A",
    ],
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
    "YOUTUBE_CLIENT_SECRETS": "client_secrets.json",
    "YOUTUBE_TOKEN_FILE": "youtube_token.json",
    "TIKTOK_ACCESS_TOKEN": os.getenv("TIKTOK_ACCESS_TOKEN", ""),
    "CLIP_MIN_SECONDS": 20,
    "CLIP_MAX_SECONDS": 59,
    "CLIPS_PER_VIDEO": 3,
    "OUTPUT_WIDTH": 1080,
    "OUTPUT_HEIGHT": 1920,
    "ENABLE_CAPTIONS": True,
    "ENABLE_BACKGROUND_MUSIC": True,
    "ENABLE_ZOOM_EFFECTS": True,
    "ENABLE_COLOR_GRADING": True,
    "ENABLE_INTRO_OUTRO": True,
    "ADD_HOOK_TEXT": True,
    "FAST_CUT_THRESHOLD": 0.7,
    "DOWNLOAD_DIR": "downloads",
    "CLIPS_DIR": "clips",
    "OUTPUT_DIR": "output",
    "MUSIC_DIR": "assets/music",
    "SFX_DIR": "assets/sfx",
    "BRANDING_DIR": "assets/branding",
    "LOG_FILE": "posted_log.json",
    "APP_LOG_FILE": "app.log",
    "AUTO_POST_TIKTOK": os.getenv("AUTO_POST_TIKTOK", "false").lower() == "true",
    "AUTO_POST_YOUTUBE": os.getenv("AUTO_POST_YOUTUBE", "false").lower() == "true",
    "MAX_VIDEOS_PER_RUN": int(os.getenv("MAX_VIDEOS_PER_RUN", "1")),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["APP_LOG_FILE"]),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

def setup_directories():
    for d in [CONFIG["DOWNLOAD_DIR"], CONFIG["CLIPS_DIR"], CONFIG["OUTPUT_DIR"],
              CONFIG["MUSIC_DIR"], CONFIG["SFX_DIR"], CONFIG["BRANDING_DIR"]]:
        Path(d).mkdir(parents=True, exist_ok=True)

def load_log():
    if not os.path.exists(CONFIG["LOG_FILE"]):
        return []
    with open(CONFIG["LOG_FILE"]) as f:
        return json.load(f)

def save_log(data):
    with open(CONFIG["LOG_FILE"], "w") as f:
        json.dump(data, f, indent=2)

def telegram_alert(msg):
    token = CONFIG["TELEGRAM_BOT_TOKEN"]
    chat = CONFIG["TELEGRAM_CHAT_ID"]
    if not token or not chat:
        return
    try:
        import requests as req
        req.post("https://api.telegram.org/bot" + token + "/sendMessage",
                 data={"chat_id": chat, "text": msg}, timeout=10)
    except Exception as e:
        log.warning("Telegram: " + str(e))

def run_ffmpeg(args, label):
    try:
        subprocess.run(["ffmpeg", "-y"] + args, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        log.warning("ffmpeg [" + label + "]: " + e.stderr.decode()[:250])
        return False
    except FileNotFoundError:
        log.error("ffmpeg not found!")
        return False

class AIClient:
    def __init__(self):
        self.provider = CONFIG["AI_PROVIDER"].lower()
        if self.provider == "claude":
            import anthropic as _a
            self._c = _a.Anthropic(api_key=CONFIG["ANTHROPIC_API_KEY"])
            log.info("AI: Claude ready")
        elif self.provider == "chatgpt":
            from openai import OpenAI as _O
            self._c = _O(api_key=CONFIG["OPENAI_API_KEY"])
            log.info("AI: ChatGPT ready")
        else:
            raise ValueError("Unknown AI_PROVIDER. Use claude or chatgpt.")

    def chat(self, system, user):
        if self.provider == "claude":
            r = self._c.messages.create(
                model="claude-opus-4-5",
                max_tokens=1500,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            return r.content[0].text.strip()
        else:
            r = self._c.chat.completions.create(
                model="gpt-4o",
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ]
            )
            return r.choices[0].message.content.strip()

def get_latest_videos(channel_id):
    import feedparser
    try:
        feed = feedparser.parse("https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id)
        return feed.entries
    except Exception as e:
        log.error("Feed error: " + str(e))
        return []

def download_video(url, out):
    from yt_dlp import YoutubeDL
    strategies = [
        {
            "format": "best[ext=mp4]/best",
            "outtmpl": out,
            "noplaylist": True,
            "quiet": False,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "extractor_args": {"youtube": {"player_client": ["ios"]}},
            "http_headers": {"User-Agent": "com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 16_3_1 like Mac OS X)"},
        },
        {
            "format": "best[ext=mp4]/best",
            "outtmpl": out,
            "noplaylist": True,
            "quiet": False,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        },
        {
            "format": "best[ext=mp4]/best",
            "outtmpl": out,
            "noplaylist": True,
            "quiet": False,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "extractor_args": {"youtube": {"player_client": ["tv_embedded"]}},
        },
    ]
    for i, opts in enumerate(strategies):
        log.info("Download attempt " + str(i + 1))
        try:
            if i > 0:
                time.sleep(random.uniform(2, 5))
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            if os.path.exists(out):
                log.info("Download success!")
                return True
        except Exception as e:
            log.warning("Attempt " + str(i + 1) + " failed: " + str(e))
    return False

def transcribe_video(path):
    try:
        import whisper
        log.info("Transcribing...")
        result = whisper.load_model("base").transcribe(path)
        return result
    except Exception as e:
        log.error("Transcription error: " + str(e))
        return {"text": "", "segments": []}

def analyse_clips(ai, transcript, title):
    if not transcript.get("segments"):
        return []
    segs = "\n".join(
        "[" + str(round(s["start"],1)) + "s-" + str(round(s["end"],1)) + "s]: " + s["text"]
        for s in transcript["segments"]
    )
    system = "You are a viral short-form video editor. Find the best highlight moments. Return valid JSON only."
    user = (
        "Video: " + title + "\n"
        "Transcript:\n" + segs + "\n\n"
        "Find the " + str(CONFIG["CLIPS_PER_VIDEO"]) + " best clips "
        "(" + str(CONFIG["CLIP_MIN_SECONDS"]) + "-" + str(CONFIG["CLIP_MAX_SECONDS"]) + "s each).\n"
        "Return JSON array: [{\"start\": 45.2, \"end\": 78.5, \"reason\": \"funny moment\", "
        "\"hook\": \"Watch this\", \"engagement_score\": 0.92, \"caption_style\": \"bold_animated\"}]"
    )
    try:
        clips = json.loads(ai.chat(system, user))
        log.info("AI found " + str(len(clips)) + " clips")
        return clips
    except Exception as e:
        log.error("AI analysis failed: " + str(e))
        return []

def fallback_split(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True
        )
        dur = float(r.stdout.strip())
    except Exception:
        dur = 180.0
    clip_len = min(CONFIG["CLIP_MAX_SECONDS"], max(CONFIG["CLIP_MIN_SECONDS"], dur / CONFIG["CLIPS_PER_VIDEO"]))
    return [
        {"start": i * clip_len, "end": min((i+1)*clip_len, dur),
         "reason": "Auto segment", "hook": "Watch this",
         "engagement_score": 0.75, "caption_style": "bold_animated"}
        for i in range(CONFIG["CLIPS_PER_VIDEO"])
        if min((i+1)*clip_len, dur) - i*clip_len >= CONFIG["CLIP_MIN_SECONDS"]
    ]

def generate_captions(ai, text, style):
    system = "You are a TikTok caption writer. Max 5 words per line. Return valid JSON only."
    user = "Style: " + style + "\nText: " + text + "\nReturn: [{\"text\": \"CAPTION\", \"start_offset\": 0.0, \"duration\": 1.5}]"
    try:
        return json.loads(ai.chat(system, user))
    except Exception:
        words = text.split()
        chunks = [" ".join(words[i:i+5]) for i in range(0, min(len(words), 25), 5)]
        return [{"text": c, "start_offset": i*2.0, "duration": 2.0} for i, c in enumerate(chunks)]

def extract_clip(src, start, end, out):
    return run_ffmpeg(["-ss", str(start), "-i", src, "-t", str(end-start),
                       "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", out], "extract")

def convert_to_vertical(src, out):
    w = str(CONFIG["OUTPUT_WIDTH"])
    h = str(CONFIG["OUTPUT_HEIGHT"])
    return run_ffmpeg([
        "-i", src,
        "-filter_complex",
        "[0:v]scale=" + w + ":" + h + ":force_original_aspect_ratio=increase,crop=" + w + ":" + h + ",boxblur=20:20[bg];[0:v]scale=" + w + ":-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[out]",
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-shortest", out
    ], "vertical")

def apply_color_grade(src, out):
    if not CONFIG["ENABLE_COLOR_GRADING"]:
        return False
    return run_ffmpeg(["-i", src,
                       "-vf", "eq=contrast=1.15:brightness=0.02:saturation=1.3,colorchannelmixer=rr=1.05:gg=1.0:bb=0.95",
                       "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", out], "grade")

def add_captions_ffmpeg(src, caps, out):
    if not CONFIG["ENABLE_CAPTIONS"] or not caps:
        return False
    filters = []
    for c in caps:
        txt = c["text"].replace("'", "\\'").replace(":", "\\:").upper()
        t0 = c.get("start_offset", 0.0)
        t1 = t0 + c.get("duration", 2.0)
        filters.append(
            "drawtext=text='" + txt + "':fontsize=72:fontcolor=white:borderw=4:bordercolor=black"
            ":x=(w-text_w)/2:y=h*0.72:enable='between(t," + str(t0) + "," + str(t1) + ")'"
        )
    return run_ffmpeg(["-i", src, "-vf", ",".join(filters),
                       "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", out], "captions")

def add_background_music(src, out):
    if not CONFIG["ENABLE_BACKGROUND_MUSIC"]:
        return False
    files = list(Path(CONFIG["MUSIC_DIR"]).glob("*.mp3")) + list(Path(CONFIG["MUSIC_DIR"]).glob("*.m4a"))
    if not files:
        return False
    music = str(random.choice(files))
    return run_ffmpeg(["-i", src, "-stream_loop", "-1", "-i", music,
                       "-filter_complex", "[1:a]volume=0.15[m];[0:a][m]amix=inputs=2:duration=first[aout]",
                       "-map", "0:v", "-map", "[aout]",
                       "-c:v", "copy", "-c:a", "aac", "-shortest", out], "music")

def add_zoom_effects(src, out):
    if not CONFIG["ENABLE_ZOOM_EFFECTS"]:
        return False
    return run_ffmpeg(["-i", src,
                       "-vf", "zoompan=z='if(lte(mod(time,10),0.5),1.05,1)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
                       "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", out], "zoom")

def add_hook_overlay(src, hook, out):
    if not CONFIG["ADD_HOOK_TEXT"] or not hook:
        return False
    txt = hook.upper().replace("'", "\\'").replace(":", "\\:")
    return run_ffmpeg(["-i", src,
                       "-vf", "drawtext=text='" + txt + "':fontsize=80:fontcolor=yellow:borderw=5:bordercolor=black:x=(w-text_w)/2:y=h*0.15:enable='between(t,0,2.5)'",
                       "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", out], "hook")

def add_intro_outro(src, out, channel="ViralClipsHQ"):
    if not CONFIG["ENABLE_INTRO_OUTRO"]:
        return False
    brand = channel.upper().replace("'", "\\'")
    return run_ffmpeg(["-i", src,
                       "-vf", "drawtext=text='" + brand + "':fontsize=40:fontcolor=white:alpha=0.7:x=20:y=20",
                       "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", out], "brand")

def process_clip(ai, source, clip, idx, title):
    import shutil
    b = "clip_" + str(idx) + "_" + str(int(time.time()))
    cd = Path(CONFIG["CLIPS_DIR"])
    od = Path(CONFIG["OUTPUT_DIR"])
    raw = str(cd / (b + "_1_raw.mp4"))
    vertical = str(cd / (b + "_2_vert.mp4"))
    graded = str(cd / (b + "_3_grade.mp4"))
    captioned = str(cd / (b + "_4_cap.mp4"))
    zoomed = str(cd / (b + "_6_zoom.mp4"))
    hooked = str(cd / (b + "_7_hook.mp4"))
    final = str(od / (b + "_FINAL.mp4"))
    cur = source
    log.info("Extracting " + str(clip["start"]) + "s-" + str(clip["end"]) + "s")
    if not extract_clip(cur, clip["start"], clip["end"], raw):
        return None
    cur = raw
    if convert_to_vertical(cur, vertical):
        cur = vertical
    if apply_color_grade(cur, graded):
        cur = graded
    caps = generate_captions(ai, clip.get("reason", title), clip.get("caption_style", "bold_animated"))
    if add_captions_ffmpeg(cur, captioned, captioned):
        cur = captioned
    if add_zoom_effects(cur, zoomed):
        cur = zoomed
    if add_hook_overlay(cur, clip.get("hook", "Watch this"), hooked):
        cur = hooked
    if add_intro_outro(cur, final):
        cur = final
    if cur != final:
        shutil.copy2(cur, final)
    log.info("Clip ready: " + final)
    return final

def review_clip(ai, clip, title):
    system = "You are a TikTok/YouTube content moderation expert. Return valid JSON only."
    user = (
        "Source: " + title + "\n"
        "Reason: " + clip.get("reason", "N/A") + "\n"
        "Return JSON: {\"approved\": true, \"monetisation_safe\": true, \"issues\": [], "
        "\"tiktok_title\": \"title\", \"youtube_title\": \"title\", "
        "\"description\": \"desc\", \"hashtags\": [\"#viral\"], \"tiktok_hashtags\": \"#viral #fyp\"}"
    )
    try:
        return json.loads(ai.chat(system, user))
    except Exception:
        return {
            "approved": True, "monetisation_safe": True, "issues": [],
            "tiktok_title": title[:100], "youtube_title": title[:100],
            "description": "Viral clip #shorts",
            "hashtags": ["#viral", "#fyp", "#shorts"],
            "tiktok_hashtags": "#viral #fyp #shorts",
        }

def main():
    log.info("ViralClipsHQ Bot starting...")
    log.info("Provider: " + CONFIG["AI_PROVIDER"].upper())
    log.info("API Key set: " + str(bool(CONFIG["ANTHROPIC_API_KEY"])))
    setup_directories()
    posted = load_log()
    telegram_alert("ViralClipsHQ Bot started")
    try:
        ai = AIClient()
    except Exception as e:
        log.critical("AI init failed: " + str(e))
        return
    processed = 0
    for channel_id in CONFIG["YOUTUBE_CHANNEL_IDS"]:
        if processed >= CONFIG["MAX_VIDEOS_PER_RUN"]:
            break
        log.info("Channel: " + channel_id)
        for video in get_latest_videos(channel_id):
            if processed >= CONFIG["MAX_VIDEOS_PER_RUN"]:
                break
            if video.link in posted:
                log.info("Already processed: " + video.title[:50])
                continue
            log.info("Processing: " + video.title)
            ts = int(time.time())
            src = str(Path(CONFIG["DOWNLOAD_DIR"]) / ("source_" + str(ts) + ".mp4"))
            if not download_video(video.link, src):
                log.error("Download failed - skipping")
                continue
            transcript = transcribe_video(src)
            clips = analyse_clips(ai, transcript, video.title) or fallback_split(src)
            for i, clip in enumerate(clips):
                review = review_clip(ai, clip, video.title)
                if not review.get("approved"):
                    continue
                final = process_clip(ai, src, clip, i, video.title)
                if not final:
                    continue
                log.info("Clip ready: " + str(final))
            posted.append(video.link)
            save_log(posted)
            processed += 1
            time.sleep(random.uniform(3, 7))
    log.info("Done. Processed " + str(processed) + " videos.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true")
    args = parser.parse_args()
    install_dependencies()
    main()
