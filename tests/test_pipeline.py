"""
tests/test_pipeline.py
======================
End-to-end pipeline tests using synthetic text resumes and job descriptions.

These tests do NOT require a real PDF file or internet access.
We simulate the pipeline by passing raw text directly to inner functions,
and also test the full pipeline with a minimal synthetic "PDF" (text bytes).
"""

import pytest
from src.pipeline import analyze_resume, _merge_skills
from src.skill_gap import analyze_skill_gap, get_gap_summary
from src.job_recommender import recommend_roles


# ---------------------------------------------------------------
# Synthetic test data
# ---------------------------------------------------------------

SYNTHETIC_RESUME_TEXT = """
Alice Kumar
alice.kumar@example.com
+91-9876543210

Education
B.Tech Computer Science, IIT Delhi, 2022

Technical Skills
Python, Machine Learning, Scikit-learn, Pandas, NumPy, SQL, Git

Work Experience
Data Science Intern at Analytics Corp, 2022-2023
  - Built ML models using Python and Scikit-learn
  - Performed SQL queries for data extraction

Projects
Customer Churn Prediction
  - Used Scikit-learn and Pandas to predict churn
  - Achieved 87% accuracy

Certifications
Machine Learning by Andrew Ng, Coursera, 2022

Achievements
1st Place, College Hackathon, 2021
"""

SYNTHETIC_JD_TEXT = """
Data Scientist

Requirements
3+ years of Python experience
Strong background in Machine Learning and Statistics

Required Skills
Python
Machine Learning
SQL
Statistics
Pandas
TensorFlow

Preferred Skills
Docker
Kubernetes
Spark
"""


# ---------------------------------------------------------------
# Skill gap tests
# ---------------------------------------------------------------

class TestSkillGap:
    def test_perfect_match(self):
        skills = ["Python", "SQL", "Machine Learning"]
        result = analyze_skill_gap(skills, skills)
        assert result["match_percentage"] == 100
        assert result["missing_required_skills"] == []
        assert len(result["matched_skills"]) == 3

    def test_no_match(self):
        result = analyze_skill_gap(
            ["React", "JavaScript"],
            ["Python", "SQL", "Machine Learning"]
        )
        assert result["match_percentage"] == 0
        assert len(result["missing_required_skills"]) == 3

    def test_partial_match(self):
        result = analyze_skill_gap(
            ["Python", "SQL"],
            ["Python", "SQL", "Docker"]
        )
        assert result["match_percentage"] == pytest.approx(66, abs=2)
        assert "Docker" in result["missing_required_skills"]
        assert "Python" in result["matched_skills"]

    def test_additional_skills(self):
        result = analyze_skill_gap(
            ["Python", "React", "Git"],
            ["Python"]
        )
        assert "React" in result["additional_skills"]
        assert "Git" in result["additional_skills"]

    def test_empty_jd_skills(self):
        result = analyze_skill_gap(["Python", "SQL"], [])
        assert result["match_percentage"] == 0
        assert result["total_required"] == 0

    def test_returns_dict_with_required_keys(self):
        result = analyze_skill_gap(["Python"], ["Python", "SQL"])
        expected_keys = {"matched_skills", "missing_required_skills",
                         "missing_preferred_skills", "additional_skills",
                         "match_percentage", "gap_count", "total_required"}
        assert expected_keys.issubset(result.keys())

    def test_case_insensitive_matching(self):
        result = analyze_skill_gap(["python"], ["Python"])
        assert result["match_percentage"] == 100


class TestGapSummary:
    def test_summary_is_string(self):
        gap = analyze_skill_gap(["Python"], ["Python", "SQL"])
        summary = get_gap_summary(gap)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_perfect_match_summary_contains_positive_message(self):
        gap = analyze_skill_gap(["Python", "SQL"], ["Python", "SQL"])
        summary = get_gap_summary(gap)
        assert "all" in summary.lower() or "✅" in summary


# ---------------------------------------------------------------
# Job recommender tests
# ---------------------------------------------------------------

class TestJobRecommender:
    def test_returns_list(self):
        result = recommend_roles(["Python", "SQL", "Machine Learning"])
        assert isinstance(result, list)

    def test_result_has_required_keys(self):
        results = recommend_roles(["Python", "Machine Learning"])
        for rec in results:
            assert "role" in rec
            assert "score" in rec
            assert "matched_skills" in rec
            assert "missing_skills" in rec

    def test_scores_in_range(self):
        results = recommend_roles(["Python", "SQL"])
        for rec in results:
            assert 0 <= rec["score"] <= 100

    def test_sorted_descending(self):
        results = recommend_roles(["Python", "SQL", "Machine Learning",
                                   "Pandas", "Scikit-learn", "TensorFlow",
                                   "Deep Learning"])
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_skills_returns_empty_or_list(self):
        result = recommend_roles([])
        assert isinstance(result, list)

    def test_top_n_respected(self):
        result = recommend_roles(["Python"], top_n=3)
        assert len(result) <= 3

    def test_data_scientist_appears_for_ml_skills(self):
        results = recommend_roles(
            ["Python", "SQL", "Machine Learning", "Statistics",
             "Pandas", "NumPy", "Scikit-learn"],
            top_n=5
        )
        roles = [r["role"] for r in results]
        assert any("Data" in role for role in roles)


# ---------------------------------------------------------------
# Merge skills helper tests
# ---------------------------------------------------------------

class TestMergeSkills:
    def test_deduplication(self):
        merged = _merge_skills(["Python", "SQL"], ["Python", "Docker"])
        assert merged.count("Python") == 1
        assert "Docker" in merged

    def test_primary_casing_preserved(self):
        merged = _merge_skills(["Python"], ["python"])
        assert "Python" in merged
        assert "python" not in merged

    def test_empty_inputs(self):
        assert _merge_skills([], []) == []
        assert _merge_skills(["Python"], []) == ["Python"]
        assert _merge_skills([], ["Python"]) == ["Python"]


# ---------------------------------------------------------------
# Full pipeline test (text-only, no real PDF)
# ---------------------------------------------------------------

class TestPipelineEdgeCases:
    def test_empty_jd_returns_error(self):
        """Pipeline should return an error dict if JD is empty."""
        result = analyze_resume(b"fake pdf bytes", "")
        assert result["success"] is False
        assert result["error"] != ""

    def test_invalid_pdf_returns_error(self):
        """Pipeline should return an error dict for an invalid PDF."""
        result = analyze_resume(b"this is not a pdf", "We need a Python developer.")
        assert result["success"] is False
        assert isinstance(result["error"], str)

    def test_result_always_has_required_keys(self):
        result = analyze_resume(b"", "")
        for key in ["success", "error", "candidate", "resume_skills",
                    "jd", "jd_skills", "matching", "skill_gap",
                    "recommendations", "warnings"]:
            assert key in result, f"Key '{key}' missing from pipeline result"
