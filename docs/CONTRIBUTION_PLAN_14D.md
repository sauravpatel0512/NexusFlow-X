# 14-day contribution plan (real work, not noise)

Goal: **one meaningful commit per day** (docs, tests, small features, refactors). Keep changes small and reviewable.

| Day | Focus | Concrete deliverable |
| --- | ----- | -------------------- |
| 1 | Hygiene | Add this plan + link from README; tighten wording in one doc |
| 2 | Tests | Add a pytest for edge-case in `quality_rules.yaml` parsing or a path helper |
| 3 | CI | Add `ruff` or `flake8` (pick one) + fix any issues found |
| 4 | DX | Improve `Makefile` help text or add `make fmt` / `make lint` |
| 5 | Observability | Improve structured logging in one streaming job (one file) |
| 6 | DQ | Add one new rule or clearer error message in data quality |
| 7 | Docs | Expand `LOCAL_RUNBOOK.md` with a troubleshooting section |
| 8 | Analytics | Small Streamlit UX tweak (labels, empty state, error banner) |
| 9 | Security | Scan for secrets; add `pre-commit` hook for basic checks |
| 10 | Perf | Document Spark tuning knobs used; add a short comment in `gold_aggregations.py` |
| 11 | Packaging | Pin versions in `requirements.txt` with rationale in commit message |
| 12 | Demo | Add a short “expected output” snippet to `DEMO_SCRIPT.md` |
| 13 | Tests | Add a contract test for a schema edge case |
| 14 | Release | Tag `v1.1.0` with notes (what changed + how to verify) |

Rules:

- Prefer **small PR-sized commits** over giant dumps.
- Never commit generated `data/` outputs.
- If you miss a day, **do not backdate** commits; just continue.
