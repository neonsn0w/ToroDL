from pathlib import Path

import http.cookiejar
import logging
import os
import re
import requests
import shutil
import yt_dlp
from gallery_dl import config, job
from typing import List, Any, Union
from urllib.parse import urlparse, parse_qs

from botTools import send_message_to_admin

logger = logging.getLogger(__name__)

cindex = 0

SUPPORTED_WEBSITES = [
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "instagram.com",
    "reddit.com",
    "redd.it",
    "donmai.us",
    "safebooru.org"
]

DESCRIPTION_TAGS = {
    "instagram": "description",
    "tiktok": "desc",
    "reddit": "selftext",
    "twitter": "content"
}


def cleanup():
    """Removes files left from the last time that the bot was executed."""
    if os.path.exists("media-downloads"):
        shutil.rmtree("media-downloads")

    if os.path.exists("yt-dlp-downloads"):
        shutil.rmtree("yt-dlp-downloads")


def fix_cut_caption_string(s: str) -> str:
    """Removes broken <a> tags from strings"""
    if s.count("<a") != s.count("</a"):
        return s.rsplit("<a", 1)[0]

    return s


def check_instagram_cookie_file(file_path: str) -> dict:
    """Checks whether an Instagram session is valid using a Netscape cookie file.

    :param file_path: Path to the .txt file containing cookies in Netscape format.
    :return: dict with 'status' and descriptive 'message'.
    """
    path = Path(file_path)
    if not path.is_file():
        return {
            "status": "FILE_ERROR",
            "message": f"Cookie file not found: {file_path}",
        }

    cookie_jar = http.cookiejar.MozillaCookieJar(file_path)
    try:
        # ignore_discard keeps session cookies; ignore_expires ignores past expiry dates
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        return {
            "status": "PARSE_ERROR",
            "message": f"Failed to parse Netscape cookies: {e}",
        }

    session = requests.Session()
    session.cookies.update(cookie_jar)

    session_id = session.cookies.get("sessionid", domain=".instagram.com")
    if not session_id:
        return {
            "status": "MISSING_SESSION",
            "message": "No 'sessionid' cookie found for instagram.com in the file.",
        }

    csrf_token = session.cookies.get("csrftoken", domain=".instagram.com")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.instagram.com/accounts/edit/",
    }

    if csrf_token:
        headers["X-CSRFToken"] = csrf_token

    url = "https://www.instagram.com/api/v1/accounts/edit/web_form_data/"

    try:
        response = session.get(
            url,
            headers=headers,
            timeout=10,
            allow_redirects=False,
        )

        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "ok" and "form_data" in data:
                    return {
                        "status": "VALID",
                        "username": data["form_data"].get(
                            "username", "Unknown"
                        ),
                        "message": "Cookie is active and authenticated.",
                    }
            except ValueError:
                pass

        if response.status_code in (301, 302):
            location = response.headers.get("Location", "")
            if "login" in location:
                return {
                    "status": "EXPIRED",
                    "message": "Session expired or invalid.",
                }
            if "challenge" in location or "checkpoint" in location:
                return {
                    "status": "CHECKPOINT",
                    "message": "Account requires verification/checkpoint.",
                }

        try:
            body = response.json()
            if body.get("message") == "checkpoint_required":
                return {
                    "status": "CHECKPOINT",
                    "message": "Session hit a security checkpoint.",
                }
        except Exception:
            pass

        if response.status_code in (401, 403):
            return {
                "status": "INVALID",
                "message": "Cookie rejected or unauthorized.",
            }

        if response.status_code == 429:
            return {
                "status": "RATE_LIMITED",
                "message": "IP rate limit hit. Switch IP or wait.",
            }

        return {
            "status": "ERROR",
            "message": f"HTTP {response.status_code}: {response.text[:100]}",
        }

    except requests.exceptions.RequestException as e:
        return {"status": "NETWORK_ERROR", "message": str(e)}


