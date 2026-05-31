from urllib.parse import urlparse
from typing import Dict, Any, Optional

from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .smartrecruiters import SmartRecruitersAdapter
from .workday import WorkdayAdapter
from .ashby import AshbyAdapter
from .personio import PersonioAdapter
from .teamtailor import TeamtailorAdapter
from .bamboohr import BambooHRAdapter
from .base import BaseATSAdapter
from ..captcha import detect_recaptcha_sitekey, solve_recaptcha_v2, inject_recaptcha_token
from database.db import find_qa_answer, load_profile
from ai.generator import propose_answer_from_cv

ADAPTERS: list[BaseATSAdapter] = [
    GreenhouseAdapter(),
    LeverAdapter(),
    SmartRecruitersAdapter(),
    WorkdayAdapter(),
    AshbyAdapter(),
    PersonioAdapter(),
    TeamtailorAdapter(),
    BambooHRAdapter(),
]


def pick_adapter(url: str) -> Optional[BaseATSAdapter]:
    for a in ADAPTERS:
        if a.matches(url):
            return a
    return None


def apply_via_ats(page, url: str, candidate: Dict[str, str], cv_pdf_path: Optional[str], cover_letter: Optional[str], prefs: Dict[str, Any], status_cb=None) -> bool:
    adapter = pick_adapter(url)
    if adapter:
        # Captcha pre-check
        sitekey = detect_recaptcha_sitekey(page)
        if sitekey:
            token = solve_recaptcha_v2(sitekey, url)
            if token:
                inject_recaptcha_token(page, token)
        return adapter.apply(page, url, candidate, cv_pdf_path, cover_letter, prefs, status_cb=status_cb)
    # Fallback: try generic form
    try:
        # upload
        for sel in [
            "input[type='file'][name*='resume']",
            "input[type='file'][id*='resume']",
            "input[type='file'][name*='cv']",
            "input[type='file']",
        ]:
            el = page.query_selector(sel)
            if el and cv_pdf_path:
                el.set_input_files(cv_pdf_path)
                if status_cb:
                    try:
                        status_cb("CV_UPLOADED")
                    except Exception:
                        pass
                break
        # Captcha check (generic)
        sitekey = detect_recaptcha_sitekey(page)
        if sitekey:
            token = solve_recaptcha_v2(sitekey, url)
            if token:
                inject_recaptcha_token(page, token)
        # name/email/phone
        name = candidate.get("name", "")
        email = candidate.get("email", "")
        for sel, val in [
            ("input[name='name']", name),
            ("input[type='email']", email),
            ("input[name*='email']", email),
            ("input[type='tel']", "+33600000000"),
        ]:
            el = page.query_selector(sel)
            if el and val and not el.input_value():
                el.fill(val)
        # cover letter
        if cover_letter:
            for sel in ["textarea[name*='cover']", "textarea"]:
                el = page.query_selector(sel)
                if el and not el.input_value():
                    el.fill(cover_letter[:2000])
                    break
        # unknown required field detection
        try:
            candidates = page.query_selector_all("input[type='text'], textarea, select")
            exclude_snippets = ["email", "e-mail", "name", "full", "phone", "tel", "mobile", "resume", "cv", "cover", "linkedin", "github", "website", "portfolio"]
            for el in candidates:
                try:
                    if not el.is_visible():
                        continue
                    tag = el.evaluate("e => e.tagName.toLowerCase()")
                    val = ""
                    if tag == "select":
                        val = el.evaluate("e => e.value || ''")
                    else:
                        val = el.input_value() or ""
                    if val:
                        continue
                    name_attr = (el.get_attribute("name") or "").lower()
                    id_attr = (el.get_attribute("id") or "").lower()
                    ph_attr = (el.get_attribute("placeholder") or "").lower()
                    aria = (el.get_attribute("aria-label") or "").lower()
                    blob = " ".join([name_attr, id_attr, ph_attr, aria])
                    if any(s in blob for s in exclude_snippets):
                        continue
                    qtext = (el.get_attribute("placeholder") or el.get_attribute("aria-label") or name_attr or id_attr or "Question inconnue")
                    # essayer via QA overrides
                    ans = find_qa_answer(qtext)
                    if not ans:
                        try:
                            prof = load_profile()
                            cv_text = getattr(prof, 'cv_text', None) if prof else None
                        except Exception:
                            cv_text = None
                        ans = propose_answer_from_cv(qtext, cv_text, prefs)
                    if ans:
                        try:
                            if tag == "select":
                                try:
                                    el.select_option(label=ans)
                                except Exception:
                                    el.select_option(value=ans)
                            else:
                                el.fill(ans)
                            continue
                        except Exception:
                            pass
                    if status_cb:
                        try:
                            status_cb("NEEDS_ANSWER", qtext)
                        except Exception:
                            pass
                    return False
                except Exception:
                    continue
        except Exception:
            pass
        # submit
        for sel in [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Postuler')",
        ]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(2000)
                if status_cb:
                    try:
                        status_cb("SUBMITTED")
                    except Exception:
                        pass
                return True
    except Exception:
        return False
    return False
