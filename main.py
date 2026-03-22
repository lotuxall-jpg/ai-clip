import os
import json
import feedparser
import requests
from yt_dlp import YoutubeDL

# ====== CONFIG ======
YOUTUBE_CHANNEL_IDS = [
    "UCWsDFclhY2DBi3GB5uykGXA",  # IShowSpeed
    "UCjiXtODGCCulmhwypZAWSag",  # Jynxzi
    "UCoEmptob-eEGKk18c2VpIJg",  # Kai Cenat
    "UCGRryxFxjXbVAtBPE9EbyMg",  # Joe Bartolozzi
    "UCKDBMEtklUsdH-xJlyrBG7A"   # Plaqueboy Max
]

TELEGRAM_BOT_TOKEN = "8699414099:AAFufCbRt0QqsY8VYdoctASGym79DO3fIdk"
TELEGRAM_CHAT_ID = "8205944221"

LOG_FILE = "posted_log.json"


# ====== LOAD LOG ======
def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return json.load(f)


def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f)


# ====== GET VIDEOS ======
def get_latest_videos(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(url)
    return feed.entries


# ====== DOWNLOAD VIDEO ======
def download_video(url):
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "video.%(ext)s",
        "noplaylist": True,
        "quiet": False,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android"]
            }
        }
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print("Download failed:", e)
        return False


# ====== SEND TO TELEGRAM ======
def send_to_telegram(file_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"

    try:
        with open(file_path, "rb") as video:
            requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={"video": video}
            )
        print("Sent to Telegram ✅")
    except Exception as e:
        print("Telegram send failed:", e)


# ====== MAIN ======
def main():
    posted = load_log()

    for channel_id in YOUTUBE_CHANNEL_IDS:
        videos = get_latest_videos(channel_id)

        for video in videos:
            # if video.link in posted:
#     continue

            print(f"Downloading: {video.title}")

            success = download_video(video.link)
            if not success:
                continue

            print("Sending to Telegram...")
            send_to_telegram("video.mp4")

            posted.append(video.link)
            save_log(posted)

            break  # only 1 video per run


if __name__ == "__main__":
    main()
