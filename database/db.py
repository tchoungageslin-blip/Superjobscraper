import os
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
# Si on utilise SQLAlchemy avec Postgres, il faut s'assurer que le préfixe est postgresql://
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Définition de la table, elle sera créée automatiquement si elle n'existe pas !
class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    platform = Column(String)
    title = Column(String)
    company = Column(String)
    link = Column(String)
    status = Column(String, default="FOUND") # FOUND, AI_PROCESSING, APPLIED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    print("☁️ Connexion directe à PostgreSQL (Supabase)...")
    try:
        # Crée les tables magiquement dans Supabase
        Base.metadata.create_all(bind=engine)
        print("✅ Table 'jobs' synchronisée et prête dans Supabase.")
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données : {e}")

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


