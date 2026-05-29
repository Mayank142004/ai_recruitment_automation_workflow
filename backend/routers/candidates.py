"""
AI Recruitment Automation — Candidate Routes

POST /api/submit       — Submit new candidate application (full pipeline)
GET  /api/candidates   — List all candidates with filters
GET  /api/candidates/{id} — Get single candidate detail
PATCH /api/candidates/{id}/status — Manual status override
"""

import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from models.database import Candidate, get_db
from services.parser import parse_resume, extract_skills, extract_text_from_pdf
from services.scorer import score_candidate
from services.filter import filter_candidate, get_job_description, get_role_config
from services.spam_detector import is_spam
from services.duplicate_checker import check_duplicate
from services.github_scorer import score_github_profile
from services.gmail_service import (
    send_shortlist_email,
    send_rejection_email,
    send_manual_review_notification,
)
from services.whatsapp_service import send_shortlist_whatsapp
from services.sheets_service import append_candidate_to_sheet
from utils.helpers import save_uploaded_file, generate_candidate_id, format_phone_number

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/submit")
async def submit_candidate(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    city: str = Form(""),
    college: str = Form(""),
    role_applied: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Submit a new candidate application.

    Full pipeline:
      1. Save uploaded PDF
      2. Spam detection
      3. Duplicate check
      4. Parse resume (text, skills, experience, education, contact)
      5. NLP enrichment
      6. GitHub profile scoring (if URL found)
      7. AI scoring via Groq LLM
      8. YAML filter rules → shortlisted / rejected / manual_review
      9. Save to database
      10. Send notifications (email + WhatsApp)
      11. Sync to Google Sheets
    """
    candidate_id = generate_candidate_id()
    phone = format_phone_number(phone)

    try:
        # ── Step 1: Save uploaded PDF ────────────────────────────────────
        if not resume.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

        file_content = await resume.read()
        file_path = save_uploaded_file(file_content, resume.filename, candidate_id)

        # ── Step 2: Parse resume ─────────────────────────────────────────
        parsed = parse_resume(file_path)
        resume_text = parsed["raw_text"]

        # ── Step 3: Spam detection ───────────────────────────────────────
        spam_result = is_spam(resume_text, parsed)
        if spam_result["is_spam"]:
            # Save spam record to DB for tracking
            candidate = Candidate(
                candidate_id=candidate_id,
                name=name,
                email=email.lower().strip(),
                phone=phone,
                city=city,
                college=college,
                role_applied=role_applied,
                resume_path=file_path,
                resume_text=resume_text,
                status="rejected",
                is_spam=True,
                spam_reason=spam_result["reason"],
                filter_reason=f"Spam detected: {spam_result['reason']}",
                application_date=datetime.utcnow(),
            )
            db.add(candidate)
            db.commit()

            return {
                "candidate_id": candidate_id,
                "status": "rejected",
                "message": f"Application flagged: {spam_result['reason']}",
                "match_score": 0,
                "recommendation": "reject",
            }

        # ── Step 4: Duplicate check ──────────────────────────────────────
        dup_result = check_duplicate(name, phone, email, db)
        if dup_result["is_duplicate"]:
            return {
                "candidate_id": candidate_id,
                "status": "duplicate",
                "message": (
                    f"Duplicate application detected "
                    f"(similarity: {dup_result['similarity_score']:.0f}%)"
                ),
                "match_score": 0,
                "recommendation": "reject",
            }

        # ── Step 5: Extract contact info from resume ─────────────────────
        contact = parsed.get("contact", {})
        github_url = contact.get("github_url", "")
        linkedin_url = contact.get("linkedin_url", "")

        # ── Step 6: GitHub profile scoring ───────────────────────────────
        github_score = 0
        if github_url:
            gh_result = score_github_profile(github_url)
            github_score = gh_result.get("score", 0)

        # ── Step 7: AI scoring via Groq LLM ─────────────────────────────
        job_description = get_job_description(role_applied)
        if not job_description:
            job_description = f"Looking for a {role_applied.replace('_', ' ')} with relevant skills and experience."

        score_data = score_candidate(resume_text, job_description, role_applied)

        # ── Step 8: Apply YAML filter rules ──────────────────────────────
        filter_result = filter_candidate(
            score_data=score_data,
            parsed_data={
                "skills": parsed["skills"],
                "experience_years": parsed["experience_years"],
                "education": parsed["education"],
            },
            role=role_applied,
        )

        status = filter_result["status"]

        # ── Step 9: Save to database ─────────────────────────────────────
        candidate = Candidate(
            candidate_id=candidate_id,
            name=name,
            email=email.lower().strip(),
            phone=phone,
            city=city,
            college=college,
            role_applied=role_applied,
            skills=parsed["skills"],
            experience_years=parsed["experience_years"],
            education_degree=parsed["education"].get("degree", ""),
            education_inst=parsed["education"].get("institution", ""),
            github_url=github_url,
            github_score=github_score,
            linkedin_url=linkedin_url,
            resume_path=file_path,
            resume_text=resume_text,
            application_date=datetime.utcnow(),
            status=status,
            filter_reason=filter_result["reason"],
            match_score=score_data.get("match_score", 0),
            ai_summary=score_data.get("candidate_summary", ""),
            matched_skills=score_data.get("matched_skills", []),
            missing_skills=score_data.get("missing_skills", []),
            experience_fit=score_data.get("experience_fit", ""),
            education_fit=score_data.get("education_fit", ""),
            red_flags=score_data.get("red_flags", []),
            recommendation=score_data.get("recommendation", ""),
            shortlist_priority=filter_result.get("shortlist_priority", 5),
            is_duplicate=False,
            is_spam=False,
        )

        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        # ── Step 10: Send notifications ──────────────────────────────────
        email_sent = False
        whatsapp_sent = False

        if status == "shortlisted":
            email_sent = send_shortlist_email(
                to=email,
                name=name,
                role=role_applied.replace("_", " ").title(),
            )
            if phone:
                whatsapp_sent = send_shortlist_whatsapp(
                    phone=phone,
                    name=name,
                    role=role_applied.replace("_", " ").title(),
                )
        elif status == "rejected":
            email_sent = send_rejection_email(
                to=email,
                name=name,
                role=role_applied.replace("_", " ").title(),
            )
        elif status == "manual_review":
            hr_email = os.getenv("HR_EMAIL", "")
            if hr_email:
                send_manual_review_notification(hr_email, candidate.to_dict())

        # Update notification flags
        candidate.email_sent = email_sent
        candidate.whatsapp_sent = whatsapp_sent
        db.commit()

        # ── Step 11: Sync to Google Sheets ───────────────────────────────
        sheets_synced = append_candidate_to_sheet(candidate.to_dict())
        candidate.sheets_synced = sheets_synced
        db.commit()

        return {
            "candidate_id": candidate_id,
            "status": status,
            "message": f"Application {status}. Thank you for applying!",
            "match_score": score_data.get("match_score", 0),
            "recommendation": score_data.get("recommendation", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Submission failed for {name}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/candidates")
async def list_candidates(
    status: str = None,
    role: str = None,
    min_score: int = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List all candidates with optional filters.

    Query params:
      - status: Filter by status (shortlisted, rejected, manual_review)
      - role: Filter by role applied
      - min_score: Minimum match score
      - limit: Max results (default: 100)
      - offset: Pagination offset
    """
    query = db.query(Candidate)

    if status:
        query = query.filter(Candidate.status == status)
    if role:
        query = query.filter(Candidate.role_applied == role)
    if min_score is not None:
        query = query.filter(Candidate.match_score >= min_score)

    total = query.count()
    candidates = (
        query.order_by(Candidate.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "candidates": [c.to_dict() for c in candidates],
    }


@router.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """Get single candidate detail by candidate_id."""
    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return candidate.to_dict()


@router.patch("/candidates/{candidate_id}/status")
async def update_candidate_status(
    candidate_id: str,
    status: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(get_db),
):
    """
    Manual status override by recruiter.

    Args:
        candidate_id: Candidate's unique ID.
        status: New status (shortlisted / rejected / manual_review).
        notes: Optional recruiter notes.
    """
    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    valid_statuses = {"shortlisted", "rejected", "manual_review"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    old_status = candidate.status
    candidate.status = status
    if notes:
        candidate.notes = (candidate.notes or "") + f"\n[{datetime.utcnow().isoformat()}] {notes}"

    candidate.updated_at = datetime.utcnow()
    db.commit()

    return {
        "candidate_id": candidate_id,
        "old_status": old_status,
        "new_status": status,
        "message": f"Status updated from '{old_status}' to '{status}'",
    }
