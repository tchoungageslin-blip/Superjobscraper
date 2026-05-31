import os
import time
import requests

TWO_CAPTCHA_API_KEY = os.getenv("TWO_CAPTCHA_API_KEY") or os.getenv("ANTICAPTCHA_API_KEY")


def detect_recaptcha_sitekey(page):
    try:
        # Try explicit container
        el = page.query_selector("div.g-recaptcha")
        if el:
            key = el.get_attribute("data-sitekey")
            if key:
                return key
        # Try iframe
        iframe = page.query_selector("iframe[src*='recaptcha']")
        if iframe:
            src = iframe.get_attribute("src")
            if src and "k=" in src:
                return src.split("k=")[1].split("&")[0]
    except Exception:
        pass
    return None


def solve_recaptcha_v2(site_key: str, url: str, timeout: int = 120) -> str | None:
    if not TWO_CAPTCHA_API_KEY:
        return None
    try:
        # Create task
        resp = requests.get("http://2captcha.com/in.php", params={
            "key": TWO_CAPTCHA_API_KEY,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": url,
            "json": 1,
        }, timeout=20)
        rid = resp.json().get("request")
        if resp.json().get("status") != 1 or not rid:
            return None
        # Poll result
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(5)
            res = requests.get("http://2captcha.com/res.php", params={
                "key": TWO_CAPTCHA_API_KEY,
                "action": "get",
                "id": rid,
                "json": 1,
            }, timeout=20)
            data = res.json()
            if data.get("status") == 1:
                return data.get("request")
            if data.get("request") != "CAPCHA_NOT_READY":
                break
    except Exception:
        return None
    return None


def inject_recaptcha_token(page, token: str) -> bool:
    try:
        # Standard response textarea
        ta = page.query_selector("textarea[name='g-recaptcha-response'], textarea#g-recaptcha-response")
        if ta:
            ta.evaluate("(el, val) => el.value = val", token)
            return True
        # Invisible recaptcha might need grecaptcha.execute; best-effort injection
        page.evaluate("token => { window.___captchaToken=token; }", token)
        return True
    except Exception:
        return False
