"""Explicit requirements first; limited OR parsing and transparent prose fallback."""
import re
from src.skill_extractor import extract_skills, extract_skill_evidence

OPTIONAL = re.compile(r"\b(preferred|optional|nice[- ]to[- ]have|bonus|good to have)\b|\ba plus\b", re.I)


def requirement_groups(text):
    # Keep the longest occurrence at each span, then join adjacent OR alternatives.
    hits = []
    for hit in extract_skill_evidence(text):
        if any(hit["start"] >= h["start"] and hit["end"] <= h["end"] for h in hits):
            continue
        hits.append(hit)
    groups = []
    previous = None
    for hit in hits:
        bridge = text[previous["end"]:hit["start"]] if previous else ""
        if previous and re.fullmatch(r"\s*(?:or|/)\s*", bridge, re.I):
            if hit["skill"] not in groups[-1]:
                groups[-1].append(hit["skill"])
        else:
            groups.append([hit["skill"]])
        previous = hit
    unique = {}
    for group in groups:
        key = tuple(sorted(s.casefold() for s in group))
        unique.setdefault(key, sorted(group))
    return list(unique.values())


def analyse_requirements(sections):
    explicit = sections.get("required_skills", []) + sections.get("qualifications", [])
    # Use explicit requirement sections when they contain known positive skills.
    has_explicit = any(extract_skills(line) for line in explicit)
    lines = explicit if has_explicit else [line for key, body in sections.items()
                                          if key != "preferred_skills" for line in body]
    required, preferred = [], list(sections.get("preferred_skills", []))
    for line in lines:
        # Separate mixed required/preferred statements at clear clause boundaries.
        clauses = re.split(r";|(?<=[.!?])\s+|,?\s+but\s+", line, flags=re.I)
        for clause in clauses:
            (preferred if OPTIONAL.search(clause) else required).append(clause)
    groups = requirement_groups("\n".join(required))
    required_skills = sorted({skill for group in groups for skill in group})
    preferred_skills = sorted(set(extract_skills("\n".join(preferred))) - set(required_skills))
    warnings = []
    if not has_explicit and groups:
        warnings.append("No explicit skills/requirements section found: requirements are inferred from prose. Review them before interpreting the score.")
    if any(OPTIONAL.search(line) and not re.search(r";|\bbut\b",line,re.I)
           and re.search(r"required|must", line, re.I) for line in lines):
        warnings.append("Mixed mandatory/optional wording detected; review the extracted requirements.")
    return {"required_groups": groups, "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "required_context": "\n".join(required),
            "requirement_source": "explicit_sections" if has_explicit else "inferred_prose",
            "requirement_warnings": warnings}


def coverage_stats(resume_skills, groups):
    present = {s.strip().casefold() for s in resume_skills}
    unique = {tuple(sorted(s.strip() for s in g)): g for g in groups if g}
    matched_skills, missing, matched_groups = set(), [], 0
    for group in unique.values():
        found = [s for s in group if s.casefold() in present]
        if found:
            matched_skills.update(found)
            matched_groups += 1
        else:
            missing.append(" or ".join(group))
    return {"coverage": matched_groups / len(unique) if unique else 0.0,
            "matched_skills": sorted(matched_skills), "missing": sorted(missing),
            "matched_groups": matched_groups, "total_groups": len(unique)}