def delete_dead_ig_cookies(bot, admin_user_id, folder_path: str = "igcookies"):
    for cookie in os.listdir(folder_path):
        result = check_instagram_cookie_file(folder_path + "/" + cookie)
        if result["status"] != "VALID" and result["message"] != "RATE_LIMITED":
            send_message_to_admin(bot, admin_user_id, f"Deleting:\n{cookie}\n{result['status']}\n{result['message']}")
            os.remove(folder_path + "/" + cookie)

    send_message_to_admin(bot, admin_user_id,
                          f"Performed a cookie check.\n\nCookies in directory: {len(os.listdir(folder_path))}")


def is_supported_website(msg: str) -> bool:
    return any(website in msg for website in SUPPORTED_WEBSITES)


def validate_url(url: str) -> bool:
    patterns = [
        # Instagram: Posts, Reels
        r'instagram\.com/(?:p|reel|reels)/',

        # Instagram Stories
        r'instagram\.com/stories/[^/]+/',

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
        r'(?:twitter|x)\.com/[^/]+/status/\d+',

        r'donmai\.us\/posts\/(\d+)',

        r'safebooru\.org',

        # Facebook: Posts, reels, videos, share shortcuts, photos, groups, and legacy query permalinks
        r'(?:[a-z0-9-]+\.)?facebook\.com/(?:'
        r'(?:[^/]+/)?(?:posts|videos|reel)/[a-zA-Z0-9]+'
        r'|groups/[^/]+/(?:posts|permalink)/[a-zA-Z0-9]+'
        r'|share/[pvr]/[a-zA-Z0-9]+'
        r'|photo(?:\.php|/)?\?[^#\s]*fbid=\d+'
        r'|media/set/\?[^#\s]*set='
        r'|watch/\?[^#\s]*v=\d+'
        r'|(?:permalink|story)\.php\?[^#\s]*story_fbid='
        r')',
        r'fb\.watch/[a-zA-Z0-9_-]+'
    ]

    for pattern in patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def get_natural_sort_key(s: Union[str, Path]) -> List[Any]:
    target = s.name if isinstance(s, Path) else s

    parts = re.split(r'(\d+)', target)

    def convert_part(part):
        return int(part) if part.isdigit() else part

    return [convert_part(p) for p in parts]


def naturally_sort_filenames(filenames: List[Union[str, Path]]) -> List[Union[str, Path]]:
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
    return re.search(r'/(?:twitter|x)\.com\/[^\/]+\/status\/(\d+)', url).group(1)


def get_tiktok_video_id(url: str) -> str:
    if "/video/" in url:
        return re.search(r'/video/(.{19})', url).group(1)

    if "/photo/" in url:
        return re.search(r'/photo/(.{19})', url).group(1)

    return re.search(r'tiktok.com/(.{9})', url).group(1)


def get_ig_video_id(url: str) -> str:
    if "stories/" in url:
        return re.search(r'stories/[^/]+/(\d+)', url).group(1)

    if "reel/" in url:
        return re.search(r'reel/(.{11})', url).group(1)

    if "reels/" in url:
        return re.search(r'reels/(.{11})', url).group(1)

    return re.search(r'/p/(.{11})', url).group(1)


def get_reddit_id(url: str) -> str:
    if "comments/" in url:
        return re.search(r'comments/(.{6})', url).group(1)

    return re.search(r'/s/(.{10)', url).group(1)


def get_danbooru_post_id(url: str) -> str:
    return re.search(r'/posts/(\d+)', url).group(1)


def get_safebooru_post_id(url: str) -> str:
    return re.search(r'[?&]id=(\d+)', url).group(1)


