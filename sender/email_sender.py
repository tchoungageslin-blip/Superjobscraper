import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")

def send_application_email(to_email, job_title, company_name, cover_letter, cv_pdf_path, candidate_name):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️ Email non configuré dans .env (SENDER_EMAIL / SENDER_PASSWORD)")
        return False
    if not to_email:
        print("⚠️ Pas d'email destinataire trouvé pour ce poste.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{candidate_name} <{SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = f"Candidature : {job_title} — {candidate_name}"

        # Corps de l'email = lettre de motivation
        body = f"""{cover_letter}

--
{candidate_name}
{SENDER_EMAIL}
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Pièce jointe : CV PDF
        if cv_pdf_path and os.path.exists(cv_pdf_path):
            with open(cv_pdf_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_name = os.path.basename(cv_pdf_path)
                pdf_attachment.add_header("Content-Disposition", "attachment", filename=pdf_name)
                msg.attach(pdf_attachment)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        print(f"📧 Email envoyé à {to_email} pour '{job_title}' chez {company_name}")
        return True

    except Exception as e:
        print(f"❌ Erreur envoi email à {to_email} : {e}")
        return False
