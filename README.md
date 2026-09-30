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

### Projection rules

Each year, in order:
1. Costs: living expenses, healthcare, goals and contributions.
2. Tax-free money first: 529s pay college goals, HSAs pay healthcare.
3. Required minimum distributions come out of traditional accounts (from 73 or
   75, depending on birth year, using the IRS Uniform Lifetime Table).
4. Anything salary, other income and RMDs don't cover is withdrawn in this order:
   taxable, traditional, HSA (65+), Roth. The withdrawal is solved (bisection)
   so that after federal income tax, payroll tax and early-withdrawal penalties,
   exactly enough is left to pay the year's costs.
5. Accounts grow by their expected return.
6. Contributions are added at year end; leftover cash in retirement is
   reinvested in the first taxable account.

Taxes (`backend/app/tax.py`) use 2026 IRS figures, indexed by the plan's
inflation rate in later years: ordinary brackets, standard and 65+ deductions,
the 2025–2028 senior deduction, long-term capital gains stacked on ordinary
income, net investment income tax, Social Security benefit taxation, payroll
tax, and the 10% early-withdrawal penalty. Roth contributions come out tax-free
before earnings. Not yet modeled: state tax, the Roth 5-year rule,
self-employment tax, itemized deductions and credits.

## Client plan files

**Save plan** downloads the current client as a `.json` file; **Open…** loads one
back. Files ending in `-plan.json` are git-ignored so client data never ends up
in the repository. Use fictional clients for practice.
