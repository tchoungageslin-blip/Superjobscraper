from __future__ import annotations
from typing import Optional, Dict, Any
import os

class BaseATSAdapter:
    hosts: tuple[str, ...] = tuple()

    def matches(self, url: str) -> bool:
        return any(h in (url or "").lower() for h in self.hosts)

    def apply(self, page, url: str, candidate: Dict[str, str], cv_pdf_path: Optional[str], cover_letter: Optional[str], prefs: Dict[str, Any]) -> bool:
        raise NotImplementedError

    # Helpers
    def _upload_cv(self, page, selectors: list[str], cv_pdf_path: Optional[str]):
        if not (cv_pdf_path and os.path.exists(cv_pdf_path)):
            return
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    el.set_input_files(cv_pdf_path)
                    return
            except Exception:
                continue

    def _fill(self, page, selector: str, value: str):
        try:
            el = page.query_selector(selector)
            if el and value and not el.input_value():
                el.fill(value)
                return True
        except Exception:
            pass
        return False

    def _click_submit(self, page, selectors: list[str]) -> bool:
        for sel in selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    return True
            except Exception:
                continue
        return False
