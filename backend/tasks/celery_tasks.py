"""
AI Recruitment Automation — Celery Async Task Definitions

Wraps heavy operations in Celery tasks for background processing.
Requires Redis as the message broker.

Usage:
  celery -A tasks.celery_tasks worker --loglevel=info
"""

import logging
import os
import time

from celery import Celery

logger = logging.getLogger(__name__)

# ── Celery App Configuration ────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "recruitment_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Rate limit scoring tasks to 25/minute
    task_default_rate_limit="25/m",
)


@celery_app.task(bind=True, name="process_resume_async", max_retries=3)
def process_resume_async(self, candidate_id: str, file_path: str):
    """
    Async task: Parse resume → Score → Filter → Save to DB.

    This runs the full processing pipeline in the background so
    the API can return immediately.
    """
    try:
        from models.database import SessionLocal, Candidate
        from services.parser import parse_resume
        from services.scorer import score_candidate
        from services.filter import filter_candidate, get_job_description

        db = SessionLocal()

        try:
            candidate = db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()

            if not candidate:
                logger.error(f"Candidate {candidate_id} not found")
                return {"status": "error", "message": "Candidate not found"}

            # Parse resume
            parsed = parse_resume(file_path)

            # Update parsed data
            candidate.resume_text = parsed["raw_text"]
            candidate.skills = parsed["skills"]
            candidate.experience_years = parsed["experience_years"]
            candidate.education_degree = parsed["education"].get("degree", "")
            candidate.education_inst = parsed["education"].get("institution", "")

            contact = parsed.get("contact", {})
            if contact.get("github_url"):
                candidate.github_url = contact["github_url"]
            if contact.get("linkedin_url"):
                candidate.linkedin_url = contact["linkedin_url"]

            # Score with Groq
            job_description = get_job_description(candidate.role_applied)
            score_data = score_candidate(
                parsed["raw_text"], job_description, candidate.role_applied
            )

            candidate.match_score = score_data.get("match_score", 0)
            candidate.ai_summary = score_data.get("candidate_summary", "")
            candidate.matched_skills = score_data.get("matched_skills", [])
            candidate.missing_skills = score_data.get("missing_skills", [])
            candidate.experience_fit = score_data.get("experience_fit", "")
            candidate.education_fit = score_data.get("education_fit", "")
            candidate.red_flags = score_data.get("red_flags", [])
            candidate.recommendation = score_data.get("recommendation", "")

            # Filter
            filter_result = filter_candidate(
                score_data=score_data,
                parsed_data={
                    "skills": parsed["skills"],
                    "experience_years": parsed["experience_years"],
                    "education": parsed["education"],
                },
                role=candidate.role_applied,
            )

            candidate.status = filter_result["status"]
            candidate.filter_reason = filter_result["reason"]
            candidate.shortlist_priority = filter_result.get("shortlist_priority", 5)

            db.commit()

            logger.info(
                f"Resume processed for {candidate_id}: "
                f"score={candidate.match_score}, status={candidate.status}"
            )

            return {
                "status": "success",
                "candidate_id": candidate_id,
                "match_score": candidate.match_score,
                "final_status": candidate.status,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"process_resume_async failed: {e}", exc_info=True)
        self.retry(countdown=5, exc=e)


@celery_app.task(bind=True, name="send_notifications_async", max_retries=2)
def send_notifications_async(self, candidate_id: str):
    """
    Async task: Send email + WhatsApp notifications based on candidate status.
    """
    try:
        from models.database import SessionLocal, Candidate
        from services.gmail_service import (
            send_shortlist_email,
            send_rejection_email,
            send_manual_review_notification,
        )
        from services.whatsapp_service import send_shortlist_whatsapp

        db = SessionLocal()

        try:
            candidate = db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()

            if not candidate:
                return {"status": "error", "message": "Candidate not found"}

            role_display = (candidate.role_applied or "").replace("_", " ").title()
            email_sent = False
            whatsapp_sent = False

            if candidate.status == "shortlisted":
                email_sent = send_shortlist_email(
                    candidate.email, candidate.name, role_display
                )
                if candidate.phone:
                    whatsapp_sent = send_shortlist_whatsapp(
                        candidate.phone, candidate.name, role_display
                    )
            elif candidate.status == "rejected":
                email_sent = send_rejection_email(
                    candidate.email, candidate.name, role_display
                )
            elif candidate.status == "manual_review":
                hr_email = os.getenv("HR_EMAIL", "")
                if hr_email:
                    email_sent = send_manual_review_notification(
                        hr_email, candidate.to_dict()
                    )

            candidate.email_sent = email_sent
            candidate.whatsapp_sent = whatsapp_sent
            db.commit()

            return {
                "status": "success",
                "email_sent": email_sent,
                "whatsapp_sent": whatsapp_sent,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"send_notifications_async failed: {e}")
        self.retry(countdown=10, exc=e)


@celery_app.task(bind=True, name="sync_to_sheets_async", max_retries=2)
def sync_to_sheets_async(self, candidate_id: str):
    """
    Async task: Sync candidate data to Google Sheets.
    """
    try:
        from models.database import SessionLocal, Candidate
        from services.sheets_service import append_candidate_to_sheet

        db = SessionLocal()

        try:
            candidate = db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()

            if not candidate:
                return {"status": "error", "message": "Candidate not found"}

            synced = append_candidate_to_sheet(candidate.to_dict())
            candidate.sheets_synced = synced
            db.commit()

            return {"status": "success", "sheets_synced": synced}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"sync_to_sheets_async failed: {e}")
        self.retry(countdown=10, exc=e)
