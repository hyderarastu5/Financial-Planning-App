"""State income tax, 2026.

Source: Tax Foundation, "2026 State Income Tax Rates and Brackets" (rates,
brackets, standard deductions, personal exemptions). Social Security and
retirement-income treatment: Kiplinger and Tax Foundation 2026 summaries.

This is an estimate. Modeled: brackets, standard deduction, personal
exemption (as a deduction or a credit), taxation of Social Security, full
retirement-income exemptions, Washington's capital gains tax. Not modeled:
phase-outs and benefit recapture, local income taxes, partial pension
exclusions, income limits on Social Security taxation, surtaxes, other
credits. Future years index amounts by the plan's inflation rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Bracket: (income where the rate starts, rate). Income below the first start is untaxed.
Brackets = List[Tuple[float, float]]


@dataclass(frozen=True)
class StateTax:
    name: str
    single: Brackets
    joint: Brackets
    std_deduction: Tuple[float, float] = (0, 0)  # (single, joint)
    exemption: Tuple[float, float] = (0, 0)  # (single, joint): a deduction, or a credit if exemption_is_credit
    exemption_is_credit: bool = False
    taxes_social_security: bool = False  # includes the federally taxable part of benefits
    retirement_exempt_age: Optional[int] = None  # pensions, annuities and IRA/401(k) money exempt from this age
    capital_gains_only: bool = False  # Washington

    def brackets(self, status: str) -> Brackets:
        return self.joint if status == "married_joint" else self.single


def _flat(rate: float, start: float = 0) -> Brackets:
    return [(start, rate)]


NO_TAX: Dict[str, str] = {
    "AK": "Alaska", "FL": "Florida", "NV": "Nevada", "NH": "New Hampshire", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "WY": "Wyoming",
}

STATES: Dict[str, StateTax] = {
    "AL": StateTax("Alabama", [(0, .02), (500, .04), (3_000, .05)], [(0, .02), (1_000, .04), (6_000, .05)],
                   (3_000, 8_500), (1_500, 3_000)),
    "AZ": StateTax("Arizona", _flat(.025), _flat(.025), (8_350, 16_700)),
    "AR": StateTax("Arkansas", [(0, .02), (4_600, .039)], [(0, .02), (4_600, .039)], (2_470, 4_940), (29, 58),
                   exemption_is_credit=True),
    "CA": StateTax("California",
                   [(0, .01), (11_079, .02), (26_264, .04), (41_452, .06), (57_542, .08), (72_724, .093),
                    (371_479, .103), (445_771, .113), (742_953, .123), (1_000_000, .133)],
                   [(0, .01), (22_158, .02), (52_528, .04), (82_904, .06), (115_084, .08), (145_448, .093),
                    (742_958, .103), (891_542, .113), (1_000_000, .123), (1_485_906, .133)],
                   (5_540, 11_080), (153, 306), exemption_is_credit=True),
    "CO": StateTax("Colorado", _flat(.044), _flat(.044), (16_100, 32_200), taxes_social_security=True),
    "CT": StateTax("Connecticut",
                   [(0, .02), (10_000, .045), (50_000, .055), (100_000, .06), (200_000, .065), (250_000, .069),
                    (500_000, .0699)],
                   [(0, .02), (20_000, .045), (100_000, .055), (200_000, .06), (400_000, .065), (500_000, .069),
                    (1_000_000, .0699)],
                   (0, 0), (15_000, 24_000), taxes_social_security=True),
    "DE": StateTax("Delaware",
                   [(2_000, .022), (5_000, .039), (10_000, .048), (20_000, .052), (25_000, .0555), (60_000, .066)],
                   [(2_000, .022), (5_000, .039), (10_000, .048), (20_000, .052), (25_000, .0555), (60_000, .066)],
                   (3_250, 6_500), (110, 220), exemption_is_credit=True),
    "DC": StateTax("District of Columbia",
                   [(0, .04), (10_000, .06), (40_000, .065), (60_000, .085), (250_000, .0925), (500_000, .0975),
                    (1_000_000, .1075)],
                   [(0, .04), (10_000, .06), (40_000, .065), (60_000, .085), (250_000, .0925), (500_000, .0975),
                    (1_000_000, .1075)],
                   (16_100, 32_200)),
    "GA": StateTax("Georgia", _flat(.0519), _flat(.0519), (12_000, 24_000)),
    "HI": StateTax("Hawaii",
                   [(0, .014), (9_600, .032), (14_400, .055), (19_200, .064), (24_000, .068), (36_000, .072),
                    (48_000, .076), (125_000, .079), (175_000, .0825), (225_000, .09), (275_000, .10),
                    (325_000, .11)],
                   [(0, .014), (19_200, .032), (28_800, .055), (38_400, .064), (48_000, .068), (72_000, .072),
                    (96_000, .076), (250_000, .079), (350_000, .0825), (450_000, .09), (550_000, .10),
                    (650_000, .11)],
                   (4_400, 8_800), (1_144, 2_288)),
    "ID": StateTax("Idaho", _flat(.053, 4_811), _flat(.053, 9_622), (16_100, 32_200)),
    "IL": StateTax("Illinois", _flat(.0495), _flat(.0495), (0, 0), (2_925, 5_850), retirement_exempt_age=0),
    "IN": StateTax("Indiana", _flat(.0295), _flat(.0295), (0, 0), (1_000, 2_000)),
    "IA": StateTax("Iowa", _flat(.038), _flat(.038), (16_100, 32_200), (40, 80), exemption_is_credit=True,
                   retirement_exempt_age=55),
    "KS": StateTax("Kansas", [(0, .052), (23_000, .0558)], [(0, .052), (46_000, .0558)], (3_605, 8_240),
                   (9_160, 18_320)),
    "KY": StateTax("Kentucky", _flat(.035), _flat(.035), (3_360, 3_360)),
    "LA": StateTax("Louisiana", _flat(.03), _flat(.03), (12_875, 25_750)),
    "ME": StateTax("Maine", [(0, .058), (27_399, .0675), (64_849, .0715)],
                   [(0, .058), (54_849, .0675), (129_749, .0715)], (8_350, 16_700), (5_300, 10_600)),
    "MD": StateTax("Maryland",
                   [(0, .02), (1_000, .03), (2_000, .04), (3_000, .0475), (100_000, .05), (125_000, .0525),
                    (150_000, .055), (250_000, .0575), (500_000, .0625), (1_000_000, .065)],
                   [(0, .02), (1_000, .03), (2_000, .04), (3_000, .0475), (150_000, .05), (175_000, .0525),
                    (225_000, .055), (300_000, .0575), (600_000, .0625), (1_200_000, .065)],
                   (3_350, 6_700), (3_200, 6_400)),
    "MA": StateTax("Massachusetts", [(0, .05), (1_083_150, .09)], [(0, .05), (1_083_150, .09)], (0, 0),
                   (4_400, 8_800)),
    "MI": StateTax("Michigan", _flat(.0425), _flat(.0425), (0, 0), (5_900, 11_800)),
    "MN": StateTax("Minnesota", [(0, .0535), (33_310, .068), (109_430, .0785), (203_150, .0985)],
                   [(0, .0535), (48_700, .068), (193_480, .0785), (337_930, .0985)], (15_300, 30_600),
                   taxes_social_security=True),
    "MS": StateTax("Mississippi", _flat(.04, 10_000), _flat(.04, 10_000), (2_300, 4_600), (6_000, 12_000),
                   retirement_exempt_age=0),
    "MO": StateTax("Missouri",
                   [(1_348, .02), (2_696, .025), (4_044, .03), (5_392, .035), (6_740, .04), (8_088, .045),
                    (9_436, .047)],
                   [(1_348, .02), (2_696, .025), (4_044, .03), (5_392, .035), (6_740, .04), (8_088, .045),
                    (9_436, .047)],
                   (16_100, 32_200)),
    "MT": StateTax("Montana", [(0, .047), (47_500, .0565)], [(0, .047), (95_000, .0565)], (16_100, 32_200),
                   taxes_social_security=True),
    "NE": StateTax("Nebraska", [(0, .0246), (4_130, .0351), (24_760, .0455)],
                   [(0, .0246), (8_250, .0351), (49_530, .0455)], (8_850, 17_700), (176, 352),
                   exemption_is_credit=True),
    "NJ": StateTax("New Jersey",
                   [(0, .014), (20_000, .0175), (35_000, .035), (40_000, .0553), (75_000, .0637), (500_000, .0897),
                    (1_000_000, .1075)],
                   [(0, .014), (20_000, .0175), (50_000, .0245), (70_000, .035), (80_000, .0553), (150_000, .0637),
                    (500_000, .0897), (1_000_000, .1075)],
                   (0, 0), (1_000, 2_000)),
    "NM": StateTax("New Mexico",
                   [(0, .015), (5_500, .032), (16_500, .043), (33_500, .047), (66_500, .049), (210_000, .059)],
                   [(0, .015), (8_000, .032), (25_000, .043), (50_000, .047), (100_000, .049), (315_000, .059)],
                   (16_100, 32_200), taxes_social_security=True),
    "NY": StateTax("New York",
                   [(0, .039), (8_500, .044), (11_700, .0515), (13_900, .054), (80_650, .059), (215_400, .0685),
                    (1_077_550, .0965), (5_000_000, .103), (25_000_000, .109)],
                   [(0, .039), (17_150, .044), (23_600, .0515), (27_900, .054), (161_550, .059), (323_200, .0685),
                    (2_155_350, .0965), (5_000_000, .103), (25_000_000, .109)],
                   (8_000, 16_050)),
    "NC": StateTax("North Carolina", _flat(.0399), _flat(.0399), (12_750, 25_500)),
    "ND": StateTax("North Dakota", [(48_475, .0195), (244_825, .025)], [(80_975, .0195), (298_075, .025)],
                   (16_100, 32_200)),
    "OH": StateTax("Ohio", _flat(.0275, 26_050), _flat(.0275, 26_050), (0, 0), (2_400, 4_800)),
    "OK": StateTax("Oklahoma", [(3_750, .025), (4_900, .035), (7_200, .045)],
                   [(7_500, .025), (9_800, .035), (14_400, .045)], (6_350, 12_700), (1_000, 2_000)),
    "OR": StateTax("Oregon", [(0, .0475), (4_550, .0675), (11_400, .0875), (125_000, .099)],
                   [(0, .0475), (9_100, .0675), (22_800, .0875), (250_000, .099)], (2_910, 5_820), (256, 512),
                   exemption_is_credit=True),
    "PA": StateTax("Pennsylvania", _flat(.0307), _flat(.0307), retirement_exempt_age=0),
    "RI": StateTax("Rhode Island", [(0, .0375), (82_050, .0475), (186_450, .0599)],
                   [(0, .0375), (82_050, .0475), (186_450, .0599)], (11_200, 22_400), (5_250, 10_500),
                   taxes_social_security=True),
    "SC": StateTax("South Carolina", [(0, 0), (3_640, .03), (18_230, .06)], [(0, 0), (3_640, .03), (18_230, .06)],
                   (8_350, 16_700)),
    "UT": StateTax("Utah", _flat(.045), _flat(.045), (0, 0), (966, 1_932), exemption_is_credit=True,
                   taxes_social_security=True),
    "VT": StateTax("Vermont", [(0, .0335), (49_400, .066), (119_700, .076), (249_700, .0875)],
                   [(0, .0335), (82_500, .066), (199_450, .076), (304_000, .0875)], (7_650, 15_300),
                   (5_300, 10_600), taxes_social_security=True),
    "VA": StateTax("Virginia", [(0, .02), (3_000, .03), (5_000, .05), (17_000, .0575)],
                   [(0, .02), (3_000, .03), (5_000, .05), (17_000, .0575)], (8_750, 17_500), (930, 1_860)),
    "WA": StateTax("Washington", [(0, .07), (1_000_000, .09)], [(0, .07), (1_000_000, .09)], (278_000, 278_000),
                   capital_gains_only=True),
    "WV": StateTax("West Virginia", [(0, .0222), (10_000, .0296), (25_000, .0333), (40_000, .0444), (60_000, .0482)],
                   [(0, .0222), (10_000, .0296), (25_000, .0333), (40_000, .0444), (60_000, .0482)], (0, 0),
                   (2_000, 4_000)),
    "WI": StateTax("Wisconsin", [(0, .035), (15_110, .044), (51_950, .053), (332_720, .0765)],
                   [(0, .035), (20_150, .044), (69_260, .053), (443_630, .0765)], (13_960, 25_840), (700, 1_400)),
}

_NAMES = {s.name.lower(): code for code, s in STATES.items()} | {n.lower(): c for c, n in NO_TAX.items()}


def lookup(state: str) -> Tuple[Optional[str], Optional[StateTax]]:
    """(state code, rules) for a code or name like 'TX' or 'texas'; (None, None) if unknown.

    A no-income-tax state returns its code with rules None.
    """
    key = state.strip()
    code = key.upper() if key.upper() in STATES or key.upper() in NO_TAX else _NAMES.get(key.lower())
    if code is None:
        return None, None
    return code, STATES.get(code)


def _bracket_tax(brackets: Brackets, taxable: float, index: float) -> float:
    tax = 0.0
    for i, (start, rate) in enumerate(brackets):
        lower = start * index
        upper = brackets[i + 1][0] * index if i + 1 < len(brackets) else float("inf")
        if taxable <= lower:
            break
        tax += (min(taxable, upper) - lower) * rate
    return tax


def state_income_tax(rules: StateTax, status: str, index: float, *, age: int, wages: float, other: float,
                     retirement: float, gains: float, taxable_social_security: float) -> float:
    """State income tax for one year.

    wages: wages after pre-tax contributions. other: business, rental and other
    taxable income. retirement: pensions, annuities, IRA/401(k) withdrawals,
    RMDs and Roth conversions. gains: capital gains (taxed as ordinary income by
    most states). taxable_social_security: the federally taxable part.
    """
    joint = status == "married_joint"
    if rules.capital_gains_only:
        return _bracket_tax(rules.brackets(status), max(0.0, gains - rules.std_deduction[joint] * index), 1.0)
    income = wages + other + gains
    if rules.retirement_exempt_age is None or age < rules.retirement_exempt_age:
        income += retirement
    if rules.taxes_social_security:
        income += taxable_social_security
    deductions = rules.std_deduction[joint] * index
    credit = 0.0
    if rules.exemption_is_credit:
        credit = rules.exemption[joint] * index
    else:
        deductions += rules.exemption[joint] * index
    tax = _bracket_tax(rules.brackets(status), max(0.0, income - deductions), index)
    return max(0.0, tax - credit)
