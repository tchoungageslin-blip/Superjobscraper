from .base import BaseATSAdapter

class SmartRecruitersAdapter(BaseATSAdapter):
    hosts = ("smartrecruiters.com", "apply.smartrecruiters.com")

    def apply(self, page, url, candidate, cv_pdf_path, cover_letter, prefs):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=35000)
            page.wait_for_timeout(1500)
            # Upload CV (peut être dans un iframe, best-effort direct)
            self._upload_cv(page, [
                "input[type='file'][name*='resume']",
                "input[type='file'][name*='cv']",
                "input[type='file']",
            ], cv_pdf_path)

            name = candidate.get("name", "")
            email = candidate.get("email", "")

            for sel, val in [
                ("input[name*='name']", name),
                ("input[type='email']", email),
                ("input[name*='email']", email),
                ("input[type='tel']", "+33600000000"),
            ]:
                self._fill(page, sel, val)

            if prefs:
                self._fill(page, "input[name*='salary']", prefs.get("salary_expectation", ""))
                self._fill(page, "input[name*='notice']", prefs.get("availability_delay", ""))
                self._fill(page, "input[name*='visa']", prefs.get("visa_status", ""))

            if cover_letter:
                for sel in ["textarea[name*='cover']", "textarea"]:
                    if self._fill(page, sel, cover_letter[:2000]):
                        break

            if self._click_submit(page, [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Apply')",
                "button:has-text('Postuler')",
            ]):
                page.wait_for_timeout(2000)
                return True
        except Exception:
            return False
        return False
