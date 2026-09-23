"""
Tests for combo_strategy_engine.py
Run: pytest test_combo_strategy_engine.py -v

test_key_figures / test_payoff_table_* reconstruct the SOXL example
(CALL 145 / CALL 170 / 2x PUT 110) discussed with the user, so the math
can be checked by hand against numbers already shown to her.

test_find_candidates_* uses a small synthetic chain designed so the
correct answer (145 / 170 / 110) is known in advance, independent of
whether that happens to be what a human would have picked.
"""
import pandas as pd
import pytest

from combo_strategy_engine import (
    ComboCandidate,
    compute_payoff_table,
    key_figures,
    margin_estimates,
    find_candidates,
    suggested_entry_order,
    price_for_pnl_threshold,
    add_position,
    load_watchlist,
    close_position,
    add_ledger_entry,
    portfolio_summary,
    _premium_mid,
)


@pytest.fixture
def soxl_candidate():
    return ComboCandidate(
        ticker="SOXL",
        expiration="2026-10-23",
        spot_price=146.0,
        anchor_call_strike=145.0,
        anchor_call_premium=19.56,
        second_call_strike=170.0,
        second_call_premium=10.75,
        put_strike=110.0,
        put_premium=5.00,
        num_puts=2,
        net_cost=-1.19,
        call_spread_width=25.0,
    )


def test_key_figures_match_manual_calculation(soxl_candidate):
    # now computed via options_engine.Position instead of hand-rolled formulas
    figs = key_figures(soxl_candidate)
    assert figs["net_cost_dollars"] == pytest.approx(-119, abs=0.5)
    assert figs["max_profit"] == pytest.approx(2619, abs=0.5)
    assert figs["max_loss_at_zero"] == pytest.approx(-21881, abs=0.5)
    assert figs["breakeven_low"] == pytest.approx(109.405, abs=0.01)
    assert len(figs["breakevens"]) == 1  # exactly one crossing for this 3-leg shape


def test_to_position_matches_options_engine_directly(soxl_candidate):
    position = soxl_candidate.to_position()
    assert position.net_cash == pytest.approx(119, abs=0.5)
    assert position.max_loss() == pytest.approx(21881, abs=0.5)
    assert position.max_profit() == pytest.approx(2619, abs=0.5)


def test_suggested_entry_order_puts_the_long_call_first(soxl_candidate):
    order = suggested_entry_order(soxl_candidate)
    # long call (protection leg) must be entered before the short legs,
    # exactly like options_engine.entry_order() does for collar/iron_condor
    kinds_dirs = [(leg.kind, leg.direction) for leg in order]
    assert kinds_dirs[0] == ("call", 1)
    assert all(d == -1 for _, d in kinds_dirs[1:])


@pytest.mark.parametrize(
    "price,expected_pnl",
    [
        (0, -21881),
        (100, -1881),
        (109.405, 0),
        (110, 119),
        (130, 119),
        (145, 119),
        (160, 1619),
        (170, 2619),
        (200, 2619),
    ],
)
def test_payoff_table_matches_hand_calculated_points(soxl_candidate, price, expected_pnl):
    table = compute_payoff_table(soxl_candidate, price_points=[price])
    assert table.iloc[0]["pnl"] == pytest.approx(expected_pnl, abs=1)


def test_margin_estimate_cash_secured(soxl_candidate):
    margins = margin_estimates(soxl_candidate)
    # 2 puts * 110 strike * 100 shares, minus premium collected
    assert margins["cash_secured"] == pytest.approx(21000, abs=100)


def test_premium_mid_prefers_bid_ask_over_last():
    row = pd.Series({"bid": 10.0, "ask": 11.0, "lastPrice": 99.0})
    assert _premium_mid(row) == 10.5


def test_premium_mid_falls_back_to_last_when_no_bid_ask():
    row = pd.Series({"bid": 0, "ask": 0, "lastPrice": 7.5})
    assert _premium_mid(row) == 7.5


def test_price_for_pnl_threshold_matches_manual_interpolation(soxl_candidate):
    # between the 0-payoff point (-21881) and the plateau (119), so exactly
    # one crossing on the downslope — same interpolation logic as breakevens()
    price = price_for_pnl_threshold(soxl_candidate, -2000)
    assert price == pytest.approx(99.41, abs=0.05)


def test_price_for_pnl_threshold_returns_none_above_best_case(soxl_candidate):
    # 3000 is above max_profit (2619) — never reached, so no crossing exists
    assert price_for_pnl_threshold(soxl_candidate, 3000) is None


def test_add_position_stores_alert_threshold_and_reference_price(soxl_candidate, tmp_path):
    path = str(tmp_path / "watchlist.json")
    add_position(soxl_candidate, note="test", alert_threshold=-2000, path=path)
    data = load_watchlist(path)
    assert data[0]["alert_threshold"] == -2000
    assert data[0]["alert_reference_price"] == pytest.approx(99.41, abs=0.05)


