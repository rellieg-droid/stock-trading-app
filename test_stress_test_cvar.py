"""
test_stress_test_cvar.py
==========================
טסטים ל-stress_test_table, historical_short_put_pnl_distribution, expected_shortfall.
"""

import pytest

from options_engine import (
    stress_test_table,
    historical_short_put_pnl_distribution,
    expected_shortfall,
    StressTestRow,
)


def test_stress_table_matches_skill_worked_example():
    """
    הדוגמה המדויקת מהסקיל המקורי (סעיף 5): S=111, K=70, premium=2, contracts=3.
    בירידה ל-50$: intrinsic_loss=(70-50)*100*3=6000, premium=600, net=-5400.
    """
    rows = stress_test_table(S=111.0, strike=70.0, premium=2.0, contracts=3)
    pct_50_down = next(r for r in rows if r.pct_move == pytest.approx(-0.50))
    # 111 * 0.50 = 55.5, לא בדיוק 50 - נבדוק ישירות בערך של 50 דרך חישוב יד:
    # (השתמשנו ב-% מהסקיל, לא במחיר קבוע - זו בדיקת עקביות פנימית)
    assert pct_50_down.stressed_price == pytest.approx(55.5)
    expected_pnl = 2.0 * 100 * 3 - max(0.0, 70.0 - 55.5) * 100 * 3
    assert pct_50_down.pnl == pytest.approx(expected_pnl)


def test_stress_table_direct_price_matches_skill_example():
    """אימות ישיר של נוסחת הסקיל במחיר $50 בדיוק, לא דרך אחוז."""
    from options_engine import Position, Leg
    position = Position(legs=[Leg("put", -1, 3, 2.0, 70.0)])
    pnl_at_50 = position.payoff_at(50.0)
    assert pnl_at_50 == pytest.approx(-5400.0)


def test_stress_table_no_loss_when_otm():
    """מחיר תמיד מעל הסטרייק -> P/L = הפרמיה בלבד, לא הפסד."""
    rows = stress_test_table(S=200.0, strike=100.0, premium=1.5, contracts=1, pct_moves=(0.0, -0.10))
    for row in rows:
        assert row.pnl == pytest.approx(150.0)  # 1.5*100*1, כי 200*0.9=180 > 100


def test_stress_table_pct_of_capital_none_without_capital():
    rows = stress_test_table(S=100.0, strike=90.0, premium=1.0, contracts=1)
    assert all(r.pct_of_capital is None for r in rows)


def test_stress_table_pct_of_capital_computed_when_capital_given():
    rows = stress_test_table(S=100.0, strike=90.0, premium=1.0, contracts=1, available_capital=1000.0)
    row = next(r for r in rows if r.pct_move == 0.0)
    assert row.pct_of_capital == pytest.approx(row.pnl / 1000.0)


def test_historical_pnl_distribution_length():
    closes = [100.0] * 300
    dist = historical_short_put_pnl_distribution(closes, strike=90.0, dte_days=30, premium=1.0, contracts=1)
    assert len(dist) == 300 - 30


def test_historical_pnl_distribution_empty_when_insufficient_data():
    closes = [100.0, 101.0]
    dist = historical_short_put_pnl_distribution(closes, strike=90.0, dte_days=30, premium=1.0, contracts=1)
    assert dist == []


def test_historical_pnl_distribution_flat_price_always_full_premium():
    closes = [100.0] * 300
    dist = historical_short_put_pnl_distribution(closes, strike=90.0, dte_days=30, premium=1.0, contracts=1)
    assert all(pnl == pytest.approx(100.0) for pnl in dist)


def test_expected_shortfall_averages_worst_tail():
    """20 תוצאות, 5% = תוצאה אחת - הגרועה ביותר בלבד."""
    pnl_distribution = list(range(-100, 100, 10))  # 20 ערכים, מ--100 עד 90
    es = expected_shortfall(pnl_distribution, tail_fraction=0.05)
    assert es == pytest.approx(-100.0)


def test_expected_shortfall_empty_distribution_returns_none():
    assert expected_shortfall([], tail_fraction=0.05) is None


def test_expected_shortfall_matches_manual_average():
    pnl_distribution = [-500, -400, -300, -200, -100, 0, 100, 200, 300, 400]
    es = expected_shortfall(pnl_distribution, tail_fraction=0.2)  # 20% מ-10 = 2
    assert es == pytest.approx((-500 + -400) / 2)
