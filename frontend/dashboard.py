"""
AI Recruitment Automation — Recruiter Dashboard

Password-protected Streamlit dashboard for HR team.
Features:
  - Candidate table with filters and color-coded status
  - Expandable candidate details (AI summary, skills, red flags)
  - Manual status override
  - Charts: applications by role, score distribution, shortlist rate, top skills
  - Excel export

Run: streamlit run frontend/dashboard.py --server.port 8502
"""

import io
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")


def check_password():
    """Simple password gate for the dashboard."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <h1>🔒 Recruiter Dashboard</h1>
        <p style="color: #666;">Enter the dashboard password to continue</p>
    </div>
    """, unsafe_allow_html=True)

    password = st.text_input("Password", type="password", key="pwd_input")
    if st.button("Login", use_container_width=True):
        if password == DASHBOARD_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Incorrect password")

    return False


def fetch_candidates(params: dict = None):
    """Fetch candidates from API."""
    try:
        resp = requests.get(f"{API_BASE}/api/candidates", params=params or {}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
    return {"total": 0, "candidates": []}


def fetch_analytics():
    """Fetch dashboard analytics."""
    try:
        resp = requests.get(f"{API_BASE}/api/analytics", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {
        "total": 0, "shortlisted": 0, "rejected": 0,
        "manual_review": 0, "avg_score": 0,
        "applications_by_role": {}, "score_distribution": [],
        "status_over_time": [], "top_skills": [],
    }


def update_status(candidate_id: str, new_status: str, notes: str = ""):
    """Update candidate status via API."""
    try:
        resp = requests.patch(
            f"{API_BASE}/api/candidates/{candidate_id}/status",
            data={"status": new_status, "notes": notes},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def trigger_notifications(candidate_id: str):
    """Trigger notifications for a candidate."""
    try:
        resp = requests.post(f"{API_BASE}/api/notify/{candidate_id}", timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def main():
    st.set_page_config(
        page_title="Recruiter Dashboard | AI Recruitment",
        page_icon="📊",
        layout="wide",
    )

    # Custom CSS
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        .stApp { font-family: 'Inter', sans-serif; }

        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            text-align: center;
            border-top: 4px solid;
        }
        .metric-card h3 { margin: 0; font-size: 2rem; font-weight: 700; }
        .metric-card p { margin: 0.3rem 0 0; color: #666; font-size: 0.9rem; }

        .status-shortlisted {
            background: #d4edda; color: #155724;
            padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        }
        .status-rejected {
            background: #f8d7da; color: #721c24;
            padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        }
        .status-manual_review {
            background: #fff3cd; color: #856404;
            padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        }

        .candidate-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 1rem;
            border-left: 4px solid;
        }
    </style>
    """, unsafe_allow_html=True)

    # Password check
    if not check_password():
        return

    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem 2rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; font-size: 1.8rem;">📊 Recruiter Dashboard</h1>
        <p style="margin: 0.3rem 0 0; opacity: 0.9;">AI Recruitment Automation — Candidate Management</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar Filters ──────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Filters")

        role_filter = st.multiselect(
            "Role",
            options=["backend_developer", "data_scientist", "frontend_developer", "devops_engineer"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

        status_filter = st.multiselect(
            "Status",
            options=["shortlisted", "rejected", "manual_review"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

        min_score = st.slider("Minimum Score", 0, 100, 0)

        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
        )

        st.markdown("---")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # ── Fetch Data ───────────────────────────────────────────────────────
    analytics = fetch_analytics()

    params = {}
    if min_score > 0:
        params["min_score"] = min_score

    data = fetch_candidates(params)
    candidates = data.get("candidates", [])

    # Apply local filters
    if role_filter:
        candidates = [c for c in candidates if c.get("role_applied") in role_filter]
    if status_filter:
        candidates = [c for c in candidates if c.get("status") in status_filter]

    # ── Tabs ─────────────────────────────────────────────────────────────
    tab_candidates, tab_charts = st.tabs(["👥 Candidates", "📈 Analytics & Charts"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CANDIDATES TAB
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_candidates:
        # Metrics row
        m1, m2, m3, m4, m5 = st.columns(5)

        with m1:
            st.markdown(f"""
            <div class="metric-card" style="border-color: #667eea;">
                <h3>{analytics['total']}</h3>
                <p>Total Applications</p>
            </div>
            """, unsafe_allow_html=True)

        with m2:
            st.markdown(f"""
            <div class="metric-card" style="border-color: #28a745;">
                <h3>{analytics['shortlisted']}</h3>
                <p>Shortlisted</p>
            </div>
            """, unsafe_allow_html=True)

        with m3:
            st.markdown(f"""
            <div class="metric-card" style="border-color: #dc3545;">
                <h3>{analytics['rejected']}</h3>
                <p>Rejected</p>
            </div>
            """, unsafe_allow_html=True)

        with m4:
            st.markdown(f"""
            <div class="metric-card" style="border-color: #ffc107;">
                <h3>{analytics['manual_review']}</h3>
                <p>Manual Review</p>
            </div>
            """, unsafe_allow_html=True)

        with m5:
            st.markdown(f"""
            <div class="metric-card" style="border-color: #17a2b8;">
                <h3>{analytics['avg_score']}</h3>
                <p>Avg Match Score</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        # Export button
        if candidates:
            df = pd.DataFrame(candidates)
            col_export, col_count = st.columns([1, 3])
            with col_export:
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine="openpyxl")
                st.download_button(
                    "📥 Export to Excel",
                    data=buffer.getvalue(),
                    file_name=f"candidates_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with col_count:
                st.markdown(f"**Showing {len(candidates)} candidates**")

        # Candidate table
        if not candidates:
            st.info("No candidates found. Submit applications through the candidate portal.")
        else:
            for c in candidates:
                status = c.get("status", "unknown")
                score = c.get("match_score", 0) or 0
                name = c.get("name", "Unknown")
                role = (c.get("role_applied", "") or "").replace("_", " ").title()

                # Color-code based on status
                border_color = {
                    "shortlisted": "#28a745",
                    "rejected": "#dc3545",
                    "manual_review": "#ffc107",
                }.get(status, "#999")

                status_class = f"status-{status}"

                with st.expander(
                    f"{'🟢' if status == 'shortlisted' else '🔴' if status == 'rejected' else '🟡'} "
                    f"{name} — {role} — Score: {score}/100 — {status.replace('_', ' ').title()}"
                ):
                    # Overview
                    col_info, col_score = st.columns([2, 1])

                    with col_info:
                        st.markdown(f"**Email:** {c.get('email', 'N/A')}")
                        st.markdown(f"**Phone:** {c.get('phone', 'N/A')}")
                        st.markdown(f"**City:** {c.get('city', 'N/A')}")
                        st.markdown(f"**College:** {c.get('college', 'N/A')}")
                        st.markdown(f"**Experience:** {c.get('experience_years', 0)} years")
                        st.markdown(f"**Education:** {c.get('education_degree', 'N/A')}")

                        if c.get("github_url"):
                            st.markdown(f"**GitHub:** [{c['github_url']}]({c['github_url']}) (Score: {c.get('github_score', 'N/A')})")

                    with col_score:
                        # Score gauge
                        fig = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=score,
                            title={"text": "Match Score"},
                            gauge={
                                "axis": {"range": [0, 100]},
                                "bar": {"color": border_color},
                                "steps": [
                                    {"range": [0, 50], "color": "#f8d7da"},
                                    {"range": [50, 65], "color": "#fff3cd"},
                                    {"range": [65, 100], "color": "#d4edda"},
                                ],
                            },
                        ))
                        fig.update_layout(height=200, margin=dict(t=40, b=10, l=30, r=30))
                        st.plotly_chart(fig, use_container_width=True)

                    # AI Summary
                    if c.get("ai_summary"):
                        st.markdown(f"**AI Summary:** {c['ai_summary']}")

                    # Skills
                    col_matched, col_missing = st.columns(2)
                    with col_matched:
                        matched = c.get("matched_skills", [])
                        if matched:
                            st.markdown("**✅ Matched Skills:**")
                            st.markdown(", ".join(f"`{s}`" for s in matched))
                    with col_missing:
                        missing = c.get("missing_skills", [])
                        if missing:
                            st.markdown("**❌ Missing Skills:**")
                            st.markdown(", ".join(f"`{s}`" for s in missing))

                    # All skills from resume
                    all_skills = c.get("skills", [])
                    if all_skills:
                        st.markdown("**📋 All Resume Skills:**")
                        st.markdown(", ".join(f"`{s}`" for s in all_skills))

                    # Red flags
                    red_flags = c.get("red_flags", [])
                    if red_flags:
                        st.markdown("**🚩 Red Flags:**")
                        for flag in red_flags:
                            st.warning(flag)

                    # Filter reason
                    if c.get("filter_reason"):
                        st.markdown(f"**Filter Decision:** {c['filter_reason']}")

                    # Role suggestion
                    if c.get("role_suggestion"):
                        st.info(f"💡 {c['role_suggestion']}")

                    st.markdown("---")

                    # Manual override
                    st.markdown("**🔧 Manual Override:**")
                    col_status, col_notes, col_btn = st.columns([1, 2, 1])

                    cid = c.get("candidate_id", "")

                    with col_status:
                        new_status = st.selectbox(
                            "New Status",
                            ["shortlisted", "rejected", "manual_review"],
                            index=["shortlisted", "rejected", "manual_review"].index(status) if status in ["shortlisted", "rejected", "manual_review"] else 0,
                            key=f"status_{cid}",
                        )

                    with col_notes:
                        notes = st.text_area("Notes", key=f"notes_{cid}", height=68)

                    with col_btn:
                        st.markdown("")
                        if st.button("💾 Save", key=f"save_{cid}"):
                            if update_status(cid, new_status, notes):
                                st.success("✅ Status updated!")
                                st.rerun()
                            else:
                                st.error("❌ Update failed")

                        if st.button("📧 Notify", key=f"notify_{cid}"):
                            result = trigger_notifications(cid)
                            if result:
                                st.success(
                                    f"Email: {'✅' if result.get('email_sent') else '❌'} | "
                                    f"WhatsApp: {'✅' if result.get('whatsapp_sent') else '❌'}"
                                )
                            else:
                                st.error("❌ Notification failed")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CHARTS TAB
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_charts:
        col_chart1, col_chart2 = st.columns(2)

        # Chart 1: Applications per Role (bar)
        with col_chart1:
            st.markdown("### Applications per Role")
            role_data = analytics.get("applications_by_role", {})
            if role_data:
                fig = px.bar(
                    x=[k.replace("_", " ").title() for k in role_data.keys()],
                    y=list(role_data.values()),
                    labels={"x": "Role", "y": "Applications"},
                    color_discrete_sequence=["#667eea"],
                )
                fig.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data yet")

        # Chart 2: Score Distribution (histogram)
        with col_chart2:
            st.markdown("### Score Distribution")
            score_dist = analytics.get("score_distribution", [])
            if score_dist:
                fig = px.bar(
                    x=[d["range"] for d in score_dist],
                    y=[d["count"] for d in score_dist],
                    labels={"x": "Score Range", "y": "Candidates"},
                    color_discrete_sequence=["#764ba2"],
                )
                fig.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data yet")

        col_chart3, col_chart4 = st.columns(2)

        # Chart 3: Shortlist Rate Over Time (line)
        with col_chart3:
            st.markdown("### Status Over Time")
            timeline = analytics.get("status_over_time", [])
            if timeline:
                df_timeline = pd.DataFrame(timeline)
                fig = px.line(
                    df_timeline,
                    x="date",
                    y="count",
                    color="status",
                    labels={"date": "Date", "count": "Candidates", "status": "Status"},
                    color_discrete_map={
                        "shortlisted": "#28a745",
                        "rejected": "#dc3545",
                        "manual_review": "#ffc107",
                    },
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data yet")

        # Chart 4: Top Skills (horizontal bar)
        with col_chart4:
            st.markdown("### Top Skills in Talent Pool")
            top_skills = analytics.get("top_skills", [])
            if top_skills:
                fig = px.bar(
                    x=[s["count"] for s in top_skills[:15]],
                    y=[s["skill"] for s in top_skills[:15]],
                    orientation="h",
                    labels={"x": "Candidates", "y": "Skill"},
                    color_discrete_sequence=["#11998e"],
                )
                fig.update_layout(
                    showlegend=False,
                    height=350,
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data yet")


if __name__ == "__main__":
    main()
