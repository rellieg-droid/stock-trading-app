"""
test_expected_move.py
======================
טסטים ל-expected_move, strike_distance_in_expected_moves.
"""

import math

import pytest

from options_engine import expected_move, strike_distance_in_expected_moves, ExpectedMove


def test_expected_move_known_value():
    """S=100, sigma=0.30, T=365 ימים -> move = 100*0.30*1 = 30."""
    result = expected_move(S=100.0, sigma=0.30, T_days=365)
    assert result.move == pytest.approx(30.0)
    assert result.low == pytest.approx(70.0)
    assert result.high == pytest.approx(130.0)
    assert result.method == "formula"


def test_expected_move_scales_with_sqrt_time():
    """4x בזמן -> 2x בתזוזה (שורש-זמן)."""
    m30 = expected_move(S=100.0, sigma=0.30, T_days=30)
    m120 = expected_move(S=100.0, sigma=0.30, T_days=120)
    assert m120.move == pytest.approx(m30.move * 2, rel=1e-9)


def test_expected_move_zero_sigma_gives_zero_move():
    result = expected_move(S=100.0, sigma=0.0, T_days=30)
    assert result.move == 0.0
    assert result.low == result.high == 100.0


def test_expected_move_rejects_negative_price():
    with pytest.raises(ValueError):
        expected_move(S=-10.0, sigma=0.3, T_days=30)


def test_expected_move_rejects_negative_sigma():
    with pytest.raises(ValueError):
        expected_move(S=100.0, sigma=-0.1, T_days=30)


def test_strike_distance_known_value():
    """S=111, K=70, move=27 -> distance = 41/27 (מהדוגמה בסקיל המקורי)."""
    distance = strike_distance_in_expected_moves(S=111.0, K=70.0, move=27.0)
    assert distance == pytest.approx(41.0 / 27.0, rel=1e-6)


def test_strike_distance_negative_when_strike_above_price():
    """סטרייק מעל המחיר הנוכחי -> מרחק שלילי (לא רלוונטי לפוט טיפוסי, אבל לא קורס)."""
    distance = strike_distance_in_expected_moves(S=100.0, K=110.0, move=10.0)
    assert distance == pytest.approx(-1.0)


def test_strike_distance_none_when_move_is_zero():
    assert strike_distance_in_expected_moves(S=100.0, K=90.0, move=0.0) is None


def test_strike_distance_zero_when_strike_equals_price():
    assert strike_distance_in_expected_moves(S=100.0, K=100.0, move=15.0) == pytest.approx(0.0)
