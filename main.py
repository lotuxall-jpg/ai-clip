import os
import json
import glob
import subprocess
import asyncio
import feedparser
import requests
import whisper

# ── CONFIG ──────────────────────────────────────────────────
LOG_FILE      = "posted_log.json"
CHANNEL_IDS   = os.environ.get("YOUTUBE_CHANNEL_IDS", "").split(",")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
CLIP_LENGTH   = 55
MAX_CLIPS     = 4
WHISPER_MODEL = "base"

VOICE_NAME     = "en-US-GuyNeural"
VOICE_RATE     = "+10%"
VOICE_MIX_MODE = "replace"

STYLE = {
    "font": "Impact", "font_size": 58,
    "primary": "&H00FFFFFF", "highlight": "&H0000FFFF",
    "outline": "&H00000000", "back": "&HA0000000",
    "outline_size": 3, "shadow": 2, "bold": -1,
    "margin_v": 120, "words_per_line": 3,
}

HOOKS = [
    "WAIT FOR IT...", "YOU NEED TO SEE THIS",
    "NOBODY TALKS ABOUT THIS", "THIS CHANGES EVERYTHING",
    "PAY ATTENTION TO THIS", "WATCH TILL THE END",
    "THIS IS INSANE", "I CAN'T BELIEVE THIS",
]

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return json.load(f)
    return []


def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f)


def clean_files():
    for f in (glob.glob("clip_*.mp4") + glob.glob("source.*")
              + glob.glob("*.ass") + glob.glob("vo_*.mp3")):
        try:
            os.remove(f)
        except Exception:
            pass


# ── GET NEW VIDEOS FROM RSS ──────────────────────────────────
def get_new_videos(channel_id, posted):
    url  = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id.strip()}"
    logger.info(f"Channel: {channel_id.strip()}")
    try:
        feed = feedparser.parse(url)
        new  = [e.link for e in feed.entries if e.link not in posted]
        return new[:2]  # get up to 2 new videos per channel
    except Exception as e:
        logger.error(f"RSS error: {e}")
        return []


# ── DOWNLOAD VIDEO (no cookies needed) ───────────────────────
def download_video(url):
    logger.info(f"Processing: {url.split('v=')[-1] if 'v=' in url else url}")

    # Method 1: Use Android client (no sign-in needed)
    opts_android = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android",
        "--format", "best[ext=mp4][height<=480]/best[ext=mp4]/best",
        "--output", "source.%(ext)s",
        "--no-playlist",
        "--socket-timeout", "30",
        "--retries", "3",
        "--quiet",
        url
    ]

    result = subprocess.run(opts_android, capture_output=True, text=True)

    if result.returncode == 0:
        files = glob.glob("source.*")
        if files:
            size = os.path.getsize(files[0]) / (1024*1024)
            logger.info(f"Downloaded: {files[0]} ({size:.1f}MB)")
            return files[0]

    # Method 2: Try iOS client
    logger.info("Trying iOS client...")
    opts_ios = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=ios",
        "--format", "best[ext=mp4][height<=480]/best",
        "--output", "source.%(ext)s",
        "--no-playlist",
        "--socket-timeout", "30",
        "--quiet",
        url
    ]

    result2 = subprocess.run(opts_ios, capture_output=True, text=True)

    if result2.returncode == 0:
        files = glob.glob("source.*")
        if files:
            return files[0]

    # Method 3: Try web client with different user agent
    logger.info("Trying web client...")
    opts_web = [
        "yt-dlp",
        "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "--format", "best[height<=480]/best",
        "--output", "source.%(ext)s",
        "--no-playlist",
        "--socket-timeout", "30",
        "--quiet",
        url
    ]

    result3 = subprocess.run(opts_web, capture_output=True, text=True)

    if result3.returncode == 0:
        files = glob.glob("source.*")
        if files:
            return files[0]

    logger.error(f"All download methods failed for {url}")
    logger.error(result.stderr[-300:] if result.stderr else "No error output")
    return None


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0


# ── TRANSCRIBE ───────────────────────────────────────────────
def transcribe(path):
    logger.info("Transcribing with Whisper...")
    model  = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(path, fp16=False, word_timestamps=True)
    segs   = result.get("segments", [])
    logger.info(f"Got {len(segs)} segments")
    return segs


# ── FIND CLIPS ───────────────────────────────────────────────
def find_clips(segs, dur):
    if not segs:
        clips, t = [], 10
        while t + CLIP_LENGTH < dur - 10 and len(clips) < MAX_CLIPS:
            clips.append({"start": t, "end": t + CLIP_LENGTH})
            t += CLIP_LENGTH + 5
        return clips
    windows, i = [], 0
    while i < len(segs):
        s = segs[i]["start"]
        e, w, j = s, 0, i
        while j < len(segs) and segs[j]["end"] - s <= CLIP_LENGTH:
            e = segs[j]["end"]
            w += len(segs[j]["text"].split())
            j += 1
        if e > s:
            windows.append({"start": s, "end": e, "score": w / (e - s)})
        i = max(j, i + 1)
    top = sorted(windows, key=lambda x: -x["score"])[:MAX_CLIPS]
    return sorted(top, key=lambda x: x["start"])


