"""Side-by-side scenarios: Roth vs. traditional contributions, and Roth conversions on vs. off.

Scenarios are compared on after-tax wealth, because a dollar in a traditional
account isn't worth a dollar: whoever withdraws it owes income tax.
Traditional and HSA balances are valued at (1 - PRETAX_BALANCE_TAX_RATE).

Leftover cash is invested in both scenarios (in the plan's surplus account,
the first taxable account, or a new one). Otherwise the scenario that pays
less tax now would just leave its savings uninvested, which isn't a fair test.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel

from .engine import project
from .models import Account, AccountType, Plan

PRETAX_BALANCE_TAX_RATE = 0.24  # tax assumed on traditional/HSA money left at the end

ComparisonKind = Literal["contribution_type", "roth_conversion"]


class ScenarioResult(BaseModel):
    name: str
    lifetime_taxes: float  # nominal
    lifetime_taxes_today_dollars: float
    balance_at_retirement_today_dollars: float
    final_net_worth_today_dollars: float
    after_tax_final_today_dollars: float  # final net worth with pre-tax balances taxed
    depletion_age: Optional[int]


class Comparison(BaseModel):
    kind: ComparisonKind
    scenarios: List[ScenarioResult]
    better: str  # name of the scenario with more after-tax wealth at the end
    difference_today_dollars: float  # how much more, today's dollars


def _with_surplus_invested(plan: Plan) -> Plan:
    if plan.surplus_account_id:
        return plan
    taxable = next((a for a in plan.accounts if a.type == AccountType.taxable), None)
    if taxable:
        return plan.model_copy(update={"surplus_account_id": taxable.id})
    returns = [a.expected_return for a in plan.accounts] or [0.07]
    savings = Account(id="leftover-savings", name="Leftover savings", type=AccountType.taxable, balance=0,
                      expected_return=sum(returns) / len(returns))
    return plan.model_copy(update={"accounts": [*plan.accounts, savings], "surplus_account_id": savings.id})


def contributions_as(plan: Plan, target: AccountType) -> Plan:
    """Redirect every traditional or Roth contribution into an account of `target` type.

    Existing balances stay where they are; a contribution to the other type is
    moved to a new, empty account of the target type with the same settings.
    """
    accounts: List[Account] = []
    for a in plan.accounts:
        if a.type in (AccountType.traditional, AccountType.roth) and a.type != target and a.annual_contribution > 0:
            accounts.append(a.model_copy(update={"annual_contribution": 0}))
            label = "Roth" if target == AccountType.roth else "pre-tax"
            accounts.append(a.model_copy(update={
                "id": f"{a.id}~{target.value}", "name": f"{a.name} ({label})", "type": target, "balance": 0,
                "cost_basis": 0 if target == AccountType.roth else None, "holdings": [],
            }))
        else:
            accounts.append(a)
    return plan.model_copy(update={"accounts": accounts})


def _evaluate(name: str, plan: Plan, start_year: Optional[int]) -> ScenarioResult:
    proj = project(plan, start_year)
    last = proj.years[-1]
    price_level = (1 + plan.spending.inflation) ** (last.year - proj.summary.start_year)
    pretax_ids = {a.id for a in plan.accounts if a.type in (AccountType.traditional, AccountType.hsa)}
    pretax = sum(last.balances[i] for i in pretax_ids)
    return ScenarioResult(
        name=name,
        lifetime_taxes=proj.summary.lifetime_taxes,
        lifetime_taxes_today_dollars=proj.summary.lifetime_taxes_today_dollars,
        balance_at_retirement_today_dollars=proj.summary.balance_at_retirement_today_dollars,
        final_net_worth_today_dollars=round(last.net_worth / price_level, 2),
        after_tax_final_today_dollars=round((last.net_worth - PRETAX_BALANCE_TAX_RATE * pretax) / price_level, 2),
        depletion_age=proj.summary.depletion_age,
    )


def compare(plan: Plan, kind: ComparisonKind, start_year: Optional[int] = None) -> Comparison:
    plan = _with_surplus_invested(plan)
    if kind == "contribution_type":
        scenarios = [
            _evaluate("Pre-tax (traditional) contributions", contributions_as(plan, AccountType.traditional),
                      start_year),
            _evaluate("Roth contributions", contributions_as(plan, AccountType.roth), start_year),
        ]
    else:
        if plan.roth_conversion is None:
            raise ValueError("The plan has no Roth conversion to compare")
        scenarios = [
            _evaluate("Without Roth conversions", plan.model_copy(update={"roth_conversion": None}), start_year),
            _evaluate("With Roth conversions", plan, start_year),
        ]
    a, b = scenarios
    better, other = (a, b) if a.after_tax_final_today_dollars >= b.after_tax_final_today_dollars else (b, a)
    return Comparison(kind=kind, scenarios=scenarios, better=better.name,
                      difference_today_dollars=round(better.after_tax_final_today_dollars
                                                     - other.after_tax_final_today_dollars, 2))
