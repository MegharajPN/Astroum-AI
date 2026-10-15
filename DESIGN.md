# DESIGN.md — Astroum AI reference console

## 0. The system in my own words
_Replace this paragraph with your own restatement before submission._
A clinical decision-support back end for Indian outpatient practice. Drug identity is resolved at salt level
from a national drug-code extract, with fixed-dose combinations decomposed. Regulatory status comes from
effective-dated gazette events. A deterministic rail checks prescriptions. Clinical narrative questions are
answered only from versioned Standard Treatment Workflow pages and the clinic's own protocol, with citations or
abstention. This scaffold proves the data layer: versioned loads, provenance on every row, a gaps register,
and read APIs over all of it.

## 0.1 The three riskiest assumptions in the materials
1. _The CDCI subset's strength units are reliable._ The file writes Thyroxine strengths in mg; the seed
   prescriptions write mcg. The loader flags this (`UNIT_MISMATCH_SUSPECTED`) but does not correct it.
2. _Brand names identify products._ The CDCI subset repeats brand names (for example "Suzith Forte" appears for
   three different products). Brand lookups are therefore ambiguous by construction.
3. _The 15-pair severe-interaction seed list is a meaningful safety surface._ It is not. The API returns
   `PARTIAL_COVERAGE` for every pair it does not contain, so the list is never read as "no interaction".

## Decisions

### D-001 — MySQL with PyMySQL, not mysqlclient
- **Decision:** `config/__init__.py` installs PyMySQL as `MySQLdb`. Django's MySQL backend runs unchanged.
- **Why:** No C toolchain is needed on Windows. The fresh-machine reproduction stays under an hour.
- **Rejected:** `mysqlclient` (needs MSVC build tools on Windows); SQLite (the brief names MySQL).
- **Implication:** `utf8mb4` is set in settings because the stock file contains Telugu billing strings.

### D-002 — Every row carries a LoadBatch; re-loads are keyed on file SHA-256
- **Decision:** Each file gets a `LoadBatch` (dataset, file name, SHA-256, source version, row counts, status).
  A file whose hash already loaded `OK` is skipped unless `--replace` is passed.
- **Why:** Any answer can be traced to the exact bytes that produced it. Re-running the loader is safe.
- **Rejected:** Upsert by natural key (silently overwrites history); timestamp-only versioning (cannot prove
  which bytes were used).
- **Implication:** A changed file creates a new batch. Old rows stay until `--replace` clears the dataset.

### D-003 — Unparseable and ambiguous input goes to the gaps register, never into a guess
- **Decision:** Rejected rows, missing strengths, unmatched or ambiguous brands and unit suspicions are written
  as `GapEntry` rows with a `reason_code`. Brand matching is exact-only. A brand shared by several products is
  left unlinked (`AMBIGUOUS`).
- **Why:** Laws 5 and 6 in the architecture document. A silent link is a wrong answer that looks right.
- **Rejected:** Fuzzy matching to pick the closest brand (fuzzy may assist search, never truth); dropping bad
  rows silently (hides the defect).
- **Implication:** Expect a large gaps backlog on first load. That backlog is the honest state of the data.

### D-004 — Interaction check is a pure lookup and reports PARTIAL_COVERAGE for unknown pairs
- **Decision:** `/api/interactions/check/` returns `HIT` for a seed pair, otherwise `PARTIAL_COVERAGE`.
  It never returns `CHECKED_NO_HIT` while the seed list is this small.
- **Why:** Law 4 (no model in the check path) and law 5 (missing data is never "safe").
- **Rejected:** A "no interaction" result for pairs absent from the list.
- **Implication:** `CHECKED_NO_HIT` becomes reachable only when the seed list is backed by a verified, complete
  source for the pair. That is a data-coverage decision, not a code change.

### D-005 — Protocol identity includes the edition
- **Decision:** `ProtocolDocument` is unique on `(code, version)`. Both STW-GP-02 editions load. Each unit links to
  its document, page and section.
- **Why:** The pack contains two editions of hypertension guidance with different first-line drugs. A retrieval
  layer that keys on code alone would blend them.
- **Rejected:** Keying on code only (blends editions); keeping only the current edition (drops the conflict
  that must be shown).
