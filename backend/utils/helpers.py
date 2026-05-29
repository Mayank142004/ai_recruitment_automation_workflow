"""
AI Recruitment Automation — Shared Utility Functions
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Upload directory for resume PDFs
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def generate_candidate_id() -> str:
    """Generate a unique candidate ID (UUID4)."""
    return str(uuid.uuid4())


def save_uploaded_file(file_content: bytes, filename: str, candidate_id: str) -> str:
    """
    Save an uploaded file to the uploads directory.

    Args:
        file_content: Raw file bytes.
        filename: Original filename.
        candidate_id: Candidate's unique ID for namespacing.

    Returns:
        Path to the saved file.
    """
    # Sanitize filename
    safe_name = f"{candidate_id}_{filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / safe_name

    with open(file_path, "wb") as f:
        f.write(file_content)

    logger.info(f"Saved uploaded file: {file_path}")
    return str(file_path)


def format_phone_number(phone: str) -> str:
    """
    Normalize phone number to consistent format.

    Removes spaces, dashes, and ensures 10-digit format.
    """
    digits = "".join(c for c in phone if c.isdigit())

    # Remove country code if present
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    return digits[-10:] if len(digits) >= 10 else digits


def get_config_path() -> Path:
    """Get the path to config.yaml."""
    return Path(__file__).parent.parent / "config.yaml"


def setup_logging(level: str = "INFO"):
    """
    Configure logging for the application.
    """
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def timestamp_now() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.utcnow().isoformat()
