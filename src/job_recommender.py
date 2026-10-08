"""
src/job_recommender.py
======================
Stage 8 — Job Role Recommendation Engine

WHAT THIS MODULE DOES:
    Given a candidate's skills, recommends the most suitable job roles
    by comparing the skills to a database of role–skill mappings.

WHY IT EXISTS:
    Even when we are not comparing against a specific job description,
    it is useful to know: "Given my skills, what roles am I best suited for?"
    This module answers that question.

DATA SOURCE:
    data/job_roles.csv — a CSV file with columns:
        Job Role, Skills, Description

    Each row represents one job role. The Skills column contains a
    semicolon-separated list of skills associated with that role.

HOW RECOMMENDATIONS WORK (step by step):
    1. Load the job roles from data/job_roles.csv.
    2. For each role, compute what fraction of the role's skills the
       candidate already has (a simple coverage ratio).
    3. Rank the roles by this score (highest first).
    4. Return the top N recommendations.

SCORING FORMULA (per role):
    score = (matched skills / total role skills) × 100

IMPORTANT:
    This is a heuristic ranking, not a guarantee of employability.
    Roles with fewer required skills may rank higher even if the
    candidate is a better fit for a more demanding role.
"""

import csv
from pathlib import Path
from typing import Dict, List

from src.utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------
# Path to the job roles data file
# ---------------------------------------------------------------
_ROLES_CSV = Path(__file__).parent.parent / "data" / "job_roles.csv"


# ---------------------------------------------------------------
# Internal: load job roles
# ---------------------------------------------------------------

def _load_job_roles() -> List[Dict]:
    """
    Load job role definitions from job_roles.csv.

    Returns a list of dicts, each with:
        role        : str — the job title
        skills      : list of str — skills required for this role
        description : str — short description of the role
    """
    if not _ROLES_CSV.exists():
        logger.error("job_roles.csv not found at %s", _ROLES_CSV)
        return []

    roles = []
    with open(_ROLES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            role_name = row.get("Job Role", "").strip()
            skills_raw = row.get("Skills", "").strip()
            description = row.get("Description", "").strip()

            if not role_name or role_name.startswith("#"):
                continue

            # Skills are semicolon-separated
            skills = [s.strip() for s in skills_raw.split(";") if s.strip()]

            roles.append({
                "role":        role_name,
                "skills":      skills,
                "description": description,
            })

    logger.info("Loaded %d job roles.", len(roles))
    return roles


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def recommend_roles(
    candidate_skills: List[str],
    top_n: int = 5,
) -> List[Dict]:
    """
    Recommend the most suitable job roles for a candidate.

    Parameters
    ----------
    candidate_skills : List of canonical skill names from the resume.
    top_n            : How many recommendations to return (default: 5).

    Returns
    -------
    List of dicts (sorted by score, highest first):
        [
            {
                "role":           "Data Scientist",
                "score":          82,
                "matched_skills": ["Python", "SQL", "Machine Learning"],
                "missing_skills": ["Deep Learning", "TensorFlow"],
                "description":    "..."
            },
            ...
        ]
    """
    if not candidate_skills:
        logger.warning("recommend_roles called with no candidate skills.")
        return []

    roles = _load_job_roles()
    if not roles:
        return []

    candidate_lower = {s.lower().strip() for s in candidate_skills}

    recommendations = []
    for role_info in roles:
        role_skills = role_info["skills"]

        if not role_skills:
            continue

        role_skills_lower = {s.lower().strip() for s in role_skills}

        # Skills the candidate already has for this role
        matched_lower = candidate_lower & role_skills_lower
        # Skills the candidate is missing for this role
        missing_lower = role_skills_lower - candidate_lower

        # Reconstruct original casing
        skill_lower_to_orig = {s.lower().strip(): s for s in role_skills}
        matched = sorted([skill_lower_to_orig[s] for s in matched_lower])
        missing = sorted([skill_lower_to_orig[s] for s in missing_lower])

        # Score = percentage of the role's skills that the candidate has
        score = int(round(len(matched) / len(role_skills) * 100))

        recommendations.append({
            "role":           role_info["role"],
            "score":          score,
            "matched_skills": matched,
            "missing_skills": missing,
            "description":    role_info["description"],
        })

    # Sort by score (descending), then alphabetically by role name for ties
    recommendations.sort(key=lambda x: (-x["score"], x["role"]))

    return recommendations[:top_n]
