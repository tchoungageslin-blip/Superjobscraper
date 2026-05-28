import os
import time
import random
from dotenv import load_dotenv

from database.db import init_db, is_job_processed, add_job, update_job_status
from scrapers.linkedin import LinkedInScraper
from ai.generator import generate_custom_cv_content, generate_cover_letter, extract_email_from_text
from ai.cv_builder import build_pdf_cv
from sender.email_sender import send_application_email

load_dotenv()

KEYWORDS = [
    "Marketing Digital",
    "Chargé de Marketing",
    "Growth Hacker",
    "SEO Manager",
    "Community Manager",
    "Responsable Marketing",
    "Digital Marketing Manager",
    "Traffic Manager",
    "Brand Manager",
    "Content Manager",
]
LOCATION = os.getenv("TARGET_COUNTRY", "France")
CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Votre Nom Complet")

CV_BASE_PATH = os.path.join(os.path.dirname(__file__), "config", "cv_base.txt")

def load_cv_base():
    try:
        with open(CV_BASE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        print("⚠️ Fichier config/cv_base.txt introuvable. Utilisation d'un CV vide.")
        return "CV non configuré."

def process_job(job, cv_base_text):
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
        adapted_cv = generate_custom_cv_content(description, cv_base_text)
    else:
        adapted_cv = cv_base_text

    # 3. Générer le CV en PDF
    pdf_path = build_pdf_cv(adapted_cv, CANDIDATE_NAME, job_id)

    # 4. Générer la lettre de motivation
    cover_letter = generate_cover_letter(title, company, description, CANDIDATE_NAME)

    # 5. Chercher un email dans la description
    recruiter_email = extract_email_from_text(description) if description else None

    # 6. Envoyer l'email si un email est disponible
    if recruiter_email:
        sent = send_application_email(
            to_email=recruiter_email,
            job_title=title,
            company_name=company,
            cover_letter=cover_letter,
            cv_pdf_path=pdf_path,
            candidate_name=CANDIDATE_NAME,
        )
        update_job_status(job_id, "APPLIED" if sent else "FAILED")
    else:
        # Pas d'email → on marque "FOUND" (on a postulé manuellement ou via LinkedIn Easy Apply à venir)
        print(f"  ℹ️ Pas d'email trouvé — statut: FOUND (candidature LinkedIn à implémenter)")
        update_job_status(job_id, "FOUND")

def main_loop():
    print("=" * 55)
    print("🚀  SUPER JOB SCRAPPER — MOTEUR 24/7 DÉMARRÉ")
    print("=" * 55)
    init_db()
    cv_base = load_cv_base()
    linkedin = LinkedInScraper()
    cycle_count = 1

    while True:
        print(f"\n{'='*55}")
        print(f"�  CYCLE #{cycle_count} — {len(KEYWORDS)} mots-clés dans la file")
        print(f"{'='*55}")

        random.shuffle(KEYWORDS)

        for keyword in KEYWORDS:
            try:
                jobs = linkedin.search_jobs(keyword, LOCATION, max_pages=3)
                new_jobs = [j for j in jobs if not is_job_processed(j["id"])]
                print(f"  🆕 {len(new_jobs)} nouvelle(s) offre(s) non traitée(s) pour '{keyword}'")

                for job in new_jobs:
                    try:
                        process_job(job, cv_base)
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