# ── ASS SUBTITLES ────────────────────────────────────────────
def ts(sec):
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(segs, cs, ce, path):
    S   = STYLE
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{S['font']},{S['font_size']},{S['primary']},{S['highlight']},{S['outline']},{S['back']},{S['bold']},0,0,0,100,100,0,0,3,{S['outline_size']},{S['shadow']},2,30,30,{S['margin_v']},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    evts = []
    for seg in segs:
        if seg["end"] <= cs or seg["start"] >= ce:
            continue
        words = []
        for w in seg.get("words", []):
            ws = max(w["start"], cs) - cs
            we = min(w["end"],   ce) - cs
            if we > ws:
                words.append({"word": w["word"].strip(), "start": ws, "end": we})
        if not words:
            txt  = seg["text"].strip().split()
            d    = max(seg["end"] - seg["start"], .1) / max(len(txt), 1)
            base = max(seg["start"] - cs, 0)
            for idx, ww in enumerate(txt):
                words.append({"word": ww, "start": base + idx*d, "end": base + (idx+1)*d})
        n = S["words_per_line"]
        for ci in range(0, len(words), n):
            chunk = words[ci:ci+n]
            if not chunk:
                continue
            ls = chunk[0]["start"]
            le = chunk[-1]["end"]
            parts = [f"{{\\k{max(int(round((ww['end']-ww['start'])*100)),1)}}}{ww['word']}"
                     for ww in chunk]
            evts.append(f"Dialogue: 0,{ts(ls)},{ts(le)},Default,,0,0,0,,{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(hdr + "\n".join(evts))
    return path


# ── HOOK TEXT ────────────────────────────────────────────────
def get_hook(text, i):
    if not GEMINI_KEY:
        return HOOKS[i % len(HOOKS)]
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text":
                f'Transcript: "{text[:300]}"\n'
                f'Write ONE punchy hook 4-6 words MAX in ALL CAPS for a TikTok. '
                f'No hashtags. No quotes. Reply with ONLY the hook text.'}]}]},
            timeout=20)
        h = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
        h = h.replace('"', '').replace("'", '').strip()
        return h if len(h) <= 40 else HOOKS[i % len(HOOKS)]
    except Exception:
        return HOOKS[i % len(HOOKS)]


# ── VOICEOVER ────────────────────────────────────────────────
async def _tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text, VOICE_NAME, rate=VOICE_RATE).save(path)


def gen_vo(text, path):
    if not text.strip():
        return None
    try:
        asyncio.run(_tts(text.strip(), path))
        return path if os.path.exists(path) and os.path.getsize(path) > 0 else None
    except Exception as e:
        logger.warning(f"Voiceover failed: {e}")
        return None


# ── RENDER CLIP ──────────────────────────────────────────────
def render(src, start, end, idx, segs, hook, vo):
    out = f"clip_{idx:02d}.mp4"
    ass = f"sub_{idx:02d}.ass"
    raw = f"raw_{idx:02d}.mp4"
    build_ass(segs, start, end, ass)
    he  = hook.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
    vf  = (
        f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920:flags=lanczos,ass={ass},"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{he}':fontsize=62:fontcolor=white:bordercolor=black:borderw=4:"
        f"shadowcolor=black@0.8:shadowx=3:shadowy=3:x=(w-text_w)/2:y=80:"
        f"box=1:boxcolor=black@0.45:boxborderw=18"
    )
    if vo and os.path.exists(vo) and VOICE_MIX_MODE == "replace":
        r1 = subprocess.run(
            ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
             "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "22", raw],
            capture_output=True)
        if r1.returncode == 0:
            r2 = subprocess.run(
                ["ffmpeg", "-y", "-i", raw, "-i", vo,
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-shortest", "-movflags", "+faststart", out],
                capture_output=True)
            for f in [raw, ass]:
                try: os.remove(f)
                except: pass
            if r2.returncode == 0:
                logger.info(f"✓ {out} (with voiceover)")
                return out
    r = subprocess.run(
        ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
         "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "22",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out],
        capture_output=True)
    try: os.remove(ass)
    except: pass
    if r.returncode == 0:
        logger.info(f"✓ {out}")
        return out
    logger.error(f"Render failed for {out}")
    return None


# ── POST TO TIKTOK ───────────────────────────────────────────
def post_tiktok(clip, caption):
    session_id = os.environ.get("TIKTOK_SESSION_ID", "")
    if not session_id:
        logger.info("No TikTok session ID — skipping")
        return False
    size = os.path.getsize(clip)
    hdrs = {
        "Cookie": f"sessionid={session_id}",
        "User-Agent": "com.zhiliaoapp.musically/2022600030 (Linux; U; Android 10; en_US)",
        "Content-Type": "application/json",
    }
    r = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
        headers=hdrs,
        json={"source": "DATA", "video_size": size, "chunk_size": size, "total_chunk_count": 1},
        timeout=30)
    d  = r.json().get("data", {})
    up = d.get("upload_url")
    pid = d.get("publish_id")
    if not up:
        logger.error(f"TikTok init failed: {r.text[:150]}")
        return False
    with open(clip, "rb") as f:
        requests.put(up, headers={"Content-Type": "video/mp4",
                                   "Content-Range": f"bytes 0-{size-1}/{size}"},
                     data=f, timeout=300)
    r2 = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=hdrs,
        json={"publish_id": pid,
              "post_info": {"title": caption, "privacy_level": "PUBLIC_TO_EVERYONE"},
              "source_info": {"source": "FILE_UPLOAD"}},
        timeout=30)
    ok = r2.status_code == 200
    logger.info(f"{'✓' if ok else '✗'} TikTok: {clip}")
    return ok


