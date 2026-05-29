"""
AI Recruitment Automation — Duplicate Candidate Checker

Uses rapidfuzz fuzzy string matching to detect duplicate candidates.
Checks name+phone combination (threshold: 85% similarity) and exact email match.
"""

import logging

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def check_duplicate(
    name: str,
    phone: str,
    email: str,
    db_session,
    similarity_threshold: float = 85.0,
) -> dict:
    """
    Check if a candidate already exists in the database.

    Checks:
      1. Exact email match (highest confidence).
      2. Fuzzy name + phone combination match (>85% similarity).

    Args:
        name: Candidate's full name.
        phone: Candidate's phone number.
        email: Candidate's email address.
        db_session: SQLAlchemy database session.
        similarity_threshold: Minimum similarity % for fuzzy match (default: 85).

    Returns:
        Dict with: is_duplicate (bool), duplicate_id (int|None), similarity_score (float).
    """
    from models.database import Candidate

    result = {
        "is_duplicate": False,
        "duplicate_id": None,
        "similarity_score": 0.0,
    }

    try:
        # ── Check 1: Exact email match ───────────────────────────────────
        if email:
            existing = db_session.query(Candidate).filter(
                Candidate.email == email.lower().strip()
            ).first()

            if existing:
                logger.info(f"Duplicate found: exact email match with candidate #{existing.id}")
                return {
                    "is_duplicate": True,
                    "duplicate_id": existing.id,
                    "similarity_score": 100.0,
                }

        # ── Check 2: Fuzzy name + phone match ───────────────────────────
        all_candidates = db_session.query(Candidate).all()

        best_score = 0.0
        best_match_id = None

        for candidate in all_candidates:
            # Compare name
            name_score = fuzz.ratio(
                (name or "").lower().strip(),
                (candidate.name or "").lower().strip(),
            )

            # Compare phone
            phone_score = fuzz.ratio(
                (phone or "").strip()[-10:],  # Last 10 digits
                (candidate.phone or "").strip()[-10:],
            )

            # Combined score: weighted average (name 60%, phone 40%)
            combined_score = (name_score * 0.6) + (phone_score * 0.4)

            if combined_score > best_score:
                best_score = combined_score
                best_match_id = candidate.id

        if best_score >= similarity_threshold:
            logger.info(
                f"Duplicate found: fuzzy match with candidate #{best_match_id} "
                f"(similarity={best_score:.1f}%)"
            )
            return {
                "is_duplicate": True,
                "duplicate_id": best_match_id,
                "similarity_score": round(best_score, 2),
            }

        result["similarity_score"] = round(best_score, 2)

    except Exception as e:
        logger.error(f"Duplicate check failed: {e}")

    return result
