import html
import json
import os
import re
import requests


def download_media_embed(shortcode: str) -> str:
    """Downloads media from Instagram using embeds"""
    cookies = {
        'wd': '1920x697',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Alt-Used': 'www.instagram.com',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i',
    }

    r = requests.get(f'https://www.instagram.com/p/{shortcode}/embed/captioned', headers=headers, cookies=cookies)

    if not os.path.exists(f'media-downloads/instagram/{shortcode}'):
        os.makedirs(f"media-downloads/instagram/{shortcode}")

    if 'class="WatchOnInstagram">Watch on Instagram' in r.text:
        raise ValueError('Exception: Video is not embeddable')

    if 'The link to this photo or video may be broken, or the post may have been removed.' in r.text:
        raise ValueError('Exception: Video is not embeddable')

    if 'edge_sidecar_to_children' in r.text:
        m = re.search(r'"contextJSON"\s*:\s*("(?:\\.|[^"\\])*")', r.text)
        ctx = json.loads(json.loads(m.group(1)))  # string → object
        media = ctx["gql_data"]
        for i, item in enumerate(media['shortcode_media']['edge_sidecar_to_children']['edges']):
            if item['node']['is_video']:
                url = item['node']['video_url']
                video = requests.get(html.unescape(url))
                with open(f'media-downloads/instagram/{shortcode}/{shortcode}{i}.mp4', 'wb') as file:
                    file.write(video.content)
            else:
                url = item['node']['display_url']
                img = requests.get(html.unescape(url))
                with open(f'media-downloads/instagram/{shortcode}/{shortcode}{i}.webp', 'wb') as file:
                    file.write(img.content)
    elif 'video_url' in r.text:
        url = r.text.split('video_url\\":\\"')[1].split('\\"')[0]
        video = requests.get(url.replace('\\', ''))
        with open(f'media-downloads/instagram/{shortcode}/{shortcode}0.mp4', 'wb') as file:
            file.write(video.content)
    elif 'img class="EmbeddedMediaImage' in r.text:
        url = r.text.split('img class="EmbeddedMediaImage"')[1].split('src="')[1].split('"')[0]
        img = requests.get(html.unescape(url))
        with open(f'media-downloads/instagram/{shortcode}/{shortcode}0.webp', 'wb') as file:
            file.write(img.content)

    if '</a><br /><br />' in r.text:
        if 'CaptionCommentsExpand' in r.text:
            return ''.join(r.text[r.text.find('</a><br /><br />') + len('</a><br /><br />'):]).split('<div')[0].replace(
                '<br />', '\n').replace('href="', 'href="https://instagram.com')
        else: # No comments
            return ''.join(r.text[r.text.find('</a><br /><br />') + len('</a><br /><br />'):]).split('</div')[
                0].replace(
                '<br />', '\n').replace('href="', 'href="https://instagram.com')
    else: # Empty caption
        return ''