# ── POST TO YOUTUBE ──────────────────────────────────────────
def get_yt_token():
    r = requests.post("https://oauth2.googleapis.com/token",
        data={"client_id":     os.environ.get("YOUTUBE_CLIENT_ID", ""),
              "client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
              "refresh_token": os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
              "grant_type":    "refresh_token"},
        timeout=30)
    return r.json().get("access_token")


def post_youtube(clip, title, desc):
    token = get_yt_token()
    if not token:
        logger.error("Could not get YouTube token")
        return False
    size = os.path.getsize(clip)
    meta = {
        "snippet": {"title": title, "description": desc,
                    "tags": ["shorts", "viral", "trending"], "categoryId": "22"},
        "status":  {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
        json=meta, timeout=30)
    if init.status_code != 200:
        logger.error(f"YouTube init failed: {init.text[:150]}")
        return False
    up = init.headers.get("Location")
    with open(clip, "rb") as f:
        r = requests.put(up, headers={"Content-Type": "video/mp4",
                                       "Content-Length": str(size)},
                         data=f, timeout=300)
    ok  = r.status_code in (200, 201)
    vid = r.json().get("id", "?") if ok else ""
    logger.info(f"{'✓' if ok else '✗'} YouTube: {clip}{(' → youtu.be/'+vid) if ok else ''}")
    return ok


# ── GENERATE CAPTIONS ────────────────────────────────────────
def make_caption(text, platform, i):
    if platform == "tiktok":
        prompt = (f"Write a TikTok caption for viral clip {i+1}. "
                  f"Hook under 10 words. Under 150 chars. "
                  f"End with #fyp #viral #trending + 2 hashtags. Caption only.")
        fallback = f"You won't believe this 🤯 #fyp #viral #trending #clips"
    else:
        prompt = (f"Write a YouTube Shorts title for clip {i+1}. "
                  f"Under 60 chars. Curiosity-driven. End with #Shorts. Title only.")
        fallback = f"You Need To See This 👀 #Shorts"

    if not GEMINI_KEY:
        return fallback
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=20)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return fallback


# ── MAIN ─────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("AI Clip Generator starting...")
    logger.info(f"Provider: CLAUDE")

    try:
        import edge_tts
        logger.info("edge-tts ready")
    except ImportError:
        logger.warning("edge-tts not installed — voiceover skipped")

    clean_files()

    posted   = load_log()
    channels = [c.strip() for c in CHANNEL_IDS if c.strip()]
    total    = 0

    for ch in channels:
        logger.info(f"Channel: {ch}")
        for url in get_new_videos(ch, posted):
            src = download_video(url)
            if not src:
                logger.warning(f"Skipping {url} — download failed")
                posted.append(url)
                save_log(posted)
                continue

            dur = get_duration(src)
            if dur < CLIP_LENGTH + 20:
                logger.warning("Video too short — skipping")
                posted.append(url)
                save_log(posted)
                try: os.remove(src)
                except: pass
                continue

            segs  = transcribe(src)
            clips = find_clips(segs, dur)

            for i, clip in enumerate(clips):
                win  = " ".join(s["text"] for s in segs
                                if s["start"] >= clip["start"] and s["end"] <= clip["end"]).strip()
                hook = get_hook(win, i)
                vo   = gen_vo(win, f"vo_{i+total:02d}.mp3")
                out  = render(src, clip["start"], clip["end"], i + total, segs, hook, vo)

                if vo and os.path.exists(vo):
                    try: os.remove(vo)
                    except: pass

                if out:
                    # Post to TikTok
                    tt_cap = make_caption(win, "tiktok", i)
                    post_tiktok(out, tt_cap)

                    # Post to YouTube
                    yt_title = make_caption(win, "youtube", i)
                    post_youtube(out, yt_title, "Subscribe for more!\n\n#Shorts #Viral")

                    total += 1

            posted.append(url)
            save_log(posted)
            try: os.remove(src)
            except: pass

    logger.info(f"Done. Processed {total} videos.")
