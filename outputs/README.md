# outputs/

Generated artifacts. Regenerate, do not hand-edit.

| File | What it is | Caveat |
|---|---|---|
| `seed_rail_results.json` | Full rail output for the 10 seeded prescriptions (every check, evidence, versions) | Computed on the 18-row CDCI excerpt in `backend/brahmo/fixtures/`, plus the full gazette (12) and interaction seed (15) files. Rerun on the full packet before relying on it. |
| `seed_prescriptions_completed.csv` | The seed template with `candidate_rail_output_state` and `candidate_evidence_note` filled per line | Same caveat. |
| `sample_trace_RX01.json` | One end-to-end trace (Module C) | The rail section is real. The grounded-answer section **abstained only because the scratch database had no STW corpus loaded**. It is not a Q&A result. |

Regenerate the seed outputs against the real database:

```powershell
cd backend
python manage.py load_packet
python manage.py run_seed_rail
```

The 11-question mini-eval (`run_eval`) has **not been run here**: the 13 STW PDFs are not on this machine.
