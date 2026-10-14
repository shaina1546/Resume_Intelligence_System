"""
src/skill_gap.py
================
Stage 7 — Skill Gap Analysis

WHAT THIS MODULE DOES:
    Compares the skills on a candidate's resume against the skills
    required by a job description and produces a clear analysis of:
        - Which skills the candidate already has (matched)
        - Which required skills are missing (gaps)
        - What extra skills the candidate has (beyond requirements)
        - An overall match percentage

WHY IT EXISTS:
    Knowing the match score is useful, but the candidate specifically
    wants to know: "What should I learn to get this job?" This module
    answers that directly.

EXAMPLE:
    JD Required Skills:  Python, SQL, Docker, Kubernetes, Machine Learning
    Resume Skills:       Python, SQL, Machine Learning, React, Git

    → Matched:   Python, SQL, Machine Learning  (3 of 5 required = 60%)
    → Missing:   Docker, Kubernetes              (the gaps to fill)
    → Additional: React, Git                    (bonus skills)
"""

from typing import Dict, List

from src.utils import get_logger

logger = get_logger(__name__)


def analyze_skill_gap(
    resume_skills: List[str],
    jd_required_skills: List[str],
    jd_preferred_skills: List[str] = None,
    jd_requirement_groups=None,
) -> Dict:
    """
    Perform a full skill gap analysis.

    Parameters
    ----------
    resume_skills        : Skills found in the candidate's resume.
    jd_required_skills   : Skills marked as required in the JD.
    jd_preferred_skills  : Skills marked as preferred (optional) in the JD.

    Returns
    -------
    dict with keys:
        matched_skills         : Required skills the candidate HAS
        missing_required_skills: Required skills the candidate is MISSING (the gap)
        missing_preferred_skills: Preferred skills the candidate is MISSING
        additional_skills      : Resume skills NOT in the JD (bonus)
        match_percentage       : int (0–100), based on required skills only
        gap_count              : number of required skills missing
        total_required         : total number of required skills
    """
    if jd_preferred_skills is None:
        jd_preferred_skills = []

    # Normalise to lowercase sets for comparison
    resume_set    = {s.lower().strip(): s for s in resume_skills}
    required_set  = {s.lower().strip(): s for s in jd_required_skills}
    preferred_set = {s.lower().strip(): s for s in jd_preferred_skills}

    # Intersection: resume skills that are in the required list
    matched_keys  = resume_set.keys() & required_set.keys()

    # Required skills missing from the resume (the skill gap)
    missing_required_keys  = required_set.keys() - resume_set.keys()

    # Preferred skills missing from the resume
    missing_preferred_keys = preferred_set.keys() - resume_set.keys()

    # Skills the candidate has that are NOT in the required or preferred lists
    all_jd_keys = required_set.keys() | preferred_set.keys()
    additional_keys = resume_set.keys() - all_jd_keys

    # Reconstruct with original casing (prefer JD casing for required/preferred)
    matched   = sorted([required_set[k] for k in matched_keys])
    missing_r = sorted([required_set[k] for k in missing_required_keys])
    missing_p = sorted([preferred_set[k] for k in missing_preferred_keys])
    additional = sorted([resume_set[k] for k in additional_keys])

    from src.requirements import coverage_stats
    groups = jd_requirement_groups if jd_requirement_groups is not None else [[s] for s in required_set.values()]
    stats = coverage_stats(resume_skills, groups)
    matched = stats["matched_skills"]
    missing_r = stats["missing"]
    total_required = stats["total_groups"]
    match_pct = round(stats["coverage"] * 100)

    return {
        "matched_skills":          matched,
        "missing_required_skills": missing_r,
        "missing_preferred_skills": missing_p,
        "additional_skills":       additional,
        "match_percentage":        match_pct,
        "gap_count":               len(missing_r),
        "total_required":          total_required,
        "matched_required_groups": stats["matched_groups"],
        "required_groups": groups,
    }


def get_gap_summary(gap_result: Dict) -> str:
    """
    Generate a human-readable summary of the skill gap analysis.

    This is displayed in the Streamlit dashboard to help the user
    understand the results at a glance.

    Parameters
    ----------
    gap_result : The dict returned by analyze_skill_gap.

    Returns
    -------
    A plain-English summary string.
    """
    matched   = gap_result.get("matched_skills", [])
    missing_r = gap_result.get("missing_required_skills", [])
    total     = gap_result.get("total_required", 0)
    pct       = gap_result.get("match_percentage", 0)

    lines = []

    if total == 0:
        lines.append("No required skills were identified in the job description.")
        return "\n".join(lines)

    lines.append(f"You match **{gap_result.get('matched_required_groups', len(matched))} of {total}** required skill requirements ({pct}%).")

    if not missing_r:
        lines.append("✅ You have all the required skills for this position!")
    else:
        lines.append(
            f"⚠️  You are missing **{len(missing_r)}** required skill(s): "
            + ", ".join(f"`{s}`" for s in missing_r)
        )
        lines.append(
            "Consider learning these skills to strengthen your application."
        )

    return "\n\n".join(lines)
