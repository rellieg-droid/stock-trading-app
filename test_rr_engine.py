"""
test_rr_engine.py
=================
בדיקות למנוע הסיכון-סיכוי. הרצה:
    C:\\PhyCharm_projects\\Stock_tracking\\.venv\\Scripts\\python.exe -m pytest test_rr_engine.py -v
"""

from datetime import date, timedelta

import pytest

import rr_engine as rr


# ---------------------------------------------------------------------------
# יסודות R
# ---------------------------------------------------------------------------

def test_risk_per_share_long():
    assert rr.risk_per_share(100.0, 95.0, "long") == pytest.approx(5.0)


def test_risk_per_share_short():
    assert rr.risk_per_share(100.0, 105.0, "short") == pytest.approx(5.0)


def test_stop_on_wrong_side_raises():
    with pytest.raises(ValueError):
        rr.risk_per_share(100.0, 105.0, "long")
    with pytest.raises(ValueError):
        rr.risk_per_share(100.0, 95.0, "short")


def test_stop_equal_entry_raises():
    with pytest.raises(ValueError):
        rr.risk_per_share(100.0, 100.0, "long")


def test_targets_are_exact_r_multiples_long():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    assert [t.price for t in plan.targets] == pytest.approx([105.0, 110.0, 115.0])


def test_targets_mirror_correctly_for_short():
    plan = rr.build_plan("TEST", entry=100.0, stop=105.0, shares=100, direction="short")
    assert [t.price for t in plan.targets] == pytest.approx([95.0, 90.0, 85.0])


def test_targets_scale_with_stop_distance():
    """היעדים נגזרים מהסיכון, לא מאחוז קבוע — סטופ רחב יותר מרחיק את היעדים."""
    tight = rr.build_plan("A", entry=100.0, stop=98.0, shares=10)
    wide = rr.build_plan("A", entry=100.0, stop=90.0, shares=10)
    assert tight.target_by_r(2.0).price == pytest.approx(104.0)
    assert wide.target_by_r(2.0).price == pytest.approx(120.0)


def test_stop_from_atr():
    assert rr.stop_from_atr(100.0, atr=2.5, atr_mult=2.0) == pytest.approx(95.0)
    assert rr.stop_from_atr(100.0, atr=2.5, atr_mult=2.0, direction="short") == pytest.approx(105.0)


def test_stop_from_atr_rejects_bad_atr():
    with pytest.raises(ValueError):
        rr.stop_from_atr(100.0, atr=0.0)


# ---------------------------------------------------------------------------
# גודל פוזיציה
# ---------------------------------------------------------------------------

def test_position_size_one_percent_rule():
    res = rr.position_size(50_000, 0.01, entry=100.0, stop=95.0)
    assert res["shares"] == 100           # 500 תקציב / 5 סיכון למניה
    assert res["risk_amount"] == pytest.approx(500.0)


def test_position_size_rounds_down_never_up():
    res = rr.position_size(10_000, 0.01, entry=50.0, stop=47.0)  # 100 / 3 = 33.33
    assert res["shares"] == 33
    assert res["risk_amount"] <= 100.0


def test_position_size_respects_exposure_cap():
    res = rr.position_size(10_000, 0.01, entry=20.0, stop=19.9, max_position_pct=0.20)
    assert res["capped_by_exposure"] is True
    assert res["notional"] <= 2_000.0


def test_position_size_rejects_percent_as_whole_number():
    with pytest.raises(ValueError):
        rr.position_size(10_000, 1, entry=100.0, stop=95.0)  # 1 במקום 0.01


def test_size_for_gap_budget_is_smaller_than_stop_based_size():
    """סיזינג לפי פער חייב להיות שמרני יותר מסיזינג לפי סטופ צר."""
    by_stop = rr.position_size(100_000, 0.01, entry=100.0, stop=97.0)["shares"]
    by_gap = rr.size_for_gap_budget(100_000, max_gap_loss_pct=0.01,
                                    entry=100.0, assumed_gap_pct=0.12)["shares"]
    assert by_gap < by_stop


# ---------------------------------------------------------------------------
# מתמטיקת רווחיות
# ---------------------------------------------------------------------------

def test_breakeven_win_rate_values():
    assert rr.breakeven_win_rate(1.0) == pytest.approx(0.50)
    assert rr.breakeven_win_rate(2.0) == pytest.approx(1 / 3)
    assert rr.breakeven_win_rate(3.0) == pytest.approx(0.25)


