"""
AI Recruitment Automation — Scoring & Analytics Routes

POST /api/score/{id}  — Re-score a specific candidate
GET  /api/analytics   — Dashboard statistics
GET  /api/roles       — List available roles from config.yaml
GET  /api/task/{task_id} — Check async task status
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import Candidate, get_db
from services.scorer import score_candidate
from services.filter import (
    filter_candidate,
    get_all_roles,
    get_job_description,
    get_role_names,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/score/{candidate_id}")
async def rescore_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """
    Re-score a specific candidate using the Groq LLM.

    Useful after updating job descriptions or when the original scoring
    may have had issues.
    """
    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if not candidate.resume_text:
        raise HTTPException(
            status_code=400,
            detail="No resume text available for re-scoring",
        )

    # Get job description for the role
    job_description = get_job_description(candidate.role_applied)
    if not job_description:
        job_description = f"Looking for a {candidate.role_applied.replace('_', ' ')}."

    # Re-score
    score_data = score_candidate(
        resume_text=candidate.resume_text,
        job_description=job_description,
        role=candidate.role_applied,
    )

    # Re-filter
    filter_result = filter_candidate(
        score_data=score_data,
        parsed_data={
            "skills": candidate.skills or [],
            "experience_years": candidate.experience_years or 0,
            "education": {
                "degree": candidate.education_degree or "",
                "institution": candidate.education_inst or "",
            },
        },
        role=candidate.role_applied,
    )

    # Update candidate record
    candidate.match_score = score_data.get("match_score", 0)
    candidate.ai_summary = score_data.get("candidate_summary", "")
    candidate.matched_skills = score_data.get("matched_skills", [])
    candidate.missing_skills = score_data.get("missing_skills", [])
    candidate.experience_fit = score_data.get("experience_fit", "")
    candidate.education_fit = score_data.get("education_fit", "")
    candidate.red_flags = score_data.get("red_flags", [])
    candidate.recommendation = score_data.get("recommendation", "")
    candidate.status = filter_result["status"]
    candidate.filter_reason = filter_result["reason"]
    candidate.shortlist_priority = filter_result.get("shortlist_priority", 5)

    db.commit()

    return {
        "candidate_id": candidate_id,
        "new_score": score_data.get("match_score", 0),
        "new_status": filter_result["status"],
        "recommendation": score_data.get("recommendation", ""),
        "message": "Candidate re-scored successfully",
    }


@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """
    Dashboard analytics data.

    Returns aggregate statistics for the recruiter dashboard.
    """
    total = db.query(Candidate).count()
    shortlisted = db.query(Candidate).filter(Candidate.status == "shortlisted").count()
    rejected = db.query(Candidate).filter(Candidate.status == "rejected").count()
    manual_review = db.query(Candidate).filter(Candidate.status == "manual_review").count()

    avg_score_result = db.query(func.avg(Candidate.match_score)).scalar()
    avg_score = round(float(avg_score_result or 0), 1)

    # Applications by role
    role_counts = (
        db.query(Candidate.role_applied, func.count(Candidate.id))
        .group_by(Candidate.role_applied)
        .all()
    )
    applications_by_role = {role: count for role, count in role_counts if role}

    # Score distribution (buckets of 10)
    score_dist = []
    for low in range(0, 100, 10):
        high = low + 10
        count = (
            db.query(Candidate)
            .filter(Candidate.match_score >= low, Candidate.match_score < high)
            .count()
        )
        score_dist.append({"range": f"{low}-{high}", "count": count})

    # Status over time (by date)
    status_over_time = (
        db.query(
            func.date(Candidate.application_date),
            Candidate.status,
            func.count(Candidate.id),
        )
        .group_by(func.date(Candidate.application_date), Candidate.status)
        .order_by(func.date(Candidate.application_date))
        .all()
    )
    status_timeline = [
        {"date": str(date), "status": status, "count": count}
        for date, status, count in status_over_time
        if date
    ]

    # Top skills across all candidates
    all_skills = db.query(Candidate.skills).filter(Candidate.skills.isnot(None)).all()
    skill_counter = {}
    for (skills_list,) in all_skills:
        if isinstance(skills_list, list):
            for skill in skills_list:
                skill_counter[skill] = skill_counter.get(skill, 0) + 1

    top_skills = sorted(skill_counter.items(), key=lambda x: x[1], reverse=True)[:20]
    top_skills_list = [{"skill": s, "count": c} for s, c in top_skills]

    return {
        "total": total,
        "shortlisted": shortlisted,
        "rejected": rejected,
        "manual_review": manual_review,
        "avg_score": avg_score,
        "applications_by_role": applications_by_role,
        "score_distribution": score_dist,
        "status_over_time": status_timeline,
        "top_skills": top_skills_list,
    }


@router.get("/roles")
async def list_roles():
    """
    List all available roles from config.yaml with their criteria.
    """
    roles = get_all_roles()
    result = []

    for name, config in roles.items():
        result.append({
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "required_skills": config.get("required_skills", []),
            "preferred_skills": config.get("preferred_skills", []),
            "min_experience_years": config.get("min_experience_years", 0),
            "min_match_score": config.get("min_match_score", 60),
            "education_required": config.get("education_required", False),
        })

    return {"roles": result}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Check async Celery task status.

    Returns task state and result if completed.
    """
    try:
        from tasks.celery_tasks import celery_app
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
        }
    except Exception as e:
        logger.warning(f"Celery not available for task status check: {e}")
        return {
            "task_id": task_id,
            "status": "UNKNOWN",
            "result": None,
            "message": "Celery task queue not available",
        }
