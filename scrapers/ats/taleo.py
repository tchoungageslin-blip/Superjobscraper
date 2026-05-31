from .base import BaseATSAdapter

class TaleoAdapter(BaseATSAdapter):
    hosts = ("taleo.net",)

    def apply(self, page, url, candidate, cv_pdf_path, cover_letter, prefs, status_cb=None):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=35000)
            page.wait_for_timeout(1200)

            self._upload_cv(page, [
                "input[type='file'][name*='resume']",
                "input[type='file'][name*='cv']",
                "input[type='file']",
            ], cv_pdf_path, status_cb)

            name = candidate.get("name", ""); email = candidate.get("email", "")
            for sel, val in [
                ("input[name='name']", name),
                ("input[type='email']", email),
                ("input[name*='email']", email),
                ("input[type='tel']", "+33600000000"),
            ]:
                self._fill(page, sel, val)

            if prefs:
                self._fill(page, "input[name*='salary']", prefs.get("salary_expectation", ""))
                self._fill(page, "input[name*='notice']", prefs.get("availability_delay", ""))

            if cover_letter:
                for sel in ["textarea[name*='cover']", "textarea"]:
                    if self._fill(page, sel, cover_letter[:2000]):
                        if status_cb:
                            try:
                                status_cb("FORM_FILLED")
                            except Exception:
                                pass
                        break

            if self._click_submit(page, [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Apply')",
                "button:has-text('Postuler')",
            ]):
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
