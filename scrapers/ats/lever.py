from .base import BaseATSAdapter

class LeverAdapter(BaseATSAdapter):
    hosts = ("lever.co", "jobs.lever.co")

    def apply(self, page, url, candidate, cv_pdf_path, cover_letter, prefs, status_cb=None):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            # Upload CV
            self._upload_cv(page, [
                "input[type='file'][name*='resume']",
                "input[type='file'][id*='resume']",
                "input[type='file']",
            ], cv_pdf_path, status_cb)

            name = candidate.get("name", "")
            first = name.split()[0] if name else ""
            last = " ".join(name.split()[1:]) if name and len(name.split())>1 else "Candidate"
            email = candidate.get("email", "")

            # Lever varie beaucoup; on tente plusieurs sélecteurs génériques
            for sel, val in [
                ("input[name='name']", name),
                ("input[name='firstName']", first),
                ("input[name='lastName']", last),
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
                for sel in ["textarea[name='coverLetter']", "textarea[name*='cover']", "textarea"]:
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
                "button:has-text('Submit')",
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
