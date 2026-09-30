# Financial Planning App

A financial planning dashboard: enter a client's profile, income, spending and
accounts, and see a year-by-year projection through retirement — including
whether the money lasts. Built as a practice alternative to commercial planning
software, and as a portfolio project built with AI assistance.

See [SCOPE.md](SCOPE.md) for the full feature plan and phases.

## Run it

Requires Python 3.12 and Node (`brew install python@3.12 node`).

```bash
# one-time setup
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
(cd frontend && npm install)

# start both servers, then open http://localhost:5173
./dev.sh
```

Run the engine tests with `cd backend && .venv/bin/pytest`.

## How it's built

| Part | Where | What |
|---|---|---|
| Finance engine | `backend/app/engine.py` | Year-by-year projection; pure Python, no web code |
| Data model | `backend/app/models.py` | Plan (input / saved file) and Projection (output), validated with Pydantic |
| API | `backend/app/main.py` | FastAPI: `POST /api/project` |
| Dashboard | `frontend/src` | React + TypeScript, charts with Recharts |
| Tests | `backend/tests` | Engine checked against closed-form formulas (compound growth, annuity future value) |

### Projection rules (Phase 1)

Each year, in order:
1. In retirement, that year's spending is withdrawn from the accounts at the start
   of the year, proportionally to each account's balance.
2. Each account grows by its expected return.
3. Contributions are added at the end of the year (by default from this year
   until the year before retirement).

Spending and income are in future (nominal) dollars; "today's dollars" divides by
cumulative inflation. Taxes, Social Security and other retirement income are
Phase 2.

## Client plan files

**Save plan** downloads the current client as a `.json` file; **Open…** loads one
back. Files ending in `-plan.json` are git-ignored so client data never ends up
in the repository. Use fictional clients for practice.
