import time
import random
import hashlib
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class LinkedInScraper:

    BASE_SEARCH_URL = "https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_TPR=r86400&start={start}"

    def random_sleep(self, min_s=1.5, max_s=4.0):
        time.sleep(random.uniform(min_s, max_s))

    def human_scroll(self, page):
        for _ in range(random.randint(3, 6)):
            page.mouse.wheel(0, random.randint(300, 700))
            time.sleep(random.uniform(0.5, 1.5))

    def make_job_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def extract_job_id_from_url(self, url):
        if "currentJobId=" in url:
            return url.split("currentJobId=")[1].split("&")[0]
        if "/jobs/view/" in url:
            return url.split("/jobs/view/")[1].split("/")[0].split("?")[0]
        return self.make_job_id(url)

    def get_job_description(self, page, job_url):
        try:
            page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            self.random_sleep(2, 4)
            self.human_scroll(page)
            # Cliquer sur "Voir plus" si disponible
            try:
                page.click("button.show-more-less-html__button", timeout=3000)
                self.random_sleep(0.5, 1)
            except Exception:
                pass
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            # Tentative sur la div de description principale
            desc_div = soup.find("div", {"class": "show-more-less-html__markup"})
            if desc_div:
                return desc_div.get_text(separator="\n").strip()
            # Fallback
            desc_div = soup.find("div", {"class": lambda c: c and "description" in c})
            if desc_div:
                return desc_div.get_text(separator="\n").strip()
        except Exception as e:
            print(f"  ⚠️ Impossible de lire la description : {e}")
        return ""

    def search_jobs(self, keyword, location, max_pages=5):
        print(f"\n🔍 [LinkedIn] Recherche : '{keyword}' @ '{location}'")
        all_jobs = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="fr-FR",
            )
            page = context.new_page()

            for page_num in range(max_pages):
                start = page_num * 25
                url = self.BASE_SEARCH_URL.format(
                    keyword=keyword.replace(" ", "%20"),
                    location=location.replace(" ", "%20"),
                    start=start
                )
                try:
                    print(f"  📄 Page {page_num + 1}/{max_pages} — offset={start}")
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    self.random_sleep(3, 6)
                    self.human_scroll(page)

                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    job_cards = soup.find_all("div", {"class": lambda c: c and "job-search-card" in c})
                    if not job_cards:
                        # Sélecteur alternatif
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

                            # Nettoyer le lien
                            if link.startswith("/"):
                                link = "https://www.linkedin.com" + link
                            link = link.split("?")[0]

                            job_id = self.extract_job_id_from_url(link)

                            # Récupérer la description complète
                            description = self.get_job_description(page, link)
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

                    # Pause entre les pages
                    self.random_sleep(4, 8)

                except Exception as e:
                    print(f"  🔥 Erreur page {page_num + 1} : {e}")
                    self.random_sleep(10, 20)
                    continue

            browser.close()

        print(f"🏁 [LinkedIn] Total extrait pour '{keyword}' : {len(all_jobs)} offres")
        return all_jobs

