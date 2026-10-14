# Run and deploy — UI v1.4

Extract `Resume_Intelligence_System-v1.4.zip`. Open the extracted `Resume_Intelligence_System` folder containing `app.py` and `requirements.txt`. Use Python **3.12**. No API keys, spaCy downloads or paid subscriptions are needed for the default configuration.

## Local run

Windows Command Prompt:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open **http://localhost:8501**. Stop with Ctrl+C. If PowerShell activation is blocked, run `.\.venv\Scripts\python.exe -m streamlit run app.py` directly (use that interpreter for installation too).

Choose PDF, Paste text or Demo; add the target JD; select Analyse resume. Review matched and missing mentions, expand candidate/source details and export the report if useful. PDF is text-based, up to 10 MB / 20 pages. Pasted resumes support Latin text, up to 25,000 characters. JD supports pasted text or UTF-8 `.txt`, up to 50,000 characters. Scanned or encrypted PDFs are unsupported. Widgets retain session results; changing document contents clears the old comparison. Text drafts survive input-method switches; file upload widgets may need reselection after changing modes or refreshing.

## Push to GitHub

For a **new empty repository**, replace YOUR_USERNAME and run:

```bash
git init
git branch -M main
git add .
git status
git commit -m "Polish Streamlit resume analysis UI"
git remote add origin https://github.com/YOUR_USERNAME/Resume_Intelligence_System.git
git push -u origin main
```

Push extracted files, including `.streamlit` and `.github`, not the ZIP. Check that `.env`, `.venv`, actual resumes and SQLite files are ignored. Follow Git's browser authentication prompt. If author identity is required, set `git config user.name "Your Name"` and `git config user.email "YOUR_EMAIL"` before committing.

For an existing checkout, copy the updated files into it without replacing `.git`, `.env`, or your environment; inspect `git diff`, run checks, then commit and push normally. Do not force-push.

## Free hosting: Streamlit Community Cloud

1. Sign in to https://share.streamlit.io and connect GitHub.
2. Create app; select your repository, branch `main`, main file `app.py`.
3. Advanced settings: explicitly select **Python 3.12**. Leave Secrets empty.
4. Deploy and inspect the build logs, then try Demo and a synthetic upload on the generated URL.

Keep `app.py`, `requirements.txt`, `.streamlit/config.toml` and `data/` at the repository root. Keep semantic model loading and database saving disabled (defaults). Requirements are pinned and lightweight compared with a neural-model install. Free hosting has variable resource limits; local SQLite is not permanent cloud history. No live account deployment was performed in this release.

Official requirements checked October 14, 2026:
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

## Checks and common fixes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python evaluation/run_evaluation.py
```

If `app.py` cannot be found, change into the project folder. If a module is missing, install using the same virtual-environment interpreter that runs the app. For an occupied port use `--server.port 8502`. For unreadable PDF errors export a selectable-text PDF from the original document. Exports include personal details and source text; share only authorised data.
