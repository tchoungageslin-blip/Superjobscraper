"""
Un seul cycle de scraping — utilisé par GitHub Actions (cron toutes les heures).
"""
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

    print(f"👤 {name} | 📍 {location} | 🔑 {len(keywords)} mots-clés")

    random.shuffle(keywords)

    with LinkedInScraper() as linkedin:
        linkedin.login(linkedin_cookie)

        for keyword in keywords:
            try:
                jobs = linkedin.search_jobs(keyword, location, max_pages=2)
                new_jobs = [j for j in jobs if not is_job_processed(j["id"])]
                print(f"  🆕 {len(new_jobs)} nouvelle(s) offre(s) pour '{keyword}'")

                for job in new_jobs:
                    try:
                        process_job(job, cv_text, name, email, scraper=linkedin)
                    except Exception as e:
                        print(f"  ❌ Erreur job : {e}")

            except Exception as e:
                print(f"🔥 Erreur sur '{keyword}': {e}")

    print("✅ Cycle terminé.")

if __name__ == "__main__":
    run_once()
