"""Streamlit interface; analysis remains in the existing src.pipeline."""
import hashlib
import json
import os
from pathlib import Path
from html import escape
import fitz
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Resume Intelligence', layout='wide')
from src.pipeline import analyze_resume
from src.database import create_database, save_analysis
from src.report_export import analysis_html

ROOT = Path(__file__).resolve().parent
DATABASE_ENABLED = os.getenv('ENABLE_DATABASE', 'false').lower() in {'true', '1', 'yes'}
# Only classes owned by this app. Native controls are styled by config.toml.
st.markdown('''<style>
.ri-header {border-left:4px solid #176b60;padding-left:18px;margin-bottom:18px}
.ri-header h1 {font:600 2rem/1.2 Georgia,serif;letter-spacing:-.04em;margin:0 0 8px;color:#26332f}
.ri-header p {font-size:.96rem;line-height:1.5;margin:0;color:#52605a;max-width:780px}
.ri-note {color:#52605a;font-size:.86rem;line-height:1.5;margin:0 0 10px;overflow-wrap:anywhere}
.ri-skills {display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 12px}
.ri-skill {background:#e5efeb;color:#225b50;border:1px solid #c9dad3;border-radius:5px;padding:4px 9px;font-size:.88rem;overflow-wrap:anywhere;max-width:100%}
.ri-skill--missing {background:#f3f0e9;color:#534e43;border-color:#d8d1c3}
@media(max-width:600px) {.ri-header h1 {font-size:1.65rem}.ri-header {padding-left:12px}}
</style>''', unsafe_allow_html=True)


def note(text):
    st.markdown('<p class="ri-note">'+escape(str(text))+'</p>', unsafe_allow_html=True)


def badges(skills, missing=False):
    if not skills:
        note('None detected.' if not missing else 'No gaps detected in the recognised requirements.')
        return
    modifier = ' ri-skill--missing' if missing else ''
    st.markdown('<div class="ri-skills">' + ''.join(
        f'<span class="ri-skill{modifier}">{escape(str(skill))}</span>'
        for skill in skills) + '</div>', unsafe_allow_html=True)


def remember_draft(widget_key, draft_key):
    st.session_state[draft_key] = st.session_state[widget_key]


def text_pdf(text):
    # Session-local only: private documents never enter shared caches.
    if 'text_pdf_cache' not in st.session_state or st.session_state.text_pdf_cache[0] != text:
        with fitz.open() as doc:
            lines = text.splitlines()
            for i in range(0, len(lines), 48):
                page = doc.new_page()
                inserted = page.insert_textbox(fitz.Rect(36, 36, 560, 790), '\n'.join(lines[i:i+48]), fontsize=10)
                if inserted < 0:
                    raise ValueError('This text is too dense to convert. Shorten it or upload a text-based PDF.')
            st.session_state.text_pdf_cache = (text, doc.tobytes())
    return st.session_state.text_pdf_cache[1]

st.markdown('''<header class="ri-header"><h1>Resume Intelligence</h1>
<p>A clearer view of your resume and the role you want. Compare requirements, review skill gaps, and trace the results to your document.</p></header>''', unsafe_allow_html=True)
resume_column, jd_column = st.columns(2, gap='medium')
pdf_bytes = b''
with resume_column, st.container(border=True):
    st.subheader('01 · Your resume')
    note('Required · Text-based PDF, up to 10 MB and 20 pages.')
    mode = st.radio('Resume input', ['PDF', 'Paste text', 'Demo'], horizontal=True, key='resume_mode')
    if mode == 'PDF':
        uploaded_file = st.file_uploader('Upload a PDF resume', type=['pdf'], key='resume_file',
                                        help='Scanned or password-protected PDFs cannot be analysed.')
        if uploaded_file:
            pdf_bytes = uploaded_file.getvalue()
    elif mode == 'Paste text':
        resume_text = st.text_area('Resume text', height=160, max_chars=25000,
                                  value=st.session_state.get('resume_draft', ''), key='resume_text_input',
                                  on_change=remember_draft, args=('resume_text_input', 'resume_draft'))
        note('Up to 25,000 characters. Latin text is supported; upload PDF for other scripts.')
        if resume_text.strip():
            try:
                pdf_bytes = text_pdf(resume_text)
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.write('Try a fictional backend developer and job description.')
        note('The demo uses the same analysis pipeline as uploaded documents.')
        pdf_bytes = text_pdf((ROOT/'data/demo/resume.txt').read_text())
