"""
src/pipeline.py
===============
Stage 10 — End-to-End Analysis Pipeline

WHAT THIS MODULE DOES:
    Provides a single public function `analyze_resume` that orchestrates
    the entire analysis from raw inputs to structured results.

WHY IT EXISTS:
    The Streamlit UI should not contain business logic. Instead, it
    calls one function — analyze_resume() — and receives one structured
    result dictionary. This makes the codebase:
        - Easier to test (test the pipeline, not the UI)
        - Easier to extend (swap out modules without touching the UI)
        - Cleaner (UI code stays UI code)

PIPELINE FLOW:
    PDF bytes or path
        → pdf_extractor.py     → raw resume text
        → text_preprocessor.py → cleaned text
        → resume_parser.py     → structured candidate fields
        → skill_extractor.py   → resume skills list
        → jd_parser.py         → structured JD fields
        → skill_extractor.py   → JD skills list
        → matcher.py           → match score + similarities
        → skill_gap.py         → gap analysis
        → job_recommender.py   → role recommendations
        → combined result dict

RESULT STRUCTURE:
    {
        "success": True/False,
        "error":   "" or error message,
        "candidate": {
            "name": ..., "email": ..., "phone": ...,
            "education": [...], "experience": [...], ...
        },
        "resume_skills": [...],
        "jd": {
            "job_title": ..., "required_skills": [...], ...
        },
        "jd_skills": [...],
        "matching": {
            "overall_score": int, "skill_score": float, ...
        },
        "skill_gap": {
            "matched_skills": [...], "missing_required_skills": [...], ...
        },
        "recommendations": [
            {"role": ..., "score": ..., ...}, ...
        ],
        "warnings": [...]   # non-fatal issues (e.g., scanned PDF)
    }
"""

from typing import Dict, List, Union
from pathlib import Path

from src.utils import get_logger
from src.pdf_extractor import extract_text_from_pdf, is_likely_scanned
from src.text_preprocessor import preprocess_for_parsing
from src.resume_parser import parse_resume
from src.jd_parser import parse_jd
from src.skill_extractor import extract_skills, extract_skills_from_list, extract_skill_evidence
from src.matcher import calculate_match
from src.skill_gap import analyze_skill_gap
from src.job_recommender import recommend_roles

