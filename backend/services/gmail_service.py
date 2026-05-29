"""
AI Recruitment Automation — Gmail API Integration

Sends emails using Gmail API with OAuth2 authentication.
Free tier: 500 emails/day.

Setup Instructions:
  1. Go to console.cloud.google.com
  2. Create project > Enable Gmail API
  3. Create OAuth 2.0 credentials (Desktop app type)
  4. Download credentials.json
  5. Run auth flow once to generate token.json
  6. Set GMAIL_CREDENTIALS_JSON=path/to/credentials.json in .env
"""

import base64
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

# ── Gmail Service ────────────────────────────────────────────────────────────
_gmail_service = None


def _get_gmail_service():
    """
    Initialize Gmail API service using OAuth2 credentials.
    Returns None if credentials are not configured.
    """
    global _gmail_service
    if _gmail_service is not None:
        return _gmail_service

    creds_path = os.getenv("GMAIL_CREDENTIALS_JSON", "")
    if not creds_path or creds_path == "path/to/credentials.json":
        logger.warning("Gmail credentials not configured — email sending disabled")
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
        creds = None

        # Check for existing token
        token_path = os.path.join(os.path.dirname(creds_path), "token.json")
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        _gmail_service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail API service initialized successfully")
        return _gmail_service

    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {e}")
        return None


def _send_email(to: str, subject: str, body_html: str, body_text: str = "") -> bool:
    """
    Send an email via Gmail API.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body_html: HTML body content.
        body_text: Plain text fallback body.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    service = _get_gmail_service()
    sender = os.getenv("GMAIL_SENDER_EMAIL", "noreply@company.com")

    if service is None:
        logger.warning(f"Gmail not configured — would send email to {to}: {subject}")
        return False

    try:
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["from"] = sender
        message["subject"] = subject

        if body_text:
            message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": raw}

        service.users().messages().send(userId="me", body=body).execute()
        logger.info(f"Email sent to {to}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


# ── Email Templates ──────────────────────────────────────────────────────────

def send_shortlist_email(
    to: str,
    name: str,
    role: str,
    interview_details: Optional[dict] = None,
) -> bool:
    """
    Send interview invitation email to shortlisted candidates.

    Args:
        to: Candidate's email address.
        name: Candidate's full name.
        role: Role they applied for.
        interview_details: Dict with date, time, location, etc.
    """
    company = os.getenv("COMPANY_NAME", "Our Company")
    hr_email = os.getenv("HR_EMAIL", "hr@company.com")

    details = interview_details or {}
    interview_date = details.get("date", "To be confirmed")
    interview_time = details.get("time", "To be confirmed")
    interview_location = details.get("location", "Virtual (link to be shared)")

    subject = f"Interview Invitation — {role} Position at {company}"

    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">🎉 Congratulations, {name}!</h1>
        </div>

        <div style="padding: 30px; background: #f9f9f9; border: 1px solid #e0e0e0;">
            <p>Dear <strong>{name}</strong>,</p>

            <p>We are pleased to inform you that your application for the
            <strong>{role}</strong> position at <strong>{company}</strong>
            has been shortlisted!</p>

            <p>We were impressed by your profile and would like to invite you
            for an interview.</p>

            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #667eea;">📋 Interview Details</h3>
                <p><strong>📅 Date:</strong> {interview_date}</p>
                <p><strong>⏰ Time:</strong> {interview_time}</p>
                <p><strong>📍 Location:</strong> {interview_location}</p>
            </div>

            <h3>What to Prepare:</h3>
            <ul>
                <li>Updated resume / CV</li>
                <li>Portfolio or project links (if applicable)</li>
                <li>Government-issued ID for verification</li>
                <li>Any relevant certifications</li>
            </ul>

            <p>If you have any questions or need to reschedule, please reach out
            to our HR team at <a href="mailto:{hr_email}">{hr_email}</a>.</p>

            <p>We look forward to speaking with you!</p>

            <p>Best regards,<br>
            <strong>HR Team</strong><br>
            {company}</p>
        </div>

        <div style="padding: 15px; text-align: center; font-size: 12px; color: #999; background: #f0f0f0; border-radius: 0 0 8px 8px;">
            This is an automated email from {company}'s recruitment system.
        </div>
    </body>
    </html>
    """

    return _send_email(to, subject, body_html)


def send_rejection_email(to: str, name: str, role: str) -> bool:
    """
    Send polite rejection email to unsuccessful candidates.
    """
    company = os.getenv("COMPANY_NAME", "Our Company")

    subject = f"Your Application for {role} — {company}"

    body_text = f"""Dear {name},

Thank you for your interest in the {role} position at {company} and for taking the time to apply.

After careful review of all applications, we regret to inform you that we have decided to move forward with other candidates whose profiles more closely match our current requirements.

This decision is in no way a reflection of your abilities or potential. We encourage you to apply again in the future when new opportunities arise that match your skill set.

We wish you all the best in your career journey.

Warm regards,
HR Team
{company}
"""

    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="padding: 30px; background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 8px;">
            <p>Dear <strong>{name}</strong>,</p>

            <p>Thank you for your interest in the <strong>{role}</strong> position
            at <strong>{company}</strong> and for taking the time to apply.</p>

            <p>After careful review of all applications, we regret to inform you that
            we have decided to move forward with other candidates whose profiles more
            closely match our current requirements.</p>

            <p>This decision is in no way a reflection of your abilities or potential.
            We encourage you to apply again in the future when new opportunities arise
            that match your skill set.</p>

            <p>We wish you all the best in your career journey.</p>

            <p>Warm regards,<br>
            <strong>HR Team</strong><br>
            {company}</p>
        </div>
    </body>
    </html>
    """

    return _send_email(to, subject, body_html, body_text)


def send_manual_review_notification(hr_email: str, candidate: dict) -> bool:
    """
    Send internal notification to HR when a candidate needs manual review.
    """
    company = os.getenv("COMPANY_NAME", "Our Company")

    name = candidate.get("name", "Unknown")
    role = candidate.get("role_applied", "Unknown")
    score = candidate.get("match_score", "N/A")
    summary = candidate.get("ai_summary", "No summary available")
    candidate_id = candidate.get("candidate_id", "N/A")

    subject = f"[Manual Review Required] {name} — {role} Application"

    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background: #ff9800; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0;">⚠️ Manual Review Required</h2>
        </div>

        <div style="padding: 30px; background: #f9f9f9; border: 1px solid #e0e0e0;">
            <p>A candidate requires manual review for the <strong>{role}</strong> position.</p>

            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #ff9800; margin: 15px 0;">
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Role:</strong> {role}</p>
                <p><strong>Match Score:</strong> {score}/100</p>
                <p><strong>Candidate ID:</strong> {candidate_id}</p>
            </div>

            <h3>AI Summary:</h3>
            <p>{summary}</p>

            <p>Please review this candidate in the recruiter dashboard and make
            a decision to shortlist or reject.</p>

            <p>— {company} Recruitment System</p>
        </div>
    </body>
    </html>
    """

    return _send_email(hr_email, subject, body_html)
