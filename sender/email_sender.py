import os
import base64
import resend
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

def send_application_email(to_email, job_title, company_name, cover_letter, cv_pdf_path, candidate_name, resend_key):
    if not resend_key:
        print("⚠️ Aucune clé API Resend configurée.")
        return False
    resend.api_key = resend_key

    if not to_email:
        print("⚠️ Pas d'email destinataire trouvé pour ce poste.")
        return False

    try:
        subject = f"Candidature : {job_title} — {candidate_name}"

        body_text = f"""{cover_letter}

--
{candidate_name}
{SENDER_EMAIL}
"""
        # Construction HTML propre
        body_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333; max-width: 700px;">
            <p>{cover_letter.replace(chr(10), '<br>')}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #888; font-size: 12px;">{candidate_name}<br>{SENDER_EMAIL}</p>
        </div>
        """

        params: resend.Emails.SendParams = {
            "from": f"{candidate_name} <{SENDER_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "text": body_text,
            "html": body_html,
        }

        # Ajouter le CV en pièce jointe si disponible
        if cv_pdf_path and os.path.exists(cv_pdf_path):
            with open(cv_pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
            pdf_name = os.path.basename(cv_pdf_path)
            params["attachments"] = [{"filename": pdf_name, "content": pdf_b64}]

        email = resend.Emails.send(params)
        print(f"📧 Email envoyé via Resend à {to_email} pour '{job_title}' chez {company_name} (id: {email.get('id', '?')})")
        return True

    except Exception as e:
        print(f"❌ Erreur Resend à {to_email} : {e}")
        return False
