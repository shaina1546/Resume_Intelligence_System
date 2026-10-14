from streamlit.testing.v1 import AppTest
from src.report_export import analysis_html


def test_demo_runs_and_retains_result():
    app=AppTest.from_file('app.py',default_timeout=30).run()
    app.radio[0].set_value('Demo').run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['analysis_result']['success']
    assert app.session_state['analysis_result']['analysis_version']=='1.3'
    from src.pipeline import analyze_resume
    expected=analyze_resume(app.session_state['text_pdf_cache'][1],app.text_area[0].value)
    actual=app.session_state['analysis_result']
    for field in ['candidate','matching','skill_gap','recommendations']:
        assert actual[field]==expected[field]
    assert len(app.tabs)==0
    assert any(e.label=='Job requirements and score explanation' for e in app.expander)
    assert len(app.get('download_button'))==2
    app.run()
    assert not app.exception
    assert app.session_state['analysis_result']['skill_gap']['match_percentage']==100


def test_paste_mode_runs():
    app=AppTest.from_file('app.py',default_timeout=30).run()
    app.radio[0].set_value('Paste text').run()
    app.text_area[0].set_value('Neha Rao\nSkills\nPython, SQL')
    app.text_area[1].set_value('Required Skills: Python, SQL')
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['analysis_result']['candidate']['name']=='Neha Rao'


def test_printable_report_escapes_user_content():
    result={'candidate':{'name':'<script>alert(1)</script>'},'jd':{'job_title':'<b>job</b>'},
            'skill_gap':{'match_percentage':100,'total_required':1,'matched_skills':['Python'],
                         'missing_required_skills':[],'missing_preferred_skills':[]},
            'matching':{'overall_score':75},'resume_skills':['Python'],'recommendations':[]}
    html=analysis_html(result)
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    assert 'href=' not in html


def test_missing_input_messages():
    app=AppTest.from_file('app.py',default_timeout=30).run()
    app.button[0].click().run()
    assert not app.exception
    assert 'Add a text-based PDF' in app.error[0].value
    app.radio[0].set_value('Paste text').run()
    app.text_area[0].set_value('Neha Rao\nSkills\nPython, SQL')
    app.button[0].click().run()
    assert 'Add a job description' in app.error[0].value


def test_drafts_survive_input_method_switch():
    app=AppTest.from_file('app.py',default_timeout=30).run()
    app.text_area[0].set_value('Required Skills: Python').run()
    app.radio[1].set_value('Upload .txt file').run()
    app.radio[1].set_value('Paste text').run()
    assert app.text_area[0].value=='Required Skills: Python'
    app.radio[0].set_value('Paste text').run()
    app.text_area[0].set_value('Neha Rao\nSkills: SQL').run()
    app.radio[0].set_value('Demo').run()
    app.radio[0].set_value('Paste text').run()
    assert app.text_area[0].value=='Neha Rao\nSkills: SQL'


def test_processing_failure_is_readable_and_keeps_inputs(monkeypatch):
    import src.pipeline as pipeline
    def fail(*args,**kwargs):
        raise RuntimeError('private diagnostic')
    monkeypatch.setattr(pipeline,'analyze_resume',fail)
    app=AppTest.from_file('app.py',default_timeout=30).run()
    app.radio[0].set_value('Demo').run()
    app.button[0].click().run()
    assert not app.exception
    assert 'Analysis could not finish' in app.error[0].value
    assert 'private diagnostic' not in app.error[0].value
    assert app.text_area[0].value
    assert 'analysis_result' not in app.session_state


def test_unreadable_pdf_has_error_not_results(monkeypatch):
    import io
    import streamlit as st
    monkeypatch.setattr(st,'file_uploader',lambda label,**kwargs: io.BytesIO(b'not pdf') if 'resume' in label.lower() else None)
    app=AppTest.from_file('app.py',default_timeout=30).run()
    app.text_area[0].set_value('Required Skills: Python')
    app.button[0].click().run()
    assert not app.exception
    assert not app.session_state['analysis_result']['success']
    assert app.error
    assert len(app.metric)==0
