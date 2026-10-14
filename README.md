# Resume Intelligence System — UI v1.4 / analysis v1.3

A student prototype that analyses a **text-based PDF resume** against a job description, shows an explainable match score, identifies skill gaps and suggests roles. No paid API, database subscription or API key is required.

**Start here:** [SETUP_AND_DEPLOYMENT.md](SETUP_AND_DEPLOYMENT.md) contains complete Windows/macOS/Linux, GitHub and free hosting instructions. [CHANGELOG.md](CHANGELOG.md) explains the fixes and verification.

## Requirements

Use **Python 3.12** for both local development and deployment. The pinned dependencies were tested on this version. Git is needed to push code to GitHub.

```bash
python -m venv .venv
# Windows Command Prompt: .venv\Scripts\activate.bat
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. Upload a text PDF, paste a JD, and select Analyse resume. Alternatively use Paste text or Demo. Download JSON or a standalone printable HTML report. Results survive widget reruns in the same session; changing the resume or JD clears the old result. Refreshing/closing the browser may end the session.

## Default free hosting configuration

Deploy to Streamlit Community Cloud with repository branch `main`, entry point `app.py`, and Python **3.12** in Advanced settings. No secrets are required. Keep `ENABLE_SEMANTIC` and `ENABLE_DATABASE` disabled (their defaults).

The default requirements exclude torch, sentence-transformers, spaCy and NLTK. The parsers use regex and the included skill CSV; spaCy and NLTK were unused by the original code. Semantic similarity remains an optional local enhancement. Python's built-in SQLite is optional for local single-user storage; it is not a durable cloud database or a multi-user history service.

## Features and architecture

`app.py` → `src/pipeline.py` → PDF extraction, resume/JD parsing, CSV skill extraction, match scoring, skill gaps, role recommendations.

- PyMuPDF extracts PDF text; image-only/scanned resumes require OCR elsewhere.
- Resume parser detects contact details and common sections, including inline and repeated headings.
- JD parser separates preferred sections and explicitly optional lines from required context.
- Skill dictionary `data/skills.csv` normalises aliases; add rows to extend coverage.
- `data/job_roles.csv` contains 22 example roles.
- scikit-learn calculates TF-IDF similarity; Plotly displays the dashboard.
- Uploaded PDFs stay in memory; database saving is disabled by default. Session results and JSON exports include extracted text and skill-evidence snippets. Exports may contain personal data; share appropriately.
- Tests cover parsers, matching, invalid PDFs, generated PDFs, database paths, exports, demo/paste modes and Streamlit reruns. The portfolio release passes 156 tests, including 24 diverse synthetic PDF evaluation cases.

## Score interpretation

With semantic scoring disabled, the documented 50:30 weights are normalised:

`overall = 100 × (0.625 × required_skill_coverage + 0.375 × tfidf_cosine)`

With semantic scoring active: `100 × (0.50 × required_skill_coverage + 0.30 × tfidf_cosine + 0.20 × semantic_cosine)`.

Model load or inference failure returns to the default weights. Required-skill coverage is matched / unique required skills. Extra and preferred skills do not lower this component. Preferred skills do not enter mandatory skill gaps. Explicit `Django or Flask` and `Django/Flask` alternatives count as one requirement. A missing alternative group is displayed as `Django or Flask`, not two independent gaps. If no required skills are detected, the skill component is unavailable and excluded; weights are normalised across available text signals. The UI shows effective weights. Explicit skills/qualification sections take priority over employer background and duties; when no explicit requirements are found, prose inference is labelled for review. Overall scoring still includes wording similarity, so 100% skill coverage does not imply 100% overall.

Scores are heuristic indicators, not validated hiring probabilities. Human review is needed.

## Role recommendations

Role-template scores are independent of the uploaded JD. In `data/job_roles.csv`:
- `Skills`: semicolon-separated core requirement groups. Within a group, `|` means OR (for example `Django|Flask|FastAPI`). Groups combine with AND when computing coverage.
- `Optional Skills`: development suggestions; excluded from core scoring.
- `Essential Skills`: gate groups that must be present before a role can be recommended. Each group requires at least one alternative.
- `Description`: quote text containing commas; edit CSV with a CSV-aware tool.

A candidate must satisfy essential gates, cover at least 50% of core groups and match at least two groups. Score is matched core groups / total core groups. Zero/weak/unrelated recommendations are suppressed. These thresholds and templates are transparent, illustrative choices, not empirically validated hiring criteria. Graphic Designer and Visual Designer are included alongside software roles. The vocabulary now has 135 canonical skills.

## Optional local settings

Copy `.env.example` to `.env` only if you need custom settings. Never commit `.env`.

- `ENABLE_DATABASE=true`: show a button to explicitly save candidate name, JD title, skills, scores and recommendations to local SQLite. Raw PDF bytes, email, phone and full resume text are not saved. Check `.gitignore` before committing.
- `DATABASE_PATH`: local SQLite location (parent directories are created automatically).
- `ENABLE_SEMANTIC=true`: first install `requirements-semantic.txt`. This downloads an embedding model on first analysis and uses substantially more memory. This path was not validated with a downloaded real model in this repair; fallback behavior was tested. Keep it disabled for the recommended free deployment.
- `SEMANTIC_MODEL`: optional model identifier.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Tests use synthetic data and create PDFs in memory; no actual resume or remote model is required. `.github/workflows/tests.yml` runs these checks on Python 3.12 after pushes/PRs.

## Limits

PDF limit: **10 MB / 20 pages**. JD limit: **50,000 characters**. Encrypted, corrupted and image-only PDFs are rejected. Unusual multi-column PDF layouts, ambiguous prose, negated skills and mixed required/preferred wording in one sentence can be misclassified. Name and contact detection are heuristic. CSV vocabulary is finite. No OCR, authentication, durable cloud history, or validated real-world accuracy benchmark is included. Basic negation rules handle explicit phrases such as "no experience with Python" and "Docker not required"; complex language is still not reliably understood. Paste-text mode uses a Latin-font PDF conversion and is limited to that character set. See [evaluation/README.md](evaluation/README.md) for measured development results and the separate real-data validation plan. Legacy evaluation CSVs remain annotation templates.

## Portfolio and evaluation

[PORTFOLIO_GUIDE.md](PORTFOLIO_GUIDE.md) explains the demo flow, what to show in an interview, an accurate resume bullet and validation still needed.

```bash
python evaluation/run_evaluation.py
```

`evaluation/cases.json` contains 24 labelled synthetic PDF cases across software, data, cloud, security, mobile and design profiles, with aliases, alternative groups, optional clauses, explicit sections, negation and a two-column layout. `evaluation/latest_results.json` records expected-field checks. All 24 pass in v1.3. This is a developer-authored regression set, not a representative/held-out real-resume benchmark. Do not describe it as 100% resume accuracy.

## Official deployment references

Checked October 8, 2026:
- https://docs.streamlit.io/deploy/streamlit-community-cloud
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

Community Cloud is free and connects to GitHub. Resource limits can change; this project deliberately avoids heavy models by default. A live deployment requires your GitHub/Streamlit account and has not been performed as part of this ZIP repair.

## UI v1.4 update

Warm neutral theme with teal accents, two main-page input panels, clear required fields and a single primary action. Results lead with document match and skill gaps; requirements, candidate information, source evidence and exports use native expanders. Input drafts survive method switches. Scoring, extraction, role templates and dependencies are unchanged. See the v1.4 entry in CHANGELOG.md for the specific files and verification.
