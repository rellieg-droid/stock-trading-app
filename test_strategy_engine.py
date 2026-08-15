# -*- coding: utf-8 -*-
"""בדיקות ל-strategy_engine. הרצה: py -m pytest test_strategy_engine.py -v"""

import math

import numpy as np
import pandas as pd
import pytest

import strategy_engine as se


# --------------------------------------------------------------------------
# עזרי בנייה
# --------------------------------------------------------------------------

def synth_prices(n=400, daily_vol=0.01, drift=0.0003, seed=42, start=100.0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, daily_vol, n)
    return pd.Series(start * np.exp(np.cumsum(rets)))


def ohlc_from_close(close, spread=0.01):
    high = close * (1 + spread)
    low = close * (1 - spread)
    return high, low, close


# --------------------------------------------------------------------------
# True Range / ATR
# --------------------------------------------------------------------------

def test_true_range_first_row_is_high_minus_low():
    tr = se.true_range([10, 11], [9, 10], [9.5, 10.5])
    assert tr.iloc[0] == pytest.approx(1.0)


def test_true_range_captures_overnight_gap():
    # פער של 5 כלפי מעלה. High-Low נאיבי היה מחזיר 1 בלבד.
    tr = se.true_range([10, 16], [9, 15], [9.5, 15.5])
    assert tr.iloc[1] == pytest.approx(6.5)


def test_atr_wilder_needs_full_period_before_emitting():
    close = synth_prices(30)
    h, l, c = ohlc_from_close(close)
    atr = se.atr_wilder(h, l, c, period=14)
    assert atr.iloc[:13].isna().all()
    assert math.isfinite(atr.iloc[-1])


def test_atr_is_positive_and_scaled_to_price():
    close = synth_prices(300)
    h, l, c = ohlc_from_close(close, spread=0.02)
    atr = se.atr_wilder(h, l, c).dropna()
    assert (atr > 0).all()
    assert 0 < atr.iloc[-1] / close.iloc[-1] < 0.2


def test_atr_short_input_returns_empty():
    assert se.atr_wilder([10], [9], [9.5]).empty


# --------------------------------------------------------------------------
# תנודתיות
# --------------------------------------------------------------------------

def test_annualized_vol_matches_expected_scale():
    close = synth_prices(2000, daily_vol=0.01, drift=0.0, seed=7)
    vol = se.annualized_vol(close)
    assert vol == pytest.approx(0.01 * math.sqrt(252), rel=0.10)


def test_annualized_vol_window_limits_sample():
    close = synth_prices(500)
    assert se.annualized_vol(close, window=60) != se.annualized_vol(close)


def test_annualized_vol_insufficient_data_is_nan():
    assert math.isnan(se.annualized_vol([100.0]))


def zigzag(n, amplitude, start=100.0):
    """סדרה דטרמיניסטית: תשואות מתחלפות בגודל קבוע. אין תלות ב-RNG."""
    rets = np.array([amplitude if i % 2 == 0 else -amplitude for i in range(n)])
    return pd.Series(start * np.exp(np.cumsum(rets)))


def test_hv_rank_calm_tail_is_low():
    storm = zigzag(300, 0.05)
    quiet = zigzag(120, 0.002, start=float(storm.iloc[-1]))
    combined = pd.concat([storm, quiet], ignore_index=True)
    assert se.hv_rank(combined) < 10


def test_hv_rank_explosive_tail_is_high():
    calm = zigzag(300, 0.002)
    storm = zigzag(60, 0.05, start=float(calm.iloc[-1]))
    combined = pd.concat([calm, storm], ignore_index=True)
    assert se.hv_rank(combined) > 90


def test_hv_rank_bounded_zero_to_hundred():
    r = se.hv_rank(synth_prices(400))
    assert 0.0 <= r <= 100.0


def test_hv_rank_insufficient_data_is_nan():
    assert math.isnan(se.hv_rank([100.0, 101.0]))


def test_relative_std_detects_double_volatility():
    bench = synth_prices(600, daily_vol=0.008, seed=11)
    stock = synth_prices(600, daily_vol=0.016, seed=12)
    assert se.relative_std(stock, bench) == pytest.approx(2.0, rel=0.20)


def test_relative_std_nan_on_empty_benchmark():
    assert math.isnan(se.relative_std(synth_prices(100), [100.0]))


# --------------------------------------------------------------------------
# תצורה לפי פרופיל סיכון
# --------------------------------------------------------------------------

