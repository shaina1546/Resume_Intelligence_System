"""
src/resume_parser.py
====================
Stage 3 — Resume Information Extraction

WHAT THIS MODULE DOES:
    Given raw text extracted from a PDF resume, this module extracts
    structured candidate information:

        {
            "name":           str,
            "email":          str,
            "phone":          str,
            "education":      [str, ...],
            "skills":         [str, ...],
            "experience":     [str, ...],
            "projects":       [str, ...],
            "certifications": [str, ...],
            "achievements":   [str, ...]
        }

WHY IT EXISTS:
    The PDF extractor gives us a wall of text. The resume parser turns
    that text into something we can reason about — structured data.

APPROACH:
    1. Use regular expressions to find emails, phone numbers.
    2. Use a name-detection heuristic for the candidate name.
    3. Use section heading detection to split the resume into sections.
    4. Return the raw text of each section for downstream processing.

LIMITATIONS:
    - Rule-based extraction may miss fields in unusual layouts.
    - The "name" heuristic works for standard resumes but can fail
      for resumes that start with a job title or address.
    - We do NOT use a large language model here.
"""

import re
from typing import Dict, List, Optional

from src.utils import get_logger
from src.text_preprocessor import preprocess_for_parsing, normalize_section_heading

logger = get_logger(__name__)


# ---------------------------------------------------------------
# Section heading aliases
# These are the many ways resume authors write the same section name.
# We map each alias to a canonical section key.
# ---------------------------------------------------------------

SECTION_ALIASES: Dict[str, List[str]] = {
    "education": [
        "education",
        "academic background",
        "academic qualifications",
        "qualifications",
        "educational background",
        "academic history",
        "schooling",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "career history",
        "internship",
        "internships",
        "professional background",
        "industry experience",
    ],
    "skills": [
        "skills",
        "technical skills",
        "key skills",
        "core skills",
        "technical competencies",
        "competencies",
        "technologies",
        "tools",
        "tools & technologies",
        "programming languages",
        "languages and technologies",
        "areas of expertise",
    ],
    "projects": [
        "projects",
        "academic projects",
        "personal projects",
        "key projects",
        "major projects",
        "project work",
        "project experience",
        "notable projects",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "professional certifications",
        "courses and certifications",
        "licenses & certifications",
        "training",
        "courses",
        "online courses",
        "professional development",
    ],
    "achievements": [
        "achievements",
        "accomplishments",
        "awards",
        "honors",
        "honours",
        "recognition",
        "awards & honors",
        "distinctions",
    ],
    "summary": [
        "summary",
        "profile",
        "professional summary",
        "career objective",
        "objective",
        "about me",
        "professional profile",
        "career summary",
    ],
}

# Build a flat lookup: normalised_alias → canonical_key
_ALIAS_LOOKUP: Dict[str, str] = {}
for canonical, aliases in SECTION_ALIASES.items():
    for alias in aliases:
        _ALIAS_LOOKUP[alias.lower()] = canonical


# ---------------------------------------------------------------
# Regular expressions for contact information
# ---------------------------------------------------------------

# Email — standard format; handles subdomains and many TLDs
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Phone — handles:
#   +91-9876543210, (555) 123-4567, 9876543210, +1 555 123 4567
PHONE_PATTERN = re.compile(
    r"""
    (?:
        (?:\+?\d{1,3}[\s\-\.])?         # optional country code
        (?:\(?\d{2,4}\)?[\s\-\.])?       # optional area code
        \d{3,5}                          # first digit group
        [\s\-\.]                         # separator
        \d{3,5}                          # second digit group
        (?:[\s\-\.]\d{2,5})?             # optional third group
    )
    """,
    re.VERBOSE,
)


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def parse_resume(raw_text: str) -> Dict:
    """
    Main function: parse raw resume text into a structured dictionary.

    Parameters
    ----------
    raw_text : str
        Text extracted from a PDF resume by pdf_extractor.py.

    Returns
    -------
    dict with keys:
        name, email, phone, education, skills, experience,
        projects, certifications, achievements, summary
    """
    if not raw_text or not raw_text.strip():
        logger.warning("parse_resume received empty text.")
        return _empty_result()

    # Step 1: Light preprocessing (preserve skill characters)
    text = preprocess_for_parsing(raw_text)

    # Step 2: Extract contact fields using regex
    email = _extract_email(text)
    phone = _extract_phone(text)

    # Step 3: Split the text into named sections
    sections = _split_into_sections(text)

    # Step 4: Attempt to extract the candidate's name
    name = _extract_name(text, sections, email)

    # Step 5: Return structured result
    return {
        "name":           name,
        "email":          email,
        "phone":          phone,
        "summary":        _clean_section_lines(sections.get("summary", [])),
        "education":      _clean_section_lines(sections.get("education", [])),
        "skills":         _clean_section_lines(sections.get("skills", [])),
        "experience":     _clean_section_lines(sections.get("experience", [])),
        "projects":       _clean_section_lines(sections.get("projects", [])),
        "certifications": _clean_section_lines(sections.get("certifications", [])),
        "achievements":   _clean_section_lines(sections.get("achievements", [])),
    }


