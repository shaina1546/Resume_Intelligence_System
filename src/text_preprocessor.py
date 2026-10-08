"""
src/text_preprocessor.py
=========================
Stage 5 (partial) — Text Preprocessing

WHAT THIS MODULE DOES:
    Cleans and normalises raw text before it is fed into parsers
    and NLP models.

WHY IT EXISTS:
    Raw PDF text often contains:
    - Extra whitespace and newlines
    - Inconsistent bullet characters (•, ◦, ▪, –)
    - Encoding artefacts

    But we must be careful NOT to destroy:
    - "C++", "C#", ".NET", "Node.js", "scikit-learn"  ← skill names
    - Email addresses and phone numbers               ← contact info
    - Years like "2020-2023"                          ← experience dates

DESIGN PRINCIPLE:
    Prefer conservative cleaning over aggressive stripping.
    It is better to leave a small amount of noise than to accidentally
    delete a skill or date.
"""

import re
from typing import List

from src.utils import get_logger, normalize_whitespace

logger = get_logger(__name__)

# ---------------------------------------------------------------
# Common bullet / separator characters found in PDFs
# ---------------------------------------------------------------
BULLET_CHARS = r"[•◦▪▸►✓✗\-–—*]"


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def preprocess_for_parsing(text: str) -> str:
    """
    Light preprocessing for section detection and field extraction.

    What we do:
    1. Normalise newlines (\\r\\n → \\n).
    2. Replace common bullet characters with a plain hyphen.
    3. Collapse runs of 3+ newlines into exactly 2 (preserves sections).
    4. Strip leading/trailing whitespace per line.

    What we do NOT do:
    - Remove punctuation (would break "C++", "C#", emails, URLs).
    - Lowercase (would confuse section headings like "EDUCATION").
    - Remove stopwords (needed for full-text similarity).
    """
    # Step 1: Normalise Windows line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 2: Replace exotic bullet characters with a simple hyphen
    text = re.sub(BULLET_CHARS, "-", text)

    # Step 3: Collapse 3+ blank lines into exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Step 4: Strip each line (removes trailing spaces, but keeps newlines)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def preprocess_for_similarity(text: str) -> str:
    """
    More aggressive preprocessing for TF-IDF and cosine similarity.

    We lowercase and remove punctuation here because similarity models
    benefit from normalised tokens. We still preserve letters, digits,
    the hyphen, the dot, and the plus/hash (for skill names).

    INPUT:  Raw or lightly cleaned text
    OUTPUT: Lowercase, punctuation-reduced text suitable for vectorisation
    """
    text = text.lower()

    # Keep alphanumerics plus characters that appear in skill names:
    # + (C++), # (C#), . (Node.js, .NET), - (scikit-learn), _ (snake_case)
    text = re.sub(r"[^a-z0-9\s\+\#\.\-\_]", " ", text)

    # Collapse multiple spaces into one
    text = normalize_whitespace(text)

    return text


def tokenize(text: str) -> List[str]:
    """
    Split text into a list of words (tokens).

    We split on whitespace after light preprocessing, which is enough
    for skill matching and TF-IDF.

    Returns a list of non-empty string tokens.
    """
    preprocessed = preprocess_for_similarity(text)
    return [token for token in preprocessed.split() if token]


def normalize_section_heading(heading: str) -> str:
    """
    Normalise a section heading for comparison.

    Examples:
        "WORK EXPERIENCE:"  → "work experience"
        "  Technical Skills " → "technical skills"

    This is used by the resume and JD parsers to detect section boundaries.
    """
    heading = heading.strip().lower()
    heading = re.sub(r"[:\-_]+$", "", heading)   # remove trailing punctuation
    heading = normalize_whitespace(heading)
    return heading
