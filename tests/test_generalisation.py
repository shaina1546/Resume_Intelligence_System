import json
from pathlib import Path
import pytest
from evaluation.run_evaluation import check_case
from src.resume_parser import parse_resume
from src.skill_extractor import extract_skills

CASES=json.loads((Path(__file__).resolve().parents[1]/'evaluation/cases.json').read_text())

@pytest.mark.parametrize('case', CASES, ids=[c['id'] for c in CASES])
def test_diverse_synthetic_pdf_cases(case):
    result=check_case(case)
    assert result['passed'], result['failures']

@pytest.mark.parametrize('text', ['No experience with Python.', 'I have not used Python.', 'Without knowledge of Python.'])
def test_explicit_negation_not_credited(text):
    assert 'Python' not in extract_skills(text)


def test_positive_mention_can_override_separate_negation():
    assert extract_skills('No experience with Python.\nLater learned Python.') == ['Python']


def test_phone_date_ranges_not_contact():
    r=parse_resume('Neha Rao\nExperience\n2018-2022\n2022-2024')
    assert r['phone']==''


def test_phone_without_separators():
    assert parse_resume('Neha Rao\n9876543210')['phone']=='9876543210'


def test_job_title_not_name():
    assert parse_resume('Backend Developer\nNeha Rao\nSkills: Python')['name']=='Neha Rao'


def test_ordinary_words_not_technical_skills():
    assert extract_skills('Please go to the office and rest after work.') == []


def test_negation_scope_across_skill_list():
    assert extract_skills('No experience with Python or SQL.') == []


def test_positive_skill_after_but_not_lost():
    assert extract_skills('No experience with Python but I use SQL.') == ['SQL']


def test_inline_heading_is_not_job_title():
    from src.jd_parser import parse_jd
    assert parse_jd('Required Skills: Python, SQL')['job_title'] == ''
