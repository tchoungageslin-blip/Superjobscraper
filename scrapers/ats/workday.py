from .base import BaseATSAdapter

class WorkdayAdapter(BaseATSAdapter):
    hosts = ("workday", "myworkdayjobs.com")

    def apply(self, page, url, candidate, cv_pdf_path, cover_letter, prefs, status_cb=None):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(1500)

            # Upload CV (Workday peut utiliser un bouton d'upload custom)
            self._upload_cv(page, [
                "input[type='file'][name*='resume']",
                "input[type='file'][id*='resume']",
                "input[type='file'][name*='cv']",
                "input[type='file']",
                "input[type='file'][data-automation-id*='fileUpload']",
            ], cv_pdf_path, status_cb)

            name = candidate.get("name", "")
            email = candidate.get("email", "")

            # Champs génériques
            for sel, val in [
                ("input[type='email']", email),
                ("input[name*='email']", email),
                ("input[name='name']", name),
                ("input[type='tel']", "+33600000000"),
            ]:
                self._fill(page, sel, val)

            # Preferences
            if prefs:
                self._fill(page, "input[name*='salary']", prefs.get("salary_expectation", ""))
                self._fill(page, "input[name*='notice']", prefs.get("availability_delay", ""))

            # Cover letter (si présent)
            if cover_letter:
                for sel in ["textarea[name*='cover']", "textarea"]:
                    if self._fill(page, sel, cover_letter[:2000]):
                        if status_cb:
                            try:
                                status_cb("FORM_FILLED")
                            except Exception:
                                pass
                        break

            # Submit
            if self._click_submit(page, [
                "button[type='submit']",
                "button[data-automation-id*='bottom-navigation-next-button']",
                "button:has-text('Apply')",
                "button:has-text('Soumettre')",
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
