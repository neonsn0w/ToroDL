import logging

import os
import yt_dlp
from gallery_dl import config, job
from gallery_dl.extractor.twitter import TwitterAPI

from toro.urls import unshorten_b23_url, get_platform_video_id, get_platform

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Path where the actual script lives (not the working dir)


def is_video_longer_than(url: str, time: int) -> bool:
    ydl_opts = {
        "quiet": True,  # Suppress output
        "no_warnings": True,
        "extract_flat": True,  # Faster metadata fetch
        "cookiefile": "../cookies.txt",
    }

    if "b23.tv" in url:
        url = unshorten_b23_url(url)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration")
            if duration:
                return duration > time
            else:
                return True  # Duration missing (livestreams)
        except Exception as e:
            logger.error(f"Error: {e}")
            return True


def configure_gallery_dl(url: str):
    global cindex

    # Reset internal config dictionary
    config.clear()

    video_id = get_platform_video_id(url)
    platform = get_platform(url)

    # Content is downloaded in ./media-downloads/platform/video_id/video_id_N.ext
    config.set(("extractor",), "base-directory", "media-downloads")
    config.set(("extractor",), "archive", None)
    config.set(("extractor",), "directory", [platform, video_id])
    config.set(("extractor",), "filename", f"{video_id}_{{num}}.{{extension}}")

    # Description download settings, description metadata is in video_id.txt
    config.set(("postprocessor", "metadata"), "module", "metadata")
    config.set(("postprocessor", "metadata"), "event", "post")
    config.set(("postprocessor", "metadata"), "filename", f"{video_id}.txt")
    config.set(("postprocessor", "metadata"), "content", "{content or description}")

    # Instagram
    config.set(("extractor", "instagram"), "videos", "ytdl")
    config.set(("extractor", "instagram"), "ytdl", {"format": "avc1"})
    config.set(("extractor", "instagram"), "ytdl-args", [
        "-f", "bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]"
    ])
    config.set(("extractor", "instagram"), "postprocessors", [
        {
            "name": "metadata",
            "extension": "txt",
            "content": "{content|description|caption}"
        }
    ])

    # TikTok
    config.set(("extractor", "tiktok"), "videos", "ytdl")
    config.set(("extractor", "tiktok"), "postprocessors", [
        {
            "name": "metadata",
            "extension": "txt",
            "content": "{description|caption}"
        }
    ])

    # Reddit
    config.set(("extractor", "reddit"), "videos", "ytdl")
    config.set(("extractor", "reddit"), "postprocessors", [
        {
            "name": "metadata",
            "extension": "txt",
            "content": "{description|caption|title}"
        }
    ])

    # Twitter
    TwitterAPI._transaction_id = lambda self, url, method="GET": None
    config.set(("extractor", "twitter"), "videos", "ytdl")
    config.set(("extractor", "twitter"), "tweet-endpoint", "restid")
    config.set(("extractor", "twitter"), "postprocessors", [
        {
            "name": "metadata",
            "extension": "txt",
            "content": "{description|caption|title}"
        },
        {
            "name": "exec",
            "event": "after",
            "filter": "type == 'animated_gif'",
            "command": 'FILE="{_path}"; ffmpeg -y -i "$FILE" "${FILE%.*}.gif" && rm "$FILE"'
        }
    ])

    # Cookie configuration, Instagram sequentially uses cookies from the igcookies directory, Instagram cookies can expire very quickly ;-;
    if "instagram" in url:
        ig_dir = os.path.join(BASE_DIR, "../igcookies")
        cookies = sorted(os.listdir(ig_dir))
        cindex = 0
        cookie_path = os.path.join(ig_dir, cookies[cindex])
        logging.info(f"Using cookie {cookies[cindex]}")
        config.set(("extractor", "instagram"), "cookies", cookie_path)
    else:
        cookie_path = os.path.join(BASE_DIR, "../cookies.txt")
        config.set(("extractor",), "cookies", cookie_path)
        config.set(("extractor", "twitter"), "cookies", cookie_path)


def download_video(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": f"yt-dlp-downloads/{filename}",
        "cookiefile": "../cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def download_audio(link: str, filename: str):
    youtube_dl_options = {
        "format": "ba[ext=m4a]",
        "outtmpl": f"yt-dlp-downloads/{filename}",
        "cookiefile": "../cookies.txt",
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            },
        ],
        "keepvideo": True,
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        info = ydl.extract_info(link, download=True)
        return info


def download_video_720(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[height<=720][ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4][height<=720]",
        "outtmpl": f"yt-dlp-downloads/{filename}",
        "cookiefile": "../cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def download_video_1080(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[height<=1080][ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4][height<=1080]",
        "outtmpl": f"yt-dlp-downloads/{filename}",
        "cookiefile": "../cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def download_media(url: str):
    configure_gallery_dl(url)
    j = job.DownloadJob(url)
    j.run()