with jd_column, st.container(border=True):
    st.subheader('02 · Target job')
    note('Required for this comparison · Up to 50,000 characters.')
    jd_method = st.radio('Job description input', ['Paste text', 'Upload .txt file'], horizontal=True, key='jd_method')
    if jd_method == 'Paste text':
        widget_key, draft_key = 'jd_'+mode, 'draft_jd_'+mode
        job_description = st.text_area('Job description', height=160, max_chars=50000, key=widget_key,
                                      value=st.session_state.get(draft_key, (ROOT/'data/demo/jd.txt').read_text() if mode == 'Demo' else ''),
                                      placeholder='Paste the role, required skills and preferred skills…',
                                      on_change=remember_draft, args=(widget_key, draft_key))
    else:
        jd_file = st.file_uploader('Upload Job Description (.txt)', type=['txt'])
        job_description = jd_file.getvalue().decode('utf-8', errors='replace') if jd_file else ''
        if '\ufffd' in job_description:
            st.warning('Some characters could not be read. Save the file as UTF-8, or paste its text.')
analyze_button = st.button('Analyse resume', type='primary', width='stretch')
note('Session-only results · No automatic saving · Local NLP and TF-IDF by default, with no paid API.')

signature = hashlib.sha256(pdf_bytes + job_description.encode()).hexdigest()
if st.session_state.get('input_signature') != signature:
    st.session_state.pop('analysis_result', None)
    st.session_state.pop('saved_analysis_id', None)
    st.session_state.input_signature = signature
if analyze_button:
    if not pdf_bytes:
        st.error('Add a text-based PDF resume, paste resume text, or select Demo.')
    elif not job_description.strip():
        st.error('Add a job description so we can compare the requirements.')
    else:
        # Clear any old result before processing. Model output remains untouched.
        st.session_state.pop('analysis_result', None)
        with st.spinner('Reading your resume and comparing the job requirements…'):
            try:
                st.session_state.analysis_result = analyze_resume(pdf_bytes, job_description)
            except Exception:
                st.error('Analysis could not finish. Try again or check the server logs; your inputs are still available.')
        st.session_state.pop('saved_analysis_id', None)
if 'analysis_result' not in st.session_state:
    st.divider()
    st.subheader('Start with the documents. Leave with a clear next step.')
    st.write('Add your resume and target job above, or select **Demo** to explore an example. Your results will show matched requirements, mentions not detected, and relevant role templates.')
    with st.expander('Supported inputs and how to interpret results'):
        st.write('Upload a text-based PDF or paste a resume. Scanned PDFs require external OCR. The current vocabulary covers common software, data, cloud, security, mobile and design skills; unfamiliar professions may be underrepresented.')
        st.write('The score compares document mentions and wording. It is not a hiring probability or a validated ATS score. Experience and education need manual review.')
    st.stop()
r = st.session_state.analysis_result
if not r['success']:
    st.error(r.get('error') or 'The document could not be analysed.')
    note('Check that the PDF has selectable text, is not password-protected, and stays within the upload limits. Your inputs are still available.')
    st.stop()
for warning in r['warnings']:
    st.warning(warning)
candidate, gap, score = r['candidate'], r['skill_gap'], r['matching']
st.divider()
st.subheader('Your comparison')
st.write(f"{candidate.get('name') or 'Uploaded resume'} · {r['jd'].get('job_title') or 'Provided job description'}")
summary_columns = st.columns(2)
summary_columns[0].metric('Document match indicator' if gap['total_required'] else 'Text similarity indicator', f"{score['overall_score']}/100")
summary_columns[1].metric('Required-skill coverage', f"{gap['match_percentage']}%" if gap['total_required'] else 'Not available')
if gap['total_required']:
    st.write(f"**{gap.get('matched_required_groups', 0)} of {gap['total_required']} recognised requirements** have supporting skill mentions in your resume.")
else:
    st.info('No required skills were recognised. The indicator reflects text similarity only; skill fit cannot be assessed.')
note('A missing mention is not proof that you lack the skill. Review the source text before changing your resume.')
matched_column, missing_column = st.columns(2)
with matched_column:
    st.markdown('**Matched required skills**')
    badges(gap['matched_skills'])
with missing_column:
    st.markdown('**Required mentions not detected**')
    if gap['total_required']:
        badges(gap['missing_required_skills'], missing=True)
    else:
        note('No recognised requirements to compare.')
if gap['missing_required_skills']:
    st.write('Next step: check whether your resume provides evidence for these requirements. Add relevant examples only if they reflect your actual experience.')