def test_expectancy_zero_at_breakeven():
    assert rr.expectancy_r(1 / 3, 2.0) == pytest.approx(0.0, abs=1e-9)


def test_expectancy_positive_above_breakeven():
    assert rr.expectancy_r(0.40, 2.0) > 0


def test_blended_r_default_ladder():
    # 0.5*1 + 0.3*2 + 0.2*3 = 1.7
    assert rr.blended_r() == pytest.approx(1.7)


def test_blended_r_rejects_bad_weights():
    with pytest.raises(ValueError):
        rr.blended_r((1, 2, 3), (0.5, 0.3, 0.3))


# ---------------------------------------------------------------------------
# חלוקת מניות
# ---------------------------------------------------------------------------

def test_share_allocation_never_loses_shares_to_rounding():
    plan = rr.build_plan("TEST", entry=100.0, stop=97.0, shares=101)
    assert sum(t.shares for t in plan.targets) == 101


def test_share_allocation_handles_tiny_position():
    plan = rr.build_plan("TEST", entry=100.0, stop=97.0, shares=1)
    assert sum(t.shares for t in plan.targets) == 1


def test_plan_auto_sizes_when_shares_not_given():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0,
                         account_value=50_000, risk_pct=0.01)
    assert plan.shares == 100


def test_summary_rows_contain_all_five_stages():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    rows = plan.to_rows()
    assert len(rows) == 5
    assert rows[1]["R"] == -1.0
    assert [r["R"] for r in rows[2:]] == [1.0, 2.0, 3.0]


# ---------------------------------------------------------------------------
# דוחות כספיים
# ---------------------------------------------------------------------------

def test_days_to_earnings():
    today = date(2026, 8, 16)
    assert rr.days_to_earnings(date(2026, 8, 20), today) == 4
    assert rr.days_to_earnings(date(2026, 8, 16), today) == 0
    assert rr.days_to_earnings(date(2026, 8, 10), today) == -6
    assert rr.days_to_earnings(None, today) is None


def test_earnings_tiers():
    assert rr.earnings_risk_tier(30) == "clear"
    assert rr.earnings_risk_tier(8) == "elevated"
    assert rr.earnings_risk_tier(4) == "high"
    assert rr.earnings_risk_tier(1) == "critical"
    assert rr.earnings_risk_tier(0) == "today"
    assert rr.earnings_risk_tier(-3) == "passed"


def test_earnings_action_shrinks_size_as_report_approaches():
    sizes = [rr.earnings_action(d).recommended_size_pct for d in (30, 8, 4, 1, 0)]
    assert sizes == sorted(sizes, reverse=True)
    assert sizes[-1] == 0.0


def test_locked_first_target_allows_larger_exposure():
    plain = rr.earnings_action(1, has_1r_locked=False).recommended_size_pct
    locked = rr.earnings_action(1, has_1r_locked=True).recommended_size_pct
    assert locked > plain


def test_report_day_is_a_hard_rule():
    assert rr.earnings_action(0).hard_rule is True
    assert rr.earnings_action(30).hard_rule is False


def test_trim_plan_math():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    res = rr.trim_plan(plan, 0.50)
    assert res["keep_shares"] == 50
    assert res["trim_shares"] == 50
    assert res["residual_risk"] == pytest.approx(250.0)


# ---------------------------------------------------------------------------
# סימולציית פערים — הליבה של מודול הדוחות
# ---------------------------------------------------------------------------

def test_gap_down_through_stop_loses_more_than_one_r():
    """הבדיקה החשובה ביותר: סטופ לא מגן מפני פער."""
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    out = rr.simulate_gap(plan, -0.15)   # פתיחה ב-85
    assert out.outcome == "stop_breached"
    assert out.realized_r == pytest.approx(-3.0)
    assert out.pnl == pytest.approx(-1500.0)      # ולא -500 כמתוכנן
    assert out.slippage_r == pytest.approx(2.0)


def test_small_gap_down_above_stop_keeps_position_open():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    out = rr.simulate_gap(plan, -0.02)
    assert out.outcome == "open"
    assert out.closed is False


def test_gap_exactly_at_stop_counts_as_breached():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    out = rr.simulate_gap(plan, -0.05)
    assert out.outcome == "stop_breached"
    assert out.realized_r == pytest.approx(-1.0)
    assert out.slippage_r == pytest.approx(0.0)


