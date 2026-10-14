# Reproducible evaluation

## Current evidence

`cases.json` contains 24 developer-authored synthetic cases. The runner renders real in-memory PDFs, invokes the full pipeline, and checks exact sets of required, matched, missing and preferred skills plus candidate name, email and phone. Cases cover backend, frontend, data, machine learning, cloud, security, mobile and design, with aliases, explicit requirements, mixed optional clauses, alternatives, negation and a two-column layout.

Run `python evaluation/run_evaluation.py` from the repository root. It writes `latest_results.json` and exits nonzero if any case fails. The same cases are included as parametrised pytest regressions. `baseline_v12_results.json` stores results from the unmodified v1.2 archive for comparison.

All 24 checks pass on v1.3. These cases informed development and are not a held-out benchmark. The score column is a model output, not a ground-truth quality label. The checks do not verify competence, actual seniority, real identity, or every unlisted skill.

## Real-data validation

The annotation CSVs are legacy empty templates, not measured performance. Populate only with consented and anonymised data. Annotate before inspecting model output, use a separate reviewer, record disagreement, and keep an untouched held-out set. Measure precision/recall/F1, contact-field accuracy and pairwise ranking agreement per role. Publish denominators, errors and scope; do not extrapolate a synthetic pass rate to all resumes.

See `PORTFOLIO_GUIDE.md` for the collection and interview plan.