- **Implication:** Retrieval must rank by edition and effective date and show both when they conflict.

### D-006 — Lexical search for protocol units in this scaffold
- **Decision:** `/api/protocol-units/?q=` uses case-insensitive `icontains`.
- **Why:** It works on MySQL without extra setup and is good enough for an 11-question corpus.
- **Rejected for now:** MySQL FULLTEXT (needs tuning and a stopword policy); a vector store (not yet justified
  by corpus size). Both are Module B work.
- **Implication:** Hybrid retrieval (lexical plus embeddings) is still to be built. Recall is not measured yet.

### D-007 — Dashboard and API errors are explicit
- **Decision:** Unhandled API exceptions are logged to the gaps register and returned as HTTP 503 with
  `SERVICE_UNAVAILABLE`. The UI shows that state.
- **Why:** Law 11: fail visibly. An empty table after a crash looks like "no data".
- **Rejected:** Returning 500 with a generic page; returning an empty list.

### D-008 — The rail is pure lookup; the worst state wins
- **Decision:** `backend/brahmo/rail.py` runs four checks (duplicate salt, prohibited FDC from events,
  severe pairs, cumulative daily exposure). The overall state is the most cautious state among all checks.
- **Why:** Laws 4 and 5. One unknown anywhere makes the prescription not-clear, however many checks pass.
- **Rejected:** Averaging states; reporting "clear" when no check fired.
- **Implication:** Most real prescriptions show NOT_CHECKED or PARTIAL_COVERAGE until registers are complete.
  That is the honest state.

### D-009 — Regulatory status is derived from events at query time
- **Decision:** An event is active if no other event on or before the as-of date supersedes it. The latest
  active event decides the status. A STAY_GRANTED active event is reported as SOURCE_CONFLICT.
- **Why:** Law 7. The fixture shows the chain EV001 → EV002 (stay) → EV003 (re-prohibition): the result must be
  PROHIBITED by GSR 411(E), not by the stay.
- **Rejected:** A stored `banned` boolean.
- **Implication:** A scope qualifier such as "(paediatric suspensions only)" or "(specific ratio)" is
  PARTIAL_COVERAGE, not HIT. The rail cannot tell which product form or patient a restriction applies to.

### D-010 — Daily ceilings are configured, each with its citation; only paracetamol has one
- **Decision:** `BRAHMO["DAILY_MAX_MG"]` holds one entry, 3 g/day from STW-GP-01. Other ingredients return
  NOT_CHECKED with the aggregate as evidence.
- **Why:** A ceiling is a clinical threshold. Adding one needs clinical sign-off, not a code change.
- **Implication:** Cumulative exposure is only a real check for paracetamol until more ceilings are signed off.

### D-011 — Grounded Q&A is extractive, with content-coverage abstention
- **Decision:** `brahmo/qa.py` returns verbatim unit text with citations. It never generates text. A unit is
  used only if it matches at least `QA_MIN_DISTINCT_TERMS` terms and at least `QA_MIN_CONTENT_COVERAGE`
  of the question's content terms.
- **Why:** Law 2. Generic words such as "first-line" and "adult" let an unrelated protocol through on a
  two-term threshold; the coverage rule stops that (the migraine question now abstains).
- **Rejected:** An LLM answer step (not needed for this slice; would need its own eval and version pinning).
- **Implication:** Generic-term and synonym lists in settings were chosen while looking at the 11 sample
  questions. **The mini-eval score is therefore optimistic** and is not a held-out measurement.

### D-012 — Editions and sources are shown, never merged
- **Decision:** Two editions of one national code both matched → `EDITION_CONFLICT` with both dates.
  National and clinic units both matched → `DIVERGENCE_SHOWN`. Clinic units are labelled as not national guidance.
- **Why:** Conflict-shown-not-merged rule in the architecture document, and the Module B brief.

## Open items (see the gaps register)
- Authentication and tenancy are not implemented. Write endpoints are open. Do not expose beyond localhost.
- Regulatory status is not yet derived. Events are served, and the derivation rule is still to be written.
- Stock is not normalised to Jan Aushadhi or NLEM. The matching is brand-level only.
