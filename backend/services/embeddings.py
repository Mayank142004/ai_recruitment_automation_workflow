"""
AI Recruitment Automation — Sentence-Transformers Embedding Service

Provides semantic similarity matching using the all-MiniLM-L6-v2 model.
Model is loaded once and cached at module level (~80MB download from HuggingFace).
"""

import logging

logger = logging.getLogger(__name__)

# ── Model Cache ──────────────────────────────────────────────────────────────
_model = None


def _get_model():
    """Lazy-load sentence-transformers model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Sentence-transformers model loaded (all-MiniLM-L6-v2)")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {e}")
    return _model


def compute_embeddings(texts: list[str]) -> list:
    """
    Compute sentence embeddings for a list of texts.

    Args:
        texts: List of strings to embed.

    Returns:
        List of embedding vectors (numpy arrays).
    """
    model = _get_model()
    if model is None:
        return []

    try:
        return model.encode(texts, convert_to_tensor=False).tolist()
    except Exception as e:
        logger.error(f"Embedding computation failed: {e}")
        return []


def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Compute cosine similarity between two texts.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Cosine similarity score (0.0 to 1.0).
    """
    model = _get_model()
    if model is None:
        return 0.0

    try:
        from sentence_transformers import util
        embeddings = model.encode([text_a, text_b], convert_to_tensor=True)
        score = float(util.cos_sim(embeddings[0], embeddings[1])[0][0])
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.error(f"Similarity computation failed: {e}")
        return 0.0


def match_resume_to_jd(resume_text: str, jd_text: str) -> dict:
    """
    Compute overall semantic match between resume and job description.

    Args:
        resume_text: Full resume text.
        jd_text: Full job description text.

    Returns:
        Dict with: similarity (float), match_level (str).
    """
    similarity = compute_similarity(resume_text, jd_text)

    if similarity >= 0.8:
        match_level = "excellent"
    elif similarity >= 0.65:
        match_level = "good"
    elif similarity >= 0.5:
        match_level = "moderate"
    else:
        match_level = "low"

    return {
        "similarity": round(similarity, 4),
        "match_level": match_level,
    }
