"""
AI Recruitment Automation — Google Sheets Sync Service

Syncs candidate data to Google Sheets using gspread.
Uses the same OAuth2 credentials as Gmail.
Free tier: unlimited reads/writes via Google Sheets API.
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# ── gspread Client ───────────────────────────────────────────────────────────
_sheets_client = None
_worksheet = None


def _get_worksheet():
    """Get or initialize the Google Sheets worksheet."""
    global _sheets_client, _worksheet

    if _worksheet is not None:
        return _worksheet

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    creds_path = os.getenv("GMAIL_CREDENTIALS_JSON", "")

    if not sheet_id or sheet_id == "your_spreadsheet_id":
        logger.warning("GOOGLE_SHEET_ID not configured — Sheets sync disabled")
        return None

    if not creds_path or creds_path == "path/to/credentials.json":
        logger.warning("Gmail credentials not configured — Sheets sync disabled")
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        # Try service account first
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        try:
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            _sheets_client = gspread.authorize(creds)
        except Exception:
            # Fall back to OAuth2 user credentials
            from google.oauth2.credentials import Credentials as UserCreds
            token_path = os.path.join(os.path.dirname(creds_path), "token.json")
            if os.path.exists(token_path):
                creds = UserCreds.from_authorized_user_file(token_path, scopes)
                _sheets_client = gspread.authorize(creds)
            else:
                logger.error("No valid credentials for Google Sheets")
                return None

        spreadsheet = _sheets_client.open_by_key(sheet_id)
        _worksheet = spreadsheet.sheet1

        # Ensure header row exists
        headers = _worksheet.row_values(1)
        if not headers:
            _worksheet.append_row([
                "Candidate ID", "Name", "Email", "Phone", "City", "College",
                "Role Applied", "Match Score", "Status", "Skills",
                "Experience (Years)", "Education", "GitHub Score",
                "AI Summary", "Red Flags", "Application Date",
            ])
            logger.info("Created header row in Google Sheet")

        logger.info("Google Sheets connection established")
        return _worksheet

    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None


def append_candidate_to_sheet(candidate_data: dict) -> bool:
    """
    Append a candidate's data as a new row in Google Sheets.

    Args:
        candidate_data: Dict with candidate information.

    Returns:
        True if row was added successfully, False otherwise.
    """
    worksheet = _get_worksheet()

    if worksheet is None:
        logger.warning("Google Sheets not available — skipping sync")
        return False

    try:
        row = [
            candidate_data.get("candidate_id", ""),
            candidate_data.get("name", ""),
            candidate_data.get("email", ""),
            candidate_data.get("phone", ""),
            candidate_data.get("city", ""),
            candidate_data.get("college", ""),
            candidate_data.get("role_applied", ""),
            str(candidate_data.get("match_score", "")),
            candidate_data.get("status", ""),
            ", ".join(candidate_data.get("skills", []) or []),
            str(candidate_data.get("experience_years", "")),
            candidate_data.get("education_degree", ""),
            str(candidate_data.get("github_score", "")),
            candidate_data.get("ai_summary", ""),
            ", ".join(candidate_data.get("red_flags", []) or []),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info(f"Candidate {candidate_data.get('name')} synced to Google Sheets")
        return True

    except Exception as e:
        logger.error(f"Failed to sync to Google Sheets: {e}")
        return False


def update_candidate_in_sheet(candidate_id: str, updates: dict) -> bool:
    """
    Update an existing candidate row in Google Sheets.

    Args:
        candidate_id: The candidate's unique ID.
        updates: Dict with fields to update.

    Returns:
        True if updated successfully, False otherwise.
    """
    worksheet = _get_worksheet()

    if worksheet is None:
        return False

    try:
        # Find the row with this candidate ID
        cell = worksheet.find(candidate_id)
        if cell is None:
            logger.warning(f"Candidate {candidate_id} not found in sheet")
            return False

        row_num = cell.row

        # Update status column (index 9, column I)
        if "status" in updates:
            worksheet.update_cell(row_num, 9, updates["status"])

        # Update match score (index 8, column H)
        if "match_score" in updates:
            worksheet.update_cell(row_num, 8, str(updates["match_score"]))

        logger.info(f"Updated candidate {candidate_id} in Google Sheets")
        return True

    except Exception as e:
        logger.error(f"Failed to update Google Sheets: {e}")
        return False
