import time
import random
import hashlib
import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .ats.dispatcher import apply_via_ats

class LinkedInScraper:

    BASE_SEARCH_URL = "https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_TPR=r86400&start={start}"

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._logged_in = False

    def start(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        
        # Charge la session si elle existe (contourne le login classique)
        state_path = "linkedin_state.json"
        storage_state = state_path if os.path.exists(state_path) else None

        self._context = self._browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            storage_state=storage_state
        )
        self._page = self._context.new_page()

    def stop(self):
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None
        self._page = None
        self._logged_in = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def random_sleep(self, min_s=1.5, max_s=4.0):
        time.sleep(random.uniform(min_s, max_s))

    def human_scroll(self):
        for _ in range(random.randint(3, 6)):
            self._page.mouse.wheel(0, random.randint(300, 700))
            time.sleep(random.uniform(0.5, 1.5))

    def make_job_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def extract_job_id_from_url(self, url):
        if "currentJobId=" in url:
            return url.split("currentJobId=")[1].split("&")[0]
        if "/jobs/view/" in url:
            return url.split("/jobs/view/")[1].split("/")[0].split("?")[0]
        return self.make_job_id(url)

    def login(self, cookie_li_at):
        if self._logged_in:
            return True
            
        # 1. Tenter avec un fichier local (si on a utilisé login_linkedin.py)
        try:
            self._page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
            self.random_sleep(2, 3)
            if any(p in self._page.url for p in ["feed", "mynetwork", "jobs"]):
                self._logged_in = True
                print("✅ Connecté à LinkedIn (via fichier de session local) !")
                return True
        except Exception:
            pass

        # 2. Injecter le cookie provenant de Supabase (Dashboard)
        if cookie_li_at:
            print("🔐 Injection du cookie de session LinkedIn (li_at)...")
            try:
                self._context.add_cookies([
                    {
                        "name": "li_at",
                        "value": cookie_li_at,
                        "domain": ".www.linkedin.com",
                        "path": "/"
                    }
                ])
                self._page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
                self.random_sleep(2, 4)
                if any(p in self._page.url for p in ["feed", "mynetwork", "jobs", "home"]):
                    self._logged_in = True
                    print("✅ Connecté à LinkedIn (via le cookie du dashboard) !")
                    return True
                print("⚠️ Le cookie fourni est invalide ou expiré.")
            except Exception as e:
                print(f"❌ Erreur lors de l'injection du cookie : {e}")

        print("⚠️ Aucune session active et aucun cookie valide fourni. Le bot ne pourra pas utiliser Easy Apply.")
        return False

    def get_job_description(self, job_url):
        try:
            self._page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            self.random_sleep(2, 4)
            self.human_scroll()
            try:
                self._page.click("button.show-more-less-html__button", timeout=3000)
                self.random_sleep(0.5, 1)
            except Exception:
                pass
            html = self._page.content()
            soup = BeautifulSoup(html, "html.parser")
            desc_div = soup.find("div", {"class": "show-more-less-html__markup"})
            if desc_div:
                return desc_div.get_text(separator="\n").strip()
            desc_div = soup.find("div", {"class": lambda c: c and "description" in c})
            if desc_div:
                return desc_div.get_text(separator="\n").strip()
        except Exception as e:
            print(f"  ⚠️ Impossible de lire la description : {e}")
        return ""

    def get_external_apply_url(self, job_url):
        """Retourne l'URL 'Postuler sur le site' si présente sur la page LinkedIn job.
        """
        try:
            self._page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            self.random_sleep(1.5, 3)
            # Boutons communs
            for sel in [
                "a[aria-label*='Postuler sur le site']",
                "a[aria-label*='Apply on company website']",
                "a[href*='companyApplyRedirect']",
                "a.jobs-apply-button--top-card",
            ]:
                try:
                    a = self._page.query_selector(sel)
                    if a and a.is_visible():
                        href = a.get_attribute("href")
                        if href and not href.startswith("/jobs/apply/"):
                            if href.startswith("/"):
                                href = "https://www.linkedin.com" + href
                            return href
                except Exception:
                    continue
        except Exception as e:
            print(f"  ⚠️ Pas d'URL d'application externe: {e}")
        return None

    def easy_apply(self, job_url, candidate_name, candidate_email, cv_pdf_path, cover_letter):
        """Tente une candidature LinkedIn Easy Apply. Retourne True si soumis."""
        if not self._logged_in:
            print("  ⚠️ Easy Apply ignoré : non connecté à LinkedIn")
            return False
        try:
            self._page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            self.random_sleep(2, 4)

            easy_apply_btn = None
            for selector in [
                "button[aria-label*='Easy Apply']",
                "button[aria-label*='Candidature simplifiée']",
                "button.jobs-apply-button",
            ]:
                try:
                    btn = self._page.wait_for_selector(selector, timeout=4000)
                    if btn and btn.is_visible():
                        label = (btn.get_attribute("aria-label") or btn.inner_text() or "").lower()
                        if "easy apply" in label or "simplifi" in label:
                            easy_apply_btn = btn
                            break
                except Exception:
                    continue

            if not easy_apply_btn:
                print("  ℹ️ Pas de bouton Easy Apply sur cette offre")
                return False

            easy_apply_btn.click()
            self.random_sleep(2, 3)

            for _ in range(10):
                self._fill_form_fields(cv_pdf_path, cover_letter)
                self.random_sleep(1, 2)
                submitted = self._handle_apply_buttons()
                if submitted:
                    print(f"  ✅ Easy Apply soumis !")
                    return True
                if not self._page.query_selector(".jobs-easy-apply-content, .artdeco-modal__content"):
                    break

            return False

        except Exception as e:
            print(f"  ❌ Erreur Easy Apply : {e}")
            try:
                self._page.keyboard.press("Escape")
            except Exception:
                pass
            return False

    def _fill_form_fields(self, cv_pdf_path, cover_letter):
        try:
            # Upload CV si champ file présent
            if cv_pdf_path and os.path.exists(cv_pdf_path):
                file_input = self._page.query_selector("input[type='file']")
                if file_input:
                    file_input.set_input_files(cv_pdf_path)
                    self.random_sleep(1, 2)

            # Lettre de motivation
            for sel in ["textarea[id*='cover']", "textarea[placeholder*='lettre']", "textarea[placeholder*='cover']", "textarea[placeholder*='Cover']"]:
                field = self._page.query_selector(sel)
                if field:
                    if not field.input_value():
                        field.fill((cover_letter or "")[:2000])
                    break

            # Téléphone si vide
            for sel in ["input[id*='phoneNumber']", "input[autocomplete*='tel']", "input[name*='phone']"]:
                field = self._page.query_selector(sel)
                if field and not field.input_value():
                    field.fill("+33600000000")
                    break

        except Exception as e:
            print(f"  ⚠️ Remplissage formulaire : {e}")

    def _handle_apply_buttons(self):
        """Clique sur Submit > Review > Next selon ce qui est disponible. Retourne True si soumis."""
        for label_fragment in ["Submit application", "Soumettre"]:
            btn = self._page.query_selector(f"button[aria-label*='{label_fragment}']")
            if btn and btn.is_visible():
                btn.click()
                self.random_sleep(2, 3)
                return True

        for label_fragment in ["Review your application", "Vérifier", "Review"]:
            btn = self._page.query_selector(f"button[aria-label*='{label_fragment}']")
            if btn and btn.is_visible():
                btn.click()
                self.random_sleep(1, 2)
                return False

        for label_fragment in ["Continue to next step", "Suivant", "Next"]:
            btn = self._page.query_selector(f"button[aria-label*='{label_fragment}']")
            if btn and btn.is_visible():
                btn.click()
                self.random_sleep(1, 2)
                return False

        return False

    def apply_on_ats(self, url, candidate_name, candidate_email, cv_pdf_path, cover_letter, prefs=None):
        """Application sur ATS via adaptateurs dédiés avec fallback générique."""
        try:
            candidate = {"name": candidate_name, "email": candidate_email}
            prefs = prefs or {}
            # délégué aux adaptateurs spécialisés
            self._page.goto(url, wait_until="domcontentloaded", timeout=25000)
            self.random_sleep(2, 4)
            self.human_scroll()
            def _status_cb(ev: str):
                print(f"    [ATS] {ev}")
            ok = apply_via_ats(self._page, url, candidate, cv_pdf_path, cover_letter, prefs, status_cb=_status_cb)
            if ok:
                print("  ✅ ATS soumis !")
                return True
            return False
        except Exception as e:
            print(f"  ❌ Erreur ATS: {e}")
            return False

    def search_jobs(self, keyword, location, max_pages=5):
        print(f"\n🔍 [LinkedIn] Recherche : '{keyword}' @ '{location}'")
        all_jobs = []

        for page_num in range(max_pages):
            start = page_num * 25
            url = self.BASE_SEARCH_URL.format(
                keyword=keyword.replace(" ", "%20"),
                location=location.replace(" ", "%20"),
                start=start
            )
            try:
                print(f"  📄 Page {page_num + 1}/{max_pages} — offset={start}")
                self._page.goto(url, wait_until="domcontentloaded", timeout=25000)
                self.random_sleep(3, 6)
                self.human_scroll()

                html = self._page.content()
                soup = BeautifulSoup(html, "html.parser")

                job_cards = soup.find_all("div", {"class": lambda c: c and "job-search-card" in c})
                if not job_cards:
                    job_cards = soup.find_all("li", {"class": lambda c: c and "result-card" in c})

                print(f"  ✅ {len(job_cards)} offres trouvées sur cette page")

                for card in job_cards:
                    try:
                        title_tag = card.find("h3") or card.find("h2")
                        company_tag = card.find("h4") or card.find("a", {"class": lambda c: c and "company" in c})
                        link_tag = card.find("a", href=True)

                        title = title_tag.get_text(strip=True) if title_tag else "N/A"
                        company = company_tag.get_text(strip=True) if company_tag else "N/A"
                        link = link_tag["href"] if link_tag else ""

                        if not link:
                            continue

                        if link.startswith("/"):
                            link = "https://www.linkedin.com" + link
                        link = link.split("?")[0]

                        job_id = self.extract_job_id_from_url(link)
                        description = self.get_job_description(link)
                        self.random_sleep(2, 5)

                        all_jobs.append({
                            "id": job_id,
                            "platform": "LinkedIn",
                            "title": title,
                            "company": company,
                            "link": link,
                            "description": description
                        })
                        print(f"    ➕ [{company}] {title}")

                    except Exception as e:
                        print(f"  ⚠️ Erreur card : {e}")
                        continue

                self.random_sleep(4, 8)

            except Exception as e:
                print(f"  🔥 Erreur page {page_num + 1} : {e}")
                self.random_sleep(10, 20)
                continue

        print(f"🏁 [LinkedIn] Total extrait pour '{keyword}' : {len(all_jobs)} offres")
        return all_jobs

