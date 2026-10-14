"""Reproducible synthetic PDF regression evaluation; not a real-world accuracy benchmark."""
import json
import sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.pipeline import analyze_resume


def make_pdf(case):
    with fitz.open() as doc:
        page = doc.new_page()
        if case.get('layout') == 'two_column':
            page.insert_text((36, 36), case['name']+'\nriya@example.com\n+91 9876543210', fontsize=10)
            page.insert_textbox(fitz.Rect(36,110,280,650), 'Summary\nPortfolio of professional work.\nEducation\nBachelor degree', fontsize=10)
            skills = case['resume'].split('Technical Skills\n')[1].split('\nWork Experience')[0]
            page.insert_textbox(fitz.Rect(310,110,570,650), 'Technical Skills\n'+skills+'\nWork Experience\nExample Organisation, 2020-2024', fontsize=10)
        else:
            page.insert_textbox(fitz.Rect(36,36,560,780),case['resume'],fontsize=10)
        return doc.tobytes()


def check_case(case):
    r = analyze_resume(make_pdf(case), case['jd'])
    failures=[]
    if not r['success']:
        return {'id':case['id'],'passed':False,'failures':[r['error']]}
    checks = {'required':r['jd_skills'],'matched':r['skill_gap']['matched_skills'],
              'missing':r['skill_gap']['missing_required_skills'],'preferred':r['jd']['preferred_skills']}
    for key, actual in checks.items():
        if set(actual) != set(case['expected_'+key]):
            failures.append(f'{key}: expected {case["expected_"+key]}, got {actual}')
    if r['candidate']['name'] != case['name']:
        failures.append('candidate name mismatch')
    if r['candidate']['email'] != 'riya@example.com':
        failures.append('email mismatch')
    if ''.join(c for c in r['candidate']['phone'] if c.isdigit()) != '919876543210':
        failures.append('phone mismatch')
    return {'id':case['id'],'passed':not failures,'failures':failures,
            'overall_score':r['matching']['overall_score'],
            'coverage':r['skill_gap']['match_percentage'],
            'requirement_source':r['jd'].get('requirement_source','legacy')}


if __name__ == '__main__':
    cases=json.loads((ROOT/'evaluation/cases.json').read_text())
    results=[check_case(c) for c in cases]
    report={'dataset':'24 hand-authored synthetic cases; development regression set, not held-out real data',
            'cases':len(results),'passed':sum(r['passed'] for r in results),'results':results}
    (ROOT/'evaluation/latest_results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    sys.exit(0 if report['passed']==report['cases'] else 1)
