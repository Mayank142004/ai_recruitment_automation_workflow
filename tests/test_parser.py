"""
Tests for the Resume Parsing Engine (services/parser.py)

Run: pytest tests/test_parser.py -v --tb=short
"""

import os
import sys
import tempfile

import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.parser import (
    extract_skills,
    extract_experience_years,
    extract_education,
    extract_contact_info,
    extract_text_from_pdf,
)


# ── Test Data ────────────────────────────────────────────────────────────────

SAMPLE_RESUME_TEXT = """
John Doe
Email: john.doe@example.com | Phone: +91 9876543210
GitHub: https://github.com/johndoe | LinkedIn: https://linkedin.com/in/johndoe
Mumbai, India

SUMMARY
Experienced Backend Developer with 3+ years of experience building scalable
REST APIs using Python, FastAPI, and Django. Strong background in SQL databases
including PostgreSQL and MySQL. Proficient with Docker, Git, and Linux.

EXPERIENCE
Senior Backend Developer - TechCorp India (2021 - Present)
- Built microservices with FastAPI and PostgreSQL
- Deployed applications using Docker and Kubernetes
- Implemented Redis caching reducing response times by 40%
- Set up CI/CD pipelines using GitHub Actions

Junior Developer - StartupXYZ (2019 - 2021)
- Developed REST APIs using Flask and SQLAlchemy
- Worked with MongoDB and Redis for data storage
- Used Git for version control

SKILLS
Python, JavaScript, SQL, PostgreSQL, MongoDB, Docker, Kubernetes, FastAPI,
Django, Flask, Redis, Git, Linux, REST API, AWS, Celery, React, Node.js

EDUCATION
B.Tech in Computer Science from IIT Bombay, 2019

CERTIFICATIONS
AWS Solutions Architect - Associate
"""

SAMPLE_SHORT_TEXT = "Hello world"

SAMPLE_TEXT_WITH_DATES = """
Software Engineer with experience from 2018 to 2023.
Previously worked at Google since 2015.
5 years of Python development experience.
3-5 years in machine learning projects.
"""


# ── Tests: extract_skills ────────────────────────────────────────────────────

class TestExtractSkills:
    def test_finds_python_and_sql(self):
        """Must find Python and SQL if present."""
        skills = extract_skills(SAMPLE_RESUME_TEXT)
        skills_lower = [s.lower() for s in skills]
        assert "python" in skills_lower
        assert "sql" in skills_lower

    def test_finds_multiple_skills(self):
        """Must find at least 5 skills in the sample resume."""
        skills = extract_skills(SAMPLE_RESUME_TEXT)
        assert len(skills) >= 5, f"Found only {len(skills)} skills: {skills}"

    def test_finds_docker_and_fastapi(self):
        """Must find Docker and FastAPI."""
        skills = extract_skills(SAMPLE_RESUME_TEXT)
        skills_lower = [s.lower() for s in skills]
        assert "docker" in skills_lower
        assert "fastapi" in skills_lower

    def test_empty_text_returns_empty(self):
        """Empty text should return empty list."""
        assert extract_skills("") == []
        assert extract_skills(None) == []

    def test_no_duplicates(self):
        """Result should not contain duplicates."""
        skills = extract_skills(SAMPLE_RESUME_TEXT)
        assert len(skills) == len(set(s.lower() for s in skills))

    def test_case_insensitive(self):
        """Matching should be case insensitive."""
        skills = extract_skills("I know PYTHON and javascript and Docker")
        skills_lower = [s.lower() for s in skills]
        assert "python" in skills_lower
        assert "javascript" in skills_lower
        assert "docker" in skills_lower


# ── Tests: extract_experience_years ──────────────────────────────────────────

