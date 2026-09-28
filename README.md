# StatScholar

A general-purpose statistical analysis platform anchored by a complete
Mann-Kendall trend-analysis suite — correlation, regression, and automated
reporting built in. Data preparation, descriptive statistics, trend analysis,
correlation, regression, visualization, automated interpretation, and report
generation in one system.

## Structure

```
statscholar/
├── render.yaml                Render deployment blueprint (backend + frontend + database)
├── backend/                   FastAPI + pandas/scipy/statsmodels/reportlab/SQLAlchemy
│   ├── app/
│   │   ├── main.py            app entrypoint, wires all routers
│   │   ├── routers/           one file per module (auth, data, trend, correlation, regression, visualization, report)
│   │   ├── services/          actual statistical logic + interpretation engine + auth/data persistence
│   │   ├── models/schemas.py  Pydantic request/response shapes
│   │   └── core/
│   │       ├── config.py      settings, incl. database_url and secret_key (env-overridable)
│   │       └── db.py          SQLAlchemy engine + table definitions (SQLite locally, Postgres in production)
│   ├── tests/                 pytest — trend_service math is unit-tested (12 tests)
│   └── requirements.txt
│
├── frontend/                  React + Vite
│   ├── src/
│   │   ├── pages/              one component per module, mirrors the sidebar
│   │   ├── components/         Layout (sidebar/mode toggle), shared UI primitives
│   │   ├── api/client.js       thin axios wrapper over the backend (VITE_API_BASE_URL configurable at build time)
│   │   └── styles/theme.js     design tokens — single source of truth for color/type
│   └── package.json
│
└── docs/
    ├── USER_GUIDE.md
    ├── TECHNICAL_REFERENCE.md
    └── DEPLOYMENT.md           step-by-step Render deployment guide, incl. free-tier caveats
```

## Deploying publicly

See `docs/DEPLOYMENT.md` for a full walkthrough of deploying to Render
using the `render.yaml` blueprint at the repo root (backend + frontend +
database, all from one file). Includes honest caveats about free-tier
limitations (the free Postgres expires after 30 days — Neon is suggested
as a genuinely persistent free alternative).

## Running locally

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (separate terminal):
```bash
cd frontend
npm install
npm run dev
```
Vite proxies `/api/*` to `http://localhost:8000` (see `vite.config.js`), so the
frontend just calls relative `/api/...` paths — no CORS wrangling needed in dev.

## Documentation

- `docs/USER_GUIDE.md` — module-by-module walkthrough for end users
- `docs/TECHNICAL_REFERENCE.md` — architecture, statistical method references,
  API endpoint list, and testing overview (useful for thesis documentation
  or IP/copyright preparation)

## Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

78 tests: 12 unit tests on the trend-test math directly, 66 integration
tests through the live API (including regression tests for two real bugs
found during development — see `docs/TECHNICAL_REFERENCE.md` for details).

## What's implemented

**Trend Analysis — all six Mann-Kendall family tests:**
- Mann-Kendall
- Sen's Slope
- Modified Mann-Kendall (Hamed & Rao, 1998 variance correction)
- Pre-Whitening (von Storch, 1995)
- Trend-Free Pre-Whitening (Yue et al., 2002)
- Seasonal Mann-Kendall (Hirsch, Slack & Smith, 1982), including a formal
  Van Belle & Hughes (1984) chi-square test for homogeneity of trend across
  seasons — not just a heuristic flag

Each has real unit tests in `tests/test_trend_service.py` covering substantive
statistical behavior (e.g. Modified MK is verified to become more conservative
under autocorrelation; TFPW is verified to preserve a real trend even under
heavy autocorrelation; the homogeneity test is verified to distinguish
genuinely homogeneous from heterogeneous seasonal trends).

**Also fully implemented:**
- Data upload, type detection, quality scoring
- A `/data/{id}/series` endpoint for raw column data, used by every chart
- Descriptive statistics
- Pearson / Spearman / Kendall correlation, with method auto-recommendation
- Simple linear regression, with residual normality + homoscedasticity checks
- The Automated Interpretation rule-based engine for all of the above
- **Real charts** in Trend Analysis (line + trend reference), Correlation
  (scatter), and Regression (scatter + fitted line) — not placeholders
- **Visualization module's chart recommendations** are computed from the
  actual dataset's column types and correlations (time-series detection,
  scatter pairs ranked by correlation strength, heatmap for 3+ numeric
  columns, bar chart for categorical/grouping columns) — not a static list
