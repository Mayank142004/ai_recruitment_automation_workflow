"""
AI Recruitment Automation — Spam / Fake Resume Detector

Detects suspicious resumes based on:
  - Word count (< 100 words → spam)
  - Skill inflation (> 80 skills → suspicious)
  - Language (non-English → flag)
  - Repetition (same sentence 3+ times → spam)
"""

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)


def is_spam(text: str, parsed_data: dict | None = None) -> dict:
    """
    Check if a resume appears to be spam, fake, or inflated.

    Args:
        text: Raw resume text.
        parsed_data: Optional dict from parser.py with extracted skills, etc.

    Returns:
        Dict with: is_spam (bool), confidence (float 0-1), reason (str).
    """
    reasons = []
    spam_score = 0.0  # Accumulates confidence toward spam

    if not text or not text.strip():
        return {
            "is_spam": True,
            "confidence": 1.0,
            "reason": "Empty or blank resume",
        }

    # ── Check 1: Word count ──────────────────────────────────────────────
    words = text.split()
    word_count = len(words)

    if word_count < 50:
        reasons.append(f"Very low word count: {word_count} (minimum: 50)")
        spam_score += 0.6
    elif word_count < 100:
        reasons.append(f"Low word count: {word_count} (minimum: 100)")
        spam_score += 0.3

    # ── Check 2: Skill inflation ─────────────────────────────────────────
    if parsed_data:
        skills = parsed_data.get("skills", [])
        if len(skills) > 80:
            reasons.append(f"Excessive skills listed: {len(skills)} (suspiciously high)")
            spam_score += 0.4
        elif len(skills) > 60:
            reasons.append(f"High skill count: {len(skills)} (possibly inflated)")
            spam_score += 0.2

    # ── Check 3: Language check ──────────────────────────────────────────
    try:
        from langdetect import detect
        lang = detect(text)
        if lang != "en":
            reasons.append(f"Non-English content detected: language={lang}")
            spam_score += 0.2
    except Exception:
        pass  # langdetect may fail on very short text

    # ── Check 4: Repetition check ────────────────────────────────────────
    # Split into sentences and check for duplicates
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 20]

    if sentences:
        sentence_counts = Counter(sentences)
        repeated = {s: c for s, c in sentence_counts.items() if c >= 3}
        if repeated:
            reasons.append(
                f"Repeated sentences found ({len(repeated)} sentences appear 3+ times)"
            )
            spam_score += 0.4

    # ── Check 5: Gibberish / random character detection ──────────────────
    # High ratio of non-alphabetic characters can indicate garbage
    alpha_chars = sum(1 for c in text if c.isalpha())
    total_chars = len(text)
    if total_chars > 0:
        alpha_ratio = alpha_chars / total_chars
        if alpha_ratio < 0.4:
            reasons.append(f"Low alphabetic ratio: {alpha_ratio:.2f} (possible gibberish)")
            spam_score += 0.3

    # ── Final Decision ───────────────────────────────────────────────────
    confidence = min(spam_score, 1.0)
    is_spam_flag = confidence >= 0.5

    reason = "; ".join(reasons) if reasons else "No spam indicators detected"

    result = {
        "is_spam": is_spam_flag,
        "confidence": round(confidence, 2),
        "reason": reason,
    }

    if is_spam_flag:
        logger.warning(f"Spam detected (confidence={confidence:.2f}): {reason}")

    return result
