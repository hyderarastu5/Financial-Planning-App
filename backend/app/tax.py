"""US federal tax rules used by the projection.

Figures are for tax year 2026 (IRS Rev. Proc. 2025-32, SSA and IRS limit
announcements). Future years index the inflation-adjusted amounts by the
plan's inflation rate; amounts that the law does not index (Social Security
taxation thresholds, NIIT thresholds, the senior deduction phase-out) stay
fixed.

Not modeled: state tax, AMT, itemized deductions, credits, self-employment
tax, the Roth 5-year rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

BASE_YEAR = 2026

SINGLE = "single"
MARRIED_JOINT = "married_joint"

# (upper bound of bracket, rate); the last bracket has no upper bound.
ORDINARY_BRACKETS = {
    SINGLE: [(12_400, 0.10), (50_400, 0.12), (105_700, 0.22), (201_775, 0.24),
             (256_225, 0.32), (640_600, 0.35), (float("inf"), 0.37)],
    MARRIED_JOINT: [(24_800, 0.10), (100_800, 0.12), (211_400, 0.22), (403_550, 0.24),
                    (512_450, 0.32), (768_700, 0.35), (float("inf"), 0.37)],
}

# Long-term capital gains: taxable income up to the first bound is taxed 0%,
# up to the second 15%, above that 20%.
LTCG_BOUNDS = {SINGLE: (49_450, 545_500), MARRIED_JOINT: (98_900, 613_700)}

STANDARD_DEDUCTION = {SINGLE: 16_100, MARRIED_JOINT: 32_200}
# Extra standard deduction per person aged 65+.
AGE_65_EXTRA_DEDUCTION = {SINGLE: 2_050, MARRIED_JOINT: 1_650}

# One Big Beautiful Bill Act senior deduction: $6,000 per person 65+, tax years
# 2025-2028 only, reduced by 6% of modified AGI above the threshold. Not indexed.
SENIOR_DEDUCTION = 6_000
SENIOR_DEDUCTION_YEARS = range(2025, 2029)
SENIOR_DEDUCTION_PHASEOUT = {SINGLE: 75_000, MARRIED_JOINT: 150_000}
SENIOR_DEDUCTION_PHASEOUT_RATE = 0.06

# Social Security benefit taxation (provisional income thresholds, not indexed).
SS_THRESHOLDS = {SINGLE: (25_000, 34_000), MARRIED_JOINT: (32_000, 44_000)}

# Net investment income tax (not indexed).
NIIT_RATE = 0.038
NIIT_THRESHOLD = {SINGLE: 200_000, MARRIED_JOINT: 250_000}

# Payroll (FICA) taxes on wages, employee share.
SOCIAL_SECURITY_RATE = 0.062
SOCIAL_SECURITY_WAGE_BASE = 184_500  # indexed
MEDICARE_RATE = 0.0145
ADDITIONAL_MEDICARE_RATE = 0.009
ADDITIONAL_MEDICARE_THRESHOLD = {SINGLE: 200_000, MARRIED_JOINT: 250_000}  # not indexed

EARLY_WITHDRAWAL_PENALTY = 0.10
PENALTY_FREE_AGE = 60  # 59½; ages are whole years here, so the first full year past it


def people(status: str) -> int:
    """Married-joint plans assume both spouses are the client's age."""
    return 2 if status == MARRIED_JOINT else 1


def rmd_start_age(birth_year: int) -> int:
    """SECURE 2.0: 73 for people born 1951-1959, 75 for 1960 or later."""
    if birth_year >= 1960:
        return 75
    if birth_year >= 1951:
        return 73
    return 72


# IRS Uniform Lifetime Table (2022 onward): age -> distribution period.
UNIFORM_LIFETIME = {
    72: 27.4, 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1,
    80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
    88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1, 94: 9.5, 95: 8.9,
    96: 8.4, 97: 7.8, 98: 7.3, 99: 6.8, 100: 6.4, 101: 6.0, 102: 5.6, 103: 5.2,
    104: 4.9, 105: 4.6, 106: 4.3, 107: 4.1, 108: 3.9, 109: 3.7, 110: 3.5, 111: 3.4,
    112: 3.3, 113: 3.1, 114: 3.0, 115: 2.9, 116: 2.8, 117: 2.7, 118: 2.5, 119: 2.3,
    120: 2.0,
}


