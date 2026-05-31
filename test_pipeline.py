"""
Script de test end-to-end du pipeline complet.
Verifier que DB, IA et PDF fonctionnent correctement.
"""
import sys

from database.db import init_db, add_job, update_job_status, is_job_processed
from ai.generator import generate_custom_cv_content, generate_cover_letter
from ai.cv_builder import build_pdf_cv
from main import load_config_from_profile

def run_tests():
    errors = []

    # TEST 1 : Connexion base de donnees
    print("--- TEST 1 : Connexion Supabase ---")
    try:
        init_db()
        config = load_config_from_profile()
        print("PASS\n")
    except Exception as e:
        print(f"FAIL : {e}\n")
        errors.append("DB")

    # TEST 2 : Adaptation CV par IA
    print("--- TEST 2 : Adaptation CV (OpenRouter IA) ---")
    try:
        cv_base = config["cv_text"]
        offre = "Nous recherchons un Digital Marketing Manager pour piloter nos campagnes SEO et Google Ads en France."
        cv_adapte = generate_custom_cv_content(offre, cv_base)
        assert len(cv_adapte) > 100, "Reponse IA trop courte"
        print(f"PASS ({len(cv_adapte)} caracteres generes)\n")
    except Exception as e:
        print(f"FAIL : {e}\n")
        errors.append("IA")
        cv_adapte = cv_base

    # TEST 3 : Generation PDF
    print("--- TEST 3 : Generation PDF ---")
    try:
        pdf_path = build_pdf_cv(cv_adapte, config["name"], "test_job_001")
        print(f"PASS -> {pdf_path}\n")
    except Exception as e:
        print(f"FAIL : {e}\n")
        errors.append("PDF")

    # TEST 4 : Ecriture / Lecture base de donnees
    print("--- TEST 4 : Ecriture et lecture Supabase ---")
    try:
        test_id = "pipeline_test_001"
        add_job(test_id, "LinkedIn", "Digital Marketing Manager", "Entreprise Test", "https://linkedin.com/test")
        update_job_status(test_id, "APPLIED")
        already_done = is_job_processed(test_id)
        assert already_done is True, "Le job ne se retrouve pas dans la BD"
        print(f"PASS (doublon detecte correctement = {already_done})\n")
    except Exception as e:
        print(f"FAIL : {e}\n")
        errors.append("BD_WRITE")

    # Lettre de motivation
    print("--- TEST 5 : Lettre de motivation (IA) ---")
    try:
        lettre = generate_cover_letter("Digital Marketing Manager", "Entreprise Test", offre, config["name"])
        assert len(lettre) > 50
        print(f"PASS ({len(lettre)} caracteres)\n")
    except Exception as e:
        print(f"FAIL : {e}\n")
        errors.append("COVER_LETTER")

    print("=" * 45)
    if errors:
        print(f"RESULTAT : {len(errors)} echec(s) -> {errors}")
        sys.exit(1)
    else:
        print("TOUS LES TESTS PASSES AVEC SUCCES !")
        print("Le pipeline est pret a tourner 24/7.")
    print("=" * 45)

if __name__ == "__main__":
    run_tests()
