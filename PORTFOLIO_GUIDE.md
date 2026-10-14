# Presenting Resume Intelligence honestly

## What is demonstrable now

- A working Streamlit app with PDF upload, pasted text and a built-in synthetic demo.
- Explainable matching: skill requirement coverage, lexical similarity, optional semantic extension, alternatives and preferred skills.
- A trace from detected skill to source snippet, plus extracted text for checking PDF layout errors.
- Generic role recommendations with essential gates, core groups and optional learning suggestions.
- JSON and printable HTML exports, session isolation and local storage disabled by default.
- Lightweight, pinned dependencies, GitHub test workflow and free Streamlit Cloud deployment instructions.
- 160 passing automated tests, including 24 hand-authored synthetic PDF regression cases. Actual results are committed with a reproducible runner.

## A resume bullet you can use after you understand and run the code

Built an explainable resume-to-job matching prototype using Python, Streamlit, PyMuPDF and scikit-learn, with skill-gap analysis, role recommendations, source evidence and report exports; verified behavior with 160 automated tests and a 24-case synthetic PDF regression suite.

Do not claim "100% accurate", "ATS-certified", "validated hiring predictions" or live deployment before actually deploying. If you used coding assistance, understand and be ready to explain the code and your contribution.

## Five-minute demo

1. Launch the app and select Demo under Resume input. Explain that the candidate and job are fictional.
2. Show required coverage alongside the overall indicator. Explain why text similarity means they can differ.
3. Point out Django or Flask as one requirement, and preferred skills as optional.
4. Show a matched skill's snippet and the extracted resume text.
5. Switch to an unrelated resume; show the distinction between job-specific fit and generic career recommendations.
6. Download the printable report. Show the automated checks and evaluation cases in the repository.
7. State the limits: it detects document mentions, not competence; education and years of experience need manual review.

## What still needs independent validation

Collect 30-50 varied, consented/anonymised resumes across the supported roles, including full, partial and poor-fit pairs. Have another reviewer annotate required skills, preferred skills, OR groups, contact fields and matching evidence before seeing app output. Separate a development set from a final held-out set. Do not modify the system using held-out results, then continue calling that set unseen.

Measure extraction precision/recall/F1 per role, contact accuracy, requirement-group accuracy, pairwise ranking agreement and the frequency of unsupported/ambiguous cases. Report sample size, per-role failures and scope. Evaluate scanned/multi-column/long documents separately; scanned PDFs are currently unsupported. Save anonymised evidence of failures and rerun the full regression suite after fixes.

A portfolio prototype is a reasonable description today. Broader production-readiness depends on independent data, deployment tests, privacy/access design and verified behavior outside these synthetic cases.