def test_profiles_order_thresholds_correctly():
    low = se.StrategyConfig.for_profile("low")
    med = se.StrategyConfig.for_profile("medium")
    high = se.StrategyConfig.for_profile("high")
    assert low.max_relative_std < med.max_relative_std < high.max_relative_std
    assert low.vix_max < med.vix_max < high.vix_max
    assert low.earnings_blackout_days > high.earnings_blackout_days


def test_hebrew_profile_names_resolve():
    assert se.StrategyConfig.for_profile("גבוהה").risk_profile == "high"
    assert se.StrategyConfig.for_profile("נמוכה").risk_profile == "low"


def test_unknown_profile_falls_back_to_medium():
    assert se.StrategyConfig.for_profile("banana").risk_profile == "medium"


# --------------------------------------------------------------------------
# קריטריונים
# --------------------------------------------------------------------------

def test_atr_criterion_fails_when_twice_the_index():
    cfg = se.StrategyConfig.for_profile("medium")
    c = se.build_atr_criterion(price=100, atr=3.0, rel_std=2.4, cfg=cfg)
    assert c.passed is False
    assert "פי 2.4" in c.current


def test_atr_criterion_passes_when_in_range():
    cfg = se.StrategyConfig.for_profile("medium")
    assert se.build_atr_criterion(100, 1.5, 1.1, cfg).passed is True


def test_atr_criterion_none_when_no_benchmark():
    cfg = se.StrategyConfig.for_profile("medium")
    assert se.build_atr_criterion(100, 1.5, float("nan"), cfg).passed is None


def test_hv_rank_criterion_flags_proxy():
    cfg = se.StrategyConfig.for_profile("medium")
    c = se.build_hv_rank_criterion(15.0, None, None, cfg)
    assert c.is_proxy is True
    assert c.passed is True


def test_hv_rank_criterion_fails_when_stretched():
    cfg = se.StrategyConfig.for_profile("medium")
    assert se.build_hv_rank_criterion(82.0, None, None, cfg).passed is False


def test_hv_rank_criterion_reports_rich_iv():
    cfg = se.StrategyConfig.for_profile("medium")
    c = se.build_hv_rank_criterion(30.0, iv=0.60, hv=0.40, cfg=cfg)
    assert "IV/HV 1.50" in c.current
    assert "50%" in c.meaning


def test_vix_criterion_thresholds():
    cfg = se.StrategyConfig.for_profile("medium")
    assert se.build_vix_criterion(12.0, cfg).passed is True
    assert se.build_vix_criterion(35.0, cfg).passed is False
    assert se.build_vix_criterion(None, cfg).passed is None


def test_events_criterion_blocks_near_earnings():
    cfg = se.StrategyConfig.for_profile("medium")
    assert se.build_events_criterion(3, None, cfg).passed is False
    assert se.build_events_criterion(30, None, cfg).passed is True


def test_events_criterion_macro_event_without_earnings_fails():
    cfg = se.StrategyConfig.for_profile("medium")
    c = se.build_events_criterion(None, "החלטת ריבית הפד", cfg)
    assert c.passed is False


def test_criterion_mark_symbols():
    cfg = se.StrategyConfig.for_profile("medium")
    assert se.build_vix_criterion(12.0, cfg).mark == "V"
    assert se.build_vix_criterion(35.0, cfg).mark == "X"
    assert se.build_vix_criterion(None, cfg).mark == "?"


# --------------------------------------------------------------------------
# גודל פוזיציה
# --------------------------------------------------------------------------

def test_position_plan_respects_one_percent_rule():
    cfg = se.StrategyConfig.for_profile("medium")
    plan = se.build_position_plan(price=100, atr=5, portfolio_value=100_000,
                                  position_pct=0.50, cfg=cfg)
    assert plan.capital_at_risk <= 100_000 * cfg.max_risk_pct
    assert plan.final_shares == plan.max_shares_by_risk


def test_position_plan_uses_intended_size_when_risk_allows():
    cfg = se.StrategyConfig.for_profile("medium")
    plan = se.build_position_plan(price=10, atr=0.05, portfolio_value=100_000,
                                  position_pct=0.05, cfg=cfg)
    assert plan.final_shares == plan.intended_shares


def test_position_plan_stop_matches_atr_multiplier():
    cfg = se.StrategyConfig.for_profile("medium")
    plan = se.build_position_plan(200, 4, 50_000, 0.1, cfg)
    assert plan.stop_distance == pytest.approx(4 * cfg.atr_stop_multiplier)
    assert plan.stop_price == pytest.approx(200 - 8)
    assert plan.stop_pct == pytest.approx(4.0)