def test_gap_up_hits_third_target():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    out = rr.simulate_gap(plan, 0.18)     # פתיחה ב-118, מעל יעד 3 (115)
    assert out.outcome == "target_3"
    assert out.closed is True
    assert out.realized_r == pytest.approx(3.6)   # מילוי טוב מהיעד, לא בדיוק 3R


def test_gap_up_hits_only_first_target():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    out = rr.simulate_gap(plan, 0.06)     # פתיחה ב-106: מעל יעד 1, מתחת ליעד 2
    assert out.outcome == "target_1"
    assert out.closed is False


def test_short_gap_up_breaches_stop():
    plan = rr.build_plan("TEST", entry=100.0, stop=105.0, shares=100, direction="short")
    out = rr.simulate_gap(plan, 0.15)     # פתיחה ב-115
    assert out.outcome == "stop_breached"
    assert out.realized_r == pytest.approx(-3.0)


def test_short_gap_down_hits_targets():
    plan = rr.build_plan("TEST", entry=100.0, stop=105.0, shares=100, direction="short")
    out = rr.simulate_gap(plan, -0.16)    # פתיחה ב-84, מתחת ליעד 3 (85)
    assert out.outcome == "target_3"


def test_gap_measured_from_reference_price_not_entry():
    """פוזיציה שכבר ברווח: הפער נמדד מהסגירה האחרונה, לא מהכניסה."""
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    out = rr.simulate_gap(plan, -0.10, ref_price=110.0)
    assert out.open_price == pytest.approx(99.0)
    assert out.outcome == "open"          # עדיין מעל הסטופ


def test_scenario_table_is_sorted_and_complete():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    rows = rr.gap_scenario_table(plan)
    assert len(rows) == len(rr.DEFAULT_GAP_GRID)
    assert rows[0].gap_pct < rows[-1].gap_pct
    assert rows[0].outcome == "stop_breached"


def test_worst_case_reports_gap_between_plan_and_reality():
    plan = rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)
    wc = rr.worst_case_gap_loss(plan, gap_pct=-0.15)
    assert wc["planned_loss"] == pytest.approx(-500.0)
    assert wc["actual_loss"] == pytest.approx(-1500.0)
    assert wc["extra_loss"] == pytest.approx(-1000.0)
    assert wc["multiple_of_plan"] == pytest.approx(3.0)


def test_worst_case_works_for_short_side():
    plan = rr.build_plan("TEST", entry=100.0, stop=105.0, shares=100, direction="short")
    wc = rr.worst_case_gap_loss(plan, gap_pct=-0.15)
    assert wc["actual_loss"] < wc["planned_loss"]


# ---------------------------------------------------------------------------
# מצב פוזיציה קיימת
# ---------------------------------------------------------------------------

def _plan():
    return rr.build_plan("TEST", entry=100.0, stop=95.0, shares=100)


def test_status_at_entry_is_flat():
    s = rr.position_status(_plan(), 100.0)
    assert s.current_r == pytest.approx(0.0)
    assert s.targets_hit == []
    assert s.next_target.r_multiple == 1.0


def test_status_between_targets():
    s = rr.position_status(_plan(), 107.5)
    assert s.current_r == pytest.approx(1.5)
    assert s.targets_hit == [1.0]
    assert s.next_target.r_multiple == 2.0
    assert s.distance_to_next_pct == pytest.approx((110 - 107.5) / 107.5)


def test_status_all_targets_hit():
    s = rr.position_status(_plan(), 116.0)
    assert s.targets_hit == [1.0, 2.0, 3.0]
    assert s.next_target is None
    assert s.distance_to_next_pct is None
    assert s.color == "green"


def test_status_below_stop_flags_breach():
    s = rr.position_status(_plan(), 94.0)
    assert s.stop_breached is True
    assert s.unrealized_pnl < -100 * 5


def test_status_losing_but_above_stop():
    s = rr.position_status(_plan(), 97.0)
    assert s.stop_breached is False
    assert s.color == "orange"
    assert s.distance_to_stop_pct == pytest.approx((97 - 95) / 97)


def test_status_short_side_mirrors():
    plan = rr.build_plan("TEST", entry=100.0, stop=105.0, shares=100, direction="short")
    s = rr.position_status(plan, 92.5)
    assert s.current_r == pytest.approx(1.5)
    assert s.targets_hit == [1.0]


def test_status_rejects_bad_price():
    with pytest.raises(ValueError):
        rr.position_status(_plan(), 0.0)


def test_breakeven_stop_is_entry():
    plan = _plan()
    assert rr.breakeven_stop_after_target(plan, 1.0) == pytest.approx(plan.entry)