def test_close_position_records_realized_pnl_and_date(soxl_candidate, tmp_path):
    path = str(tmp_path / "watchlist.json")
    add_position(soxl_candidate, path=path)
    close_position(0, gross_pnl=-350.0, path=path)  # default commission=15, tax_rate=0.25
    entry = load_watchlist(path)[0]
    assert entry["status"] == "closed"
    assert entry["realized_pnl_gross"] == -350.0
    assert entry["commission"] == 15.0
    assert entry["tax"] == 0.0  # a loss isn't taxed
    assert entry["realized_pnl"] == -365.0  # net = gross - commission (no tax on a loss)
    assert "close_date" in entry


def test_compute_net_realized_taxes_only_a_positive_net():
    from combo_strategy_engine import compute_net_realized
    profit = compute_net_realized(1000.0, commission=15.0, tax_rate=0.25)
    assert profit["pre_tax_net"] == 985.0
    assert profit["tax"] == pytest.approx(246.25)
    assert profit["net_pnl"] == pytest.approx(738.75)

    loss = compute_net_realized(-350.0, commission=15.0, tax_rate=0.25)
    assert loss["tax"] == 0.0
    assert loss["net_pnl"] == -365.0

    # commission alone can flip a tiny gross profit into a net loss — still no tax
    marginal = compute_net_realized(10.0, commission=15.0, tax_rate=0.25)
    assert marginal["pre_tax_net"] == -5.0
    assert marginal["tax"] == 0.0
    assert marginal["net_pnl"] == -5.0


def test_portfolio_summary_aggregates_ledger_margin_and_realized_pnl(soxl_candidate, tmp_path):
    wp = str(tmp_path / "watchlist.json")
    lp = str(tmp_path / "ledger.json")

    add_position(soxl_candidate, available_capital=50000, path=wp)  # stays open
    add_position(soxl_candidate, path=wp)
    close_position(1, gross_pnl=-350.0, path=wp)  # closed, net -365 after 15$ commission

    add_ledger_entry(50000, "deposit", path=lp)
    add_ledger_entry(-5000, "withdrawal", path=lp)

    summary = portfolio_summary(wp, lp, refreshed_open=[{"mtm_pnl_dollars": 220.0}])
    assert summary["total_capital"] == 45000
    assert summary["open_count"] == 1
    assert summary["closed_count"] == 1
    assert summary["realized_pnl_gross_total"] == -350.0
    assert summary["realized_pnl_total"] == -365.0
    assert summary["commission_total"] == 15.0
    assert summary["tax_total"] == 0.0
    assert summary["net_worth_now"] == pytest.approx(44635.0)  # 45000 + (-365)
    assert summary["unrealized_pnl"] == 220.0
    assert summary["margin_in_use_reg_t"] == pytest.approx(3200.0, abs=0.5)


def test_get_entry_margins_recomputes_for_old_entries_missing_the_field(soxl_candidate):
    from combo_strategy_engine import get_entry_margins
    from dataclasses import asdict
    old_style_entry = asdict(soxl_candidate)  # no margin_reg_t / margin_cash_secured keys
    assert "margin_reg_t" not in old_style_entry
    margins = get_entry_margins(old_style_entry)
    assert margins["cash_secured"] == pytest.approx(21000, abs=100)


def test_portfolio_summary_includes_margin_for_old_style_entries(soxl_candidate, tmp_path):
    wp = str(tmp_path / "watchlist.json")
    add_position(soxl_candidate, path=wp)  # current version — has margin fields
    # simulate an old entry saved before margin storage existed
    data = load_watchlist(wp)
    del data[0]["margin_reg_t"]
    del data[0]["margin_cash_secured"]
    from combo_strategy_engine import save_watchlist
    save_watchlist(data, wp)

    summary = portfolio_summary(wp, str(tmp_path / "ledger.json"))
    assert summary["margin_in_use_reg_t"] == pytest.approx(3200.0, abs=0.5)


def test_find_candidates_recovers_known_pattern_from_synthetic_chain():
    calls = pd.DataFrame(
        {
            "strike": [140, 145, 150, 165, 170, 175],
            "bid": [21.5, 19.5, 16.5, 11.0, 9.5, 8.0],
            "ask": [22.5, 20.5, 17.5, 12.0, 10.5, 9.0],
            "lastPrice": [22.0, 20.0, 17.0, 11.5, 10.0, 8.5],
        }
    )
    puts = pd.DataFrame(
        {
            "strike": [100, 105, 110, 115],
            "bid": [2.8, 3.8, 4.8, 6.5],
            "ask": [3.2, 4.2, 5.2, 6.9],
            "lastPrice": [3.0, 4.0, 5.0, 6.7],
        }
    )
    # By construction: anchor=145 (mid 20.0), second=170 (mid 10.0, exactly
    # half), put=110 (mid 5.0, so 2*5.0=10.0 exactly cancels the 10.0 call
    # spread debit) is the net-zero, closest match.
    candidates = find_candidates(
        calls, puts, spot_price=146.0, ticker="SOXL", expiration="2026-10-23"
    )
    assert len(candidates) > 0
    best = candidates[0]
    assert best.anchor_call_strike == 145.0
    assert best.second_call_strike == 170.0
    assert best.put_strike == 110.0
    assert best.net_cost == pytest.approx(0.0, abs=0.01)
