import os
import time
import random
from dotenv import load_dotenv

from database.db import init_db, is_job_processed, add_job, update_job_status, load_profile
from scrapers.linkedin import LinkedInScraper
from ai.generator import generate_custom_cv_content, generate_cover_letter, extract_email_from_text
from ai.cv_builder import build_pdf_cv
from sender.email_sender import send_application_email

load_dotenv()

CV_BASE_PATH = os.path.join(os.path.dirname(__file__), "config", "cv_base.txt")

DEFAULT_KEYWORDS = [
    "Marketing Digital", "Chargé de Marketing", "Growth Hacker",
    "SEO Manager", "Community Manager", "Responsable Marketing",
]

def load_config_from_profile():
    profile = load_profile()
    if profile:
        print(f"✅ Profil chargé depuis Supabase : {profile.name} — {profile.job_field}")
        keywords_raw = profile.keywords or ""
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        if not keywords:
            keywords = DEFAULT_KEYWORDS
        return {
            "name": profile.name or "Candidat",
            "email": profile.email or "",
            "keywords": keywords,
            "location": profile.location or "France",
            "cv_text": profile.cv_text or load_cv_base(),
            "linkedin_email": profile.linkedin_email or "",
            "linkedin_password": profile.linkedin_password or "",
        }
    print("⚠️ Aucun profil trouvé dans Supabase. Utilisation des valeurs par défaut.")
    return {
        "name": os.getenv("CANDIDATE_NAME", "Candidat"),
        "email": "",
        "keywords": DEFAULT_KEYWORDS,
        "location": os.getenv("TARGET_COUNTRY", "France"),
        "cv_text": load_cv_base(),
        "linkedin_email": os.getenv("LINKEDIN_EMAIL", ""),
        "linkedin_password": os.getenv("LINKEDIN_PASSWORD", ""),
    }

def load_cv_base():
    try:
        with open(CV_BASE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "CV non configuré."

def process_job(job, cv_base_text, candidate_name, candidate_email, openrouter_key, resend_key, scraper=None):
    job_id = job["id"]
    title = job["title"]
    company = job["company"]
    link = job["link"]
    description = job.get("description", "")
    platform = job["platform"]

    # 1. Vérifier si déjà traité
    if is_job_processed(job_id):
        return

    print(f"\n⚙️ Traitement : [{company}] {title}")
    add_job(job_id, platform, title, company, link)
    update_job_status(job_id, "AI_PROCESSING")

    # 2. Adapter le CV via IA
    if description:
        adapted_cv = generate_custom_cv_content(description, cv_base_text, openrouter_key)
    else:
        adapted_cv = cv_base_text

    # 3. Générer le CV en PDF
    pdf_path = build_pdf_cv(adapted_cv, candidate_name, job_id)

    # 4. Générer la lettre de motivation
    cover_letter = generate_cover_letter(title, company, description, candidate_name, openrouter_key)

    applied = False

    # 5. LinkedIn Easy Apply (si connecté et offre LinkedIn)
    if scraper and platform == "LinkedIn" and scraper._logged_in:
        easy_applied = scraper.easy_apply(link, candidate_name, candidate_email, pdf_path, cover_letter)
        if easy_applied:
            applied = True

    # 6. Email (si email trouvé dans la description — on envoie en plus de Easy Apply)
    recruiter_email = extract_email_from_text(description) if description else None
    if recruiter_email:
        sent = send_application_email(
            to_email=recruiter_email,
            job_title=title,
            company_name=company,
            cover_letter=cover_letter,
            cv_pdf_path=pdf_path,
            candidate_name=candidate_name,
            resend_key=resend_key,
        )
        if sent:
            applied = True

    update_job_status(job_id, "APPLIED" if applied else "FOUND")

def main_loop():
    print("=" * 55)
    print("🚀  SUPER JOB SCRAPPER — MOTEUR 24/7 DÉMARRÉ")
    print("=" * 55)
    init_db()

    cycle_count = 1

    while True:
        config            = load_config_from_profile()
        keywords          = config["keywords"]
        location          = config["location"]
        cv_text           = config["cv_text"]
        name              = config["name"]
        email             = config["email"]
        linkedin_email    = config["linkedin_email"]
        linkedin_password = config["linkedin_password"]

        openrouter_key    = config["openrouter_key"]
        resend_key        = config["resend_key"]

        print(f"\n{'='*55}")
        print(f"🔄  CYCLE #{cycle_count} — {len(keywords)} mots-clés | {name} | {location}")
        print(f"{'='*55}")

        random.shuffle(keywords)

        with LinkedInScraper() as linkedin:
            linkedin.login(linkedin_email, linkedin_password)

            for keyword in keywords:
                try:
                    jobs = linkedin.search_jobs(keyword, location, max_pages=3)
                    new_jobs = [j for j in jobs if not is_job_processed(j["id"])]
                    print(f"  🆕 {len(new_jobs)} nouvelle(s) offre(s) non traitée(s) pour '{keyword}'")

                    for job in new_jobs:
                        try:
                            process_job(job, cv_text, name, email, openrouter_key, resend_key, scraper=linkedin)
                        except Exception as e:
                            print(f"  ❌ Erreur sur un job : {e}")
                            continue

                    pause = random.randint(45, 120)
                    print(f"  ⏳ Pause {pause}s avant le prochain mot-clé...")
                    time.sleep(pause)

                except Exception as e:
                    print(f"🔥 ERREUR MOTEUR sur '{keyword}': {e}")
                    print("  ↻ Redémarrage dans 3 minutes...")
                    time.sleep(180)
                    continue

        print(f"\n✅ Cycle #{cycle_count} terminé.")
        long_pause = random.randint(600, 1200)
        print(f"💤 Pause entre cycles : {long_pause // 60} min. Prochain cycle dans peu...")
        time.sleep(long_pause)
        cycle_count += 1

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n🛑 Moteur arrêté manuellement.")
