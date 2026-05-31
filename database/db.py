import os
import uuid
from sqlalchemy import create_engine, Column, String, DateTime, Text, LargeBinary, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    platform = Column(String)
    title = Column(String)
    company = Column(String)
    link = Column(String)
    status = Column(String, default="FOUND")
    created_at = Column(DateTime, default=datetime.utcnow)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    email = Column(String)
    job_field = Column(String)
    keywords = Column(String)   # Mots-clés séparés par des virgules
    location = Column(String, default="France")
    cv_text = Column(Text)
    cv_pdf = Column(LargeBinary)
    cv_filename = Column(String)
    cv_mime = Column(String)
    # Préférences ATS
    visa_status = Column(String)
    mobility = Column(String)
    salary_expectation = Column(String)
    availability_delay = Column(String)
    linkedin_email = Column(String)
    linkedin_cookie = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    print("☁️ Connexion directe à PostgreSQL (Supabase)...")
    try:
        Base.metadata.create_all(bind=engine)
        _migrate_profiles()
        print("✅ Tables 'jobs' et 'profiles' synchronisées dans Supabase.")
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données : {e}")

def _migrate_profiles():
    """Ajoute les colonnes linkedin_*/cv_* et préférences ATS si elles n'existent pas."""
    db = SessionLocal()
    try:
        for col in [
            "linkedin_email", "linkedin_cookie", "cv_filename", "cv_mime",
            "visa_status", "mobility", "salary_expectation", "availability_delay",
        ]:
            db.execute(text(f"ALTER TABLE profiles ADD COLUMN IF NOT EXISTS {col} VARCHAR"))
        # Colonne binaire pour le CV
        db.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cv_pdf BYTEA"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def load_profile():
    db = SessionLocal()
    try:
        profile = db.query(Profile).order_by(Profile.created_at.desc()).first()
        return profile
    except Exception as e:
        print(f"⚠️ Erreur lecture profil : {e}")
        return None
    finally:
        db.close()

def save_profile(name, email, job_field, keywords, location, cv_text, linkedin_email="", linkedin_cookie=""):
    db = SessionLocal()
    try:
        existing = db.query(Profile).first()
        if existing:
            existing.name = name
            existing.email = email
            existing.job_field = job_field
            existing.keywords = keywords
            existing.location = location
            existing.cv_text = cv_text
            existing.linkedin_email = linkedin_email
            existing.linkedin_cookie = linkedin_cookie
            existing.updated_at = datetime.utcnow()
        else:
            profile = Profile(
                id=str(uuid.uuid4()),
                name=name, email=email, job_field=job_field,
                keywords=keywords, location=location, cv_text=cv_text,
                linkedin_email=linkedin_email, linkedin_cookie=linkedin_cookie
            )
            db.add(profile)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"⚠️ Erreur sauvegarde profil : {e}")
        return False
    finally:
        db.close()

def save_cv_file(file_bytes: bytes, filename: str, mime: str) -> bool:
    """Enregistre le fichier CV original (PDF/DOCX) dans la ligne unique du profil."""
    db = SessionLocal()
    try:
        existing = db.query(Profile).first()
        if not existing:
            existing = Profile(id=str(uuid.uuid4()), name="", email="", job_field="", keywords="", location="France", cv_text="")
            db.add(existing)
            db.flush()
        existing.cv_pdf = file_bytes
        existing.cv_filename = filename
        existing.cv_mime = mime
        existing.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"⚠️ Erreur sauvegarde CV (binaire) : {e}")
        return False
    finally:
        db.close()

def export_cv_to_temp(path: str | None = None) -> str | None:
    """Extrait le CV binaire vers un fichier temporaire; retourne le chemin ou None."""
    db = SessionLocal()
    try:
        profile = db.query(Profile).first()
        if not profile or not profile.cv_pdf:
            return None
        filename = profile.cv_filename or "cv.pdf"
        if path is None:
            base = os.path.join(os.getcwd(), "data", "uploads")
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, filename)
        with open(path, "wb") as f:
            f.write(profile.cv_pdf)
        return path
    except Exception as e:
        print(f"⚠️ Erreur export CV : {e}")
        return None
    finally:
        db.close()

def is_job_processed(job_id):
    db = SessionLocal()
    exists = db.query(Job).filter(Job.id == job_id).first() is not None
    db.close()
    return exists

def add_job(job_id, platform, title, company, link):
    if is_job_processed(job_id):
        return
        
    db = SessionLocal()
    new_job = Job(id=job_id, platform=platform, title=title, company=company, link=link)
    db.add(new_job)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Erreur DB (add_job) : {e}")
    finally:
        db.close()

def update_job_status(job_id, new_status):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = new_status
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"⚠️ Erreur DB (update_job_status) : {e}")
    db.close()


