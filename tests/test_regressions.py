"""Regression coverage for analysis correctness, uploads, persistence and UI reruns."""
import io
import fitz
import pytest
from src.pipeline import analyze_resume
from src.resume_parser import parse_resume
from src.skill_extractor import extract_skills
from src.skill_gap import analyze_skill_gap
from src.matcher import calculate_match, _tfidf_cosine


def resume_pdf():
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), 'Alice Kumar\nalice@example.com\nSkills: Python, SQL, C++\nEducation\nB.Tech Computer Science\nExperience\nBuilt Python projects using SQL.')
        return doc.tobytes()


def test_pdf_analysis_separates_preferred_skills():
    result = analyze_resume(resume_pdf(), 'Developer\nRequired Skills: Python, SQL\nPreferred Skills: Docker, Kubernetes')
    assert result['success'], result['error']
    assert result['jd_skills'] == ['Python', 'SQL']
    assert result['jd']['preferred_skills'] == ['Docker', 'Kubernetes']
    assert result['skill_gap']['missing_required_skills'] == []
    assert result['skill_gap']['missing_preferred_skills'] == ['Docker', 'Kubernetes']


def test_optional_prose_does_not_become_required():
    result = analyze_resume(resume_pdf(), 'Python developer\nSQL is required.\nDocker experience is preferred.')
    assert result['success']
    assert 'Docker' not in result['jd_skills']
    assert result['jd']['preferred_skills'] == ['Docker']


def test_repeated_inline_resume_sections():
    parsed = parse_resume('Alice Kumar\nSkills: Python\nSkills: SQL\nEducation: B.Tech')
    assert parsed['skills'] == ['Python', 'SQL']
    assert parsed['education'] == ['B.Tech']


def test_cplusplus_not_plain_c():
    assert extract_skills('C++, C#') == ['C#', 'C++']
    assert extract_skills('C language') == ['C']


def test_unique_skill_coverage():
    assert analyze_skill_gap(['Python'], ['Python', 'python'])['match_percentage'] == 100


def test_tfidf_distinguishes_technical_symbols():
    assert _tfidf_cosine('C++', 'C++') > .99
    assert _tfidf_cosine('C++', 'C#') == 0


def test_model_not_loaded_by_default(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    result = calculate_match('Python', 'Python', ['Python'], ['Python'])
    assert not result['semantic_used']
    assert result['overall_score'] == 100


def test_inference_failure_redistributes_weights(monkeypatch):
    import src.matcher as matcher
    monkeypatch.setattr(matcher, '_get_semantic_model', lambda: object())
    result = matcher.calculate_match('Python', 'Python', ['Python'], ['Python'])
    assert not result['semantic_used']
    assert result['overall_score'] == 100


def test_long_jd_rejected():
    assert not analyze_resume(resume_pdf(), 'x' * 50001)['success']


def test_encrypted_and_overlength_pdfs_rejected():
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), 'Python SQL')
        locked = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='user')
        assert not analyze_resume(locked, 'Python')['success']
        for _ in range(20):
            doc.new_page()
        assert not analyze_resume(doc.tobytes(), 'Python')['success']


def test_database_nested_path(monkeypatch, tmp_path):
    from src.database import create_database, save_analysis, retrieve_recent_analyses
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'nested' / 'history.db'))
    assert create_database()
    result = analyze_resume(resume_pdf(), 'Python developer')
    assert save_analysis(result)
    assert len(retrieve_recent_analyses()) == 1


def test_streamlit_rerun_and_changed_input(monkeypatch, tmp_path):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'no-autosave.db'))
    monkeypatch.delenv('ENABLE_DATABASE', raising=False)
    pdf_data = resume_pdf()
    monkeypatch.setattr(st, 'file_uploader', lambda label, **kwargs: io.BytesIO(pdf_data) if 'resume' in label.lower() else None)
    app = AppTest.from_file('app.py', default_timeout=30).run()
    assert not app.exception
    app.text_area[0].set_value('Required Skills: Python, SQL')
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['analysis_result']['success']
    score = app.session_state['analysis_result']['matching']['overall_score']
    app.run()  # download/chart/widget reruns must retain successful result
    assert not app.exception
    assert app.session_state['analysis_result']['matching']['overall_score'] == score
    assert not (tmp_path / 'no-autosave.db').exists()
    app.text_area[0].set_value('Required Skills: Java').run()
    assert 'analysis_result' not in app.session_state
    assert not app.exception
