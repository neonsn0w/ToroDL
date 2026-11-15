from urllib.parse import urlsplit, urlunsplit, urlparse, parse_qs

import logging
import re

from .x_embed_fixers import X_EMBED_FIXERS

logger = logging.getLogger(__name__)

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
        r'fb\.watch/[a-zA-Z0-9_-]+',

        # Twitch clips
        r'(?:clips\.twitch\.tv/|twitch\.tv/[^/]+/clip/)[^/?\s]+',

        # Bilibili videos
        r"^https?://(?:(?:www\.|m\.)?bilibili\.com/(?:video/(?:BV[A-Za-z0-9]+|av\d+)|bangumi/play/(?:ep\d+|ss\d+))|b23\.tv/[A-Za-z0-9]+)(?:[/?#].*)?$",
    ]

    for pattern in patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def extract_https_url(text: str) -> str:
    match = re.search(r'https://[^\s]+', text)
    return match.group(0) if match else None


def unfix_url(url: str) -> str:
    """Replaces Twitter/X embed fixer domains with x.com"""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()

    if host.startswith("www."):  # Just in case...
        host = host[4:]

    is_fixer = any(host == d or host.endswith("." + d) for d in X_EMBED_FIXERS)
    if not is_fixer:
        return url

    new_url = urlunsplit(parts._replace(netloc="x.com"))
    return str(new_url)


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


def get_twitch_clip_id(url: str) -> str:
    return re.search(r'(?:clips\.twitch\.tv/|/clip/)([^/?]+)', url).group(1)


def get_bilibili_video_id(url: str) -> str:
    if not validate_url(url):
        return "-1"

    if "/video/" in url:
        return re.search(r"bilibili\.com/video/(BV[A-Za-z0-9]+|av\d+)", url).group(1)
    elif "/bangumi/" in url:
        return re.search(r"bilibili\.com/bangumi/play/(ep\d+|ss\d+)", url).group(1)
    else:
        return re.search(r"b23\.tv/([A-Za-z0-9]+)", url).group(1)


def unshorten_b23_url(url: str) -> str:
    if "b23.tv" in url:
        return "https://www.bilibili.com/video/" + get_bilibili_video_id(url)

    return "-1"


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
    elif "twitch.tv" in url:
        return get_twitch_clip_id(url)
    elif "bilibili.com" in url or "b23.tv" in url:
        return get_bilibili_video_id(url)
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
    elif "twitch.tv" in url:
        return "twitch"
    elif "bilibili.com" in url or "b23.tv" in url:
        return "bilibili"
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
        elif "twitch.tv" in url:
            return get_twitch_clip_id(url) + "." + ext
        elif "bilibili.com" in url or "b23.tv" in url:
            return get_bilibili_video_id(url) + "." + ext
        else:
            return "-1"
    except Exception as e:
        return "-1"


def get_description_tag(platform: str) -> str:
    return DESCRIPTION_TAGS.get(platform, "None")
