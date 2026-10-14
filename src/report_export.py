"""Escaped, standalone printable HTML report. No remote resources or scripts."""
from html import escape

def analysis_html(result):
    def e(value): return escape(str(value))
    candidate=result['candidate']; gap=result['skill_gap']; matching=result['matching']
    items=lambda values: ''.join('<li>'+e(v)+'</li>' for v in values) or '<li>None</li>'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Resume analysis</title>
    <style>body{{font:16px/1.6 system-ui;max-width:900px;margin:40px auto;padding:0 24px;color:#17324d}}h1,h2{{line-height:1.2}}.note{{color:#526274}}@media print{{body{{margin:0}}}}</style>
    <h1>Resume Intelligence | Analysis Report</h1>
    <p class="note">Version {e(result.get('analysis_version',''))}. A document-based comparison, not a hiring decision.</p>
    <h2>{e(candidate.get('name') or 'Name not detected')}</h2><p>{e(candidate.get('email',''))}</p>
    <p>Job: {e(result['jd'].get('job_title') or 'Provided description')}</p>
    <p><strong>Overall indicator: {matching['overall_score']}/100</strong><br>
    Required-skill coverage: {str(gap['match_percentage'])+'%' if gap['total_required'] else 'Not available'}<br>
    Requirements: {gap.get('matched_required_groups',len(gap['matched_skills']))} of {gap['total_required']} satisfied.</p>
    <h2>Matched required skills</h2><ul>{items(gap['matched_skills'])}</ul>
    <h2>Missing required skill groups</h2><ul>{items(gap['missing_required_skills'])}</ul>
    <h2>Missing preferred skills</h2><ul>{items(gap['missing_preferred_skills'])}</ul>
    <h2>All detected resume skills</h2><ul>{items(result['resume_skills'])}</ul>
    <h2>Generic role recommendations</h2><ul>{items([r['role']+' - '+str(r['score'])+'% template coverage' for r in result['recommendations']])}</ul>
    <h2>Review notes</h2><ul>{items(result.get('warnings',[])+result.get('limitations',[]))}</ul>
    <p class="note">An absent skill means it was not detected in this document. It does not prove the person lacks it. Experience, education and claimed competence require manual review. No real-world accuracy guarantee.</p></html>'''
