"""
test_probability_models.py
===========================
טסטים ל-historical_put_otm_probability, student_t_cdf, fat_tail_otm_probability.
"""

import math
import random

import pytest

from options_engine import (
    HistoricalProbability,
    FatTailProbability,
    historical_put_otm_probability,
    student_t_cdf,
    fat_tail_otm_probability,
)


# ---------------------------------------------------------------------------
# historical_put_otm_probability
# ---------------------------------------------------------------------------

def test_historical_all_above_strike_is_100_percent_otm():
    """מחיר שתמיד מעל הסטרייק -> 100% OTM בכל תקופה זמינה."""
    closes = [100.0] * (252 * 3 + 30)
    result = historical_put_otm_probability(closes, strike=50.0, dte_days=30)
    assert result.by_period[1] == pytest.approx(1.0)
    assert result.by_period[3] == pytest.approx(1.0)
    assert result.weighted_otm == pytest.approx(1.0)


def test_historical_all_below_strike_is_0_percent_otm():
    closes = [10.0] * (252 + 30)
    result = historical_put_otm_probability(closes, strike=50.0, dte_days=30)
    assert result.by_period[1] == pytest.approx(0.0)


def test_historical_insufficient_data_returns_none_not_fabricated():
    """פחות נתונים מ-DTE אחד -> None, לא ערך מומצא."""
    closes = [100.0, 101.0, 99.0]
    result = historical_put_otm_probability(closes, strike=90.0, dte_days=30)
    assert result.by_period[1] is None
    assert result.periods_available == 0
    assert result.weighted_otm is None
    assert "אין מספיק" in result.note


def test_historical_partial_periods_flagged_not_silently_averaged():
    """יש מספיק לשנה 1 אבל לא ל-10 -> משוקלל רק על הזמין, עם הערה."""
    closes = [100.0] * (252 * 2)  # ~2 שנים, מספיק ל-1Y בלבד (dte_days=30 קטן)
    result = historical_put_otm_probability(closes, strike=50.0, dte_days=30)
    assert result.by_period[1] is not None
    assert result.by_period[10] is None
    assert result.periods_available == 1
    assert result.weighted_otm == pytest.approx(1.0)
    assert "מתוך" in result.note


def test_historical_known_breach_rate():
    """3 מתוך 252 תקופות פורצות את הסטרייק -> OTM = 249/252, בדיוק (חלון 1Y מלא)."""
    dte = 5
    window_days = 252  # 1Y
    closes = [100.0] * (window_days + dte)
    strike = 95.0
    for i in (0, 1, 2):
        closes[i + dte] = 90.0
    result = historical_put_otm_probability(closes, strike=strike, dte_days=dte)
    assert result.by_period[1] == pytest.approx((window_days - 3) / window_days)


# ---------------------------------------------------------------------------
# student_t_cdf
# ---------------------------------------------------------------------------

def test_student_t_cdf_at_zero_is_half():
    assert student_t_cdf(0.0, df=10) == pytest.approx(0.5, abs=1e-9)


def test_student_t_cdf_matches_known_table_values():
    # ערכי טבלה סטנדרטיים: t(df=10) חד-זנבי ב-0.05 -> t≈1.812
    cdf_at_critical = student_t_cdf(1.812, df=10)
    assert cdf_at_critical == pytest.approx(0.95, abs=1e-3)


def test_student_t_cdf_converges_to_normal_at_high_df():
    from statistics import NormalDist
    normal_cdf = NormalDist().cdf(1.5)
    t_cdf_high_df = student_t_cdf(1.5, df=10_000)
    assert t_cdf_high_df == pytest.approx(normal_cdf, abs=1e-3)


def test_student_t_cdf_symmetry():
    assert student_t_cdf(1.3, df=7) == pytest.approx(1.0 - student_t_cdf(-1.3, df=7), abs=1e-9)


def test_student_t_cdf_rejects_nonpositive_df():
    with pytest.raises(ValueError):
        student_t_cdf(0.5, df=0)


# ---------------------------------------------------------------------------
# fat_tail_otm_probability
# ---------------------------------------------------------------------------

def test_fat_tail_insufficient_observations_returns_none_not_fabricated():
    returns = [0.001] * 10
    result = fat_tail_otm_probability(returns, S=100.0, K=90.0, dte_days=30)
    assert result.otm_probability is None
    assert "אין מספיק" in result.note


def test_fat_tail_zero_variance_returns_none():
    returns = [0.0] * 50
    result = fat_tail_otm_probability(returns, S=100.0, K=90.0, dte_days=30)
    assert result.otm_probability is None


def test_fat_tail_strike_far_below_price_gives_high_otm_probability():
    random.seed(42)
    returns = [random.gauss(0.0002, 0.015) for _ in range(500)]
    result = fat_tail_otm_probability(returns, S=100.0, K=50.0, dte_days=30)
    assert result.otm_probability > 0.95


def test_fat_tail_strike_far_above_price_gives_low_otm_probability():
    random.seed(42)
    returns = [random.gauss(0.0002, 0.015) for _ in range(500)]
    result = fat_tail_otm_probability(returns, S=100.0, K=200.0, dte_days=30)
    assert result.otm_probability < 0.05


def test_fat_tail_high_kurtosis_data_produces_low_degrees_of_freedom():
    """נתונים עם קפיצות קיצון (leptokurtic) -> df נמוך (זנבות שמנים מובהקים)."""
    random.seed(7)
    fat_returns = [random.gauss(0, 0.01) for _ in range(400)]
    for i in range(0, len(fat_returns), 20):
        fat_returns[i] = random.choice([0.08, -0.08])  # קפיצות קיצון נדירות
    result = fat_tail_otm_probability(fat_returns, S=100.0, K=90.0, dte_days=30)
    assert result.degrees_of_freedom < 30.0


def test_fat_tail_note_empty_when_successful():
    random.seed(1)
    returns = [random.gauss(0.0, 0.01) for _ in range(100)]
    result = fat_tail_otm_probability(returns, S=100.0, K=80.0, dte_days=10)
    assert result.note == ""
    assert 0.0 <= result.otm_probability <= 1.0