def test_position_plan_rejects_zero_atr():
    cfg = se.StrategyConfig.for_profile("medium")
    assert se.build_position_plan(100, 0, 10_000, 0.05, cfg) is None


def test_position_plan_never_negative_shares():
    cfg = se.StrategyConfig.for_profile("medium")
    plan = se.build_position_plan(price=5000, atr=200, portfolio_value=1000,
                                  position_pct=0.05, cfg=cfg)
    assert plan.final_shares == 0


# --------------------------------------------------------------------------
# פסק דין
# --------------------------------------------------------------------------

def _crit(passed):
    return se.Criterion("k", "l", "o", "c", passed, "m")


def test_decide_all_pass_is_invest():
    assert se.decide([_crit(True)] * 4, []) == "INVEST"


def test_decide_three_of_four_is_reduced():
    assert se.decide([_crit(True)] * 3 + [_crit(False)], []) == "INVEST_REDUCED"


def test_decide_two_of_four_is_wait():
    assert se.decide([_crit(True)] * 2 + [_crit(False)] * 2, []) == "WAIT"


def test_decide_one_of_four_is_avoid():
    assert se.decide([_crit(True)] + [_crit(False)] * 3, []) == "AVOID"


def test_veto_overrides_majority():
    assert se.decide([_crit(True)] * 4, ["דוח מחר"]) == "WAIT"


def test_double_veto_is_avoid():
    assert se.decide([_crit(True)] * 4, ["דוח מחר", "VIX 40"]) == "AVOID"


def test_decide_ignores_unknown_criteria():
    assert se.decide([_crit(True), _crit(None)], []) == "INVEST"


def test_decide_all_unknown_is_wait():
    assert se.decide([_crit(None)] * 4, []) == "WAIT"


# --------------------------------------------------------------------------
# evaluate — אינטגרציה
# --------------------------------------------------------------------------

def _ideal(**over):
    base = dict(ticker="TEST", price=100.0, atr=2.0, rel_std=1.1,
                hv_rank_value=15.0, vix=13.0, days_to_earnings=45,
                portfolio_value=100_000, position_pct=0.05,
                risk_profile="medium")
    base.update(over)
    return se.evaluate(**base)


def test_evaluate_ideal_setup_invests_with_position():
    r = _ideal()
    assert r.verdict == "INVEST"
    assert r.score_text == "4/4"
    assert r.position is not None
    assert r.position.final_shares > 0


def test_evaluate_earnings_veto_blocks_and_drops_position():
    r = _ideal(days_to_earnings=2)
    assert r.verdict == "WAIT"
    assert r.position is None
    assert r.vetoes


def test_evaluate_panic_vix_is_veto():
    r = _ideal(vix=34.0)
    assert r.vetoes
    assert r.verdict in ("WAIT", "AVOID")


def test_evaluate_always_reports_proxy_note():
    assert any("פרוקסי" in n for n in _ideal().notes)


def test_evaluate_reduced_size_is_half():
    full = _ideal()
    reduced = _ideal(hv_rank_value=88.0)
    assert reduced.verdict == "INVEST_REDUCED"
    assert reduced.position.final_shares < full.position.final_shares


def test_evaluate_table_has_five_columns_and_four_rows():
    df = _ideal().to_table()
    assert list(df.columns) == ["אינדיקטור", "מצב אופטימלי (לונג)",
                                "המצב הנוכחי", "עמידה", "מה זה מלמד אותך"]
    assert len(df) == 4


def test_evaluate_headline_contains_verdict():
    r = _ideal()
    assert r.verdict_label in r.headline


def test_evaluate_flavor_exists_for_every_verdict():
    for v in se.VERDICT_LABELS:
        assert se.VERDICT_FLAVOR[v]


def test_risk_profile_changes_outcome():
    low = _ideal(hv_rank_value=45.0, risk_profile="low")
    high = _ideal(hv_rank_value=45.0, risk_profile="high")
    assert low.passed_count < high.passed_count


def test_evaluate_missing_data_does_not_crash():
    r = se.evaluate(ticker="X", price=100, atr=2, rel_std=float("nan"),
                    hv_rank_value=float("nan"), vix=None,
                    portfolio_value=0, position_pct=0.05)
    assert r.verdict in se.VERDICT_LABELS
