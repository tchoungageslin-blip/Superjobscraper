#!/usr/bin/env bash
# Script de build pour Render
set -e

echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

echo "🌐 Installation des navigateurs Playwright (Chromium)..."
python -m playwright install chromium
python -m playwright install-deps chromium

echo "✅ Build terminé."
