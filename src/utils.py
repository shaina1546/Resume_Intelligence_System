"""
src/utils.py
============
Shared helper utilities used by multiple modules.

WHY THIS FILE EXISTS:
  Small helper functions that don't belong to any specific module
  (e.g., text cleaning, safe file deletion, environment variable
  loading) are placed here so they can be reused without creating
  circular imports between the main modules.
"""

import os
import re
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists (it's optional — the app works without it)
load_dotenv()

# ---------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------
# We configure a simple logger that writes to the console.
# In production, you might write to a file instead.
# We deliberately do NOT log full resume text to protect privacy.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(name)


# ---------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------

def get_env(key: str, default: str = "") -> str:
    """
    Read an environment variable, falling back to `default`.

    This is a thin wrapper around os.getenv that makes it easy to
    switch between .env files and real environment variables without
    changing the calling code.
    """
    return os.getenv(key, default)


# ---------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------

def normalize_whitespace(text: str) -> str:
    """
    Replace any run of whitespace characters (spaces, tabs, newlines)
    with a single space, and strip leading/trailing whitespace.

    Example:
        "Hello   World\\n\\n" → "Hello World"
    """
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    """
    Light-touch text cleaning that preserves skill-related characters.

    What we remove:
        - Unicode replacement characters (U+FFFD)
        - Non-printable control characters (except newlines)

    What we intentionally KEEP:
        - "+", "#", ".", "-" because skills like "C++", "C#",
          ".NET", "Node.js", "scikit-learn" need them.
        - All alphanumeric content.

    Returns the cleaned string.
    """
    # Remove Unicode replacement character
    text = text.replace("\ufffd", "")
    # Remove non-printable control characters (ASCII 0-8, 11-31)
    # but keep newline (10) and carriage return (13)
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    return text


def safe_lower(text: str) -> str:
    """Lowercase a string safely, returning '' for non-string input."""
    if not isinstance(text, str):
        return ""
    return text.lower()


# ---------------------------------------------------------------
# File utilities
# ---------------------------------------------------------------

def safe_delete(file_path: str) -> bool:
    """
    Delete a file without raising an exception if it doesn't exist.

    Returns True if the file was deleted, False otherwise.

    WHY: We use temporary files for uploaded PDFs and want to clean
    them up after processing. If the file was already deleted or
    never created, we don't want the app to crash.
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception as exc:
        logger = get_logger(__name__)
        logger.warning("Could not delete file %s: %s", file_path, exc)
        return False


def ensure_dir(dir_path: str) -> Path:
    """
    Create a directory (and any missing parents) if it doesn't exist.

    Returns the Path object for the directory.
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path