def rmd_amount(prior_year_end_balance: float, age: int, birth_year: int) -> float:
    if age < rmd_start_age(birth_year) or prior_year_end_balance <= 0:
        return 0.0
    return prior_year_end_balance / UNIFORM_LIFETIME[min(age, 120)]


@dataclass(frozen=True)
class TaxYear:
    """Tax rules for one year: 2026 amounts indexed by the plan's inflation."""

    year: int
    status: str
    index: float  # cumulative inflation factor since BASE_YEAR

    @classmethod
    def for_year(cls, year: int, status: str, inflation: float) -> "TaxYear":
        return cls(year, status, (1 + inflation) ** max(0, year - BASE_YEAR))

    def brackets(self) -> List[Tuple[float, float]]:
        return [(bound * self.index, rate) for bound, rate in ORDINARY_BRACKETS[self.status]]

    def deduction(self, age: int, magi: float) -> float:
        d = STANDARD_DEDUCTION[self.status] * self.index
        if age >= 65:
            n = people(self.status)
            d += AGE_65_EXTRA_DEDUCTION[self.status] * self.index * n
            if self.year in SENIOR_DEDUCTION_YEARS:
                excess = max(0.0, magi - SENIOR_DEDUCTION_PHASEOUT[self.status])
                d += max(0.0, SENIOR_DEDUCTION * n - SENIOR_DEDUCTION_PHASEOUT_RATE * excess)
        return d

    def ordinary_tax(self, taxable: float) -> float:
        tax, lower = 0.0, 0.0
        for upper, rate in self.brackets():
            if taxable <= lower:
                break
            tax += (min(taxable, upper) - lower) * rate
            lower = upper
        return tax

    def ltcg_tax(self, ordinary_taxable: float, gains_taxable: float) -> float:
        """Gains are stacked on top of ordinary taxable income."""
        zero_top, fifteen_top = (b * self.index for b in LTCG_BOUNDS[self.status])
        start, end = ordinary_taxable, ordinary_taxable + gains_taxable
        at_15 = max(0.0, min(end, fifteen_top) - max(start, zero_top))
        at_20 = max(0.0, end - max(start, fifteen_top))
        return 0.15 * at_15 + 0.20 * at_20

    def payroll_tax(self, wages: float) -> float:
        ss = SOCIAL_SECURITY_RATE * min(wages, SOCIAL_SECURITY_WAGE_BASE * self.index)
        medicare = MEDICARE_RATE * wages
        medicare += ADDITIONAL_MEDICARE_RATE * max(0.0, wages - ADDITIONAL_MEDICARE_THRESHOLD[self.status])
        return ss + medicare


def taxable_social_security(benefits: float, other_income: float, status: str) -> float:
    """Portion of Social Security benefits included in income (0%, up to 50%, up to 85%)."""
    if benefits <= 0:
        return 0.0
    base1, base2 = SS_THRESHOLDS[status]
    provisional = other_income + 0.5 * benefits
    if provisional <= base1:
        return 0.0
    if provisional <= base2:
        return min(0.5 * (provisional - base1), 0.5 * benefits)
    return min(0.85 * (provisional - base2) + min(0.5 * (base2 - base1), 0.5 * benefits), 0.85 * benefits)


def income_tax(tax_year: TaxYear, *, ordinary: float, gains: float, social_security: float, age: int) -> float:
    """Federal income tax.

    ordinary: wages (after pre-tax contributions), pensions, IRA withdrawals, etc.
    gains: long-term capital gains realized.
    social_security: gross benefits; the taxable share is computed here.
    """
    ss_taxable = taxable_social_security(social_security, ordinary + gains, tax_year.status)
    agi = ordinary + gains + ss_taxable
    taxable = max(0.0, agi - tax_year.deduction(age, agi))
    gains_taxable = min(gains, taxable)  # the deduction offsets ordinary income first
    ordinary_taxable = taxable - gains_taxable
    tax = tax_year.ordinary_tax(ordinary_taxable) + tax_year.ltcg_tax(ordinary_taxable, gains_taxable)
    tax += NIIT_RATE * max(0.0, min(gains, agi - NIIT_THRESHOLD[tax_year.status]))
    return tax
