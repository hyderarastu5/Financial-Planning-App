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
1. Costs: living expenses, healthcare, goals (a financed goal costs its down
   payment, then fixed loan payments), debt payments and contributions.
   One-time inflows such as an inheritance land in a taxable account.
2. Tax-free money first: 529s pay college goals, HSAs pay healthcare.
3. Required minimum distributions come out of traditional accounts (from 73 or
   75, depending on birth year, using the IRS Uniform Lifetime Table).
4. Anything salary, other income and RMDs don't cover is withdrawn in this order:
   taxable, traditional, HSA (65+), Roth. The withdrawal is solved (regula
   falsi) so that after federal and state income tax, payroll tax and
   early-withdrawal penalties, exactly enough is left to pay the year's costs.
   A planned Roth conversion moves money to Roth and the withdrawal is re-solved
   to cover its tax.
5. Accounts grow by their expected return.
6. Contributions are added at year end; leftover cash goes to the plan's
   surplus account (or, in retirement, the first taxable account).

**Federal tax** (`tax.py`) uses 2026 IRS figures, indexed by the plan's inflation
rate: brackets, standard and 65+ deductions, the 2025–2028 senior deduction,
long-term capital gains stacked on ordinary income, net investment income tax,
Social Security benefit taxation, payroll tax and the 10% early-withdrawal
penalty.

**State tax** (`states.py`) covers all 50 states and DC from the Tax Foundation's
2026 tables: brackets, standard deductions, personal exemptions, which states
tax Social Security, full retirement-income exemptions (IL, MS, PA, IA 55+) and
Washington's capital gains tax. Phase-outs, local taxes and partial pension
exclusions are not modeled.

Not yet modeled: the Roth 5-year rule, self-employment tax, itemized deductions
and credits.

### Market data and simulation

- `market_data.py` fetches prices, fund asset mix, sectors and 10 years of
  monthly history from Yahoo Finance with `yfinance`, cached on disk under
  `backend/.cache/`; if Yahoo is unreachable, the last cached copy is used.
- `holdings.py` turns an account's holdings into live value, historical growth,
  volatility and allocation.
- `simulation.py` runs the plan under 1,000 random market paths (lognormal
  returns, accounts 80% correlated) for the probability the money lasts, each
  goal's probability of being funded, and balance percentile bands.
- `compare.py` runs side-by-side scenarios (pre-tax vs. Roth contributions,
  Roth conversions on vs. off) and compares after-tax wealth.

### API

| Endpoint | Does |
|---|---|
| `POST /api/project` | Year-by-year projection of a plan |
| `POST /api/simulate` | Monte Carlo probabilities and bands |
| `POST /api/compare` | Side-by-side scenario comparison |
| `POST /api/holdings/analyze` | Live value, returns and allocation for a list of holdings |

## Client plan files

**Save plan** downloads the current client as a `.json` file; **Open…** loads one
back. Files ending in `-plan.json` are git-ignored so client data never ends up
in the repository. Use fictional clients for practice.
