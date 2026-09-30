"""State income tax, checked against hand-worked 2026 examples."""

import pytest

from app import states


def tax(code, status="single", age=40, wages=0.0, other=0.0, retirement=0.0, gains=0.0, ss=0.0):
    _, rules = states.lookup(code)
    return states.state_income_tax(rules, status, 1.0, age=age, wages=wages, other=other, retirement=retirement,
                                   gains=gains, taxable_social_security=ss)


def test_every_state_and_dc_is_covered():
    assert len(states.STATES) + len(states.NO_TAX) == 51
    assert not set(states.STATES) & set(states.NO_TAX)


def test_lookup_by_code_or_name():
    assert states.lookup("ca")[0] == "CA"
    assert states.lookup("New York")[0] == "NY"
    assert states.lookup("TX") == ("TX", None)  # no income tax
    assert states.lookup("") == (None, None)
    assert states.lookup("Atlantis") == (None, None)


def test_california_progressive_brackets_and_credit():
    # 100,000 - 5,540 = 94,460 taxable, through six brackets, minus the $153 exemption credit.
    expected = (0.01 * 11_079 + 0.02 * (26_264 - 11_079) + 0.04 * (41_452 - 26_264) + 0.06 * (57_542 - 41_452)
                + 0.08 * (72_724 - 57_542) + 0.093 * (94_460 - 72_724) - 153)
    assert tax("CA", wages=100_000) == pytest.approx(expected)


def test_flat_tax_with_no_deductions():
    assert tax("PA", wages=100_000) == pytest.approx(3_070)


def test_zero_rate_band_below_first_bracket():
    # Mississippi: 4% only above $10,000, after the $2,300 deduction and $6,000 exemption.
    assert tax("MS", wages=50_000) == pytest.approx(0.04 * (50_000 - 8_300 - 10_000))


def test_retirement_income_exemptions():
    assert tax("IL", age=70, retirement=50_000) == 0
    assert tax("IL", wages=50_000) == pytest.approx(0.0495 * (50_000 - 2_925))
    assert tax("IA", age=54, retirement=50_000) > 0  # Iowa's exemption starts at 55
    assert tax("IA", age=55, retirement=50_000) == 0
    assert tax("OH", age=70, retirement=50_000) > 0  # most states tax it


def test_social_security_taxed_only_in_states_that_do():
    assert tax("MN", ss=20_000) > 0
    assert tax("GA", ss=20_000) == 0


def test_washington_taxes_only_large_capital_gains():
    assert tax("WA", wages=500_000) == 0
    assert tax("WA", gains=300_000) == pytest.approx(0.07 * 22_000)


def test_married_joint_uses_joint_brackets():
    single, joint = tax("KS", wages=60_000), tax("KS", status="married_joint", wages=60_000)
    assert joint < single


def test_amounts_are_indexed_for_inflation():
    _, rules = states.lookup("PA")
    assert states.state_income_tax(rules, "single", 1.5, age=40, wages=100_000, other=0, retirement=0, gains=0,
                                   taxable_social_security=0) == pytest.approx(3_070)  # flat, no deductions
    _, rules = states.lookup("NC")
    base = states.state_income_tax(rules, "single", 1.0, age=40, wages=50_000, other=0, retirement=0, gains=0,
                                   taxable_social_security=0)
    later = states.state_income_tax(rules, "single", 1.1, age=40, wages=50_000, other=0, retirement=0, gains=0,
                                    taxable_social_security=0)
    assert later == pytest.approx(base - 0.0399 * 12_750 * 0.1)
