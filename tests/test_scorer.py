"""
Tests for the Groq LLM Scoring Service (services/scorer.py)

Uses unittest.mock to avoid actual API calls.
Run: pytest tests/test_scorer.py -v --tb=short
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.scorer import (
    _parse_llm_response,
    score_candidate,
    _mock_score,
)


# ── Test Data ────────────────────────────────────────────────────────────────

VALID_JSON_RESPONSE = json.dumps({
    "match_score": 78,
    "matched_skills": ["Python", "SQL", "Docker"],
    "missing_skills": ["Kubernetes"],
    "experience_fit": "yes",
    "education_fit": "partial",
    "candidate_summary": "Strong backend developer with relevant experience.",
    "red_flags": [],
    "recommendation": "shortlist",
})

MARKDOWN_WRAPPED_RESPONSE = f"""```json
{VALID_JSON_RESPONSE}
```"""

MALFORMED_RESPONSE = "This is not JSON at all, just text"

PARTIAL_RESPONSE = json.dumps({
    "match_score": 65,
    "matched_skills": ["Python"],
    # Missing several required keys
})

SAMPLE_RESUME = """
John Doe - Python Developer
3 years experience with Python, Django, FastAPI, SQL, PostgreSQL.
B.Tech from IIT Delhi, 2020.
"""


# ── Tests: _parse_llm_response ──────────────────────────────────────────────

class TestParseLlmResponse:
    def test_valid_json(self):
        """Should parse valid JSON correctly."""
        result = _parse_llm_response(VALID_JSON_RESPONSE)
        assert result is not None
        assert result["match_score"] == 78
        assert "Python" in result["matched_skills"]
        assert result["recommendation"] == "shortlist"

    def test_markdown_wrapped_json(self):
        """Should strip ```json ``` fences and parse correctly."""
        result = _parse_llm_response(MARKDOWN_WRAPPED_RESPONSE)
        assert result is not None
        assert result["match_score"] == 78

    def test_malformed_response(self):
        """Malformed text should return None."""
        result = _parse_llm_response(MALFORMED_RESPONSE)
        assert result is None

    def test_empty_response(self):
        """Empty/None input should return None."""
        assert _parse_llm_response("") is None
        assert _parse_llm_response(None) is None

    def test_partial_response_fills_defaults(self):
        """Missing keys should be filled with defaults."""
        result = _parse_llm_response(PARTIAL_RESPONSE)
        assert result is not None
        assert result["match_score"] == 65
        assert "recommendation" in result  # Default filled

    def test_score_clamped_to_100(self):
        """Score above 100 should be clamped."""
        resp = json.dumps({
            "match_score": 150,
            "matched_skills": [],
            "missing_skills": [],
            "experience_fit": "yes",
            "education_fit": "yes",
            "candidate_summary": "Test",
            "red_flags": [],
            "recommendation": "shortlist",
        })
        result = _parse_llm_response(resp)
        assert result["match_score"] == 100

    def test_score_clamped_to_0(self):
        """Negative score should be clamped to 0."""
        resp = json.dumps({
            "match_score": -10,
            "matched_skills": [],
            "missing_skills": [],
            "experience_fit": "no",
            "education_fit": "no",
            "candidate_summary": "Test",
            "red_flags": [],
            "recommendation": "reject",
        })
        result = _parse_llm_response(resp)
        assert result["match_score"] == 0

    def test_all_required_keys_present(self):
        """Parsed result must contain all required keys."""
        result = _parse_llm_response(VALID_JSON_RESPONSE)
        required = {
            "match_score", "matched_skills", "missing_skills",
            "experience_fit", "education_fit", "candidate_summary",
            "red_flags", "recommendation",
        }
        assert required.issubset(result.keys())


# ── Tests: score_candidate (mocked) ─────────────────────────────────────────

class TestScoreCandidate:
    @patch("services.scorer._get_groq_client")
    def test_returns_dict_with_required_keys(self, mock_get_client):
        """score_candidate must return dict with all required keys."""
        # Mock the Groq client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = VALID_JSON_RESPONSE
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = score_candidate(SAMPLE_RESUME, "Backend Developer JD", "backend_developer")

        assert isinstance(result, dict)
        assert "match_score" in result
        assert "matched_skills" in result
        assert "recommendation" in result
        assert 0 <= result["match_score"] <= 100

    @patch("services.scorer._get_groq_client")
    def test_retry_on_api_error(self, mock_get_client):
        """Should retry on API errors."""
        mock_client = MagicMock()
        # First call raises exception, second returns valid response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = VALID_JSON_RESPONSE
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_client.chat.completions.create.side_effect = [
            Exception("API Error"),
            mock_response,
        ]
        mock_get_client.return_value = mock_client

        result = score_candidate(
            SAMPLE_RESUME, "JD", "backend_developer",
            max_retries=2, retry_delay=0.1,
        )

        assert isinstance(result, dict)
        assert result["match_score"] == 78

    @patch("services.scorer._get_groq_client")
    def test_all_retries_exhausted_returns_mock(self, mock_get_client):
        """When all retries fail, should return mock score."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Always fails")
        mock_get_client.return_value = mock_client

        result = score_candidate(
            SAMPLE_RESUME, "JD", "backend_developer",
            max_retries=2, retry_delay=0.1,
        )

        assert isinstance(result, dict)
        assert "match_score" in result
        # Mock score should indicate it's a fallback
        assert any("mock" in str(f).lower() or "Mock" in str(f) for f in result.get("red_flags", []))

    def test_mock_score_returns_valid_dict(self):
        """_mock_score should return a valid scoring dict."""
        result = _mock_score(SAMPLE_RESUME, "backend_developer")
        assert isinstance(result, dict)
        assert 0 <= result["match_score"] <= 100
        assert result["recommendation"] in ("shortlist", "reject", "manual_review")
        assert isinstance(result["matched_skills"], list)

    @patch("services.scorer._get_groq_client")
    def test_handles_malformed_llm_output(self, mock_get_client):
        """Should handle cases where LLM returns non-JSON."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I cannot score this resume."
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 20
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = score_candidate(
            SAMPLE_RESUME, "JD", "backend_developer",
            max_retries=1, retry_delay=0.1,
        )

        # Should fall back to mock score
        assert isinstance(result, dict)
        assert "match_score" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
