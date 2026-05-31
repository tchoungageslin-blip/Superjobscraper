"""
Un seul cycle de scraping — utilisé par GitHub Actions (cron toutes les heures).
"""
import os
import random
from dotenv import load_dotenv

from database.db import init_db, is_job_processed, load_profile
from scrapers.linkedin import LinkedInScraper
from main import load_config_from_profile, process_job
from ai.generator import generate_keywords

load_dotenv()

def run_once():
    print("🚀 SUPER JOB SCRAPPER — CYCLE UNIQUE (GitHub Actions)")
    init_db()

    config   = load_config_from_profile()
    # Aligne avec main: génère dynamiquement les mots-clés
    prof = load_profile()
    ai_keywords = generate_keywords(config["cv_text"], prof.job_field if prof else "")
    keywords = ai_keywords or config["keywords"]
    location = config["location"]
    cv_text  = config["cv_text"]
    name     = config["name"]
    email    = config["email"]

    linkedin_email    = config["linkedin_email"]
    linkedin_cookie   = config["linkedin_cookie"]
    prefs = {
        "visa_status": config.get("visa_status", ""),
        "mobility": config.get("mobility", ""),
        "salary_expectation": config.get("salary_expectation", ""),
        "availability_delay": config.get("availability_delay", ""),
    }

    # Limiteurs de test via ENV (défaut = 1 pour un cycle court)
    try:
        max_keywords = int(os.getenv("MAX_KEYWORDS_PER_RUN", "1") or "1")
    except ValueError:
        max_keywords = 1
    try:
        max_jobs = int(os.getenv("MAX_JOBS_PER_RUN", "1") or "1")
    except ValueError:
        max_jobs = 1
    try:
        search_max_pages = int(os.getenv("SEARCH_MAX_PAGES", "1") or "1")
    except ValueError:
        search_max_pages = 1

    print(f"👤 {name} | 📍 {location} | 🔑 {len(keywords)} mots-clés (test: {max_keywords} kw, {max_jobs} job, {search_max_pages} page)")

    random.shuffle(keywords)

    total_processed = 0
    with LinkedInScraper() as linkedin:
        linkedin.login(linkedin_cookie)

        for idx, keyword in enumerate(keywords):
            if idx >= max_keywords:
                break
            try:
                jobs = linkedin.search_jobs(keyword, location, max_pages=search_max_pages)
                new_jobs = [j for j in jobs if not is_job_processed(j["id"])]
                print(f"  🆕 {len(new_jobs)} nouvelle(s) offre(s) pour '{keyword}'")

                for job in new_jobs:
                    try:
                        process_job(job, cv_text, name, email, scraper=linkedin, prefs=prefs)
                        total_processed += 1
                    except Exception as e:
                        print(f"  ❌ Erreur job : {e}")
                    if total_processed >= max_jobs:
                        break

            except Exception as e:
                print(f"🔥 Erreur sur '{keyword}': {e}")
            if total_processed >= max_jobs:
                break

    print("✅ Cycle terminé.")

if __name__ == "__main__":
    run_once()
