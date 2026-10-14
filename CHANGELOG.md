# UI v1.4 — October 14, 2026

UI-only release on the v1.3 analysis engine. No backend modules, scoring formulas, thresholds, role templates, datasets or dependency files changed.

## Changes

- Warm off-white native theme, dark text and a single teal accent. Small CSS block targets only app-owned classes; no generated selectors, JavaScript, external fonts or new custom components.
- Compact brand header; required resume and JD inputs on the main page, with a single primary action. Native columns stack on mobile.
- Comparison summary and skill gaps appear first. Candidate information, requirement/score details, source evidence and exports use native expanders rather than four dashboard tabs.
- Accurate labels distinguish document match, required coverage, optional requirements, missing mentions and generic role-template coverage. All values remain grounded in existing pipeline output.
- Text drafts survive input-method switches. Clear errors for missing inputs, invalid characters, unreadable PDFs and unexpected processing failure. Session results remain available on ordinary widget/download interactions.
- Printable and JSON exports retained; existing opt-in local-save behavior retained. No new workflow or persistence added.

## Modified files

`app.py`, `.streamlit/config.toml`, `tests/test_portfolio_ui.py`, `README.md`, `SETUP_AND_DEPLOYMENT.md`, `PORTFOLIO_GUIDE.md`, `CHANGELOG.md`.

## Verification performed

- 160 automated tests pass, including the complete pipeline regressions, the 24-case synthetic evaluation, draft/method switches, missing input messages, processing failures, unreadable PDF handling and session reruns.
- UI demo outputs for candidate, score, gaps and recommendations equal direct calls to the existing pipeline.
- Fresh Python 3.12 dependency installation and pip check pass; dependencies unchanged.
- Chromium inspection at 1366 x 900 and 390 x 844: native input panels stack on mobile and there is no page-level horizontal overflow. Desktop input/results and mobile views were visually inspected.
- Live local-browser flow tested: demo analysis, detail expanders, unsupported `.txt` resume rejection, unreadable `.pdf` error, actual synthetic PDF upload, JD comparison, skill gaps, role recommendations and JSON download. Exported candidate and coverage checked; no browser page errors.
- HTTP health and source compilation pass. Browser-check tooling was used only in scratch and is not shipped or required by the app.
- Analysis `src/`, data and requirements files are byte-identical to the v1.3 archive; 24-case outputs unchanged.

## Limits

No live account deployment performed. Mobile checks used a browser viewport, not a physical phone. Local commands were tested on Linux/Python 3.12; Windows/macOS commands are documented but not executed on those systems here. Existing limitations remain: no OCR, limited skill vocabulary and heuristic parsing; synthetic checks are not a real-world accuracy guarantee. File widgets may require reselection after switching modes/refreshing. Exports can contain personal data. No persistent cloud database is assumed.

Official hosting requirements checked October 14, 2026. Deploy entrypoint `app.py`, branch `main`, Python 3.12, default lightweight requirements, no secrets. See SETUP_AND_DEPLOYMENT.md.

---

# v1.3 portfolio release — October 8, 2026

## Broader correctness improvements

- Extract known requirements from explicit skills/qualification sections before using broader prose; show the inference source and warn when prose fallback is used.
- Treat adjacent explicit `or` and `/` alternatives as a single JD requirement in both match scoring and gap analysis.
- Exclude common explicit negated skill phrases and optional/not-required statements. Split mixed clauses at semicolons and clear sentence/but boundaries.
- Reduce false positives from ordinary "go to", "rest", "express", "spring" and ambiguous "CV" wording.
- Correct continuous phone-number handling, preserve country prefixes and skip year ranges. Avoid job-title lines as candidate names.
- Sort PDF text by location, close documents reliably and enforce file/page/extracted-text limits.
- Include source snippets and extracted text to make errors reviewable. Exports now include sensitive source text; SQLite remains opt-in and stores only its defined summary fields.

## Presentation and usability

- Reorganise the UI into candidate, requirement/gap, role and evidence tabs with summary metrics and visible active weights.
- Add built-in fictional Demo and Paste text input; preserve results across widget reruns.
- Add escaped standalone printable HTML alongside JSON export.
- Add an interview/demo guide and a truthful resume-project description.

## Verified evidence

156 automated tests pass, including 24 diverse synthetic PDF cases. All 24 pass exact skill-field/contact checks; v1.2 passes 16/24 skill-field checks and 0/24 complete checks due to the tested phone format. See evaluation/EVALUATION_REPORT.md and machine-readable results. These are development regressions, not independent real-world accuracy estimates.

Default runtime dependencies are unchanged. Fresh Python 3.12 install, dependency consistency, source compilation, Streamlit UI interactions and HTTP health pass. No live cloud deployment performed. Real-browser screenshot review could not be completed because the browser download failed.

Complex/negated prose, multilingual names and layouts remain heuristic; OCR and automatic experience/education eligibility scoring are not implemented. Unsupported skills/professions still need manual review. Broader real-document validation is the next evidence requirement, not a promised universal accuracy claim.

