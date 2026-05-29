"""
AI Recruitment Automation — Meta WhatsApp Cloud API Integration

Sends WhatsApp messages using Meta's Cloud API.
Free tier: 1,000 messages/month.

Setup:
  1. Go to developers.facebook.com
  2. Create App > Business type > Add WhatsApp product
  3. WhatsApp > Getting Started > copy Test Token and Phone Number ID
  4. Add recipient phone number to test allowlist
  5. Set WHATSAPP_TOKEN and WHATSAPP_PHONE_ID in .env
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

# WhatsApp Cloud API base URL
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"


def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """
    Send a WhatsApp text message using Meta Cloud API.

    Args:
        phone_number: International phone number without '+' (e.g., '919876543210').
        message: Text message to send.

    Returns:
        True if message was sent successfully, False otherwise.
    """
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")

    if not token or token == "your_meta_whatsapp_token":
        logger.warning(f"WhatsApp not configured — would send to {phone_number}: {message[:50]}...")
        return False

    if not phone_id or phone_id == "your_phone_number_id":
        logger.warning("WHATSAPP_PHONE_ID not configured")
        return False

    # Normalize phone number: remove spaces, dashes, and leading '+'
    phone_clean = phone_number.replace(" ", "").replace("-", "").lstrip("+")

    # Add country code if not present (default: India 91)
    if len(phone_clean) == 10:
        phone_clean = "91" + phone_clean

    url = f"{WHATSAPP_API_URL}/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_clean,
        "type": "text",
        "text": {"body": message},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            logger.info(f"WhatsApp message sent to {phone_clean}")
            return True
        else:
            logger.error(
                f"WhatsApp API error: status={response.status_code}, "
                f"response={response.text}"
            )
            return False

    except requests.RequestException as e:
        logger.error(f"WhatsApp API request failed: {e}")
        return False


def send_shortlist_whatsapp(phone: str, name: str, role: str) -> bool:
    """
    Send shortlist notification via WhatsApp.

    Args:
        phone: Candidate's phone number.
        name: Candidate's name.
        role: Role they applied for.
    """
    company = os.getenv("COMPANY_NAME", "Our Company")

    message = (
        f"🎉 Congratulations, {name}!\n\n"
        f"Your application for the *{role}* position at *{company}* "
        f"has been shortlisted!\n\n"
        f"Our HR team will contact you shortly with interview details.\n\n"
        f"Please keep your phone reachable and check your email for "
        f"the interview invitation.\n\n"
        f"Best of luck! 🍀\n"
        f"— {company} HR Team"
    )

    return send_whatsapp_message(phone, message)


def send_interview_reminder(
    phone: str, name: str, date: str, time: str
) -> bool:
    """
    Send interview reminder via WhatsApp.

    Args:
        phone: Candidate's phone number.
        name: Candidate's name.
        date: Interview date string.
        time: Interview time string.
    """
    company = os.getenv("COMPANY_NAME", "Our Company")

    message = (
        f"⏰ Interview Reminder\n\n"
        f"Hi {name},\n\n"
        f"This is a friendly reminder about your upcoming interview "
        f"at *{company}*.\n\n"
        f"📅 Date: {date}\n"
        f"⏰ Time: {time}\n\n"
        f"Please ensure you have:\n"
        f"✅ Updated resume\n"
        f"✅ Portfolio/project links\n"
        f"✅ Government ID\n\n"
        f"Good luck! 🍀\n"
        f"— {company} HR Team"
    )

    return send_whatsapp_message(phone, message)
