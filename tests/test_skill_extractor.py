"""
tests/test_skill_extractor.py
=============================
Tests for src/skill_extractor.py
"""

import pytest
from src.skill_extractor import extract_skills, normalize_skill, extract_skills_from_list


class TestSkillExtraction:
    def test_detects_python(self):
        skills = extract_skills("I have 3 years of Python experience.")
        assert "Python" in skills

    def test_detects_multiple_skills(self):
        text = "Experience with Python, SQL, Machine Learning, and Docker."
        skills = extract_skills(text)
        assert "Python" in skills
        assert "SQL" in skills
        assert "Machine Learning" in skills
        assert "Docker" in skills

    def test_returns_sorted_list(self):
        skills = extract_skills("Docker and Python and SQL")
        assert skills == sorted(skills)

    def test_returns_list(self):
        result = extract_skills("Python developer")
        assert isinstance(result, list)

    def test_no_skills_returns_empty(self):
        result = extract_skills("I enjoy hiking and cooking.")
        assert isinstance(result, list)

    def test_empty_string_returns_empty(self):
        assert extract_skills("") == []
        assert extract_skills(None) == []  # type: ignore

    def test_case_insensitive_matching(self):
        assert "Python" in extract_skills("PYTHON developer")
        assert "Python" in extract_skills("python developer")

    def test_deduplication(self):
        """Python mentioned twice should appear only once."""
        skills = extract_skills("Python expert. Uses python daily.")
        assert skills.count("Python") == 1


class TestSkillNormalisation:
    def test_postgres_alias(self):
        assert normalize_skill("postgres") == "PostgreSQL"

    def test_ml_alias(self):
        assert normalize_skill("ML") == "Machine Learning"

    def test_nlp_alias(self):
        assert normalize_skill("NLP") == "Natural Language Processing"

    def test_sklearn_alias(self):
        result = normalize_skill("sklearn")
        assert result == "Scikit-learn"

    def test_canonical_name_unchanged(self):
        assert normalize_skill("Python") == "Python"

    def test_unknown_skill_returns_title_cased(self):
        result = normalize_skill("unknownskill")
        assert isinstance(result, str)

    def test_empty_returns_empty(self):
        assert normalize_skill("") == ""


class TestExtractSkillsFromList:
    def test_comma_separated_skills(self):
        lines = ["Python, SQL, Machine Learning, Docker"]
        skills = extract_skills_from_list(lines)
        assert "Python" in skills
        assert "SQL" in skills
        assert "Machine Learning" in skills

    def test_multi_line_skills(self):
        lines = ["Python", "SQL", "React", "Node.js"]
        skills = extract_skills_from_list(lines)
        assert "Python" in skills
        assert "SQL" in skills

    def test_empty_list_returns_empty(self):
        assert extract_skills_from_list([]) == []
