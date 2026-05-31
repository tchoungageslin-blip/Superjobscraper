from .base import BaseATSAdapter

class GreenhouseAdapter(BaseATSAdapter):
    hosts = ("greenhouse.io", "boards.greenhouse.io")

    def apply(self, page, url, candidate, cv_pdf_path, cover_letter, prefs, status_cb=None):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            # Upload CV
            self._upload_cv(page, [
                "input[type='file'][id*='resume']",
                "input[type='file'][name*='resume']",
                "input[type='file'][name*='cv']",
                "input[type='file']",
            ], cv_pdf_path, status_cb)

            # Remplir champs
            name = candidate.get("name", "")
            first = name.split()[0] if name else ""
            last = " ".join(name.split()[1:]) if name and len(name.split())>1 else "Candidate"
            email = candidate.get("email", "")

            for sel, val in [
                ("input[name='first_name']", first),
                ("input[name='last_name']", last),
                ("input[name='name']", name),
                ("input[name='email']", email),
                ("input[type='email']", email),
                ("input[name*='phone']", "+33600000000"),
            ]:
                self._fill(page, sel, val)

            # Preferences fréquentes
            if prefs:
                self._fill(page, "input[name*='salary']", prefs.get("salary_expectation", ""))
                self._fill(page, "input[name*='notice']", prefs.get("availability_delay", ""))
                self._fill(page, "input[name*='visa']", prefs.get("visa_status", ""))

            # Cover letter
            if cover_letter:
                if self._fill(page, "textarea[name*='cover']", cover_letter[:2000]) and status_cb:
                    try:
                        status_cb("FORM_FILLED")
                    except Exception:
                        pass

            # Submit
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
