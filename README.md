# Super Job Scrapper

Machine autonome de recherche et candidature automatique 24h/24.

## Architecture

```
main.py               ← Moteur principal (boucle infinie 24/7)
scrapers/linkedin.py  ← Scraper LinkedIn furtif (Playwright)
ai/generator.py       ← Adaptation CV + lettre (OpenRouter IA)
ai/cv_builder.py      ← Génération PDF (ReportLab)
sender/email_sender.py← Envoi email avec CV en pièce jointe
database/db.py        ← Mémoire Supabase (PostgreSQL)
web-dashboard/        ← Dashboard Next.js (déployer sur Vercel)
config/cv_base.txt    ← VOTRE CV DE BASE (à remplir)
```

## Configuration obligatoire avant lancement

Éditez le fichier `.env` à la racine :

```env
OPENROUTER_API_KEY=sk-or-v1-...
DATABASE_URL=postgresql://...supabase.com.../postgres
CANDIDATE_NAME="Prénom Nom"
SENDER_EMAIL=votre@gmail.com
SENDER_PASSWORD=mot_de_passe_app_gmail
TARGET_COUNTRY=France
```

> **Gmail** : utilisez un "Mot de passe d'application" (pas votre vrai mot de passe).
> Activez-le ici : myaccount.google.com > Sécurité > Mots de passe des applications

Puis remplissez `config/cv_base.txt` avec votre vrai CV.

## Lancer localement

```bash
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

## Déployer le Scraper sur Render (24/7)

1. Créez un compte sur [render.com](https://render.com)
2. "New > Background Worker" > connectez votre repo GitHub
3. Render détecte `render.yaml` automatiquement
4. Ajoutez les variables d'environnement dans le dashboard Render :
   - `DATABASE_URL`
   - `OPENROUTER_API_KEY`
   - `CANDIDATE_NAME`
   - `SENDER_EMAIL`
   - `SENDER_PASSWORD`
5. Cliquez "Deploy" — le scraper tournera 24/7

## Déployer le Dashboard sur Vercel

1. Allez dans le dossier `web-dashboard/`
2. Créez un compte sur [vercel.com](https://vercel.com)
3. "New Project" > importez le dossier `web-dashboard`
4. Ajoutez ces variables d'environnement dans Vercel :
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://lffeiajzjdhsjdcsialt.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = votre clé anon (Supabase > Settings > API)
5. Déployez — votre dashboard sera accessible en ligne

## Supabase — Activer les permissions de lecture publique

Dans votre projet Supabase :
1. Table Editor > `jobs` > "RLS" (Row Level Security)
2. Ajoutez une politique : `SELECT` autorisé pour `anon` (lecture publique pour le dashboard)

## Tester le pipeline

```bash
python test_pipeline.py
```

## Flux de traitement

```
Keyword (ex: "SEO Manager")
  → LinkedIn Scraper (Playwright furtif)
    → Offre détectée + description extraite
      → Vérification doublon (Supabase)
        → IA adapte le CV (OpenRouter)
          → PDF généré (ReportLab)
            → Lettre de motivation générée (IA)
              → Email envoyé au recruteur
                → Statut mis à jour (Supabase)
                  → Visible sur le Dashboard Vercel en temps réel
```
