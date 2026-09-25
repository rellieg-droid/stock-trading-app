"""טסטים לסעיף 9 ב-options_engine.py: chain_strike_rows."""
import math

import pytest

from options_engine import bs_greeks, chain_strike_rows

S, DTE, R = 200.0, 30, 0.045
T = DTE / 365


def _row(K, iv, half_spread=0.02, **extra):
    """שורת שרשרת שה-Mid שלה מתומחר בדיוק ב-BS עם iv נתון."""
    mid = bs_greeks("put", S, K, T, iv, R).price
    row = {"strike": K, "bid": mid - half_spread, "ask": mid + half_spread,
           "volume": 100, "openInterest": 1000}
    row.update(extra)
    return row


def _chain():
    # skew: IV עולה ככל שהסטרייק יורד
    return [_row(K, 0.30 + (200 - K) * 0.004) for K in range(150, 205, 5)]


def test_band_filter_and_sorted():
    rows = chain_strike_rows(_chain(), S, DTE, r=R)
    assert rows, "צריך לפחות שורה אחת בטווח"
    assert all(0.10 <= r.delta <= 0.35 for r in rows)
    assert [r.strike for r in rows] == sorted(r.strike for r in rows)


def test_iv_recovered_per_strike_skew():
    rows = {r.strike: r for r in chain_strike_rows(_chain(), S, DTE, r=R)}
    for K, r in rows.items():
        # Mid מעוגל לסנט -> IV קרוב, לא זהה
        assert r.iv == pytest.approx(0.30 + (200 - K) * 0.004, abs=0.01)
    ks = sorted(rows)
    assert rows[ks[0]].iv > rows[ks[-1]].iv  # ה-skew נשמר


def test_premium_is_mid_and_consistent():
    for r in chain_strike_rows(_chain(), S, DTE, r=R):
        assert r.premium == pytest.approx(bs_greeks("put", S, r.strike, T, r.iv, R).price, abs=0.006)
        assert r.breakeven == pytest.approx(r.strike - r.premium)
        assert r.xem_distance > 0  # פוט OTM: סטרייק מתחת למחיר


def test_no_live_quote_skipped():
    chain = _chain()
    for row in chain:
        row["bid"] = 0.0
    assert chain_strike_rows(chain, S, DTE, r=R) == []


def test_below_intrinsic_skipped():
    # ITM עמוק עם Mid מתחת לערך הפנימי - אין IV, לא מנחשים
    chain = [{"strike": 260.0, "bid": 1.0, "ask": 1.2, "volume": 1, "openInterest": 1}]
    assert chain_strike_rows(chain, S, DTE, r=R, delta_band=(0.0, 1.0)) == []


def test_max_rows_keeps_closest_to_band_mid():
    rows_all = chain_strike_rows(_chain(), S, DTE, r=R, delta_band=(0.0, 1.0), max_rows=100)
    rows_cut = chain_strike_rows(_chain(), S, DTE, r=R, delta_band=(0.0, 1.0), max_rows=3)
    assert len(rows_cut) == 3 and len(rows_all) > 3
    worst_kept = max(abs(r.delta - 0.5) for r in rows_cut)
    dropped = [r for r in rows_all if r.strike not in {c.strike for c in rows_cut}]
    assert all(abs(r.delta - 0.5) >= worst_kept for r in dropped)


def test_counts_and_dirty_rows():
    chain = _chain() + [{"strike": None, "bid": 1, "ask": 2}, {"strike": math.nan, "bid": 1, "ask": 2}]
    chain[0]["volume"] = None
    chain[1]["openInterest"] = math.nan
    rows = chain_strike_rows(chain, S, DTE, r=R, delta_band=(0.0, 1.0), max_rows=100)
    by_k = {r.strike: r for r in rows}
    assert by_k[150.0].volume == 0 and by_k[155.0].open_interest == 0


def test_fat_tail_only_with_returns():
    assert all(r.prob_otm_fat_tail is None for r in chain_strike_rows(_chain(), S, DTE, r=R))
    import random
    rnd = random.Random(1)
    rets = [rnd.gauss(0, 0.02) for _ in range(500)]
    rows = chain_strike_rows(_chain(), S, DTE, r=R, daily_log_returns=rets)
    assert all(r.prob_otm_fat_tail is not None and 0 <= r.prob_otm_fat_tail <= 1 for r in rows)


@pytest.mark.parametrize("s,dte", [(0, 30), (200, 0), (-1, 30)])
def test_bad_inputs(s, dte):
    assert chain_strike_rows(_chain(), s, dte) == []
