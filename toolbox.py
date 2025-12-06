import os
import re
import time
import logging

from typing import List, Any
from gallery_dl import config, job

import yt_dlp

logger = logging.getLogger(__name__)

SUPPORTED_WEBSITES = [
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "instagram.com",
    "reddit.com",
    "redd.it"
]


def is_supported_website(msg: str) -> bool:
    return any(website in msg for website in SUPPORTED_WEBSITES)


def validate_url(url: str) -> bool:
    patterns = [
        # Instagram: Posts, Reels
        r'instagram\.com/(?:p|reel)/',

        # TikTok: Matches @user/video/ID AND @user/photo/ID
        # Also catches short links (vm/vt)
        r'tiktok\.com/@[^/]+/(?:video|photo)/\d+',
        r'(?:vm|vt)\.tiktok\.com/',

        # YouTube: Watch, Shorts, or shortened youtu.be links
        r'(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)',

        # Reddit: Must contain /comments/ or be a redd.it shortlink
        r'reddit\.com/r/[^/]+/comments/',
        r'redd\.it/',

        # X (Twitter): Must contain /status/
        r'(?:twitter|x)\.com/[^/]+/status/\d+'
    ]

    for pattern in patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def get_natural_sort_key(s: str) -> List[Any]:
    parts = re.split('(\d+)', s)

    def convert_part(part):
        return int(part) if part.isdigit() else part

    return [convert_part(p) for p in parts]


def naturally_sort_filenames(filenames: List[str]) -> List[str]:
    return sorted(filenames, key=get_natural_sort_key)


def extract_https_url(text: str) -> str:
    match = re.search(r'https://[^\s]+', text)
    return match.group(0) if match else None


def cleanup_mp4_url(url: str) -> str:
    return url.split('?')[0]


def check_if_mp4_url(url: str) -> bool:
    if cleanup_mp4_url(url).endswith(".mp4"):
        return True

    return False


def check_if_mp4_url_is_larger_than_50mb(url: str) -> bool:
    import urllib.request

    req = urllib.request.Request(url, method='HEAD')

    try:
        with urllib.request.urlopen(req) as response:
            content_length = response.getheader('Content-Length')

            if content_length:
                size_in_bytes = int(content_length)
                size_in_mb = size_in_bytes / (1024 * 1024)

                if size_in_mb > 50:
                    return True
                else:
                    return False

            else:
                return True

    except Exception as e:
        logger.error(e)
        return False


def get_yt_video_id(url: str) -> str:
    if "youtu.be" in url:
        return re.search(r'youtu.be/(.{11})', url).group(1)

    if "/shorts/" in url:
        return re.search(r'/shorts/(.{11})', url).group(1)

    match = re.search(r'[?&]v=([^&]{11})', url)
    return match.group(1) if match else None


def get_yt_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def get_x_status_id(url: str) -> str:
    return re.search(r'status/(.{18})', url).group(1)


def get_tiktok_video_id(url: str) -> str:
    if "/video/" in url:
        return re.search(r'/video/(.{19})', url).group(1)

    if "/photo/" in url:
        return re.search(r'/photo/(.{19})', url).group(1)

    return re.search(r'tiktok.com/(.{9})', url).group(1)


def get_ig_video_id(url: str) -> str:
    if "reel/" in url:
        return re.search(r'reel/(.{11})', url).group(1)

    if "reels/" in url:
        return re.search(r'reels/(.{11})', url).group(1)

    return re.search(r'/p/(.{11})', url).group(1)


def get_reddit_id(url: str) -> str:
    if "comments/" in url:
        return re.search(r'comments/(.{7})', url).group(1)

    return re.search(r'/s/(.{10)', url).group(1)


def get_platform_video_id(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return get_yt_video_id(url)
    elif "twitter.com" in url or "x.com" in url:
        return get_x_status_id(url)
    elif "tiktok.com" in url:
        return get_tiktok_video_id(url)
    elif "instagram.com" in url:
        return get_ig_video_id(url)
    elif "reddit.com" in url or "redd.it" in url:
        return get_reddit_id(url)
    else:
        return "-1"


def get_platform(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "twitter.com" in url or "x.com" in url:
        return "twitter"
    elif "tiktok.com" in url:
        return "tiktok"
    elif "instagram.com" in url:
        return "instagram"
    elif "reddit.com" in url or "redd.it" in url:
        return "reddit"
    else:
        return "-1"


def get_filename(url: str, ext: str) -> str:
    if ext.startswith("."):
        ext = ext[1:]  # removes first char

    try:
        if "youtube.com" in url or "youtu.be" in url:
            return get_yt_video_id(url) + "." + ext
        elif "x.com" in url or "twitter.com" in url:
            return get_x_status_id(url) + "." + ext
        elif "tiktok.com" in url:
            return get_tiktok_video_id(url) + "." + ext
        elif "instagram.com" in url:
            return get_ig_video_id(url) + "." + ext
        elif "reddit.com" in url or "redd.it" in url:
            return get_reddit_id(url) + "." + ext
        else:
            return "-1"
    except Exception as e:
        return "-1"


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
            logger.error(f"Error: {e}")
            return False


def download_video(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": filename,
        "cookiefile": "cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def download_media(url: str):
    config.load()  # config file is in /etc/gallery-dl.conf or %APPDATA%\gallery-dl\config.json
    config.set(("extractor",), "cookies", "cookies.txt")
    config.set(("extractor",), "directory", [get_platform(url), get_platform_video_id(url)])
    config.set(("extractor",), "filename", get_platform_video_id(url) + "_{num}.{extension}")

    j = job.DownloadJob(url)

    j.run()


def download_video_720(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[height<=720][ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4][height<=720]",
        "outtmpl": filename,
        "cookiefile": "cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def is_file_smaller_than_50mb(file_path: str) -> bool:
    return os.path.getsize(file_path) < 50 * 1024 * 1024
