"""
tests/test_matcher.py
=====================
Tests for src/matcher.py

We test the TF-IDF cosine and skill Jaccard components without
requiring the semantic model (so tests run offline).
"""

import pytest
from src.matcher import calculate_match, _skill_jaccard, _tfidf_cosine


class TestSkillJaccard:
    def test_perfect_match(self):
        skills_a = ["Python", "SQL", "Machine Learning"]
        skills_b = ["Python", "SQL", "Machine Learning"]
        score, matched, missing = _skill_jaccard(skills_a, skills_b)
        assert score == 1.0
        assert len(matched) == 3
        assert len(missing) == 0

    def test_no_match(self):
        score, matched, missing = _skill_jaccard(["Python"], ["Java"])
        assert score == 0.0
        assert matched == []
        assert missing == ["Java"]

    def test_partial_match(self):
        score, matched, missing = _skill_jaccard(
            ["Python", "SQL"],
            ["Python", "SQL", "Docker"]
        )
        assert 0 < score < 1
        assert "Python" in matched
        assert "Docker" in missing

    def test_empty_jd_skills(self):
        score, matched, missing = _skill_jaccard(["Python"], [])
        assert score == 0.0
        assert matched == []
        assert missing == []

    def test_empty_resume_skills(self):
        score, matched, missing = _skill_jaccard([], ["Python", "SQL"])
        assert score == 0.0
        assert matched == []
        assert len(missing) == 2

    def test_case_insensitive(self):
        score, matched, missing = _skill_jaccard(["python"], ["Python"])
        assert score == 1.0


class TestTFIDFCosine:
    def test_identical_texts_score_one(self):
        text = "Python machine learning data science SQL pandas"
        score = _tfidf_cosine(text, text)
        assert score > 0.99

    def test_completely_different_texts(self):
        a = "Python machine learning deep learning neural network"
        b = "cooking recipes baking chocolate vanilla flour"
        score = _tfidf_cosine(a, b)
        assert score < 0.3

    def test_similar_texts_higher_than_different(self):
        base = "Python data science machine learning SQL"
        similar = "Python experience data analysis machine learning tools"
        different = "Java Spring Boot REST microservices"
        sim_score = _tfidf_cosine(base, similar)
        diff_score = _tfidf_cosine(base, different)
        assert sim_score >= diff_score

    def test_empty_texts_return_zero(self):
        assert _tfidf_cosine("", "some text") == 0.0
        assert _tfidf_cosine("some text", "") == 0.0

    def test_returns_float(self):
        result = _tfidf_cosine("Python developer", "Python engineer")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0


class TestCalculateMatch:
    RESUME_TEXT = (
        "Experienced data scientist with Python, SQL, Machine Learning, "
        "Pandas, and Scikit-learn. Worked on NLP and deep learning projects."
    )
    JD_TEXT = (
        "We need a data scientist with Python, SQL, Machine Learning, "
        "TensorFlow, and Docker experience."
    )
    RESUME_SKILLS = ["Python", "SQL", "Machine Learning", "Pandas", "Scikit-learn", "Natural Language Processing"]
    JD_SKILLS     = ["Python", "SQL", "Machine Learning", "TensorFlow", "Docker"]

    def test_returns_dict(self):
        result = calculate_match(
            self.RESUME_TEXT, self.JD_TEXT,
            self.RESUME_SKILLS, self.JD_SKILLS
        )
        assert isinstance(result, dict)

    def test_expected_keys_present(self):
        result = calculate_match(
            self.RESUME_TEXT, self.JD_TEXT,
            self.RESUME_SKILLS, self.JD_SKILLS
        )
        for key in ["overall_score", "skill_score", "tfidf_score",
                    "matched_skills", "missing_skills"]:
            assert key in result, f"Key '{key}' missing from result"

    def test_score_is_in_range(self):
        result = calculate_match(
            self.RESUME_TEXT, self.JD_TEXT,
            self.RESUME_SKILLS, self.JD_SKILLS
        )
        assert 0 <= result["overall_score"] <= 100

    def test_matched_and_missing_are_lists(self):
        result = calculate_match(
            self.RESUME_TEXT, self.JD_TEXT,
            self.RESUME_SKILLS, self.JD_SKILLS
        )
        assert isinstance(result["matched_skills"], list)
        assert isinstance(result["missing_skills"], list)

    def test_perfect_skill_match_gives_high_score(self):
        skills = ["Python", "SQL", "Machine Learning"]
        result = calculate_match(
            "Python SQL Machine Learning",
            "Python SQL Machine Learning",
            skills, skills
        )
        assert result["overall_score"] > 70