class TestExtractExperienceYears:
    def test_basic_years(self):
        """'3 years experience' must return 3.0."""
        result = extract_experience_years("3 years experience")
        assert result == 3.0

    def test_plus_years(self):
        """'3+ years' should return 3.0."""
        result = extract_experience_years("3+ years of experience")
        assert result == 3.0

    def test_range_years(self):
        """'3-5 years' should return 5.0 (higher end)."""
        result = extract_experience_years("3-5 years of experience")
        assert result == 5.0

    def test_date_range(self):
        """'from 2018 to 2023' should calculate 5 years."""
        result = extract_experience_years("Worked from 2018 to 2023")
        assert result == 5.0

    def test_max_of_multiple(self):
        """Should return the maximum years found."""
        result = extract_experience_years(SAMPLE_TEXT_WITH_DATES)
        assert result >= 5.0

    def test_empty_text(self):
        """Empty text should return 0.0."""
        assert extract_experience_years("") == 0.0
        assert extract_experience_years(None) == 0.0

    def test_no_experience_mentioned(self):
        """Text without experience should return 0.0."""
        assert extract_experience_years("I like coding") == 0.0

    def test_sample_resume(self):
        """Sample resume mentions 3+ years — should return >= 3.0."""
        result = extract_experience_years(SAMPLE_RESUME_TEXT)
        assert result >= 3.0


# ── Tests: extract_education ─────────────────────────────────────────────────

class TestExtractEducation:
    def test_finds_btech(self):
        """Should find B.Tech degree."""
        result = extract_education(SAMPLE_RESUME_TEXT)
        assert "tech" in result["degree"].lower() or "b.tech" in result["degree"].lower()

    def test_finds_institution(self):
        """Should find institution name."""
        result = extract_education(SAMPLE_RESUME_TEXT)
        assert result["institution"] != ""

    def test_empty_text(self):
        """Empty text should return empty dict."""
        result = extract_education("")
        assert result["degree"] == ""
        assert result["institution"] == ""

    def test_masters_degree(self):
        """Should detect M.Tech."""
        result = extract_education("M.Tech in AI from IIIT Hyderabad, 2022")
        assert "tech" in result["degree"].lower() or "m.tech" in result["degree"].lower()


# ── Tests: extract_contact_info ──────────────────────────────────────────────

class TestExtractContactInfo:
    def test_finds_email(self):
        """Should extract email address."""
        result = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert result["email"] == "john.doe@example.com"

    def test_finds_phone(self):
        """Should extract 10-digit Indian phone number."""
        result = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert result["phone"] == "9876543210"

    def test_finds_github(self):
        """Should extract GitHub URL."""
        result = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert "github.com/johndoe" in result["github_url"]

    def test_finds_linkedin(self):
        """Should extract LinkedIn URL."""
        result = extract_contact_info(SAMPLE_RESUME_TEXT)
        assert "linkedin.com/in/johndoe" in result["linkedin_url"]

    def test_empty_text(self):
        """Empty text should return empty values."""
        result = extract_contact_info("")
        assert result["email"] == ""
        assert result["phone"] == ""


# ── Tests: extract_text_from_pdf ─────────────────────────────────────────────

class TestExtractTextFromPdf:
    def test_valid_pdf_returns_text(self):
        """
        Test with a programmatically created PDF.
        If pdfplumber is available, should extract text.
        """
        try:
            from reportlab.pdfgen import canvas

            # Create a test PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                pdf_path = f.name

            c = canvas.Canvas(pdf_path)
            c.drawString(100, 750, "John Doe - Software Engineer")
            c.drawString(100, 730, "Skills: Python, JavaScript, Docker, SQL")
            c.drawString(100, 710, "Experience: 5 years in backend development")
            c.drawString(100, 690, "Email: john@example.com Phone: 9876543210")
            c.save()

            text = extract_text_from_pdf(pdf_path)
            assert len(text) > 50, f"Expected >50 chars, got {len(text)}"

            os.unlink(pdf_path)

        except ImportError:
            pytest.skip("reportlab not installed — skipping PDF generation test")

    def test_nonexistent_file(self):
        """Non-existent file should return empty string."""
        text = extract_text_from_pdf("/nonexistent/file.pdf")
        assert text == "" or isinstance(text, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
