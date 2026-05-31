import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

"""
Sélection dynamique de modèle OpenRouter avec fallback.
Priorité:
1) OPENROUTER_MODEL (si défini)
2) Liste de modèles gratuits connus
"""

def _model_candidates() -> list[str]:
    env_model = os.getenv("OPENROUTER_MODEL", "").strip()
    cands: list[str] = []
    if env_model:
        cands.append(env_model)
    # Liste de secours (susceptible de changer côté OpenRouter)
    cands.extend([
        "openchat/openchat-7b:free",
        "mistralai/mistral-7b-instruct:free",
        "qwen/qwen-2-7b-instruct:free",
        "google/gemma-7b-it:free",
    ])
    # Déduplication en conservant l'ordre
    seen = set()
    out = []
    for m in cands:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out

def _chat_complete(messages: list[dict], max_tokens: int, temperature: float) -> str | None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    for model in _model_candidates():
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"⚠️ Erreur IA ({model}): {e}")
            continue
    return None

def generate_keywords(cv_text: str, job_field: str, max_terms: int = 20) -> list[str]:
    """Génère une liste de mots-clés (FR+EN) à partir du CV et du domaine ciblé.
    Retourne une liste dédupliquée et normalisée.
    """
    prompt = f"""
Tu es un moteur de requêtes d'emploi. A partir de ce CV et du domaine "{job_field}",
produis une liste plate (séparée par des virgules) de mots-clés de recherche pertinents (FR + EN),
incluant intitulés de postes, compétences, technologies, synonymes.
Max {max_terms} termes. Pas de phrases. Exemple de format: "product manager, chef de produit, agile, roadmap, jira, ...".

CV:
---
{(cv_text or '')[:4000]}
---
"""
    try:
        text = _chat_complete(
            [
                {"role": "system", "content": "Tu produis uniquement une liste de mots-clés séparés par des virgules."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.2,
        ) or ""
        # Parse en liste
        parts = re.split(r"[,\n;]+", text)
        terms = []
        seen = set()
        for p in parts:
            t = p.strip()
            if not t:
                continue
            k = t.lower()
            if k not in seen:
                seen.add(k)
                terms.append(t)
            if len(terms) >= max_terms:
                break
        return terms
    except Exception as e:
        print(f"⚠️ Erreur IA (generate_keywords): {e}")
        # Fallback: renvoie le domaine découpé + quelques basiques
        fallback = [job_field] if job_field else []
        fallback += ["cv", "resume", "hiring"]
        return list(dict.fromkeys(fallback))

def generate_custom_cv_content(job_description, original_cv_text, job_title="ce poste", company_name="votre entreprise"):
    print("🧠 [IA] Adaptation du CV pour l'offre...")

    prompt = f"""Tu es un assistant automatique de formatage de CV.

Voici le CV original du candidat :
---
{original_cv_text}
---

Titre de l'offre ciblée : {job_title}
Entreprise ciblée : {company_name}

TA MISSION STRICTE ET UNIQUE :
1. Ne modifie ABSOLUMENT RIEN au contenu original du CV (garde toutes les expériences, compétences, dates à l'identique).
2. Ajoute simplement cette phrase exacte tout en haut du CV, avant même le titre :
"J'aimerais postuler au poste de {job_title} au sein de {company_name}."
3. Retourne UNIQUEMENT le texte complet du CV mis à jour. Aucun commentaire supplémentaire, aucune salutation.
"""
    try:
        text = _chat_complete(
            [
                {"role": "system", "content": "Tu es un outil automatique de modification de CV. Tu retournes uniquement le CV final sans aucun dialogue."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.1,
        )
        return text or original_cv_text
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
        text = _chat_complete(
            [
                {"role": "system", "content": "Tu rédiges des lettres de motivation en français, professionnelles et personnalisées."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.6,
        )
        return text or ""
    except Exception as e:
        print(f"❌ Erreur IA (generate_cover_letter) : {e}")
        return ""

def extract_email_from_text(text):
    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return emails[0] if emails else None

def propose_answer_from_cv(question_text: str, cv_text: str | None, prefs: dict | None = None) -> str | None:
    """Propose une réponse courte à une question ATS à partir du CV et des préférences.
    Retourne une chaîne (<=200 char) ou None si non déterminable.
    """
    prefs = prefs or {}
    ql = (question_text or "").lower()
    # Heuristiques rapides
    if "visa" in ql or "work authorization" in ql or "permit" in ql:
        if prefs.get("visa_status"):
            return prefs["visa_status"]
    if any(k in ql for k in ["salary", "compensation", "rémunération", "salaire"]):
        if prefs.get("salary_expectation"):
            return prefs["salary_expectation"]
    if any(k in ql for k in ["notice", "availability", "préavis", "disponibil"]):
        if prefs.get("availability_delay"):
            return prefs["availability_delay"]

    try:
        prompt = f"""
Tu es un assistant pour candidatures en ligne. Donne UNE réponse brève (<= 120 caractères) à la question ci-dessous
en t'appuyant uniquement sur le CV et ces préférences. Si l'information n'est pas disponible, réponds "N/A".

Question: {question_text}

Préférences (JSON): {json.dumps(prefs, ensure_ascii=False)}

CV:
---
{(cv_text or '')[:3000]}
---
"""
        ans = _chat_complete(
            [
                {"role": "system", "content": "Tu donnes UNE réponse factuelle courte (<=120 char). Pas d'explication."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=60,
            temperature=0.1,
        ) or ""
        if not ans or ans.lower().startswith("n/a"):
            return None
        return ans[:200]
    except Exception as e:
        print(f"⚠️ Erreur IA (propose_answer_from_cv): {e}")
        return None
