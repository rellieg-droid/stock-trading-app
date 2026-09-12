"""
test_rv_rank.py
================
טסטים ל-rv_rank, rv_percentile.
"""

import random

import pytest

from options_engine import rv_rank, rv_percentile


def _closes_with_increasing_volatility(n=300, vol_window=20):
    """סדרת מחירים שהתנודתיות שלה עולה בהדרגה - RV האחרון אמור להיות הגבוה ביותר."""
    random.seed(11)
    closes = [100.0]
    for i in range(n):
        vol = 0.005 + (i / n) * 0.05  # מ-0.5% ליום עד 5.5% ליום
        closes.append(closes[-1] * (1 + random.gauss(0, vol)))
    return closes


def test_rv_rank_is_high_when_current_vol_is_highest_in_window():
    closes = _closes_with_increasing_volatility()
    rank = rv_rank(closes, vol_window=20, lookback_days=252)
    assert rank is not None
    assert rank > 80  # התנודתיות האחרונה הכי גבוהה בטווח -> Rank קרוב ל-100


def test_rv_rank_is_low_when_current_vol_is_lowest_in_window():
    closes = list(reversed(_closes_with_increasing_volatility()))
    rank = rv_rank(closes, vol_window=20, lookback_days=252)
    assert rank is not None
    assert rank < 20


def test_rv_rank_none_with_insufficient_data():
    closes = [100.0, 101.0, 99.5, 100.2]
    assert rv_rank(closes, vol_window=20, lookback_days=252) is None


def test_rv_rank_none_when_volatility_never_changes():
    """מחיר שטוח לחלוטין -> RV=0.0 מדויק בכל חלון -> max==min -> None, לא חלוקה באפס."""
    closes = [100.0] * 400
    assert rv_rank(closes, vol_window=20, lookback_days=252) is None


def test_rv_rank_bounded_0_to_100():
    random.seed(5)
    closes = [100.0]
    for _ in range(400):
        closes.append(closes[-1] * (1 + random.gauss(0, 0.02)))
    rank = rv_rank(closes, vol_window=20, lookback_days=252)
    assert rank is None or 0.0 <= rank <= 100.0


def test_rv_percentile_is_100_when_current_is_max():
    closes = _closes_with_increasing_volatility()
    pct = rv_percentile(closes, vol_window=20, lookback_days=252)
    assert pct is not None
    assert pct > 95.0


def test_rv_percentile_none_with_insufficient_data():
    closes = [100.0, 101.0]
    assert rv_percentile(closes, vol_window=20, lookback_days=252) is None


def test_rv_percentile_bounded_0_to_100():
    random.seed(9)
    closes = [100.0]
    for _ in range(400):
        closes.append(closes[-1] * (1 + random.gauss(0, 0.02)))
    pct = rv_percentile(closes, vol_window=20, lookback_days=252)
    assert pct is None or 0.0 <= pct <= 100.0