def get_facebook_post_id(url: str) -> str | None:
    """
    Extracts the unique Post or Video ID from any Facebook URL.
    Returns the alphanumeric ID string, or None if no match is found.
    """

    # Hello, this is neonsn0w, I would like to let you know that this function is completely slopped and I
    # have no intention to make this function better, because if anyone thinks that I will put any effort
    # into parsing 10 different url formats for a platform that is absolute dog water they are dead wrong.

    if not url:
        return None

    # Normalize: strip trailing whitespace, ensure scheme for proper parsing
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # 1. Query parameters: story_fbid, fbid, and v (videos)
    for key in ['story_fbid', 'fbid', 'v', 'id']:
        # If 'id' is present, only treat it as post ID if it's on a permalink/story page
        if key == 'id' and not any(p in parsed.path for p in ['permalink.php', 'story.php']):
            continue
        if key in params and params[key]:
            val = params[key][0]
            if val:
                return val

    # 2. Path-based patterns
    path = parsed.path.strip('/')

    patterns = [
        # Standard Posts & Permalinks
        r'(?:posts|permalink|post)/([a-zA-Z0-9]+)',
        # Reels & Videos
        r'(?:reel|videos)/([a-zA-Z0-9]+)',
        # Modern Share links: facebook.com/share/p/{id}/ or /share/v/{id}/ or /share/r/{id}/
        r'share/[pvr]/([a-zA-Z0-9]+)',
        # Photos: photos/a.123.../{photo_id} or photos/{album_id}/{photo_id}
        r'photos/(?:[^/]+/)?([0-9]+)',
        # Legacy photo structure: photos/{user_id}/{photo_id}
        r'photos/[^/]+/[^/]+/([0-9]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, path)
        if match:
            return match.group(1)

    return None


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
    elif "donmai.us" in url:
        return get_danbooru_post_id(url)
    elif "safebooru.org" in url:
        return get_safebooru_post_id(url)
    elif "facebook.com" in url:
        return get_facebook_post_id(url)
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
    elif "donmai.us" in url:
        return "danbooru"
    elif "safebooru.org" in url:
        return "safebooru"
    elif "facebook.com" in url:
        return "facebook"
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
        elif "donmai.us" in url:
            return get_danbooru_post_id(url) + "." + ext
        elif "safebooru.org" in url:
            return get_safebooru_post_id(url) + "." + ext
        elif "facebook.com" in url:
            return get_facebook_post_id(url) + "." + ext
        else:
            return "-1"
    except Exception as e:
        return "-1"


def get_description_tag(platform: str) -> str:
    return DESCRIPTION_TAGS.get(platform, "None")


def is_video_longer_than(url: str, time: int) -> bool:
    ydl_opts = {
        "quiet": True,  # Suppress output
        "no_warnings": True,
        "extract_flat": True,  # Faster metadata fetch
        "cookiefile": "cookies.txt",
    }

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


def download_video(link: str, filename: str):
    youtube_dl_options = {
        "format": "bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": f"yt-dlp-downloads/{filename}",
        "cookiefile": "cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def download_audio(link: str, filename: str):
    youtube_dl_options = {
        "format": "ba[ext=m4a]",
        "outtmpl": f"yt-dlp-downloads/{filename}",
        "cookiefile": "cookies.txt",
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
        "cookiefile": "cookies.txt",
    }
    with yt_dlp.YoutubeDL(youtube_dl_options) as ydl:
        return ydl.download([link])


def download_media(url: str):
    global cindex
    config.load()  # config file is in /etc/gallery-dl.conf or %APPDATA%\gallery-dl\config.json
    if "instagram" in url:
        cookies = os.listdir('igcookies')
        cindex = cindex + 1
        if cindex >= len(cookies):
            cindex = 0
        with open(f'./igcookies/{cookies[cindex]}', 'r') as cookiefile:
            cstr = cookiefile.read()
        logging.info(f'using cookie {cookies[cindex]}')
        config.set(("extractor",), "cookies", f'./igcookies/{cookies[cindex]}')
    else:
        config.set(("extractor",), "cookies", "cookies.txt")
    config.set(("extractor",), "directory", [get_platform(url), get_platform_video_id(url)])
    config.set(("extractor",), "filename", get_platform_video_id(url) + "_{num}.{extension}")

    config.set(("postprocessor", "metadata"), "module", "metadata")

    config.set(("postprocessor", "metadata"), "event", "post")
    config.set(("postprocessor", "metadata"), "filename", get_platform_video_id(url) + ".txt")
    config.set(("postprocessor", "metadata"), "content", "{content or description}")

    j = job.DownloadJob(url)

    j.run()


def is_file_smaller_than_50mb(file_path: str) -> bool:
    return os.path.getsize(file_path) < 50 * 1024 * 1024


def is_arr_smaller_than_50mb(files) -> bool:
    for f in files:
        if not is_file_smaller_than_50mb(f):
            return False

    return True


def chunk_list(data: list, size: int):
    """Yield successive n-sized chunks from a list."""
    for i in range(0, len(data), size):
        yield data[i:i + size]