logger = get_logger(__name__)


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def analyze_resume(
    resume_source: Union[str, Path, bytes],
    job_description: str,
    top_n_roles: int = 5,
) -> Dict:
    """
    Run the full Resume Intelligence pipeline.

    Parameters
    ----------
    resume_source   : Path to a PDF file, or raw PDF bytes from Streamlit.
    job_description : The full text of the job description.
    top_n_roles     : How many job role recommendations to return.

    Returns
    -------
    A structured result dictionary (see module docstring for schema).

    This function NEVER raises an exception. All errors are caught and
    reported in result["error"] and result["success"] = False.
    """
    result = _empty_result()
    warnings: List[str] = []

    try:
        if not isinstance(job_description, str) or not job_description.strip():
            result["error"] = "Job description is empty. Please provide a job description."
            return result
        if len(job_description) > 50000:
            result["error"] = "Job description must contain at most 50,000 characters."
            return result
        # --------------------------------------------------------
        # Step 1: Extract text from the PDF
        # --------------------------------------------------------
        logger.info("Pipeline: extracting PDF text...")
        resume_text = extract_text_from_pdf(resume_source)

        if not resume_text.strip():
            result["error"] = (
                "Could not extract text from the uploaded PDF.\n\n"
                "Possible reasons:\n"
                "• The PDF is a scanned image (OCR is not supported in Version 1).\n"
                "• The PDF is password-protected.\n"
                "• The PDF is corrupted.\n\n"
                "Please try uploading a text-based PDF resume."
            )
            return result

        if is_likely_scanned(resume_text):
            warnings.append(
                "⚠️ Very little text was extracted. This PDF may be a scanned "
                "image. Results may be incomplete."
            )

        # --------------------------------------------------------
        # Step 2: Parse the resume
        # --------------------------------------------------------
        logger.info("Pipeline: parsing resume...")
        candidate = parse_resume(resume_text)

        if not candidate.get("name"):
            warnings.append(
                "ℹ️ Candidate name could not be detected automatically."
            )

        # --------------------------------------------------------
        # Step 3: Extract skills from resume
        # --------------------------------------------------------
        logger.info("Pipeline: extracting resume skills...")
        # Combine dedicated skills section + full text for best coverage
        skills_section_text = " ".join(candidate.get("skills", []))
        resume_skills_from_section = extract_skills_from_list(
            candidate.get("skills", [])
        )
        # Also scan the full text to catch skills mentioned in experience/projects
        resume_skills_full = extract_skills(resume_text)

        # Merge both and de-duplicate (preserve skills from section as priority)
        resume_skills = _merge_skills(resume_skills_from_section, resume_skills_full)

        if not resume_skills:
            warnings.append(
                "⚠️ No skills were detected in the resume. "
                "The skill dictionary may not cover the skills in this resume."
            )

        # --------------------------------------------------------
        # Step 4: Parse the Job Description
        # --------------------------------------------------------
        logger.info("Pipeline: parsing job description...")
        if not job_description or not job_description.strip():
            result["error"] = "Job description is empty. Please provide a job description."
            return result

        jd = parse_jd(job_description)

        # --------------------------------------------------------
        # Step 5: Extract skills from JD
        # --------------------------------------------------------
        logger.info("Pipeline: extracting JD skills...")
        jd_skills = jd["required_skills"]
        jd_preferred_skills = jd["preferred_skills"]
        warnings.extend(jd.get("requirement_warnings", []))

        if not jd_skills:
            warnings.append(
                "⚠️ No recognisable skills were found in the job description. "
                "The match score may rely more on text similarity."
            )

        # --------------------------------------------------------
        # Step 6: Calculate match score
        # --------------------------------------------------------
        logger.info("Pipeline: calculating match score...")
        matching = calculate_match(
            resume_text       = resume_text,
            jd_text           = job_description,
            resume_skills     = resume_skills,
            jd_required_skills = jd_skills,
            jd_requirement_groups = jd.get("required_groups", []),
        )

        # --------------------------------------------------------
        # Step 7: Skill gap analysis
        # --------------------------------------------------------
        logger.info("Pipeline: analysing skill gaps...")
        skill_gap = analyze_skill_gap(
            resume_skills       = resume_skills,
            jd_required_skills  = jd_skills,
            jd_preferred_skills = jd_preferred_skills,
            jd_requirement_groups = jd.get("required_groups", []),
        )

        # --------------------------------------------------------
        # Step 8: Job role recommendations
        # --------------------------------------------------------
        logger.info("Pipeline: generating role recommendations...")
        recommendations = recommend_roles(resume_skills, top_n=top_n_roles)

        # --------------------------------------------------------
        # Step 9: Build the final result
        # --------------------------------------------------------
        result.update({
            "success":         True,
            "error":           "",
            "candidate":       candidate,
            "resume_skills":   resume_skills,
            "jd":              jd,
            "jd_skills":       jd_skills,
            "matching":        matching,
            "skill_gap":       skill_gap,
            "recommendations": recommendations,
            "warnings":        warnings,
            "evidence": extract_skill_evidence(resume_text, max_per_skill=3),
            "extracted_resume_text": resume_text,
            "analysis_version": "1.3",
            "limitations": ["Skills are text mentions, not verified competence.",
                            "Years of experience and education eligibility need manual review.",
                            "Dictionary coverage and prose parsing are limited."],
        })

        logger.info(
            "Pipeline complete. Score: %d, Skills matched: %d/%d",
            matching.get("overall_score", 0),
            len(skill_gap.get("matched_skills", [])),
            len(jd_skills),
        )

    except Exception as exc:
        logger.exception("Unexpected error in pipeline: %s", exc)
        result["error"] = (
            f"An unexpected error occurred: {exc}\n\n"
            "Please check the logs for more details."
        )

    return result


# ---------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------

def _empty_result() -> Dict:
    """Return a safe default result structure."""
    return {
        "success":         False,
        "error":           "",
        "candidate":       {},
        "resume_skills":   [],
        "jd":              {},
        "jd_skills":       [],
        "matching":        {},
        "skill_gap":       {},
        "recommendations": [],
        "warnings":        [],
    }


def _merge_skills(primary: List[str], secondary: List[str]) -> List[str]:
    """
    Merge two skill lists, removing duplicates.

    Primary skills take precedence (their casing is preserved).
    Secondary skills are added only if not already present.
    """
    seen_lower = {s.lower() for s in primary}
    merged = list(primary)

    for skill in secondary:
        if skill.lower() not in seen_lower:
            merged.append(skill)
            seen_lower.add(skill.lower())

    return sorted(merged)
