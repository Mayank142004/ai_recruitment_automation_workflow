"""
Tests for the Filtering Engine (services/filter.py)

Tests shortlist, reject, and manual_review cases against config.yaml rules.
Run: pytest tests/test_filter.py -v --tb=short
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.filter import (
    filter_candidate,
    load_config,
    get_role_config,
    get_all_roles,
    get_role_names,
)


# ── Test: Config Loading ────────────────────────────────────────────────────

class TestConfigLoading:
    def test_config_loads(self):
        """config.yaml should load without errors."""
        config = load_config(force_reload=True)
        assert "roles" in config
        assert len(config["roles"]) > 0

    def test_all_four_roles_present(self):
        """config.yaml must define all 4 roles."""
        roles = get_all_roles()
        expected = {"backend_developer", "data_scientist", "frontend_developer", "devops_engineer"}
        assert expected.issubset(set(roles.keys())), (
            f"Missing roles: {expected - set(roles.keys())}"
        )

    def test_role_config_has_required_fields(self):
        """Each role must have required_skills, min_experience_years, min_match_score."""
        roles = get_all_roles()
        for name, config in roles.items():
            assert "required_skills" in config, f"{name} missing required_skills"
            assert "min_experience_years" in config, f"{name} missing min_experience_years"
            assert "min_match_score" in config, f"{name} missing min_match_score"
            assert isinstance(config["required_skills"], list)

    def test_get_role_config_returns_dict(self):
        """get_role_config should return dict for valid role."""
        config = get_role_config("backend_developer")
        assert config is not None
        assert "required_skills" in config

    def test_get_role_config_invalid_role(self):
        """get_role_config should return None for unknown role."""
        config = get_role_config("nonexistent_role")
        assert config is None

    def test_get_role_names(self):
        """get_role_names should return list of strings."""
        names = get_role_names()
        assert isinstance(names, list)
        assert len(names) >= 4
        assert "backend_developer" in names


# ── Test: Shortlist Case ────────────────────────────────────────────────────

class TestShortlistCase:
    def test_shortlisted_when_all_criteria_met(self):
        """
        score=80, has all required skills, experience >= threshold
        → should be shortlisted.
        """
        score_data = {
            "match_score": 80,
            "recommendation": "shortlist",
        }
        parsed_data = {
            "skills": ["Python", "SQL", "REST API", "Docker", "FastAPI"],
            "experience_years": 3.0,
            "education": {"degree": "B.Tech", "institution": "IIT"},
        }

        result = filter_candidate(score_data, parsed_data, "backend_developer")

        assert result["status"] == "shortlisted"
        assert result["score"] == 80
        assert result["shortlist_priority"] in range(1, 6)

    def test_high_score_gets_high_priority(self):
        """Score >= 90 should get priority 1."""
        score_data = {"match_score": 95}
        parsed_data = {
            "skills": ["Python", "SQL", "REST API"],
            "experience_years": 5.0,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "backend_developer")
        assert result["shortlist_priority"] == 1


# ── Test: Rejection Case ────────────────────────────────────────────────────

class TestRejectCase:
    def test_rejected_when_low_score(self):
        """
        score=30, missing required skills → should be rejected.
        """
        score_data = {
            "match_score": 30,
            "recommendation": "reject",
        }
        parsed_data = {
            "skills": ["HTML", "CSS"],  # Missing Python, SQL, REST API
            "experience_years": 0.5,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "backend_developer")

        assert result["status"] == "rejected"
        assert result["score"] == 30
        assert "reason" in result

    def test_rejected_with_missing_required_skills(self):
        """Even with high score, missing required skills → rejected or manual_review."""
        score_data = {"match_score": 85}
        parsed_data = {
            "skills": ["Docker", "Kubernetes"],  # Missing Python, SQL, REST API
            "experience_years": 5.0,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "backend_developer")
        # Should be manual_review (good score but missing skills) or rejected
        assert result["status"] in ("rejected", "manual_review")

    def test_rejected_with_no_experience(self):
        """No experience and low score → rejected."""
        score_data = {"match_score": 40}
        parsed_data = {
            "skills": ["Python"],
            "experience_years": 0.0,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "backend_developer")
        assert result["status"] == "rejected"


# ── Test: Manual Review Case ────────────────────────────────────────────────

class TestManualReviewCase:
    def test_manual_review_borderline_score(self):
        """
        score=58 (within min_score-15 to min_score for backend=65)
        → should be manual_review.
        """
        score_data = {"match_score": 58}
        parsed_data = {
            "skills": ["Python", "SQL", "REST API"],
            "experience_years": 2.0,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "backend_developer")
        # 58 is between 50 (65-15) and 65 → manual_review
        assert result["status"] == "manual_review"

    def test_manual_review_with_good_score_but_missing_skills(self):
        """Good score but missing required skills → manual_review."""
        score_data = {"match_score": 75}
        parsed_data = {
            "skills": ["Python", "Docker"],  # Missing SQL, REST API
            "experience_years": 3.0,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "backend_developer")
        assert result["status"] == "manual_review"


# ── Test: Different Roles ────────────────────────────────────────────────────

class TestDifferentRoles:
    def test_data_scientist_requires_education(self):
        """Data scientist role requires education — missing degree should affect decision."""
        score_data = {"match_score": 75}
        parsed_data = {
            "skills": ["Python", "Machine Learning", "pandas", "TensorFlow"],
            "experience_years": 2.0,
            "education": {"degree": "", "institution": ""},  # No education
        }

        result = filter_candidate(score_data, parsed_data, "data_scientist")
        # Education is required for data scientist
        assert result["status"] in ("rejected", "manual_review")

    def test_frontend_developer(self):
        """Frontend developer with all criteria met → shortlisted."""
        score_data = {"match_score": 70}
        parsed_data = {
            "skills": ["JavaScript", "React", "TypeScript", "CSS"],
            "experience_years": 2.0,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "frontend_developer")
        assert result["status"] == "shortlisted"

    def test_devops_higher_threshold(self):
        """DevOps has min_match_score=70, so 65 should not shortlist."""
        score_data = {"match_score": 65}
        parsed_data = {
            "skills": ["Docker", "Linux", "Git", "AWS"],
            "experience_years": 3.0,
            "education": {},
        }

        result = filter_candidate(score_data, parsed_data, "devops_engineer")
        # 65 < 70 threshold, but within borderline → manual_review
        assert result["status"] in ("manual_review", "rejected")

    def test_unknown_role_returns_manual_review(self):
        """Unknown role should return manual_review by default."""
        result = filter_candidate(
            {"match_score": 50},
            {"skills": [], "experience_years": 0, "education": {}},
            "nonexistent_role",
        )
        assert result["status"] == "manual_review"


# ── Test: Result Structure ──────────────────────────────────────────────────

class TestResultStructure:
    def test_result_has_required_keys(self):
        """Filter result must have status, reason, score, shortlist_priority."""
        result = filter_candidate(
            {"match_score": 50},
            {"skills": ["Python"], "experience_years": 1, "education": {}},
            "backend_developer",
        )

        assert "status" in result
        assert "reason" in result
        assert "score" in result
        assert "shortlist_priority" in result

    def test_status_is_valid(self):
        """Status must be one of the three valid values."""
        result = filter_candidate(
            {"match_score": 50},
            {"skills": [], "experience_years": 0, "education": {}},
            "backend_developer",
        )
        assert result["status"] in ("shortlisted", "rejected", "manual_review")

    def test_priority_in_range(self):
        """Shortlist priority must be 1-5."""
        result = filter_candidate(
            {"match_score": 50},
            {"skills": [], "experience_years": 0, "education": {}},
            "backend_developer",
        )
        assert 1 <= result["shortlist_priority"] <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
