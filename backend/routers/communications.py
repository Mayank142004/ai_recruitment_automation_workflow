"""
AI Recruitment Automation — Communication Routes

POST /api/notify/{id} — Manually trigger notifications for a candidate
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import Candidate, get_db
from services.gmail_service import (
    send_shortlist_email,
    send_rejection_email,
    send_manual_review_notification,
)
from services.whatsapp_service import send_shortlist_whatsapp
from services.sheets_service import append_candidate_to_sheet

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/notify/{candidate_id}")
async def notify_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """
    Manually trigger notifications (email + WhatsApp) for a candidate.

    Sends appropriate notifications based on the candidate's current status.
    """
    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    results = {
        "candidate_id": candidate_id,
        "status": candidate.status,
        "email_sent": False,
        "whatsapp_sent": False,
        "sheets_synced": False,
    }

    role_display = (candidate.role_applied or "").replace("_", " ").title()

    # ── Send email based on status ───────────────────────────────────────
    if candidate.status == "shortlisted":
        results["email_sent"] = send_shortlist_email(
            to=candidate.email,
            name=candidate.name,
            role=role_display,
        )
        if candidate.phone:
            results["whatsapp_sent"] = send_shortlist_whatsapp(
                phone=candidate.phone,
                name=candidate.name,
                role=role_display,
            )

    elif candidate.status == "rejected":
        results["email_sent"] = send_rejection_email(
            to=candidate.email,
            name=candidate.name,
            role=role_display,
        )

    elif candidate.status == "manual_review":
        hr_email = os.getenv("HR_EMAIL", "")
        if hr_email:
            results["email_sent"] = send_manual_review_notification(
                hr_email=hr_email,
                candidate=candidate.to_dict(),
            )

    # ── Sync to Google Sheets ────────────────────────────────────────────
    if not candidate.sheets_synced:
        results["sheets_synced"] = append_candidate_to_sheet(candidate.to_dict())

    # ── Update notification flags in DB ──────────────────────────────────
    if results["email_sent"]:
        candidate.email_sent = True
    if results["whatsapp_sent"]:
        candidate.whatsapp_sent = True
    if results["sheets_synced"]:
        candidate.sheets_synced = True

    db.commit()

    return results
