import csv
from pathlib import Path
import pytest
from src.matcher import calculate_match
from src.job_recommender import recommend_roles, _load_job_roles
from src.skill_extractor import extract_skills, get_all_canonical_skills


def test_extra_skills_never_reduce_required_component(monkeypatch):
    monkeypatch.setenv('ENABLE_SEMANTIC', 'false')
    a = calculate_match('Python SQL', 'Python SQL', ['Python', 'SQL'], ['Python', 'SQL'])
    b = calculate_match('Python SQL', 'Python SQL', ['Python', 'SQL', 'Docker', 'Figma'], ['Python', 'SQL'])
    assert a['overall_score'] == b['overall_score'] == 100
    assert b['skill_score'] == 1
    assert b['weights'] == pytest.approx({'skill': .625, 'tfidf': .375, 'semantic': 0})


def test_no_required_skills_uses_text_only(monkeypatch):
    monkeypatch.setenv('ENABLE_SEMANTIC', 'false')
    r = calculate_match('creative artwork', 'creative artwork', [], [])
    assert not r['required_skills_detected']
    assert r['weights']['skill'] == 0
    assert r['overall_score'] == 100


def test_required_duplicates_and_whitespace():
    r = calculate_match('Python', 'Python', [' python '], ['Python', ' python '])
    assert r['skill_score'] == 1


def test_design_tools_detected():
    skills = extract_skills('Adobe Photoshop, Illustrator, InDesign, Figma, Typography, Brand Identity, Packaging Design, Print Production')
    assert len(skills) == 8
    assert 'Adobe Photoshop' in skills


def test_backend_alternatives_not_reported_as_gaps():
    skills = ['Python', 'Django', 'SQL', 'REST API', 'Git', 'PostgreSQL', 'Docker']
    r = next(r for r in recommend_roles(skills) if r['role'] == 'Backend Developer')
    assert r['score'] == 100
    assert r['missing_skills'] == []
    assert 'Redis' in r['optional_missing_skills']


def test_optional_skills_dont_reduce_or_inflate_core_score():
    base = ['Python', 'Django', 'SQL', 'REST API', 'Git', 'PostgreSQL', 'Docker']
    a = next(r for r in recommend_roles(base) if r['role'] == 'Backend Developer')
    b = next(r for r in recommend_roles(base + ['Redis', 'Microservices']) if r['role'] == 'Backend Developer')
    assert a['score'] == b['score'] == 100
    assert 'Redis' in b['optional_matched_skills']


def test_multiple_alternatives_only_count_once():
    r = next(r for r in recommend_roles(['Python', 'Java', 'Django', 'FastAPI', 'SQL', 'REST API', 'Git', 'PostgreSQL', 'Docker']) if r['role'] == 'Backend Developer')
    assert r['matched_groups'] == r['total_groups'] == 7
    assert r['score'] == 100


def test_no_roles_for_zero_overlap_or_soft_skills_only():
    assert recommend_roles(['Communication', 'Leadership', 'Teamwork']) == []
    assert recommend_roles(['Unknown skill']) == []


def test_shared_infrastructure_does_not_imply_ai_fit():
    roles = recommend_roles(['Python', 'Git', 'Docker', 'Kubernetes', 'REST API'])
    assert 'AI Engineer' not in [r['role'] for r in roles]
    assert all(r['score'] >= 50 for r in roles)


def test_design_candidate_recommended_for_design():
    roles = recommend_roles(extract_skills('Adobe Photoshop Adobe Illustrator Adobe InDesign Figma Typography Brand Identity Print Production Packaging Design Communication Leadership'))
    assert roles[0]['role'] == 'Graphic Designer'
    assert roles[0]['score'] == 100
    assert 'AI Engineer' not in [r['role'] for r in roles]


def test_catalogue_integrity_and_vocabulary():
    known = set(get_all_canonical_skills())
    roles = _load_job_roles()
    assert len(roles) == 22
    for role in roles:
        assert len(role['description'].split()) >= 6
        for group in role['groups'] + role['optional_groups'] + role['essential_groups']:
            assert set(group) <= known, (role['role'], group)
    with Path('data/job_roles.csv').open() as f:
        assert all(None not in row for row in csv.DictReader(f))


def test_recommendation_limits():
    assert recommend_roles(['Python'], top_n=0) == []
    assert len(recommend_roles(['Python', 'SQL', 'Docker', 'Git', 'Django'], top_n=1)) <= 1


def test_generic_backend_skills_dont_suggest_mobile_roles():
    roles = recommend_roles(['Python', 'Django', 'REST API', 'Git', 'SQL', 'Docker'])
    assert 'Android Developer' not in [r['role'] for r in roles]
    assert 'iOS Developer' not in [r['role'] for r in roles]
