"""
AI Recruitment Automation — Candidate Submission Portal

Streamlit-based candidate-facing application form.
Submits data + PDF resume to the FastAPI backend.

Run: streamlit run frontend/app.py --server.port 8501
"""

import os
import re
import sys

import requests
import streamlit as st

# API base URL
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_available_roles():
    """Fetch available roles from the API."""
    try:
        resp = requests.get(f"{API_BASE}/api/roles", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            roles = data.get("roles", [])
            return {r["display_name"]: r["name"] for r in roles}
    except Exception:
        pass

    # Fallback roles if API is not available
    return {
        "Backend Developer": "backend_developer",
        "Data Scientist": "data_scientist",
        "Frontend Developer": "frontend_developer",
        "DevOps Engineer": "devops_engineer",
    }


def validate_phone(phone: str) -> bool:
    """Validate Indian phone number (10 digits)."""
    digits = re.sub(r'\D', '', phone)
    if digits.startswith("91") and len(digits) == 12:
        return True
    return len(digits) == 10


def validate_email(email: str) -> bool:
    """Basic email validation."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def main():
    # ── Page Config ──────────────────────────────────────────────────────
    st.set_page_config(
        page_title="Apply Now | AI Recruitment",
        page_icon="🚀",
        layout="centered",
    )

    # ── Custom CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        .stApp {
            font-family: 'Inter', sans-serif;
        }

        .main-header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
        }

        .main-header h1 {
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0;
        }

        .main-header p {
            font-size: 1.1rem;
            opacity: 0.9;
            margin-top: 0.5rem;
        }

        .success-box {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            padding: 2rem;
            border-radius: 12px;
            color: white;
            text-align: center;
            margin: 1rem 0;
        }

        .error-box {
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: white;
            text-align: center;
        }

        .info-card {
            background: #f0f4ff;
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            margin: 1rem 0;
        }

        div[data-testid="stForm"] {
            border: 1px solid #e0e0e0;
            border-radius: 16px;
            padding: 2rem;
            background: white;
        }

        .stButton > button {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.8rem 2rem;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────────────────
    company_name = os.getenv("COMPANY_NAME", "Our Company")

    st.markdown(f"""
    <div class="main-header">
        <h1>🚀 Apply at {company_name}</h1>
        <p>Submit your application and let AI match you with the perfect role</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Get Available Roles ──────────────────────────────────────────────
    roles = get_available_roles()

    # ── Application Form ─────────────────────────────────────────────────
    with st.form("application_form", clear_on_submit=False):
        st.markdown("### 📋 Application Form")
        st.markdown("Fill in your details below. All fields marked with * are required.")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Full Name *", placeholder="John Doe")
            email = st.text_input("Email *", placeholder="john@example.com")
            phone = st.text_input("Phone *", placeholder="9876543210 (10 digits)")

        with col2:
            city = st.text_input("City", placeholder="Mumbai")
            college = st.text_input("College / University", placeholder="IIT Bombay")
            role_display = st.selectbox(
                "Role Applied For *",
                options=list(roles.keys()),
            )

        st.markdown("---")

        resume = st.file_uploader(
            "Upload Resume (PDF only) *",
            type=["pdf"],
            help="Maximum file size: 10 MB",
        )

        st.markdown("")
        submitted = st.form_submit_button("🚀 Submit Application", use_container_width=True)

    # ── Handle Submission ────────────────────────────────────────────────
    if submitted:
        # Validation
        errors = []

        if not name or len(name.strip()) < 2:
            errors.append("Full name is required (minimum 2 characters)")
        if not email or not validate_email(email):
            errors.append("Valid email address is required")
        if not phone or not validate_phone(phone):
            errors.append("Valid 10-digit phone number is required")
        if not resume:
            errors.append("Resume PDF is required")

        if errors:
            for err in errors:
                st.error(f"❌ {err}")
            return

        # Submit to API
        role_key = roles.get(role_display, "backend_developer")

        with st.spinner("🔄 Processing your application... This may take 15-25 seconds."):
            try:
                files = {"resume": (resume.name, resume.getvalue(), "application/pdf")}
                data = {
                    "name": name.strip(),
                    "email": email.strip().lower(),
                    "phone": phone.strip(),
                    "city": city.strip(),
                    "college": college.strip(),
                    "role_applied": role_key,
                }

                resp = requests.post(
                    f"{API_BASE}/api/submit",
                    data=data,
                    files=files,
                    timeout=60,
                )

                if resp.status_code == 200:
                    result = resp.json()
                    status = result.get("status", "")
                    candidate_id = result.get("candidate_id", "")
                    match_score = result.get("match_score", 0)

                    if status == "duplicate":
                        st.markdown(f"""
                        <div class="error-box">
                            <h3>⚠️ Duplicate Application</h3>
                            <p>{result.get('message', 'A similar application already exists.')}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    elif status == "rejected" and result.get("match_score", 0) == 0:
                        st.markdown(f"""
                        <div class="error-box">
                            <h3>⚠️ Application Issue</h3>
                            <p>{result.get('message', 'There was an issue with your application.')}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    else:
                        status_emoji = {
                            "shortlisted": "🎉",
                            "manual_review": "⏳",
                            "rejected": "📝",
                        }.get(status, "✅")

                        st.markdown(f"""
                        <div class="success-box">
                            <h2>{status_emoji} Application Submitted!</h2>
                            <p>Thank you, <strong>{name}</strong>!</p>
                            <p>Your application ID: <strong>{candidate_id[:8]}...</strong></p>
                            <p>Match Score: <strong>{match_score}/100</strong></p>
                        </div>
                        """, unsafe_allow_html=True)

                        if status == "shortlisted":
                            st.success("🎉 Congratulations! You've been shortlisted. Check your email for interview details.")
                        elif status == "manual_review":
                            st.info("⏳ Your application is under review. Our HR team will contact you soon.")
                        elif status == "rejected":
                            st.info("📝 Thank you for applying. We'll keep your profile for future opportunities.")

                        st.balloons()

                else:
                    error_detail = resp.json().get("detail", "Unknown error")
                    st.error(f"❌ Submission failed: {error_detail}")

            except requests.ConnectionError:
                st.error(
                    "❌ Cannot connect to the API server. "
                    "Make sure the backend is running on http://localhost:8000"
                )
            except requests.Timeout:
                st.error("❌ Request timed out. Please try again.")
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")

    # ── Footer ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f"""
        <div style="text-align: center; color: #999; font-size: 0.85rem;">
            <p>Powered by AI Recruitment Automation | {company_name}</p>
            <p>Your data is processed securely. We use AI to match you with the best role.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