# ---------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------

def _empty_result() -> Dict:
    """Return a blank result dictionary with all keys present."""
    return {
        "name": "",
        "email": "",
        "phone": "",
        "summary": [],
        "education": [],
        "skills": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "achievements": [],
    }


def _extract_email(text: str) -> str:
    """Find the first email address in the text."""
    match = EMAIL_PATTERN.search(text)
    return match.group(0).strip() if match else ""


def _extract_phone(text: str) -> str:
    """
    Find the first phone-like number in the text.

    We remove the email address first so we don't accidentally match
    numbers inside an email domain.
    """
    # Remove emails first so we don't match digits inside email addresses
    text_no_email = EMAIL_PATTERN.sub("", text)
    match = PHONE_PATTERN.search(text_no_email)
    if match:
        raw = match.group(0).strip()
        # Filter out short/invalid matches (fewer than 7 digits)
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 7:
            return raw
    return ""


def _extract_name(text: str, sections: Dict, email: str) -> str:
    """
    Heuristic name extraction.

    STRATEGY:
    Most resumes begin with the candidate's name on the first one or
    two lines, often in a larger font (which PyMuPDF may still export
    as a line by itself).

    We look at the first non-empty lines before any section heading
    appears and apply a simple filter:
    - The line should contain 2–4 words.
    - Each word should start with a capital letter.
    - It should not be a known heading, email, or phone number.
    - It should not be a URL.

    This heuristic will fail for some edge cases (e.g., resumes that
    start with a job title, or all-caps names). That is acceptable for
    Version 1.
    """
    lines = text.split("\n")
    known_headings = set(_ALIAS_LOOKUP.keys())

    for line in lines[:15]:  # only look at first 15 lines
        stripped = line.strip()
        if not stripped:
            continue

        normalised = normalize_section_heading(stripped)

        # Skip lines that are section headings
        if normalised in known_headings:
            break

        # Skip lines with @ (email) or digits that look like phone numbers
        if "@" in stripped or re.search(r"\d{5,}", stripped):
            continue

        # Skip URLs
        if re.search(r"https?://|www\.", stripped, re.IGNORECASE):
            continue

        # Split into words and check capitalization
        words = stripped.split()
        if 2 <= len(words) <= 4:
            # Each word should start with an uppercase letter
            if all(w[0].isupper() for w in words if w.isalpha()):
                # Avoid things like "Work Experience" being picked up as a name
                # by checking that it is NOT a known heading
                candidate = " ".join(words)
                if normalised not in known_headings:
                    return candidate

    return ""


def _split_into_sections(text: str) -> Dict[str, List[str]]:
    """
    Split resume text into named sections using heading detection.

    HOW IT WORKS:
    1. Iterate over each line of the text.
    2. Check if the line matches a known section heading.
    3. When a new heading is found, start collecting lines for it.
    4. When the next heading is found, save the previous section.

    Returns a dict mapping canonical section name → list of text lines.
    """
    sections: Dict[str, List[str]] = {}
    current_section: Optional[str] = None
    current_lines: List[str] = []

    for line in text.split("\n"):
        stripped = line.strip()

        # Check whether this line is a section heading
        detected = _detect_section_heading(stripped)

        if detected:
            # Save the previous section before starting a new one
            if current_section and current_lines:
                sections[current_section] = current_lines

            current_section = detected
            current_lines = []
        else:
            if current_section is not None:
                current_lines.append(stripped)

    # Save the last section
    if current_section and current_lines:
        sections[current_section] = current_lines

    return sections


def _detect_section_heading(line: str) -> Optional[str]:
    """
    Determine whether a line is a section heading.

    Returns the canonical section name if the line is a heading,
    or None if it is not.

    HEURISTICS:
    - Must be 1–5 words (long lines are content, not headings).
    - Is found in our alias lookup table (after normalisation).
    - OR is entirely uppercase and 1–4 words (e.g., "EDUCATION").
    """
    if not line.strip():
        return None

    # Normalise for comparison
    normalised = normalize_section_heading(line)

    # Check against alias lookup (most reliable)
    if normalised in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[normalised]

    # Check for ALL-CAPS headings not in our alias list
    words = line.strip().split()
    if 1 <= len(words) <= 5 and line.strip().isupper():
        # See if we can match when lowercased
        lower_version = line.strip().lower()
        if lower_version in _ALIAS_LOOKUP:
            return _ALIAS_LOOKUP[lower_version]

    return None


def _clean_section_lines(lines: List[str]) -> List[str]:
    """
    Remove blank lines and leading/trailing whitespace from section content.
    Also removes pure-separator lines (e.g., "---", "===").
    """
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip separator lines (3+ repeated dashes, underscores, equals)
        if re.match(r"^[\-_=]{3,}$", stripped):
            continue
        cleaned.append(stripped)
    return cleaned
