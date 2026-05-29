"""
AI Recruitment Automation — Database Models & Session Management

Uses SQLAlchemy ORM with SQLite (dev) or PostgreSQL (prod via Supabase free tier).
"""

import os
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, JSON, String, Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recruitment.db")

# Handle SQLite-specific args
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Candidate(Base):
    """Candidate application record with all parsed/scored data."""

    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String, unique=True, index=True)  # UUID
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    city = Column(String(50))
    college = Column(String(150))
    role_applied = Column(String(50))

    # Parsed resume data
    skills = Column(JSON)  # list of strings
    experience_years = Column(Float)
    education_degree = Column(String(50))
    education_inst = Column(String(150))

    # GitHub profile
    github_url = Column(String(200))
    github_score = Column(Integer)
    linkedin_url = Column(String(200))

    # Resume file
    resume_path = Column(String(300))
    resume_text = Column(Text)  # Extracted raw text for re-scoring

    # Application metadata
    application_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), index=True)  # shortlisted / rejected / manual_review
    filter_reason = Column(Text)  # Why the filter made this decision

    # AI scoring
    match_score = Column(Integer)
    ai_summary = Column(Text)
    matched_skills = Column(JSON)  # list of matched skills
    missing_skills = Column(JSON)  # list of missing skills
    experience_fit = Column(String(10))  # yes / no / partial
    education_fit = Column(String(10))  # yes / no / partial
    red_flags = Column(JSON)
    recommendation = Column(String(20))  # shortlist / reject / manual_review

    # Multi-role scoring
    best_role = Column(String(50))
    all_role_scores = Column(JSON)  # {role: score}
    role_suggestion = Column(Text)

    # Interview tracking
    interview_round = Column(Integer, default=0)
    interview_date = Column(DateTime)
    shortlist_priority = Column(Integer)  # 1-5

    # Spam & duplicate flags
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer)
    is_spam = Column(Boolean, default=False)
    spam_reason = Column(String(200))

    # Named entities from NLP
    named_entities = Column(JSON)
    language = Column(String(10))

    # Manual recruiter notes
    notes = Column(Text)

    # Notification tracking
    email_sent = Column(Boolean, default=False)
    whatsapp_sent = Column(Boolean, default=False)
    sheets_synced = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert candidate record to dictionary for API responses."""
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "city": self.city,
            "college": self.college,
            "role_applied": self.role_applied,
            "skills": self.skills or [],
            "experience_years": self.experience_years,
            "education_degree": self.education_degree,
            "education_inst": self.education_inst,
            "github_url": self.github_url,
            "github_score": self.github_score,
            "linkedin_url": self.linkedin_url,
            "resume_path": self.resume_path,
            "application_date": self.application_date.isoformat() if self.application_date else None,
            "status": self.status,
            "filter_reason": self.filter_reason,
            "match_score": self.match_score,
            "ai_summary": self.ai_summary,
            "matched_skills": self.matched_skills or [],
            "missing_skills": self.missing_skills or [],
            "experience_fit": self.experience_fit,
            "education_fit": self.education_fit,
            "red_flags": self.red_flags or [],
            "recommendation": self.recommendation,
            "best_role": self.best_role,
            "all_role_scores": self.all_role_scores,
            "role_suggestion": self.role_suggestion,
            "interview_round": self.interview_round,
            "interview_date": self.interview_date.isoformat() if self.interview_date else None,
            "shortlist_priority": self.shortlist_priority,
            "is_duplicate": self.is_duplicate,
            "is_spam": self.is_spam,
            "spam_reason": self.spam_reason,
            "named_entities": self.named_entities,
            "language": self.language,
            "notes": self.notes,
            "email_sent": self.email_sent,
            "whatsapp_sent": self.whatsapp_sent,
            "sheets_synced": self.sheets_synced,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
