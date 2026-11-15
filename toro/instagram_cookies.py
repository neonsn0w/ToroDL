import os

import http.cookiejar
from pathlib import Path

import requests

from bot_tools import send_message_to_admin


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
    cookie = sorted(os.listdir(folder_path))[0]
    result = check_instagram_cookie_file(folder_path + "/" + cookie)
    if result["status"] != "VALID" and result["message"] != "RATE_LIMITED":
        send_message_to_admin(bot, admin_user_id, f"Deleting:\n{cookie}\n{result['status']}\n{result['message']}")
        os.remove(folder_path + "/" + cookie)

    send_message_to_admin(bot, admin_user_id,
                          f"Performed a cookie check.\n\nCookies in directory: {len(os.listdir(folder_path))}")
