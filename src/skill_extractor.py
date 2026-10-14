"""
src/skill_extractor.py
======================
Stage 5 — Skill Extraction and Normalisation

WHAT THIS MODULE DOES:
    1. Loads the skill dictionary from data/skills.csv.
    2. Scans a block of text (resume section or full JD) for known skills.
    3. Normalises aliases to canonical skill names.
    4. Returns a de-duplicated list of canonical skill names.

WHY IT EXISTS:
    Resumes and job descriptions use skill names inconsistently.
    Someone might write "ML" instead of "Machine Learning", or "Postgres"
    instead of "PostgreSQL". This module standardises those differences
    so the matcher can compare apples to apples.

HOW IT WORKS (step by step):
    1. Build two lookup structures from skills.csv:
       a. A set of canonical skill names (e.g., "PostgreSQL")
       b. A dict mapping every alias to its canonical name
          (e.g., "postgres" → "PostgreSQL")
    2. For each skill / alias, build a regex pattern that matches
       the word as a whole (not as part of a longer word).
    3. Scan the input text with every pattern.
    4. Return the unique canonical names of all matched skills.

EXTENDING THE SKILL LIST:
    Just add a new row to data/skills.csv. No code changes required.
    Format:
        Skill,Category,Aliases
        NewSkill,Category,alias1;alias2
"""

import re
import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------
# Path to the skills data file
# ---------------------------------------------------------------
_SKILLS_CSV = Path(__file__).parent.parent / "data" / "skills.csv"


# ---------------------------------------------------------------
# Skill database — built once at import time
# ---------------------------------------------------------------