- **The session-wide Automated Interpretation log** is populated automatically
  every time Trend Analysis, Correlation, or Regression produces a result
- **DOCX and PDF report export**, both pulling from that same log. PDF export
  sanitizes characters ReportLab's built-in fonts can't render (Greek letters,
  subscripts) into plain-text equivalents rather than silently producing
  black boxes — see `sanitize_for_pdf` in `routers/report.py`
- **Real chart images embedded in exported reports** — the Trend Analysis,
  Correlation, and Regression sections carry an actual matplotlib-rendered
  chart (line/scatter/heatmap/bar) alongside the text, generated server-side
  from the same dataset, in both DOCX and PDF — see `chart_service.py`
- **Real formatted tables in exported reports** — the "Figures & tables"
  section includes an actual Descriptive Statistics table and Correlation
  Matrix table (proper rows/columns/borders in both DOCX and PDF), not just
  text summarizing the numbers
- **Visualization connects to Report Generation** — clicking "Add to report"
  on any chart recommendation adds it as its own section in the report,
  complete with an embedded image, without needing to separately run that
  comparison through Trend/Correlation/Regression
- **Disk-backed dataset persistence** — uploaded datasets survive a backend
  restart (including uvicorn `--reload` triggering on a code change), not
  just an in-memory dict that silently loses everything
- **Visualization renders real charts inline** — clicking a recommendation
  fetches the actual data and draws the chart (line/scatter/bar/heatmap)
  on the page itself, not just a suggestion pointing you to another module
- **Multi-user accounts with real data isolation** — sign up / log in
  (bcrypt-hashed passwords, JWT session tokens), and every dataset is tagged
  with its owner. Every single endpoint that touches a dataset enforces
  ownership — one user genuinely cannot see, analyze, or export another
  user's data, verified across all 7 dataset-touching endpoints and
  confirmed to survive a backend restart — see `auth_service.py` and
  `NotOwnedError` in `data_service.py`
- **Email verification and password reset** — real tokens (single-use,
  expiring), with a dev-mode fallback that prints the email content
  (including the working link) to the backend's terminal when SMTP isn't
  configured, so the whole flow works locally with zero email setup. Set
  `STATSCHOLAR_SMTP_HOST`/`SMTP_USERNAME`/`SMTP_PASSWORD` to send real
  email instead — see `email_service.py`. **Resetting a password
  invalidates every previously-issued session token**, not just the
  password hash — found and fixed after real end-to-end browser testing
  showed an old, pre-reset session remaining logged in indefinitely
- **Email verification is actually enforced**, not just a status flag —
  a `require_verified_user` dependency blocks all 7 real-work endpoints
  (upload, series, descriptive stats, trend, correlation, regression,
  visualization, report export) until an account is verified, while
  `/auth/me` and `/auth/resend-verification` stay reachable so an
  unverified account isn't locked out with no way forward. Verified with
  a dedicated test suite plus a full real-browser walkthrough: signed up,
  confirmed a false "I've verified" click is correctly rejected, verified
  for real, confirmed the app unlocks and a genuine file upload succeeds
- **Deployment-ready persistence** — migrated from local disk (SQLite file
  + CSV files, which would be wiped on most hosting platforms' ephemeral
  filesystems) to SQLAlchemy against a real database. Same code runs
  against SQLite locally (zero setup) or PostgreSQL in production (just a
  different `STATSCHOLAR_DATABASE_URL`) — verified against an actual local
  PostgreSQL server, not just assumed, including a real bug this caught:
  the test suite's database-reset-between-runs logic only worked for
  SQLite until fixed. See `core/db.py` and `docs/DEPLOYMENT.md`.

## Deliberately out of scope for v1

- Multiple linear regression and logistic regression (simple linear only)
- A covariance-aware version of Seasonal Mann-Kendall that accounts for
  cross-season correlation (the current version assumes independence
  between seasons, which is the standard basic form of this test)

## Before deploying auth beyond your own machine

`auth_service.py` has a hardcoded JWT secret key with a comment flagging
exactly this — fine for local/single-machine use where nobody else can
reach the process to forge a token, but **must** be replaced with a real
secret from an environment variable before deploying anywhere reachable by
other people. User accounts live in `backend/data_store/users.db` (SQLite);
back that file up like you would any other data before wiping `data_store/`.

## Design reference

`frontend/src/styles/theme.js` holds the design tokens: ink navy `#1B2A4A`, teal
`#2F6F6B`, amber `#C97D34` for flags, Source Serif 4 for interpretation text,
IBM Plex Sans for UI chrome, IBM Plex Mono for numeric output.
