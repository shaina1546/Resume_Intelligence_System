# 📄 Resume Intelligence System

> **Academic/Prototype Project** — This system is a learning tool and demonstration prototype. It is NOT a hiring decision system and should NOT be used as the sole basis for employment decisions.

---

## 1. Problem Statement

Job seekers struggle to understand how well their resume matches a given job description. Recruiters receive hundreds of applications and need quick signals about candidate fit. This project provides an **automated, explainable resume analysis system** that:

- Extracts structured information from resumes.
- Compares resumes against job descriptions.
- Identifies skill gaps.
- Recommends suitable job roles.

All using **traditional NLP and machine learning** — no paid API required.

---

## 2. Objectives

1. Upload a PDF resume and extract text automatically.
2. Parse candidate information (name, email, skills, education, experience).
3. Accept a job description and extract requirements.
4. Calculate a matching score using TF-IDF, skill overlap, and semantic similarity.
5. Identify matched skills, missing skills, and skill gaps.
6. Recommend suitable job roles based on extracted skills.
7. Display everything in a clean, beginner-friendly Streamlit dashboard.

---

## 3. Features

| Feature | Status |
|---|---|
| PDF text extraction | ✅ |
| Resume information parsing | ✅ |
| JD parsing | ✅ |
| Skill extraction & normalisation | ✅ |
| TF-IDF cosine similarity | ✅ |
| Semantic similarity (sentence-transformers) | ✅ with TF-IDF fallback |
| Skill gap analysis | ✅ |
| Job role recommendations | ✅ |
| Streamlit dashboard | ✅ |
| SQLite persistence | ✅ (optional) |
| pytest test suite | ✅ |
| Deployment-ready | ✅ |

---

## 4. Architecture

```
Resume PDF
    ↓
pdf_extractor.py     → Raw text
    ↓
text_preprocessor.py → Cleaned text
    ↓
resume_parser.py     → Structured candidate fields
    ↓
skill_extractor.py   → Candidate skill list
    ↓
jd_parser.py         → Structured JD fields
    ↓
skill_extractor.py   → JD skill list
    ↓
matcher.py           → Match score (Skill + TF-IDF + Semantic)
    ↓
skill_gap.py         → Gap analysis
    ↓
job_recommender.py   → Role recommendations
    ↓
pipeline.py          → Combined result dict
    ↓
app.py               → Streamlit dashboard
```

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| PDF extraction | PyMuPDF (fitz) |
| NLP | spaCy, NLTK, Regex |
| ML | scikit-learn (TF-IDF, cosine similarity) |
| Semantic similarity | sentence-transformers/all-MiniLM-L6-v2 |
| Data | pandas, CSV |
| Database | SQLite (built-in Python) |
| Visualisation | Plotly |
| Testing | pytest |
| Deployment | Streamlit Community Cloud |

---

## 6. Folder Structure

```
Resume_Intelligence_System/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── src/
│   ├── __init__.py
│   ├── pdf_extractor.py    # PDF → raw text
│   ├── resume_parser.py    # Extract structured fields from resume
│   ├── jd_parser.py        # Extract structured fields from JD
│   ├── text_preprocessor.py# Clean & normalise text
│   ├── skill_extractor.py  # Detect & normalise skills
│   ├── matcher.py          # Calculate match score
│   ├── skill_gap.py        # Gap analysis
│   ├── job_recommender.py  # Recommend roles
│   ├── pipeline.py         # Orchestrate the full analysis
│   ├── database.py         # SQLite persistence
│   └── utils.py            # Shared helpers
│
├── data/
│   ├── skills.csv          # Skill dictionary with aliases
│   └── job_roles.csv       # Role → skills mapping
│
├── tests/
│   ├── test_pdf_extractor.py
│   ├── test_resume_parser.py
│   ├── test_jd_parser.py
│   ├── test_skill_extractor.py
│   ├── test_matcher.py
│   └── test_pipeline.py
│
├── evaluation/
│   ├── README.md
│   ├── resume_annotations.csv
│   ├── jd_annotations.csv
│   ├── pair_annotations.csv
│   └── results.csv
│
└── .streamlit/
    └── config.toml
```

---

## 7. Installation

