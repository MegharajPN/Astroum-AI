# CLAUDE.md — conventions for this repo

## What this is
Astroum AI / BRAHMO assessment: reference data (drug master, NLEM, Jan Aushadhi, gazette, interaction seeds,
pharmacy stock, STW protocols) in MySQL, a deterministic safety rail, a grounded Q&A slice, and a React console.

## Non-negotiable rules (from the architecture document)
1. No model call in any safety-check path. `rail.py` must stay pure lookup over versioned rows.
2. Missing data is never "safe". Use the 8-state vocabulary exactly (`rail.py` constants).
3. No silent resolution. Ambiguous brands are queued in `GapEntry`, never linked.
4. Every row carries a `LoadBatch`. Every result carries rule and data versions.
5. No hardcoded thresholds, lists or severities in code paths. They live in `backend/config/settings.py` under `BRAHMO`,
   each with its citation where clinical.
6. Dose questions: quote, never compute for a patient. No patient-specific dose calculator anywhere.
7. Fences: no diagnostic ranking, triage scoring, treatment plans or patient-facing advice.

## Layout
- `backend/config/settings.py` — DB block (env-overridable), `BRAHMO` config, rule versions.
- `backend/brahmo/ingest.py` — loaders. Rejects and logs; never guesses.
- `backend/brahmo/rail.py` — safety rail. `qa.py` — grounded Q&A. `trace.py` — end-to-end trace.
- `backend/brahmo/fixtures/` — verbatim excerpts of packet files used by tests (not the full packet).
- `eval/sample_questions.json` — mini-eval labels. Hand-written; see DESIGN.md D-011 on optimism.
- `outputs/` — generated seed-rail and trace outputs.

## Commands
- `python manage.py test brahmo` — tests (must pass before any commit).
- `python manage.py load_packet` — load `../data` (idempotent by file hash; `--replace` to reload).
- `python manage.py run_seed_rail` — fill the seeded prescription outputs.
- `python manage.py run_eval` — score the Q&A slice (needs the STW corpus loaded).

## Working agreements
- Run the test suite before reporting a change as done.
- Do not commit the packet data (`data/*.csv`, `data/corpus/`); `.gitignore` covers it.
- Do not add a dependency without pinning its version.
- Record any new clinical threshold in DESIGN.md with its source.
