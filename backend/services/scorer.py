"""
AI Recruitment Automation — Groq LLM Scoring Service

Scores candidates against job descriptions using Groq's free-tier Llama 3 70B model.
Free tier: 14,400 requests/day, 30 requests/minute.

Rate limiter: max 25 requests/minute to stay safe.
Retry logic: 3 retries with 2-second delay on API errors.
"""

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Groq Client ──────────────────────────────────────────────────────────────
_groq_client = None


def _get_groq_client():
    """Lazy-load Groq client."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            logger.warning("GROQ_API_KEY not set — LLM scoring will return mock results")
            return None
        try:
            from groq import Groq
            _groq_client = Groq(api_key=api_key)
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            return None
    return _groq_client


# ── Rate Limiter ─────────────────────────────────────────────────────────────
_request_timestamps: list[float] = []
MAX_REQUESTS_PER_MINUTE = 25


def _wait_for_rate_limit():
    """Wait if we're approaching the rate limit."""
    now = time.time()
    # Remove timestamps older than 60 seconds
    _request_timestamps[:] = [t for t in _request_timestamps if now - t < 60]

    if len(_request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        wait_time = 60 - (now - _request_timestamps[0]) + 0.5
        if wait_time > 0:
            logger.info(f"Rate limit: waiting {wait_time:.1f}s before next request")
            time.sleep(wait_time)

    _request_timestamps.append(time.time())


# ── System Prompt ────────────────────────────────────────────────────────────
SCORING_SYSTEM_PROMPT = """You are an expert technical recruiter. Analyze the resume against the job description and return ONLY a valid JSON object with no additional text, markdown, or explanation. JSON schema:
{
  "match_score": <integer 0-100>,
  "matched_skills": [<list of strings>],
  "missing_skills": [<list of strings>],
  "experience_fit": <"yes" | "no" | "partial">,
  "education_fit": <"yes" | "no" | "partial">,
  "candidate_summary": <string, max 2 sentences>,
  "red_flags": [<list of strings or empty list>],
  "recommendation": <"shortlist" | "reject" | "manual_review">
}"""


def _parse_llm_response(response_text: str) -> Optional[dict]:
    """
    Parse JSON from LLM response, stripping markdown code fences if present.

    Args:
        response_text: Raw text from Groq API.

    Returns:
        Parsed dict or None if parsing fails.
    """
    if not response_text:
        return None

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = response_text.strip()
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        # Validate required keys
        required_keys = {
            "match_score", "matched_skills", "missing_skills",
            "experience_fit", "education_fit", "candidate_summary",
            "red_flags", "recommendation",
        }
        if not required_keys.issubset(data.keys()):
            missing = required_keys - set(data.keys())
            logger.warning(f"LLM response missing keys: {missing}")
            # Fill in defaults for missing keys
            for key in missing:
                if key in ("matched_skills", "missing_skills", "red_flags"):
                    data[key] = []
                elif key == "match_score":
                    data[key] = 0
                elif key in ("experience_fit", "education_fit"):
                    data[key] = "partial"
                elif key == "candidate_summary":
                    data[key] = "Unable to generate summary."
                elif key == "recommendation":
                    data[key] = "manual_review"

        # Ensure match_score is an integer 0-100
        data["match_score"] = max(0, min(100, int(data.get("match_score", 0))))

        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nRaw response: {response_text[:500]}")
        return None


def score_candidate(
    resume_text: str,
    job_description: str,
    role: str,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> dict:
    """
    Score a candidate's resume against a job description using Groq LLM.

    Args:
        resume_text: Extracted text from the candidate's resume.
        job_description: Job description text or role requirements.
        role: Name of the role being applied for.
        max_retries: Number of retries on API errors (default: 3).
        retry_delay: Seconds to wait between retries (default: 2.0).

    Returns:
        Scoring dict with: match_score, matched_skills, missing_skills,
        experience_fit, education_fit, candidate_summary, red_flags, recommendation.
    """
    model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    client = _get_groq_client()

    if client is None:
        logger.warning("Groq client not available — returning mock score")
        return _mock_score(resume_text, role)

    user_message = f"""Role: {role}

Job Description:
{job_description[:3000]}

Resume:
{resume_text[:5000]}

Score this candidate against the job description. Return ONLY valid JSON."""

    for attempt in range(1, max_retries + 1):
        try:
            _wait_for_rate_limit()

            start_time = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            elapsed = time.time() - start_time

            # Log API call
            usage = response.usage
            logger.info(
                f"Groq API call: model={model} | attempt={attempt} | "
                f"time={elapsed:.2f}s | tokens_in={usage.prompt_tokens} | "
                f"tokens_out={usage.completion_tokens} | "
                f"timestamp={datetime.utcnow().isoformat()}"
            )

            result_text = response.choices[0].message.content
            parsed = _parse_llm_response(result_text)

            if parsed is not None:
                return parsed
            else:
                logger.warning(f"Attempt {attempt}: Failed to parse LLM response")
                if attempt < max_retries:
                    time.sleep(retry_delay)

        except Exception as e:
            logger.error(f"Groq API error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)

    # All retries exhausted — return mock score
    logger.error("All Groq API retries exhausted — returning mock score")
    return _mock_score(resume_text, role)


def score_batch(
    candidates: list[dict],
    job_description: str,
    role: str,
) -> list[dict]:
    """
    Score multiple candidates in batch with rate-limit-safe delays.

    Args:
        candidates: List of dicts with at least 'resume_text' key.
        job_description: Job description for the role.
        role: Role name.

    Returns:
        List of scoring dicts in the same order as input.
    """
    results = []
    for i, candidate in enumerate(candidates):
        logger.info(f"Scoring candidate {i + 1}/{len(candidates)}")
        resume_text = candidate.get("resume_text", "")
        score = score_candidate(resume_text, job_description, role)
        results.append(score)

        # Sleep between calls to respect Groq free tier limits
        if i < len(candidates) - 1:
            time.sleep(1)

    return results


def score_against_all_roles(
    resume_text: str,
    applied_role: str,
    role_descriptions: dict[str, str],
) -> dict:
    """
    Score a resume against all available roles to find the best fit.

    Args:
        resume_text: Extracted resume text.
        applied_role: The role the candidate originally applied for.
        role_descriptions: Dict mapping role name -> job description text.

    Returns:
        Dict with: best_role, all_scores, suggestion.
    """
    all_scores = {}
    for role, jd in role_descriptions.items():
        result = score_candidate(resume_text, jd, role)
        all_scores[role] = result.get("match_score", 0)

    best_role = max(all_scores, key=all_scores.get) if all_scores else applied_role
    applied_score = all_scores.get(applied_role, 0)
    best_score = all_scores.get(best_role, 0)

    suggestion = ""
    if best_role != applied_role and best_score - applied_score >= 15:
        suggestion = (
            f"Candidate may be a better fit for {best_role} "
            f"(scored {best_score} vs {applied_score} for {applied_role})"
        )

    return {
        "best_role": best_role,
        "all_scores": all_scores,
        "suggestion": suggestion,
    }


def _mock_score(resume_text: str, role: str) -> dict:
    """
    Generate a mock score when Groq API is unavailable.
    Uses basic heuristics for a reasonable approximation.
    """
    from services.parser import extract_skills, extract_experience_years

    skills = extract_skills(resume_text)
    experience = extract_experience_years(resume_text)

    # Simple heuristic scoring
    skill_score = min(len(skills) * 5, 50)  # Up to 50 points for skills
    exp_score = min(experience * 10, 30)  # Up to 30 points for experience
    base_score = 20  # Base score
    match_score = min(int(skill_score + exp_score + base_score), 100)

    recommendation = "shortlist" if match_score >= 65 else (
        "manual_review" if match_score >= 50 else "reject"
    )

    return {
        "match_score": match_score,
        "matched_skills": skills[:10],
        "missing_skills": [],
        "experience_fit": "yes" if experience >= 1.5 else ("partial" if experience > 0 else "no"),
        "education_fit": "partial",
        "candidate_summary": f"Candidate has {len(skills)} relevant skills and {experience} years of experience. Mock scoring used (Groq API unavailable).",
        "red_flags": ["Scored using mock heuristics — Groq API unavailable"],
        "recommendation": recommendation,
    }
