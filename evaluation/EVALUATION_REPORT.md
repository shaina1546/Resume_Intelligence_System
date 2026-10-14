# v1.3 development evaluation report

Evaluation environment: Python 3.12, semantic scoring disabled, pinned requirements.

| Check | v1.2 | v1.3 |
|---|---:|---:|
| Synthetic cases passing all required/matched/missing/preferred skill-set checks | 16 / 24 | 24 / 24 |
| Synthetic cases passing every check including name, email and phone | 0 / 24 | 24 / 24 |

The v1.2 phone parser lost the country prefix in this contact format, so every case fails its strict phone check. The 0/24 is not a claim that all older skill extraction was wrong. v1.3 fixes that contact pattern; its larger skill improvements concern alternatives, negation, mixed optional clauses and explicit requirements. Development fixes were informed by this suite. It is not held-out or representative real data, and it does not validate overall scoring accuracy.

| Case | v1.3 expected-field checks | Required coverage | Overall indicator |
|---|---|---:|---:|
| backend_full | Pass | 100% | 70 / 100 |
| backend_partial | Pass | 50% | 35 / 100 |
| backend_nonmatch | Pass | 0% | 1 / 100 |
| frontend_full | Pass | 100% | 64 / 100 |
| frontend_partial | Pass | 75% | 53 / 100 |
| data_aliases | Pass | 100% | 63 / 100 |
| data_analyst | Pass | 100% | 67 / 100 |
| ml_missing_framework | Pass | 67% | 48 / 100 |
| cloud_or | Pass | 100% | 68 / 100 |
| framework_or | Pass | 100% | 68 / 100 |
| framework_both | Pass | 100% | 67 / 100 |
| or_group_missing | Pass | 67% | 45 / 100 |
| security_partial | Pass | 67% | 48 / 100 |
| android_full | Pass | 100% | 71 / 100 |
| ios_full | Pass | 100% | 69 / 100 |
| design_full | Pass | 100% | 67 / 100 |
| preferred_section | Pass | 100% | 67 / 100 |
| mixed_clauses | Pass | 100% | 63 / 100 |
| explicit_not_employer_stack | Pass | 100% | 65 / 100 |
| negated_resume | Pass | 50% | 33 / 100 |
| negated_jd | Pass | 100% | 64 / 100 |
| prose_fallback | Pass | 100% | 64 / 100 |
| punctuated_languages | Pass | 100% | 69 / 100 |
| two_column | Pass | 100% | 69 / 100 |

The scores are outputs, not human-labelled targets. Full coverage may produce a lower overall indicator due to wording differences. A mismatch with zero skill coverage may still have a nonzero text score. No scientifically established pass/fail threshold is claimed.

156 automated tests pass. This includes these 24 evaluation cases; do not add them again to claim 180 tests. Fresh dependency checks, Streamlit demo/paste interactions, export escaping, session reruns and HTTP server health pass. Browser screenshot verification was unavailable because the browser binary download failed; layout has not been visually checked in a real browser here. Live account deployment and Windows/macOS execution were not performed.

Independent validation should use consented/anonymised real documents with reviewer annotations created before model output is seen, plus a held-out subset. See PORTFOLIO_GUIDE.md.
