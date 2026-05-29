"""
AI Recruitment Automation — NLP Entity Extraction & Semantic Matching

Uses spaCy for named entity recognition and sentence-transformers for
semantic skill matching.

Models are loaded at module level to avoid re-loading per request.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Load spaCy model at module level ─────────────────────────────────────────
_nlp_model = None

def _get_nlp():
    """Lazy-load spaCy model (loaded once, cached)."""
    global _nlp_model
    if _nlp_model is None:
        try:
            import spacy
            _nlp_model = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            _nlp_model = None
    return _nlp_model


# ── Load sentence-transformers model at module level ─────────────────────────
_st_model = None

def _get_st_model():
    """Lazy-load sentence-transformers model (~80MB, downloads once from HuggingFace)."""
    global _st_model
    if _st_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _st_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("sentence-transformers all-MiniLM-L6-v2 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {e}")
            _st_model = None
    return _st_model


def extract_named_entities(text: str) -> dict:
    """
    Extract named entities from text using spaCy.

    Extracts PERSON, ORG (organizations), and GPE (geo-political entities / locations).

    Args:
        text: Raw resume text.

    Returns:
        Dict with keys: persons, organizations, locations — each a list of strings.
    """
    result = {"persons": [], "organizations": [], "locations": []}

    nlp = _get_nlp()
    if nlp is None or not text:
        return result

    # spaCy has a max doc length; truncate if needed
    max_len = 100_000
    doc = nlp(text[:max_len])

    persons = set()
    organizations = set()
    locations = set()

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            persons.add(ent.text.strip())
        elif ent.label_ == "ORG":
            organizations.add(ent.text.strip())
        elif ent.label_ == "GPE":
            locations.add(ent.text.strip())

    result["persons"] = sorted(persons)
    result["organizations"] = sorted(organizations)
    result["locations"] = sorted(locations)

    return result


def semantic_skill_match(
    resume_skills: list[str],
    jd_skills: list[str],
    threshold: float = 0.75,
) -> dict:
    """
    Semantically match resume skills against job description skills
    using sentence-transformers cosine similarity.

    For each JD skill, finds the best matching resume skill. If the
    similarity is >= threshold, the skill is considered matched.

    Args:
        resume_skills: List of skills found in the resume.
        jd_skills: List of skills required/preferred for the role.
        threshold: Minimum cosine similarity to consider a match (default: 0.75).

    Returns:
        Dict with keys: matched (list), missing (list), score (float 0-1).
    """
    result = {"matched": [], "missing": [], "score": 0.0}

    if not resume_skills or not jd_skills:
        result["missing"] = jd_skills or []
        return result

    model = _get_st_model()

    if model is None:
        # Fallback: exact case-insensitive matching
        resume_lower = {s.lower() for s in resume_skills}
        for skill in jd_skills:
            if skill.lower() in resume_lower:
                result["matched"].append(skill)
            else:
                result["missing"].append(skill)
        if jd_skills:
            result["score"] = len(result["matched"]) / len(jd_skills)
        return result

    try:
        # Encode all skills
        resume_embeddings = model.encode(resume_skills, convert_to_tensor=True)
        jd_embeddings = model.encode(jd_skills, convert_to_tensor=True)

        # Compute cosine similarities
        from sentence_transformers import util
        cos_scores = util.cos_sim(jd_embeddings, resume_embeddings)

        for i, jd_skill in enumerate(jd_skills):
            max_sim = float(cos_scores[i].max())
            if max_sim >= threshold:
                result["matched"].append(jd_skill)
            else:
                result["missing"].append(jd_skill)

        if jd_skills:
            result["score"] = len(result["matched"]) / len(jd_skills)

    except Exception as e:
        logger.error(f"Semantic matching failed: {e}")
        # Fallback to exact match
        resume_lower = {s.lower() for s in resume_skills}
        for skill in jd_skills:
            if skill.lower() in resume_lower:
                result["matched"].append(skill)
            else:
                result["missing"].append(skill)
        if jd_skills:
            result["score"] = len(result["matched"]) / len(jd_skills)

    return result


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.

    Uses the langdetect library. Returns ISO 639-1 language code.
    Non-English text is flagged as suspicious.

    Args:
        text: Text to detect language of.

    Returns:
        ISO 639-1 language code (e.g., 'en', 'hi', 'fr').
        Returns 'unknown' if detection fails.
    """
    if not text or len(text.strip()) < 20:
        return "unknown"

    try:
        from langdetect import detect
        lang = detect(text)
        if lang != "en":
            logger.warning(f"Non-English resume detected: language={lang}")
        return lang
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return "unknown"


def enrich_candidate_data(text: str, resume_skills: list[str], jd_skills: list[str]) -> dict:
    """
    Run full NLP enrichment pipeline on resume text.

    Args:
        text: Raw resume text.
        resume_skills: Skills already extracted by parser.
        jd_skills: Skills required for the applied role.

    Returns:
        Dict with: entities, skill_match, language.
    """
    entities = extract_named_entities(text)
    skill_match = semantic_skill_match(resume_skills, jd_skills)
    language = detect_language(text)

    return {
        "entities": entities,
        "skill_match": skill_match,
        "language": language,
    }
