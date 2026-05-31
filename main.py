import os
import time
import random
from dotenv import load_dotenv

from database.db import init_db, is_job_processed, add_job, update_job_status, load_profile, export_cv_to_temp
from scrapers.linkedin import LinkedInScraper
from ai.generator import generate_keywords, generate_cover_letter, extract_email_from_text
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
            "linkedin_cookie": profile.linkedin_cookie or "",
            "visa_status": getattr(profile, "visa_status", "") or "",
            "mobility": getattr(profile, "mobility", "") or "",
            "salary_expectation": getattr(profile, "salary_expectation", "") or "",
            "availability_delay": getattr(profile, "availability_delay", "") or "",
        }
    print("⚠️ Aucun profil trouvé dans Supabase. Utilisation des valeurs par défaut.")
    return {
        "name": os.getenv("CANDIDATE_NAME", "Candidat"),
        "email": "",
        "keywords": DEFAULT_KEYWORDS,
        "location": os.getenv("TARGET_COUNTRY", "France"),
        "cv_text": load_cv_base(),
        "linkedin_email": "",
        "linkedin_cookie": "",
        "visa_status": "",
        "mobility": "",
        "salary_expectation": "",
        "availability_delay": "",
    }

def load_cv_base():
    try:
        with open(CV_BASE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "CV non configuré."

def process_job(job, cv_base_text, candidate_name, candidate_email, scraper=None, prefs=None):
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

    # 2. On utilise le CV original tel quel (exporté depuis la DB)
    pdf_path = export_cv_to_temp()

    # 3. Générer la lettre de motivation
    cover_letter = generate_cover_letter(title, company, description, candidate_name)

    applied = False

    def status_cb(ev: str, details: str | None = None):
        try:
            update_job_status(job_id, ev, details)
        except Exception:
            pass

    # 4. LinkedIn Easy Apply puis ATS externe si dispo
    if scraper and platform == "LinkedIn":
        if scraper._logged_in:
            update_job_status(job_id, "APPLYING")
            easy_applied = scraper.easy_apply(link, candidate_name, candidate_email, pdf_path, cover_letter, status_cb=status_cb)
            if easy_applied:
                applied = True
        # Si pas appliqué via Easy Apply, tenter l'ATS externe même si non connecté
        if not applied:
            try:
                ext = scraper.get_external_apply_url(link)
            except Exception:
                ext = None
            if ext:
                update_job_status(job_id, "APPLYING")
                ats_applied = scraper.apply_on_ats(ext, candidate_name, candidate_email, pdf_path, cover_letter, prefs or {}, status_cb=status_cb)
                if ats_applied:
                    applied = True

    # 5. Email (si email trouvé dans la description — on envoie en plus de Easy Apply)
    recruiter_email = extract_email_from_text(description) if description else None
    if recruiter_email:
        sent = send_application_email(
            to_email=recruiter_email,
            job_title=title,
            company_name=company,
            cover_letter=cover_letter,
            cv_pdf_path=pdf_path,
            candidate_name=candidate_name,
        )
        if sent:
            applied = True

    update_job_status(job_id, "APPLIED" if applied else "FAILED")

def main_loop():
    print("=" * 55)
    print("🚀  SUPER JOB SCRAPPER — MOTEUR 24/7 DÉMARRÉ")
    print("=" * 55)
    init_db()

    cycle_count = 1

    while True:
        config            = load_config_from_profile()
        # Génère dynamiquement les mots-clés à partir du CV et du domaine
        ai_keywords       = generate_keywords(config["cv_text"], profile.job_field if (profile := load_profile()) else "")
        keywords          = ai_keywords or config["keywords"]
        location          = config["location"]
        cv_text           = config["cv_text"]
        name              = config["name"]
        email             = config["email"]
        linkedin_email    = config["linkedin_email"]
        linkedin_cookie   = config["linkedin_cookie"]
        prefs             = {
            "visa_status": config.get("visa_status", ""),
            "mobility": config.get("mobility", ""),
            "salary_expectation": config.get("salary_expectation", ""),
            "availability_delay": config.get("availability_delay", ""),
        }

        print(f"\n{'='*55}")
        print(f"🔄  CYCLE #{cycle_count} — {len(keywords)} mots-clés | {name} | {location}")
        print(f"{'='*55}")

        random.shuffle(keywords)

        with LinkedInScraper() as linkedin:
            linkedin.login(linkedin_cookie)

            for keyword in keywords:
                try:
                    jobs = linkedin.search_jobs(keyword, location, max_pages=3)
                    new_jobs = [j for j in jobs if not is_job_processed(j["id"])]
                    print(f"  🆕 {len(new_jobs)} nouvelle(s) offre(s) non traitée(s) pour '{keyword}'")

                    for job in new_jobs:
                        try:
                            process_job(job, cv_text, name, email, scraper=linkedin, prefs=prefs)
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
