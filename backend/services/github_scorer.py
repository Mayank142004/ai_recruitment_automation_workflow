"""
AI Recruitment Automation — GitHub Profile Scorer

Scores candidate GitHub profiles using the free public API (no auth needed).
Score formula: (public_repos * 2) + (followers * 0.5) + (total_stars * 1.5) + (recent_activity_bonus)
Capped at 100.
"""

import logging
import re
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


def _extract_username(github_url: str) -> str | None:
    """
    Extract GitHub username from a URL.

    Handles: github.com/username, https://github.com/username, etc.
    """
    if not github_url:
        return None

    match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', github_url)
    return match.group(1) if match else None


def score_github_profile(github_url: str) -> dict:
    """
    Score a GitHub profile based on public activity.

    Uses the free GitHub API (no auth needed for public repos).
    Rate limit: 60 requests/hour for unauthenticated requests.

    Scoring formula:
      - public_repos * 2 (max 30 points)
      - followers * 0.5 (max 15 points)
      - total_stars * 1.5 (max 30 points)
      - recent_activity_bonus (max 25 points based on 90-day commit activity)

    Args:
        github_url: GitHub profile URL (e.g., 'https://github.com/username').

    Returns:
        Dict with: score (0-100), repos, stars, followers, top_languages, profile_url.
    """
    result = {
        "score": 0,
        "repos": 0,
        "stars": 0,
        "followers": 0,
        "top_languages": [],
        "profile_url": github_url,
        "error": None,
    }

    username = _extract_username(github_url)
    if not username:
        result["error"] = "Could not extract GitHub username from URL"
        return result

    try:
        # ── Fetch user profile ───────────────────────────────────────────
        user_resp = requests.get(
            f"{GITHUB_API_BASE}/users/{username}",
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"},
        )

        if user_resp.status_code == 404:
            result["error"] = f"GitHub user '{username}' not found"
            return result

        if user_resp.status_code != 200:
            result["error"] = f"GitHub API error: {user_resp.status_code}"
            return result

        user_data = user_resp.json()
        result["repos"] = user_data.get("public_repos", 0)
        result["followers"] = user_data.get("followers", 0)

        # ── Fetch repositories ───────────────────────────────────────────
        repos_resp = requests.get(
            f"{GITHUB_API_BASE}/users/{username}/repos",
            params={"per_page": 100, "sort": "updated"},
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"},
        )

        total_stars = 0
        languages = {}
        recent_repos = 0
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)

        if repos_resp.status_code == 200:
            repos = repos_resp.json()

            for repo in repos:
                total_stars += repo.get("stargazers_count", 0)

                lang = repo.get("language")
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1

                # Check if updated in last 90 days
                updated_at = repo.get("updated_at", "")
                if updated_at:
                    try:
                        updated_date = datetime.strptime(
                            updated_at, "%Y-%m-%dT%H:%M:%SZ"
                        )
                        if updated_date > ninety_days_ago:
                            recent_repos += 1
                    except ValueError:
                        pass

        result["stars"] = total_stars
        result["top_languages"] = sorted(
            languages.keys(), key=lambda x: languages[x], reverse=True
        )[:5]

        # ── Calculate score ──────────────────────────────────────────────
        repo_score = min(result["repos"] * 2, 30)
        follower_score = min(result["followers"] * 0.5, 15)
        star_score = min(total_stars * 1.5, 30)
        activity_score = min(recent_repos * 5, 25)

        total_score = int(repo_score + follower_score + star_score + activity_score)
        result["score"] = min(total_score, 100)

        logger.info(
            f"GitHub score for {username}: {result['score']} "
            f"(repos={result['repos']}, stars={total_stars}, "
            f"followers={result['followers']})"
        )

    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        result["error"] = str(e)

    return result
