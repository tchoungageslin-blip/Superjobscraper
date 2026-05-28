import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "meta-llama/llama-3-70b-instruct"

def generate_custom_cv_content(job_description, original_cv_text):
    print("🧠 [IA] Adaptation du CV pour l'offre...")
    prompt = f"""Tu es un expert en recrutement et en rédaction de CV.

Voici le CV original du candidat :
---
{original_cv_text}
---

Voici l'offre d'emploi :
---
{job_description[:3000]}
---

Ta mission :
1. Réécris le TITRE du CV pour qu'il corresponde exactement au poste demandé dans l'offre.
2. Réécris le PROFIL/RÉSUMÉ (2-3 lignes max) pour cibler précisément cette offre.
3. Mets en valeur les COMPÉTENCES les plus pertinentes pour ce poste.
4. Garde les expériences professionnelles dans le même ordre, mais reformule les bullet points pour qu'ils résonnent avec les mots-clés de l'offre.
5. Ne change pas les dates, les noms d'entreprise, les diplômes.
6. Retourne uniquement le CV réécrit en texte structuré (pas de commentaires).
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
