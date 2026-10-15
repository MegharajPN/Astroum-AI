# Astroum AI — Reference console (Django REST + React + MySQL)

A back end that ingests the assessment data packet into MySQL with full provenance, and a React dashboard
over its APIs. Read `DESIGN.md` first. It records the decisions and the riskiest assumptions.

```
Astroum AI/
├── backend/          Django 5.1 + DRF, MySQL via PyMySQL
│   ├── config/       settings.py (DB block), urls, wsgi
│   └── brahmo/       models, ingest (loaders), serializers, views, tests, management command
├── frontend/         React 18 + Vite; pages for drugs, interactions, stock, protocols, gaps
├── data/             Put the packet files here (see data/README.md)
├── DESIGN.md         Decisions, rejected alternatives, riskiest assumptions
└── README.md
```

## 1. Prerequisites
- Python 3.11+, Node 20+
- MySQL 8 on `127.0.0.1:3306`, user `root`, password `123456789` (or set the env vars below)

## 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Create the database if it does not exist (Django does not create it):
python -c "import pymysql; c=pymysql.connect(host='127.0.0.1',user='root',password='123456789'); c.cursor().execute('CREATE DATABASE IF NOT EXISTS astroum_ai_db CHARACTER SET utf8mb4'); print('ok')"

python manage.py migrate
python manage.py test brahmo
python manage.py load_packet            # reads ../data (or --data-dir)
python manage.py runserver
```

Database settings live in `config/settings.py`. Override with environment variables, not by editing the file:

| Key | Default |
|---|---|
| `DB_CONNECTION` | `mysql` (anything else refuses to start) |
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | `3306` |
| `DB_DATABASE` | `astroum_ai_db` |
| `DB_USERNAME` | `root` |
| `DB_PASSWORD` | `123456789` (local dev only; move to env before sharing the repo) |

`load_packet` is idempotent per file hash. Use `--replace` to clear and reload a dataset.

## 3. Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to 127.0.0.1:8000)
npm run build      # production bundle
```

## 4. API

| Endpoint | Purpose |
|---|---|
| `GET /api/dashboard/` | Row counts, open gaps by severity, latest load per dataset |
| `GET /api/products/?q=&ingredient=&fdc=true` | Drug master with salt decomposition |
| `GET /api/nlem/?q=&care_level=P` | Essential medicines |
| `GET /api/jan-aushadhi/?q=` | Generic catalogue prices |
| `GET /api/regulatory-events/?target=&as_of=` | Gazette events (status is derived, not stored) |
| `GET /api/interactions/` · `GET /api/interactions/check/?ingredients=a,b,c` | Seed pairs; pairwise check returns `HIT` or `PARTIAL_COVERAGE` |
| `GET /api/stock/?q=&match_status=&expiring=1` · `GET /api/stock-summary/` | Clinic stock lines and summary |
| `GET /api/protocols/?source_kind=` · `GET /api/protocol-units/?q=&unit_type=` | STW editions and decision units with page anchors |
| `GET /api/gaps/?status=OPEN` · `POST /api/gaps/` · `PATCH /api/gaps/{id}/` | Gaps register (resolve or accept, with a note) |
| `GET /api/load-batches/` | Provenance: file, SHA-256, counts, status |
| `POST /api/rail/check/` | Module A.6 rail: `{prescription: [{written_product, dose_frequency, strength_as_written}], as_of?}` → 8-state result with evidence and versions |
| `GET /api/qa/?q=` | Module B: cited, verbatim answer or explicit abstention (no model) |
| `POST /api/trace/` | Module C: `{prescription, question?}` → one JSON trace with every version used |

Every list is paginated (`?page=`, 25 per page).

## 4a. Seeded rail, Q&A eval and trace

```powershell
cd backend
python manage.py run_seed_rail     # fills the seeded template outputs (needs data/seed_prescriptions_template.csv)
python manage.py run_eval          # mini-eval; needs the STW corpus loaded (see DESIGN.md D-011)
```

Outputs land in `outputs/`. See `outputs/README.md` for what each file is and what has and has not been run.

## 5. Known limits (scaffold)
- No auth. Write endpoints (gap resolution) are open. Localhost use only.
- Protocol search is lexical. No hybrid retrieval yet.
- PDF parsing assumes the STW one-page layout (uppercase headings, `•` bullets). Verify against the real files.
- The packet CSVs are not checked into this repo. Place them in `data/` as described in `data/README.md`.