class SkillDatabase:
    """
    Holds all known skills and their aliases.

    Attributes
    ----------
    canonical_skills : set of str
        All canonical (official) skill names, e.g., "PostgreSQL".
    alias_to_canonical : dict
        Maps every lowercase alias to its canonical name.
    patterns : list of (pattern, canonical_name)
        Compiled regex patterns for fast full-text matching.
    """

    def __init__(self):
        self.canonical_skills: Set[str] = set()
        self.alias_to_canonical: Dict[str, str] = {}
        self.patterns: List[Tuple[re.Pattern, str]] = []
        self._load()

    def _load(self):
        """Load skills from CSV and build lookup structures."""
        if not _SKILLS_CSV.exists():
            logger.error("skills.csv not found at %s", _SKILLS_CSV)
            return

        with open(_SKILLS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                skill = row.get("Skill", "").strip()
                aliases_raw = row.get("Aliases", "").strip()

                if not skill or skill.startswith("#"):
                    continue  # skip comments and blank rows

                self.canonical_skills.add(skill)

                # The canonical name itself is an alias of itself
                all_aliases = [skill]

                # Parse semicolon-separated aliases
                if aliases_raw:
                    extras = [a.strip() for a in aliases_raw.split(";") if a.strip()]
                    all_aliases.extend(extras)

                # Register all aliases in the lookup dict
                for alias in all_aliases:
                    self.alias_to_canonical[alias.lower()] = skill

                # Build a regex for each alias
                for alias in all_aliases:
                    pattern = self._build_pattern(alias)
                    if pattern:
                        self.patterns.append((pattern, skill))

        logger.info(
            "Loaded %d canonical skills with %d alias patterns.",
            len(self.canonical_skills), len(self.patterns)
        )

    @staticmethod
    def _build_pattern(alias: str) -> re.Pattern:
        """
        Build a word-boundary-aware regex for a skill alias.

        WHY WORD BOUNDARIES MATTER:
            Without \\b, searching for "R" would match inside "React",
            "Docker", etc. We want "R" to match only when it appears
            as a standalone word.

        SPECIAL CASES:
            - "C++" and "C#" contain special regex characters, so we
              escape them before compiling.
            - ".NET" starts with a dot, which is a regex wildcard, so
              we escape it.
            - We use case-insensitive matching (re.IGNORECASE).

        Returns None if the alias is empty.
        """
        if not alias.strip():
            return None

        escaped = re.escape(alias)

        # For short tokens like "C", "R", "Go", add strict word boundaries
        # to avoid false positives inside longer words.
        # For longer tokens the word boundary is still useful.
        try:
            return re.compile(r"(?<![a-zA-Z0-9_+#])" + escaped + r"(?![a-zA-Z0-9_+#])",
                               re.IGNORECASE)
        except re.error as exc:
            logger.warning("Could not compile pattern for alias '%s': %s", alias, exc)
            return None


# Module-level singleton — loaded once when the module is first imported
_DB = SkillDatabase()


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def extract_skills(text: str) -> List[str]:
    """
    Find all known skills mentioned in `text`.

    INPUT:
        text — any block of text (resume section, full resume, JD text).

    OUTPUT:
        A sorted, de-duplicated list of canonical skill names found in text.
        Example: ["Machine Learning", "PostgreSQL", "Python"]

    HOW TO USE:
        from src.skill_extractor import extract_skills
        skills = extract_skills("I have experience with Python, SQL, and ML.")
        # → ["Machine Learning", "Python", "SQL"]
    """
    if not text or not isinstance(text, str):
        return []

    return sorted({hit["skill"] for hit in extract_skill_evidence(text)})


def extract_skill_evidence(text: str, max_per_skill=None) -> List[Dict]:
    """Return positive dictionary matches with source snippets; not proof of competence.

    Explicit local negation and a few common ambiguous aliases are excluded.
    This is conservative phrase handling, not full language understanding.
    """
    if not isinstance(text, str) or not text:
        return []
    hits = []
    seen = set()
    evidence_counts = {}
    for pattern, canonical in _DB.patterns:
        for match in pattern.finditer(text):
            start, end = match.span()
            left = re.split(r"[\n;.!?]|\bbut\b", text[max(0, start-100):start], flags=re.I)[-1]
            right = re.split(r"[\n;.!?]", text[end:end+60])[0]
            if re.search(r"\b(no|not|without|never)\s+(?:(?:any|prior|hands-on|experience|knowledge|of|with|in|using|used|worked|learned)\s+)*$", left, re.I):
                continue
            if re.search(r"\b(?:no experience|no knowledge|without experience|without knowledge|not used|never used)\b.{0,70}$", left, re.I):
                continue
            if re.match(r"\s+(?:(?:experience|knowledge)\s+)?(?:is\s+)?(?:not required|not needed|not necessary|not available|not used)", right, re.I):
                continue
            raw = match.group(0)
            if raw.casefold() == "go" and re.match(r"\s+(to|live|beyond|ahead|through|back)\b", right, re.I):
                continue
            if raw.casefold() in {"rest", "express", "spring"} and raw.islower():
                context = left + raw + right
                if not re.search(r"api|framework|boot|node|javascript|web", context, re.I):
                    continue
            if raw.casefold() == "cv" and not re.search(r"vision|image|model", left+right, re.I):
                continue
            if max_per_skill is not None and evidence_counts.get(canonical, 0) >= max_per_skill:
                continue
            key = (canonical, start, end)
            if key in seen:
                continue
            seen.add(key)
            evidence_counts[canonical] = evidence_counts.get(canonical, 0) + 1
            hits.append({"skill": canonical, "matched_text": raw, "start": start,
                         "end": end, "snippet": text[max(0,start-45):end+65].strip()})
    return sorted(hits, key=lambda h: (h["start"], -(h["end"]-h["start"]), h["skill"]))


def normalize_skill(raw_skill: str) -> str:
    """
    Normalise a single skill string to its canonical name.

    If the skill is not in our dictionary, return it unchanged (title-cased).

    Examples:
        "postgres"       → "PostgreSQL"
        "ML"             → "Machine Learning"
        "scikit learn"   → "Scikit-learn"
        "unknown_skill"  → "Unknown_skill"  (not in dict, returned as-is)
    """
    if not raw_skill:
        return ""
    canonical = _DB.alias_to_canonical.get(raw_skill.strip().lower())
    return canonical if canonical else raw_skill.strip().title()


def extract_skills_from_list(skill_lines: List[str]) -> List[str]:
    """
    Extract and normalise skills from a list of text lines.

    This is useful when we already have the "Skills" section lines
    from the resume parser and want to extract individual skills from them.

    INPUT:
        skill_lines — e.g., ["Python, SQL, Machine Learning",
                              "- Docker, Kubernetes"]

    OUTPUT:
        A sorted, de-duplicated list of canonical skill names.
    """
    combined_text = " ".join(skill_lines)
    return extract_skills(combined_text)


def get_all_canonical_skills() -> List[str]:
    """
    Return all canonical skill names in alphabetical order.

    Useful for displaying the full skill vocabulary in the UI.
    """
    return sorted(_DB.canonical_skills)
