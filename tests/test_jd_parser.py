"""
tests/test_jd_parser.py
=======================
Tests for src/jd_parser.py
"""

import pytest
from src.jd_parser import parse_jd


JD_STANDARD = """
Data Scientist

Responsibilities
Build predictive models using Python and machine learning
Analyse large datasets with SQL and Pandas
Present insights to stakeholders using Tableau

Requirements
3+ years of experience in data science
Strong knowledge of Python, SQL, and Statistics
Experience with Machine Learning frameworks

Required Skills
Python
SQL
Machine Learning
Statistics
Pandas

Preferred Skills
TensorFlow
Docker
Spark
"""

JD_MINIMAL = """
Backend Developer

We need someone with Python and Django experience.
Experience with REST APIs and PostgreSQL is required.
Docker knowledge is a plus.
"""

JD_EMPTY = ""

JD_ALTERNATE_HEADINGS = """
Senior NLP Engineer

Job Responsibilities
Design NLP pipelines using Python and Hugging Face
Deploy models using Docker and Kubernetes

Qualifications
PhD or M.Sc. in Computer Science or related field
5+ years of NLP experience

Technical Skills
Python
Natural Language Processing
Deep Learning
PyTorch
Hugging Face

Preferred Qualifications
Knowledge of Kubernetes
Experience with MLOps
"""


class TestJDParsing:
    def test_returns_dict(self):
        result = parse_jd(JD_STANDARD)
        assert isinstance(result, dict)

    def test_all_keys_present(self):
        result = parse_jd(JD_STANDARD)
        expected_keys = {"job_title", "required_skills", "preferred_skills",
                         "education", "experience", "responsibilities", "qualifications"}
        assert expected_keys.issubset(result.keys())

    def test_required_skills_detected(self):
        result = parse_jd(JD_STANDARD)
        assert len(result["required_skills"]) > 0

    def test_preferred_skills_detected(self):
        result = parse_jd(JD_STANDARD)
        assert len(result["preferred_skills"]) > 0

    def test_responsibilities_detected(self):
        result = parse_jd(JD_STANDARD)
        assert len(result["responsibilities"]) > 0

    def test_empty_jd_returns_empty_result(self):
        result = parse_jd(JD_EMPTY)
        assert result["job_title"] == ""
        assert result["required_skills"] == []
        assert result["preferred_skills"] == []

    def test_alternate_headings(self):
        """
        'Job Responsibilities' → responsibilities
        'Qualifications' → qualifications
        'Technical Skills' → required_skills
        'Preferred Qualifications' → preferred_skills
        """
        result = parse_jd(JD_ALTERNATE_HEADINGS)
        assert len(result["responsibilities"]) > 0, "Job Responsibilities not detected"

    def test_list_fields_are_lists(self):
        result = parse_jd(JD_STANDARD)
        for key in ["required_skills", "preferred_skills", "education",
                    "experience", "responsibilities", "qualifications"]:
            assert isinstance(result[key], list), f"{key} should be a list"

    def test_missing_sections_return_empty_list(self):
        result = parse_jd(JD_MINIMAL)
        # JD_MINIMAL has no explicit sections, all should be lists
        assert isinstance(result["required_skills"], list)
        assert isinstance(result["preferred_skills"], list)
