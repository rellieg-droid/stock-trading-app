"""
test_breakeven.py
===================
"""
import pytest
from options_engine import short_put_breakeven


def test_breakeven_basic():
    assert short_put_breakeven(strike=120.0, premium=40.91) == pytest.approx(79.09)


def test_breakeven_zero_premium():
    assert short_put_breakeven(strike=100.0, premium=0.0) == pytest.approx(100.0)


def test_breakeven_can_be_negative_with_large_premium():
    """פרמיה גדולה מהסטרייק (תיאורטית, נדיר) - לא קורס, פשוט שלילי."""
    assert short_put_breakeven(strike=10.0, premium=15.0) == pytest.approx(-5.0)
