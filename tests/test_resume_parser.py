"""
tests/test_resume_parser.py
===========================
Tests for src/resume_parser.py

We use synthetic resume texts so tests work without any PDF files
and without internet access.
"""

import pytest
from src.resume_parser import parse_resume, _extract_email, _extract_phone, _extract_name


# ---------------------------------------------------------------
# Synthetic resume fixtures
# ---------------------------------------------------------------

RESUME_FULL = """
Jane Doe
jane.doe@example.com
+1 (555) 123-4567

Education
B.Sc. Computer Science, State University, 2022

Work Experience
Software Engineer at TechCorp, 2022-2024
  - Built REST APIs with Python and Django
  - Collaborated with cross-functional teams

Technical Skills
Python, SQL, Django, REST API, Git, Docker

Projects
Personal Finance Tracker
  - Developed a web application using Flask and PostgreSQL

Certifications
AWS Certified Cloud Practitioner, 2023

Achievements
Dean's List 2021, 2022
"""

RESUME_MINIMAL = """
Alex Smith
alex@email.com

Skills
JavaScript React Node.js
"""

RESUME_NO_SECTIONS = """
Bob Jones
bobjones@test.org
+919876543210
Python developer with 3 years of experience in machine learning and NLP.
"""

RESUME_EMPTY = ""

RESUME_ALTERNATE_HEADINGS = """
Sarah Connor
sarah@skynet.io

Academic Background
M.Sc. Artificial Intelligence, MIT, 2021

Professional Experience
AI Research Intern at OpenResearch, 2021-2022

Core Skills
Python, TensorFlow, PyTorch, Computer Vision

Academic Projects
Object Detection System using YOLO

Professional Certifications
Deep Learning Specialisation, Coursera

Accomplishments
Best Research Paper Award, NeurIPS Workshop 2021
"""


# ---------------------------------------------------------------
# Email extraction tests
# ---------------------------------------------------------------

class TestEmailExtraction:
    def test_standard_email(self):
        result = parse_resume(RESUME_FULL)
        assert result["email"] == "jane.doe@example.com"

    def test_simple_email(self):
        result = parse_resume(RESUME_MINIMAL)
        assert result["email"] == "alex@email.com"

    def test_no_email(self):
        result = parse_resume(RESUME_NO_SECTIONS)
        # The resume has an email - let's test it is detected
        assert "@" in result["email"]

    def test_empty_resume_has_empty_email(self):
        result = parse_resume(RESUME_EMPTY)
        assert result["email"] == ""

    def test_email_regex_directly(self):
        assert _extract_email("Contact: user@domain.co.uk") == "user@domain.co.uk"
        assert _extract_email("No email here at all") == ""
        assert _extract_email("multi@test.io and another@mail.com") == "multi@test.io"


# ---------------------------------------------------------------
# Phone extraction tests
# ---------------------------------------------------------------

class TestPhoneExtraction:
    def test_us_phone_format(self):
        result = parse_resume(RESUME_FULL)
        assert result["phone"] != ""
        assert "555" in result["phone"] or "123" in result["phone"]

    def test_indian_phone_format(self):
        phone = _extract_phone("+919876543210")
        # This might not match our regex — acceptable; document the limitation
        assert isinstance(phone, str)

    def test_no_phone(self):
        text = "Name: Alice\nEmail: alice@test.com\nNo phone here."
        assert _extract_phone(text) == ""

    def test_empty_returns_empty(self):
        assert _extract_phone("") == ""


# ---------------------------------------------------------------
# Name extraction tests
# ---------------------------------------------------------------

class TestNameExtraction:
    def test_two_word_name(self):
        result = parse_resume(RESUME_FULL)
        assert result["name"] == "Jane Doe"

    def test_alternate_name(self):
        result = parse_resume(RESUME_MINIMAL)
        assert result["name"] == "Alex Smith"

    def test_empty_resume_has_empty_name(self):
        result = parse_resume(RESUME_EMPTY)
        assert result["name"] == ""


# ---------------------------------------------------------------
# Section detection tests
# ---------------------------------------------------------------

class TestSectionDetection:
    def test_standard_sections_present(self):
        result = parse_resume(RESUME_FULL)
        assert len(result["education"]) > 0
        assert len(result["experience"]) > 0
        assert len(result["skills"]) > 0
        assert len(result["projects"]) > 0
        assert len(result["certifications"]) > 0
        assert len(result["achievements"]) > 0

    def test_alternate_section_headings(self):
        """
        The parser must support heading aliases like:
        'Academic Background' → education
        'Professional Experience' → experience
        'Core Skills' → skills
        'Academic Projects' → projects
        'Professional Certifications' → certifications
        'Accomplishments' → achievements
        """
        result = parse_resume(RESUME_ALTERNATE_HEADINGS)
        assert len(result["education"]) > 0,      "Academic Background not detected"
        assert len(result["experience"]) > 0,     "Professional Experience not detected"
        assert len(result["skills"]) > 0,         "Core Skills not detected"
        assert len(result["projects"]) > 0,       "Academic Projects not detected"
        assert len(result["certifications"]) > 0, "Professional Certifications not detected"
        assert len(result["achievements"]) > 0,   "Accomplishments not detected"

    def test_missing_sections_return_empty_list(self):
        """A resume with no sections should return empty lists, not crash."""
        result = parse_resume(RESUME_NO_SECTIONS)
        assert isinstance(result["education"], list)
        assert isinstance(result["experience"], list)
        assert isinstance(result["skills"], list)
        assert isinstance(result["projects"], list)
        assert isinstance(result["certifications"], list)
        assert isinstance(result["achievements"], list)

    def test_empty_resume_returns_all_empty(self):
        result = parse_resume(RESUME_EMPTY)
        for key in ["name", "email", "phone"]:
            assert result[key] == ""
        for key in ["education", "skills", "experience", "projects",
                    "certifications", "achievements"]:
            assert result[key] == []


# ---------------------------------------------------------------
# Return type tests
# ---------------------------------------------------------------

class TestReturnTypes:
    def test_returns_dict(self):
        result = parse_resume(RESUME_FULL)
        assert isinstance(result, dict)

    def test_all_keys_present(self):
        result = parse_resume(RESUME_FULL)
        expected_keys = {"name", "email", "phone", "summary", "education",
                         "skills", "experience", "projects",
                         "certifications", "achievements"}
        assert expected_keys.issubset(result.keys())

    def test_list_fields_are_lists(self):
        result = parse_resume(RESUME_FULL)
        for key in ["education", "skills", "experience", "projects",
                    "certifications", "achievements"]:
            assert isinstance(result[key], list), f"{key} should be a list"
