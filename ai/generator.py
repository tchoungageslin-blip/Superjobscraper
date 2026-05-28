import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "meta-llama/llama-3-70b-instruct"

def generate_custom_cv_content(job_description, original_cv_text):
    print("🧠 [IA] Adaptation du CV pour l'offre...")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    prompt = f"""Tu es un expert en recrutement et en rédaction de CV.

Voici le CV original du candidat :
---
{original_cv_text}
---

Voici l'offre d'emploi ciblée :
---
{job_description[:3000]}
---

RÈGLES STRICTES DE MODIFICATION :
1. Modifie UNIQUEMENT le TITRE du CV pour qu'il corresponde exactement au poste de l'offre.
2. Modifie UNIQUEMENT la section PROFIL / RÉSUMÉ / OBJECTIF (2-3 phrases) pour montrer en quoi le candidat est le profil idéal pour cette entreprise et ce poste spécifique.
3. NE MODIFIE STRICTEMENT RIEN D'AUTRE. Garde exactement les mêmes expériences, dates, entreprises, écoles, compétences, langues et loisirs. 
4. Ne supprime aucune ligne du reste du CV. Ne rajoute pas d'expériences inventées.
5. Retourne le CV entier avec juste le titre et le résumé modifiés. Ne fais aucun commentaire en dehors du CV.
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert en rédaction de CV professionnel, spécialisé dans l'optimisation ATS."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Erreur IA (generate_custom_cv_content) : {e}")
        return original_cv_text

def generate_cover_letter(job_title, company_name, job_description, candidate_name):
    print(f"✍️ [IA] Rédaction de la lettre de motivation pour {company_name}...")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    prompt = f"""Rédige une lettre de motivation professionnelle, concise et percutante (max 3 paragraphes) pour :
- Candidat : {candidate_name}
- Poste : {job_title}
- Entreprise : {company_name}
- Contexte de l'offre : {job_description[:1500]}

La lettre doit :
1. Accrocher dès la première phrase.
2. Montrer que le candidat connaît l'entreprise et le poste.
3. Mettre en avant 2-3 compétences clés.
4. Terminer par un appel à l'action (demande d'entretien).
Langue : Français. Pas de [PLACEHOLDER] ou de crochets. Retourne uniquement la lettre.
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Tu rédiges des lettres de motivation en français, professionnelles et personnalisées."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Erreur IA (generate_cover_letter) : {e}")
        return ""

def extract_email_from_text(text):
    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return emails[0] if emails else None