with st.expander('Job requirements and score explanation'):
    note('Requirement source: '+r['jd'].get('requirement_source', 'unknown').replace('_', ' ')+'. For alternative groups, one listed skill is sufficient.')
    present = {skill.casefold() for skill in r['resume_skills']}
    rows = [{'Requirement': ' or '.join(group), 'Evidence': 'Mention found' if any(skill.casefold() in present for skill in group) else 'Not detected'} for group in r['jd'].get('required_groups', [])]
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    if r['jd']['preferred_skills']:
        st.markdown('**Preferred skills · optional**'); badges(r['jd']['preferred_skills'])
        note('Preferred mentions not detected: '+(', '.join(gap['missing_preferred_skills']) or 'None'))
    weights = score['weights']
    components = [ {'Component': 'Required-skill coverage', 'Value': f"{score['skill_score']:.0%}" if gap['total_required'] else 'Unavailable', 'Active weight': f"{weights['skill']:.1%}"},
                   {'Component': 'TF-IDF text similarity', 'Value': f"{score['tfidf_score']:.0%}", 'Active weight': f"{weights['tfidf']:.1%}"},
                   {'Component': 'Semantic similarity', 'Value': f"{score['semantic_score']:.0%}" if score['semantic_used'] else 'Not used', 'Active weight': f"{weights['semantic']:.1%}"} ]
    st.dataframe(pd.DataFrame(components), hide_index=True, width='stretch')
    st.write('The indicator combines the available components using these weights. Text similarity measures wording overlap; skill coverage measures requirement groups. Neither verifies competence or predicts hiring.')
    for line in r['jd'].get('experience', []) + r['jd'].get('education', []):
        st.text(line)
    note('Experience and education are displayed for manual review and do not contribute to the score.')
with st.expander('Extracted resume information'):
    st.write(candidate.get('name') or 'Name not detected')
    st.write('Email: '+(candidate.get('email') or 'Not detected')+' · Phone: '+(candidate.get('phone') or 'Not detected'))
    st.markdown('**All detected skills**'); badges(r['resume_skills'])
    for heading, key in [('Summary', 'summary'), ('Education', 'education'), ('Experience', 'experience'), ('Projects', 'projects')]:
        if candidate.get(key):
            st.markdown('**'+heading+'**')
            for line in candidate[key]:
                st.text(line)
    note('Missing or incorrect fields? Review the extracted text below; unusual layouts can affect parsing.')
st.subheader('Roles to explore')
note('These compare your skills with generic role templates, independently of the target job. Template coverage is not eligibility.')
if not r['recommendations']:
    st.info('No suitable templates found in the current catalogue. It may not represent your profession.')
for index, rec in enumerate(r['recommendations']):
    with st.expander(f"{rec['role']} · {rec['score']}% template coverage", expanded=index == 0):
        st.write(rec['description'])
        note(f"{rec['matched_groups']} of {rec['total_groups']} core requirement groups matched. Essential template requirements are satisfied.")
        st.markdown('**Supporting skills**'); badges(rec['matched_skills'])
        if rec['missing_skills']:
            st.markdown('**Core mentions not detected**'); badges(rec['missing_skills'], missing=True)
        if rec['optional_missing_skills']:
            note('Optional areas to explore: '+'; '.join(rec['optional_missing_skills']))
with st.expander('Source evidence and extracted text'):
    st.write('Check whether each detected mention describes your own skills. These snippets do not establish proficiency.')
    if r.get('evidence'):
        st.dataframe(pd.DataFrame(r['evidence'])[['skill', 'matched_text', 'snippet']], hide_index=True, width='stretch')
    st.text(r.get('extracted_resume_text', 'No source text available.'))
with st.expander('Export analysis'):
    note('Exports can contain personal details and the full extracted resume text. Share only documents you are authorised to share.')
    exports = st.columns(2)
    exports[0].download_button('Download printable report', analysis_html(r), file_name='resume_analysis.html', mime='text/html', width='stretch')
    exports[1].download_button('Download JSON', json.dumps(r, indent=2), file_name='resume_analysis.json', mime='application/json', width='stretch')
    if DATABASE_ENABLED:
        note('Existing opt-in local save stores a summary; it is not permanent cloud history.')
        if st.button('Save locally', disabled=bool(st.session_state.get('saved_analysis_id'))):
            aid = save_analysis(r) if create_database() else None
            if aid:
                st.session_state.saved_analysis_id = aid; st.success('Saved locally.')
            else:
                st.error('Save failed. Check the configured path and permissions.')
note('Resume Intelligence · UI v1.4 / analysis v1.3 · Local NLP, explainable results, human review.')
