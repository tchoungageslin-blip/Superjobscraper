import os
from playwright.sync_api import sync_playwright

def login_and_save_session():
    print("=" * 60)
    print("🚀 OUVERTURE DU NAVIGATEUR POUR CONNEXION LINKEDIN")
    print("=" * 60)
    print("👉 Un navigateur va s'ouvrir. Connectez-vous normalement à votre compte.")
    print("👉 (Vous pouvez utiliser 'Continuer avec Google', résoudre les captchas, etc.)")
    print("⏳ Vous avez 2 minutes pour vous connecter.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Mode visible
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.goto("https://www.linkedin.com/login")
        
        try:
            # On attend que l'utilisateur atterrisse sur la page d'accueil (feed)
            page.wait_for_url("https://www.linkedin.com/feed/**", timeout=120000)
            print("\n✅ Connexion réussie détectée !")
            
            # Sauvegarde des cookies de session
            context.storage_state(path="linkedin_state.json")
            print("💾 Session sauvegardée avec succès dans 'linkedin_state.json' !")
            print("🤖 Le scraper utilisera désormais ce fichier pour contourner l'écran de connexion.")
        except Exception as e:
            print("\n❌ Temps écoulé ou erreur. Assurez-vous d'être bien connecté et d'atterrir sur l'accueil (feed).")
        
        browser.close()

if __name__ == "__main__":
    login_and_save_session()
