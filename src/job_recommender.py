"""Generic role templates: core groups are AND, alternatives within a group are OR.
Optional skills are reported separately and never penalise core coverage.
Only roles with at least 50% core coverage and two matched core groups appear.
Essential groups must also be satisfied to avoid generic skill overlap suggesting unrelated careers.
These are illustrative templates, independent of the uploaded job description.
"""
import csv
from pathlib import Path
from src.skill_extractor import normalize_skill
from src.utils import get_logger

logger = get_logger(__name__)
_ROLES_CSV = Path(__file__).parent.parent / "data" / "job_roles.csv"


def _groups(raw):
    groups = []
    seen = set()
    for entry in raw.split(";"):
        group = sorted({normalize_skill(s.strip()) for s in entry.split("|") if s.strip()})
        key = tuple(s.casefold() for s in group)
        if group and key not in seen:
            groups.append(group)
            seen.add(key)
    return groups


def _load_job_roles():
    if not _ROLES_CSV.exists():
        logger.error("Role catalogue missing: %s", _ROLES_CSV)
        return []
    roles = []
    with _ROLES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if None in row:
                raise ValueError("Malformed role CSV: quote descriptions containing commas.")
            name = row.get("Job Role", "").strip()
            groups = _groups(row.get("Skills", ""))
            if name and groups:
                roles.append({"role": name, "groups": groups,
                              "optional_groups": _groups(row.get("Optional Skills", "")),
                              "essential_groups": _groups(row.get("Essential Skills", "")),
                              "description": row.get("Description", "").strip()})
    return roles


def recommend_roles(candidate_skills, top_n=5, min_score=50):
    if not candidate_skills or top_n <= 0:
        return []
    present = {normalize_skill(s).casefold() for s in candidate_skills}
    recommendations = []
    for role in _load_job_roles():
        if any(not any(s.casefold() in present for s in group)
               for group in role["essential_groups"]):
            continue
        matched, missing, matched_groups = set(), [], 0
        for group in role["groups"]:
            hits = [s for s in group if s.casefold() in present]
            if hits:
                matched.update(hits)
                matched_groups += 1
            else:
                missing.append(" or ".join(group))
        coverage = matched_groups / len(role["groups"])
        score = round(coverage * 100)
        if coverage * 100 < min_score or matched_groups < 2:
            continue
        optional_matched, optional_missing = set(), []
        for group in role["optional_groups"]:
            hits = [s for s in group if s.casefold() in present]
            if hits:
                optional_matched.update(hits)
            else:
                optional_missing.append(" or ".join(group))
        recommendations.append({"role": role["role"], "score": score,
            "matched_skills": sorted(matched), "missing_skills": sorted(missing),
            "optional_matched_skills": sorted(optional_matched),
            "optional_missing_skills": sorted(optional_missing),
            "matched_groups": matched_groups, "total_groups": len(role["groups"]),
            "description": role["description"]})
    recommendations.sort(key=lambda r: (-r["score"], r["role"]))
    return recommendations[:top_n]
