import os
import re

import yt_dlp

SUPPORTED_WEBSITES = [
    "youtube.com",
    "youtu.be",
    # "twitter.com",
    # "x.com",
    # "tiktok.com",
    # "instagram.com",
    # "reddit.com",
    # "redd.it"
]


def is_supported_website(msg: str) -> bool:
    return any(website in msg for website in SUPPORTED_WEBSITES)


def extract_https_url(text: str) -> str:
    match = re.search(r'https://[^\s]+', text)
    return match.group(0) if match else None


def get_video_id(url: str) -> str:
    if "youtu.be" in url:
        return re.search(r'youtu.be/(.{11})', url).group(1)

    if "/shorts/" in url:
        return re.search(r'/shorts/(.{11})', url).group(1)

    match = re.search(r'[?&]v=([^&]{11})', url)
    return match.group(1) if match else None


def get_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def is_video_longer_than(url: str, time: int) -> bool:
    ydl_opts = {
        "quiet": True,  # Suppress output
        "no_warnings": True,
        "extract_flat": True,  # Faster metadata fetch
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration")
            if duration:
                return duration > time
            else:
                return False  # Duration missing (livestreams)
        except Exception as e:
            print(f"Error: {e}")
            return False


def download_video(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": filename,
        "cookiefile": "cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])

def download_video_720(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[height<=720][ext=mp4]+ba[ext=m4a]/b[ext=mp4][height<=720]",
        "outtmpl": filename,
        "cookiefile": "cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def is_file_smaller_than_50mb(file_path: str) -> bool:
    return os.path.getsize(file_path) < 50 * 1024 * 1024
