# Evaluation Framework — Resume Intelligence System

## Purpose

This folder contains annotation templates and evaluation results for
assessing the quality of the Resume Intelligence System.

## What is evaluation and why does it matter?

A rule-based NLP system like this one needs to be *measured* against
known-correct answers to understand how well it works. This is called
**evaluation** or **benchmarking**.

## Files

| File | Purpose |
|---|---|
| `resume_annotations.csv` | Ground-truth extracted fields for 10 sample resumes |
| `jd_annotations.csv` | Ground-truth extracted fields for 5 sample job descriptions |
| `pair_annotations.csv` | Ground-truth match scores for resume–JD pairs |
| `results.csv` | Computed metrics (filled in after running evaluation) |

## Metrics used

### For extraction (Name, Email, Phone, Skills, etc.)
- **Precision** = correctly extracted / total extracted
- **Recall** = correctly extracted / total that should have been extracted
- **F1 Score** = harmonic mean of precision and recall

### For matching scores
- **Mean Absolute Error (MAE)** vs human-annotated match scores

## Status

⚠️  Annotation data has not been populated yet.

To contribute annotations:
1. Collect 10 diverse resume PDFs (anonymized)
2. Manually extract the ground-truth fields
3. Fill in `resume_annotations.csv`
4. Repeat for 5 job descriptions → `jd_annotations.csv`
5. Create 50 resume–JD pairs with human match scores → `pair_annotations.csv`
6. Run `python -m evaluation.evaluate` to compute metrics → `results.csv`

## Important note

Do not fabricate evaluation results.
Leave blank rows if ground-truth data is not yet available.
