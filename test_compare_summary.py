"""טסטים לסעיף 10 ב-options_engine.py: compare_summary (לפי הטבלה האמיתית מ-NVDA)."""
import pytest

from options_engine import compare_summary

S = 223.30


def _nvda_rows():
    # מהצילום: NVDA 23/10/2026, סטרייקים 200-215
    return [
        dict(strike=215, premium=3.67, breakeven=211.33, prob_model=68.6, fat_tail=71.1, xem=0.48,
             iv=32.0, spread_pct=1.4, low_liquidity=False, expiry="23/10/2026"),
        dict(strike=200, premium=1.16, breakeven=198.84, prob_model=87.6, fat_tail=82.5, xem=1.11,
             iv=35.7, spread_pct=3.4, low_liquidity=False, expiry="23/10/2026"),
        dict(strike=210, premium=2.50, breakeven=207.50, prob_model=76.6, fat_tail=75.3, xem=0.71,
             iv=33.0, spread_pct=1.2, low_liquidity=False, expiry="23/10/2026"),
        dict(strike=205, premium=1.69, breakeven=203.31, prob_model=82.9, fat_tail=79.1, xem=0.92,
             iv=34.2, spread_pct=3.6, low_liquidity=False, expiry="23/10/2026"),
    ]


def test_needs_two_strikes():
    assert compare_summary([]) is None
    assert compare_summary(_nvda_rows()[:1], S) is None


def test_ranges_sorted_by_strike():
    s = compare_summary(_nvda_rows(), S)
    assert s.n == 4 and s.strikes == (200, 205, 210, 215)
    assert s.premium_range == (1.16, 3.67)
    assert s.breakeven_range == (198.84, 211.33)
    assert s.prob_model_range == (87.6, 68.6)
    assert s.drop_to_breakeven_pct[0] == pytest.approx((S - 198.84) / S * 100)
    assert s.drop_to_breakeven_pct[1] == pytest.approx((S - 211.33) / S * 100)


def test_fat_tail_below_model():
    # 200: 82.5 < 87.6, 205: 79.1 < 82.9, 210: 75.3 < 76.6 (1.3 נק') -> כולם מעל הסף
    # 215: 71.1 > 68.6 -> לא
    assert compare_summary(_nvda_rows(), S).fat_below_model == (200, 205, 210)


def test_fat_tail_threshold_and_missing():
    rows = _nvda_rows()
    rows[2]["fat_tail"] = 76.0   # 210: פער 0.6 -> מתחת לסף
    rows[1]["fat_tail"] = None   # 200: אין נתון
    assert compare_summary(rows, S).fat_below_model == (205,)


def test_expected_move_split():
    s = compare_summary(_nvda_rows(), S)
    assert s.outside_em == (200,) and s.inside_em == (205, 210, 215)


def test_skew_direction():
    assert compare_summary(_nvda_rows(), S).skew == "down"
    rows = _nvda_rows()
    for r in rows:
        r["iv"] = 33.0
    assert compare_summary(rows, S).skew == "flat"


def test_steps_tradeoff():
    steps = compare_summary(_nvda_rows(), S).steps
    assert [(st.from_strike, st.to_strike) for st in steps] == [(200, 205), (205, 210), (210, 215)]
    first, last = steps[0], steps[-1]
    assert first.premium_add == pytest.approx(0.53)
    assert first.prob_drop_pts == pytest.approx(4.7)
    assert first.premium_per_pt == pytest.approx(0.53 / 4.7)
    assert last.premium_add == pytest.approx(1.17)
    assert last.prob_drop_pts == pytest.approx(8.0)


def test_step_without_prob_drop_has_no_ratio():
    rows = _nvda_rows()[:2]
    rows[0]["prob_model"] = rows[1]["prob_model"]  # אותה הסתברות
    assert compare_summary(rows, S).steps[0].premium_per_pt is None


def test_liquidity_spread_and_expiries():
    rows = _nvda_rows()
    rows[0]["low_liquidity"] = True
    rows[3]["spread_pct"] = 14.8
    rows[2]["expiry"] = "30/10/2026"
    s = compare_summary(rows, S)
    assert s.low_liquidity == (215,)
    assert s.wide_spread == (205,)
    assert s.spread_range == (1.2, 14.8)
    assert s.mixed_expiries


def test_no_spot_no_drop():
    assert compare_summary(_nvda_rows()).drop_to_breakeven_pct is None
