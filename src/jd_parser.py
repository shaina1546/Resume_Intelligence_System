"""
src/jd_parser.py
================
Stage 4 — Job Description Information Extraction

WHAT THIS MODULE DOES:
    Given raw job description text (typed or pasted by the user),
    this module extracts:

        {
            "job_title":        str,
            "required_skills":  [str, ...],
            "preferred_skills": [str, ...],
            "education":        [str, ...],
            "experience":       [str, ...],
            "responsibilities": [str, ...],
            "qualifications":   [str, ...]
        }

WHY IT EXISTS:
    Before we can compare a resume to a job, we need to understand
    what the job requires. This module turns a raw job description
    text into structured requirements.

APPROACH:
    Similar to resume_parser.py but with JD-specific heading aliases.
    We also extract skills that appear *anywhere* in the JD, even if
    there is no explicit "Skills" section.
"""

import re
from typing import Dict, List, Optional

from src.utils import get_logger
from src.text_preprocessor import preprocess_for_parsing, normalize_section_heading

logger = get_logger(__name__)


# ---------------------------------------------------------------
# Section heading aliases for job descriptions
# ---------------------------------------------------------------

JD_SECTION_ALIASES: Dict[str, List[str]] = {
    "required_skills": [
        "required skills",
        "technical skills",
        "must have",
        "must-have",
        "skills",
        "required technical skills",
        "key skills",
        "core skills",
        "skills required",
        "skills & experience",
        "tools and technologies",
        "tech stack",
    ],
    "preferred_skills": [
        "preferred skills",
        "nice to have",
        "good to have",
        "preferred qualifications",
        "bonus skills",
        "preferred experience",
        "optional skills",
        "plus points",
    ],
    "qualifications": [
        "qualifications",
        "requirements",
        "required qualifications",
        "minimum qualifications",
        "basic qualifications",
        "job requirements",
        "what we're looking for",
        "what we look for",
        "candidate requirements",
    ],
    "responsibilities": [
        "responsibilities",
        "job responsibilities",
        "key responsibilities",
        "role responsibilities",
        "duties",
        "what you'll do",
        "what you will do",
        "your role",
        "role overview",
        "about the role",
        "day to day",
    ],
    "education": [
        "education",
        "educational requirements",
        "academic requirements",
        "degree requirements",
        "qualifications and education",
    ],
    "experience": [
        "experience",
        "required experience",
        "work experience",
        "professional experience",
        "years of experience",
    ],
    "about_role": [
        "about the job",
        "job description",
        "about this role",
        "position overview",
        "role description",
        "job summary",
        "overview",
    ],
}

# Build flat lookup: normalised_alias → canonical_key
_JD_ALIAS_LOOKUP: Dict[str, str] = {}
for canonical, aliases in JD_SECTION_ALIASES.items():
    for alias in aliases:
        _JD_ALIAS_LOOKUP[alias.lower()] = canonical


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def parse_jd(raw_text: str) -> Dict:
    """
    Main function: parse a job description into a structured dictionary.

    Parameters
    ----------
    raw_text : str
        The full text of the job description (may be pasted or
        extracted from a file).

    Returns
    -------
    dict with keys:
        job_title, required_skills, preferred_skills,
        education, experience, responsibilities, qualifications
    """
    if not raw_text or not raw_text.strip():
        logger.warning("parse_jd received empty text.")
        return _empty_jd_result()

    # Light preprocessing
    text = preprocess_for_parsing(raw_text)

    # Try to extract the job title from the first non-empty line
    job_title = _extract_job_title(text)

    # Split into sections
    sections = _split_jd_into_sections(text)
    from src.requirements import analyse_requirements
    requirements = analyse_requirements(sections)

    return {
        "job_title":        job_title,
        **requirements,
        "required_skills": requirements["required_skills"],
        "preferred_skills": requirements["preferred_skills"],
        "education":        _clean_lines(sections.get("education", [])),
        "experience":       _clean_lines(sections.get("experience", [])),
        "responsibilities": _clean_lines(sections.get("responsibilities", [])),
        "qualifications":   _clean_lines(sections.get("qualifications", [])),
    }


# ---------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------

def _empty_jd_result() -> Dict:
    """Return a blank JD result with all keys present."""
    return {
        "job_title":        "",
        "required_skills":  [],
        "preferred_skills": [],
        "education":        [],
        "experience":       [],
        "responsibilities": [],
        "qualifications":   [],
    }


def _extract_job_title(text: str) -> str:
    """
    Attempt to find the job title.

    Strategy:
    - Look at the first 5 non-empty lines.
    - The job title is often short (1–6 words) and appears near the top.
    - Common patterns: "Job Title: Data Scientist" or just "Data Scientist"

    We check for an explicit "Job Title:" label first, then fall back
    to returning the first short line.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Look for an explicit "job title:" prefix
    for line in lines[:10]:
        match = re.match(r"(?:job\s+title|position|role)\s*[:\-]\s*(.+)",
                         line, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Fall back to first short line (≤ 6 words, not a known heading)
    for line in lines[:5]:
        normalised = normalize_section_heading(line.partition(":")[0])
        if normalised in _JD_ALIAS_LOOKUP:
            continue
        words = line.split()
        if 1 <= len(words) <= 6:
            return line

    return ""


def _split_jd_into_sections(text: str) -> Dict[str, List[str]]:
    from src.sections import split_sections
    return split_sections(text, _JD_ALIAS_LOOKUP, initial="about_role")


def _detect_jd_section_heading(line: str) -> Optional[str]:
    """
    Detect whether a line is a JD section heading.

    Returns the canonical section key, or None.
    """
    if not line.strip():
        return None

    normalised = normalize_section_heading(line)

    if normalised in _JD_ALIAS_LOOKUP:
        return _JD_ALIAS_LOOKUP[normalised]

    # Try ALL-CAPS headings
    words = line.strip().split()
    if 1 <= len(words) <= 6 and line.strip().isupper():
        lower = line.strip().lower()
        if lower in _JD_ALIAS_LOOKUP:
            return _JD_ALIAS_LOOKUP[lower]

    return None


def _clean_lines(lines: List[str]) -> List[str]:
    """Remove blank lines and separator lines from a section's content."""
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[\-_=]{3,}$", stripped):
            continue
        # Remove common leading bullet characters left after preprocessing
        stripped = re.sub(r"^[-•]\s*", "", stripped)
        if stripped:
            cleaned.append(stripped)
    return cleaned
