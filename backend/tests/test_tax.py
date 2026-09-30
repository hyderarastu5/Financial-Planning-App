"""Tax rules checked against hand-worked 2026 examples."""

import pytest

from app.tax import (MARRIED_JOINT, SINGLE, TaxYear, income_tax, rmd_amount,
                     rmd_start_age, taxable_social_security)

Y2026_SINGLE = TaxYear.for_year(2026, SINGLE, inflation=0.025)
Y2026_JOINT = TaxYear.for_year(2026, MARRIED_JOINT, inflation=0.025)


def test_wages_single():
    # $100k wages: taxable 83,900 -> 1,240 + 4,560 + 7,370
    assert income_tax(Y2026_SINGLE, ordinary=100_000, gains=0, social_security=0, age=40) == pytest.approx(13_170)


def test_wages_married_joint():
    # $100k wages: taxable 67,800 -> 2,480 + 5,160
    assert income_tax(Y2026_JOINT, ordinary=100_000, gains=0, social_security=0, age=40) == pytest.approx(7_640)


def test_gains_inside_zero_percent_bracket_are_untaxed():
    assert income_tax(Y2026_SINGLE, ordinary=0, gains=60_000, social_security=0, age=40) == 0


def test_gains_stack_on_top_of_ordinary_income():
    # AGI 70k, taxable 53,900: ordinary 33,900 -> 3,820; gains 33,900-53,900, 15% above 49,450 -> 667.50
    assert income_tax(Y2026_SINGLE, ordinary=50_000, gains=20_000, social_security=0, age=40) == pytest.approx(4_487.5)


def test_niit_on_high_income_gains():
    base = income_tax(Y2026_SINGLE, ordinary=250_000, gains=0, social_security=0, age=40)
    with_gains = income_tax(Y2026_SINGLE, ordinary=250_000, gains=10_000, social_security=0, age=40)
    assert with_gains - base == pytest.approx(10_000 * (0.15 + 0.038))


@pytest.mark.parametrize("benefits, other, expected", [
    (20_000, 5_000, 0),  # provisional 15k: below 25k
    (20_000, 20_000, 2_500),  # provisional 30k: half of the 5k over 25k
    (30_000, 20_000, 5_350),  # provisional 35k: 0.85*1k + 4.5k
    (30_000, 200_000, 25_500),  # capped at 85% of benefits
])
def test_social_security_taxable_share(benefits, other, expected):
    assert taxable_social_security(benefits, other, SINGLE) == pytest.approx(expected)


def test_standard_deduction_grows_with_inflation():
    assert TaxYear.for_year(2027, SINGLE, 0.025).deduction(age=40, magi=0) == pytest.approx(16_100 * 1.025)


def test_senior_deductions():
    # 65+: standard 16,100 + extra 2,050 + senior 6,000 (2025-2028, phased out above 75k MAGI)
    assert Y2026_SINGLE.deduction(age=70, magi=50_000) == pytest.approx(24_150)
    assert Y2026_SINGLE.deduction(age=70, magi=100_000) == pytest.approx(24_150 - 0.06 * 25_000)
    y2029 = TaxYear.for_year(2029, SINGLE, 0.0)
    assert y2029.deduction(age=70, magi=50_000) == pytest.approx(18_150)


def test_payroll_tax():
    assert Y2026_SINGLE.payroll_tax(100_000) == pytest.approx(7_650)
    # Social Security capped at 184,500; extra 0.9% Medicare above 200k
    assert Y2026_SINGLE.payroll_tax(300_000) == pytest.approx(11_439 + 4_350 + 900)


def test_rmd_start_ages():
    assert rmd_start_age(1955) == 73
    assert rmd_start_age(1960) == 75


def test_rmd_amounts():
    assert rmd_amount(265_000, age=73, birth_year=1953) == pytest.approx(10_000)
    assert rmd_amount(265_000, age=72, birth_year=1953) == 0
    assert rmd_amount(246_000, age=74, birth_year=1962) == 0
    assert rmd_amount(246_000, age=75, birth_year=1962) == pytest.approx(10_000)
