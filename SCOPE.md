# Financial Planning App — Scope (draft)

A financial planning dashboard: enter a client's profile, income, accounts and goals,
and it projects their finances year by year through retirement, with correct tax
treatment per account type and live market data for investments.

Built as a practice alternative to Zola, for personal use, and as a portfolio project.

Status: all five phases built. Edit freely as the plan grows.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Finance engine | Python | All projection and tax math in one tested module, separate from the UI |
| Market data | `yfinance` | No API key, no request quotas. Unofficial, so results are cached and failures are handled gracefully |
| Backend API | FastAPI | Serves the engine and market data to the frontend |
| Frontend | React + TypeScript (Vite) | Dashboard UI and charts |
| Storage | One JSON file per client plan | Save, load and share a plan as a separate file |

## Client data (inputs)

**Personal**
- Name, date of birth (spouse/partner optional)
- Place of residence (state — drives state tax later)
- Retirement age, life expectancy

**Income**
- Salary / primary income, expected raises
- Other income: business income, rental, side income
- Retirement income: Social Security, pensions, annuities, business income continuing into retirement
- Expected inheritance (amount, approximate year)

**Spending**
- Current spending (what they spend) vs. target spending (what they want to spend)
- Basic living expenses, healthcare costs (pre- and post-Medicare)

**Investment accounts**
- Account type: taxable brokerage, Traditional IRA/401(k), Roth IRA/401(k), 529, HSA
- Current balance, holdings (tickers) or a simple expected-growth rate
- Contributions per account: amount, start year, stop year

**Goals** (each is a cost in a given year or range of years)
- Home purchase / new home (with mortgage financing), home improvement
- Kids' college (linked to 529), grandkids
- Travel, charitable giving, healthcare, other

**Liabilities** (light)
- Debts that last into retirement: mortgage, loans, with balance, rate, payoff date

## Outputs

- Year-by-year projection from today to life expectancy: balances by account, income, spending, taxes
- Charts: net worth over time, account balances, income vs. spending in retirement
- Goal check: is each goal funded, and when
- Goal probability: how likely each goal is to be funded, from Monte Carlo simulation
- Asset allocation of current holdings (stocks / bonds / cash / sectors), from live data
- Answer to "does the money last?" — the age when assets run out, if they do

## Tax rules (must be correct)

- **Traditional accounts:** contributions reduce taxable income now; withdrawals taxed as ordinary income; required minimum distributions (RMDs) from age 73/75
- **Roth accounts:** contributions from after-tax income; qualified withdrawals tax-free (age 59½ + 5-year rule)
- **529:** after-tax contributions; tax-free growth and withdrawals for qualified education costs
- **HSA:** deductible in, tax-free growth, tax-free out for medical costs
- **Taxable:** capital gains tax on growth when sold
- Early-withdrawal 10% penalty before 59½ (with common exceptions)
- Federal brackets, standard deduction, and contribution limits stored as yearly tables so they can be updated each year
- State income tax by residence (later phase)

## Phases

**Phase 1 — works end to end (day one)** ✅ done
- Client profile form: DOB, income, spending, retirement age, life expectancy
- Accounts with balance, yearly contribution, expected growth rate
- Year-by-year projection and growth chart
- Save / load / share a client plan as a JSON file

**Phase 2 — real planning** ✅ done
- Account tax types and correct federal tax on contributions and withdrawals
- Retirement income sources (Social Security, pension, annuities, business income)
- Goals as cash flows, with contributions' start/stop years
- RMDs, early-withdrawal penalties

**Phase 3 — live market data** ✅ done
- Holdings by ticker via `yfinance`: current prices, history, fund data
- Historical returns to suggest expected growth rates
- Asset allocation breakdown
- Caching so repeated lookups don't hit Yahoo each time
- Monte Carlo simulation using each fund's historical volatility: probability the plan succeeds and each goal is funded (e.g. "College: 87% likely")

**Phase 4 — advanced** ✅ done
- State taxes, mortgage/financing calculator, debts, inheritance
- Roth vs. Traditional comparison and Roth conversions (fixed amount or fill a tax bracket)

**Phase 5 — UI** ✅ done (navy-and-gold advisor look, light and dark themes)
- Screens for holdings and allocation, Monte Carlo results, debts, inflows, conversions and comparisons
- Printable/PDF client report (Download report → Save as PDF)
- Optional password-protected (encrypted) client files

## Data & privacy

- Plans stay on the user's machine as files; nothing is uploaded anywhere
- Use fictional clients for practice. Real client data from work should follow the firm's compliance rules

## Out of scope for now

- Copilot Studio (not needed — `yfinance` covers live data)
- Multi-user accounts / hosting online
- Direct connections to brokerages or banks