---

# v1.2 improvements after user testing — October 8, 2026

- Replace the JD skill Jaccard component with required-skill coverage; extra skills no longer reduce it. Preserve the optional semantic path and lightweight default dependencies.
- Return/show effective signal weights. With no detected requirements, exclude the unavailable skill component and label the result text similarity only.
- Expand vocabulary from 119 to 135 skills, including Adobe tools, Figma, typography, brand identity and print/packaging skills. Fill missing vocabulary referenced in existing role templates.
- Rebuild the CSV with correct quoting. The prior unquoted commas caused descriptions such as "Design" and "Manage" to be truncated.
- Separate generic role requirements into core groups, OR alternatives, optional suggestions and essential gates. Matching Django no longer creates mandatory gaps for Flask and FastAPI. One cloud provider satisfies its alternative group.
- Suppress zero-match roles and roles below 50% core coverage or two matched groups. Essential role gates prevent generic API/Git overlap from suggesting Android, iOS or AI roles without domain skills.
- Add Graphic Designer and Visual Designer templates. UI explains why generic role coverage differs from JD matching and labels optional skills separately.

## Verification

118 tests pass in the isolated Python 3.12 environment, including 13 new v1.2 regression tests for extra-skill fairness, absent requirements, design extraction, alternatives, optional requirements, catalogue integrity and unrelated-role suppression. Streamlit's existing successful-analysis/rerun test passes. Runtime requirements are unchanged; pip dependency check and HTTP health smoke check pass.

The same two final synthetic PDFs and JD give: Aarav required coverage 100%, overall 75%, Backend Developer template coverage 100%; Meera required coverage 0%, overall 6%, Graphic Designer and Visual Designer template coverage 100%. These confirm the intended behavior on this pair, not general accuracy.

## Remaining limits

No live cloud deployment performed. Role gates/thresholds are illustrative and can omit transferable-career candidates. The app does not verify that claimed skills are true or reliably enforce years of experience/education. Ambiguous/negated skills and complex PDF layouts still need human review. No OCR or real-model semantic benchmark added.

---

# v1.1 repair report — October 8, 2026

## Fixed

- Streamlit results disappearing after widget reruns: keep results in session state, clear them when input contents change, read uploads with `getvalue()` instead of consuming their stream.
- Preferred JD skills incorrectly counted as mandatory: scan nonpreferred context, canonicalise the separate required/preferred lists, recognise inline headings and optional prose. Repeated sections are appended rather than overwritten.
- Default installation and model loading too heavy for free hosting: remove unused spaCy/NLTK and move sentence-transformers to an optional requirements file; require explicit opt-in before model loading. No default model downloads.
- Semantic inference failure silently treated as a valid zero score: mark the component unavailable and redistribute weights.
- C++/C# also detected as C: tighten skill regex boundaries. TF-IDF now retains technical tokens such as C++ and C#.
- Duplicate required skills lowering coverage: count unique normalised required skills.
- Automatic candidate-name persistence despite optional-storage claims: default to session-only results and provide an explicit local save button only when configured.
- PDF documents not always closed: close in a `finally` block, including extraction errors and rejected documents. Reject encrypted PDFs, more than 20 pages, and oversized byte/stream uploads.
- Empty/oversized JD validation: validate before parsing/extracting the resume.
- Nested database path failures: create missing parent directories, set a connection timeout, and use UTC-aware timestamps.
- Misleading "all required skills" message when no skills are found: show unavailable coverage.
- HTML skill labels: escape badge content. Remove unnecessary remote sidebar image request.
- Dependency drift: pin direct runtime dependencies and separate development requirements. Add GitHub Actions tests.
- Replace stale README instructions (mandatory spaCy download, heavy default model, fixed RAM claim) with a checked free deployment guide.

## Verification completed

- Fresh isolated Python 3.12 virtual environment installed from `requirements-dev.txt` successfully.
- **105 tests passed**: original tests plus 12 regression tests. Includes generated real PDF analysis, required/preferred separation, technical token extraction, optional model fallback, database paths, PDF rejection and Streamlit successful analysis/rerun/input-change behavior.
- `pip check`: no broken requirements in the fresh environment.
- Streamlit server started with the fresh environment; HTTP `/_stcore/health` returned **200 / ok**; server shut down cleanly.
- Python source compilation succeeded.
- Distribution excludes environment files, actual resumes, SQLite databases, environments and test caches.

## Limits of verification

This is deployment-prepared source, not proof of a live hosted deployment. No GitHub account push or Streamlit Cloud account deployment was performed. Windows/macOS commands are documented but were not executed on those OSes. A real sentence-transformers model was not downloaded or benchmarked; only optional-model fallback behavior was tested. The default deployment uses lexical scoring. No real-world accuracy claim is supported by the evaluation templates. Scanned resumes still require OCR outside this app; complex layouts and ambiguous requirement wording remain heuristic limitations.