### Prerequisites
- Python 3.11+ ([download](https://www.python.org/downloads/))
- Git ([download](https://git-scm.com/))

### Step-by-step

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/Resume_Intelligence_System.git
cd Resume_Intelligence_System

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Download the spaCy English model
python -m spacy download en_core_web_sm

# 6. (Optional) Copy the environment template
cp .env.example .env
```

---

## 8. How to Run Locally

```bash
# Make sure your virtual environment is activated
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## 9. How to Upload a Resume

1. In the **sidebar**, click "Browse files" under "Upload Your Resume".
2. Select a **text-based PDF** resume (not a scanned image).
3. Paste or upload a **job description** in the JD section.
4. Click **"🚀 Analyze Resume"**.

> **Tip:** If the app says no skills were detected, make sure your resume has a "Skills" or "Technical Skills" section.

---

## 10. How Matching Works

The match score is a weighted combination of three signals:

| Signal | Weight | Method |
|---|---|---|
| Skill Match | 50% | Jaccard similarity between resume skills and JD required skills |
| Text Similarity | 30% | TF-IDF cosine similarity |
| Semantic Similarity | 20% | sentence-transformers/all-MiniLM-L6-v2 |

**Formula:**
```
Score = 0.50 × skill_jaccard + 0.30 × tfidf_cosine + 0.20 × semantic_cosine
```

If the semantic model is unavailable, the 20% weight is redistributed proportionally.

**Important:** This score is a system-generated indicator. It is not a scientifically validated hiring probability.

---

## 11. How Skill Gap Analysis Works

1. Extract skills from the resume using `skill_extractor.py`.
2. Extract required skills from the JD using `skill_extractor.py`.
3. Compute:
   - **Matched** = resume_skills ∩ jd_required_skills
   - **Missing** = jd_required_skills − resume_skills
   - **Additional** = resume_skills − jd_required_skills
4. Match percentage = |Matched| / |JD Required Skills| × 100

---

## 12. How Job Recommendations Work

1. Load `data/job_roles.csv` (20 predefined roles with required skills).
2. For each role, compute:
   ```
   score = |resume_skills ∩ role_skills| / |role_skills| × 100
   ```
3. Sort roles by score (descending).
4. Return the top 5 roles with matched/missing skills.

---

## 13. Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src --cov-report=term-missing

# Run a specific test file
pytest tests/test_resume_parser.py -v
```

All tests are designed to run **offline** — no internet or real PDF files required.

---

## 14. Evaluation Methodology

See [`evaluation/README.md`](evaluation/README.md) for full details.

**Metrics:**
- Extraction quality: Precision, Recall, F1
- Matching quality: Mean Absolute Error vs human-annotated scores

> ⚠️ Annotation data has not been populated yet. The templates are in `evaluation/`. Real evaluations require anonymised real-world resumes.

---

## 15. Deployment on Streamlit Community Cloud

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/Resume_Intelligence_System.git
   git push -u origin main
   ```

2. **Open [share.streamlit.io](https://share.streamlit.io)**

3. Click **"New app"**

4. Select:
   - Repository: `YOUR_USERNAME/Resume_Intelligence_System`
   - Branch: `main`
   - Main file: `app.py`

5. Click **"Deploy"**

6. Wait 2–5 minutes for the build (sentence-transformers is large).

7. Share the public URL.

> **Note on memory:** `sentence-transformers` and `torch` are large. Free Streamlit Cloud has 1 GB RAM. The app gracefully falls back to TF-IDF if the model cannot be loaded.

---

## 16. Known Limitations (Version 1)

1. **Scanned PDFs are not supported.** OCR is not included.
2. **Password-protected PDFs** cannot be extracted.
3. **Rule-based extraction** may fail on unusual resume layouts.
4. **The skill dictionary** does not cover every possible skill.
5. **TF-IDF** is lexical — it misses synonyms and paraphrases.
6. **Semantic models** are still not perfect and can be biased.
7. **Match scores are system-generated**, not scientifically validated.
8. **Job recommendations** are limited to the 20 roles in `job_roles.csv`.
9. **Name detection** is heuristic and may fail for some formats.
10. **No OCR support** for scanned documents.

---

## 17. Future Scope

- OCR support for scanned PDFs (e.g., Tesseract).
- Larger, more accurate skill dictionaries.
- LLM-powered extraction for edge cases (with user consent).
- Support for DOCX and other resume formats.
- Multi-language support.
- Bias detection and fairness analysis.
- User accounts and history.
- Bulk analysis for recruiters.
- Fine-tuned matching model on real resume–JD pairs.

---

## 18. Disclaimer

This system is an **academic prototype** built for learning purposes. It should not be used as the sole basis for hiring or employment decisions. Match scores are algorithmic estimates, not ground truth assessments of candidate quality.

---

*Built with ❤️ using Python, spaCy, scikit-learn, sentence-transformers, and Streamlit.*
