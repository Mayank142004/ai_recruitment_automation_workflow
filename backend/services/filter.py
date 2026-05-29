"""
AI Recruitment Automation — YAML-Driven Candidate Filtering

Loads filtering rules from config.yaml and routes candidates to:
  - shortlisted   — passes all criteria
  - manual_review — borderline score (within 15 points of threshold)
  - rejected      — fails one or more criteria
"""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# ── Config Loading ───────────────────────────────────────────────────────────
_config_cache: dict | None = None
_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config(force_reload: bool = False) -> dict:
    """
    Load role configuration from config.yaml.

    Caches the result — use force_reload=True to refresh.
    """
    global _config_cache
    if _config_cache is not None and not force_reload:
        return _config_cache

    config_path = _CONFIG_PATH
    if not config_path.exists():
        logger.error(f"config.yaml not found at {config_path}")
        return {"roles": {}}

    with open(config_path, "r", encoding="utf-8") as f:
        _config_cache = yaml.safe_load(f)

    logger.info(f"Loaded config with {len(_config_cache.get('roles', {}))} roles")
    return _config_cache


def get_role_config(role: str) -> dict | None:
    """
    Get filtering criteria for a specific role.

    Args:
        role: Role key (e.g., 'backend_developer').

    Returns:
        Role config dict or None if role not found.
    """
    config = load_config()
    roles = config.get("roles", {})
    return roles.get(role)


def get_all_roles() -> dict:
    """Get all role configurations."""
    config = load_config()
    return config.get("roles", {})


def get_role_names() -> list[str]:
    """Get list of all available role names."""
    return list(get_all_roles().keys())


def get_job_description(role: str) -> str:
    """Get the job description text for a given role."""
    role_config = get_role_config(role)
    if role_config:
        return role_config.get("job_description", "")
    return ""


def filter_candidate(
    score_data: dict,
    parsed_data: dict,
    role: str,
) -> dict:
    """
    Filter a candidate based on their AI score, parsed resume data,
    and the role's YAML configuration.

    Decision logic:
      1. If ALL required_skills present AND experience >= threshold
         AND match_score >= min_score → shortlisted
      2. If match_score is between (min_score - 15) and min_score → manual_review
      3. Otherwise → rejected

    Args:
        score_data: Dict from scorer.py with match_score, recommendation, etc.
        parsed_data: Dict from parser.py with skills, experience_years, education, etc.
        role: Role key (e.g., 'backend_developer').

    Returns:
        Dict with: status, reason, score, shortlist_priority (1-5).
    """
    role_config = get_role_config(role)

    if role_config is None:
        logger.warning(f"No config found for role '{role}' — defaulting to manual_review")
        return {
            "status": "manual_review",
            "reason": f"No filtering rules defined for role '{role}'",
            "score": score_data.get("match_score", 0),
            "shortlist_priority": 3,
        }

    required_skills = [s.lower() for s in role_config.get("required_skills", [])]
    min_experience = role_config.get("min_experience_years", 0)
    min_score = role_config.get("min_match_score", 60)
    education_required = role_config.get("education_required", False)

    # Extract candidate data
    candidate_skills = [s.lower() for s in (parsed_data.get("skills", []) or [])]
    experience_years = parsed_data.get("experience_years", 0) or 0
    education = parsed_data.get("education", {}) or {}
    match_score = score_data.get("match_score", 0) or 0

    # ── Check required skills ────────────────────────────────────────────
    missing_required = [
        s for s in required_skills if s not in candidate_skills
    ]
    has_required_skills = len(missing_required) == 0

    # ── Check experience ─────────────────────────────────────────────────
    meets_experience = experience_years >= min_experience

    # ── Check education (if required) ────────────────────────────────────
    meets_education = True
    if education_required:
        degree = education.get("degree", "") if isinstance(education, dict) else ""
        meets_education = bool(degree and len(degree) > 1)

    # ── Check match score ────────────────────────────────────────────────
    meets_score = match_score >= min_score
    borderline_score = (min_score - 15) <= match_score < min_score

    # ── Decision Logic ───────────────────────────────────────────────────
    reasons = []

    if not has_required_skills:
        reasons.append(f"Missing required skills: {', '.join(missing_required)}")

    if not meets_experience:
        reasons.append(
            f"Insufficient experience: {experience_years} years "
            f"(minimum: {min_experience})"
        )

    if not meets_education:
        reasons.append("Education requirement not met")

    if not meets_score:
        reasons.append(f"Match score {match_score} below threshold {min_score}")

    # Determine final status
    if has_required_skills and meets_experience and meets_education and meets_score:
        status = "shortlisted"
        reason = f"All criteria met: score={match_score}, experience={experience_years}yrs"
    elif borderline_score and has_required_skills and meets_experience:
        status = "manual_review"
        reason = f"Borderline score ({match_score}, threshold={min_score}). " + "; ".join(reasons)
    elif not has_required_skills and meets_score:
        status = "manual_review"
        reason = f"Good score but missing skills. " + "; ".join(reasons)
    else:
        status = "rejected"
        reason = "; ".join(reasons) if reasons else "Does not meet minimum criteria"

    # ── Calculate shortlist priority (1=highest, 5=lowest) ───────────────
    if match_score >= 90:
        priority = 1
    elif match_score >= 80:
        priority = 2
    elif match_score >= 70:
        priority = 3
    elif match_score >= 60:
        priority = 4
    else:
        priority = 5

    return {
        "status": status,
        "reason": reason,
        "score": match_score,
        "shortlist_priority": priority,
    }
