"""טסטים לסעיף 8 ב-options_engine.py: quote_summary, nearest_strike."""
import math

import pytest

from options_engine import quote_summary, nearest_strike, QuoteSummary


class TestQuoteSummary:
    def test_live_quote(self):
        q = quote_summary(1.00, 1.20)
        assert q.is_live
        assert q.mid == pytest.approx(1.10)
        assert q.spread == pytest.approx(0.20)
        assert q.spread_pct == pytest.approx(0.20 / 1.10)

    def test_zero_bid_is_not_live(self):
        # מחוץ לשעות המסחר - אין fallback
        assert quote_summary(0.0, 1.20) == QuoteSummary(False, None, None, None)

    def test_zero_ask_is_not_live(self):
        assert not quote_summary(1.0, 0.0).is_live

    def test_crossed_market_is_not_live(self):
        assert not quote_summary(1.30, 1.20).is_live

    def test_locked_market_is_live(self):
        q = quote_summary(1.20, 1.20)
        assert q.is_live and q.spread == 0 and q.spread_pct == 0

    @pytest.mark.parametrize("bid,ask", [(None, 1.0), (1.0, None), ("x", 1.0),
                                         (math.nan, 1.0), (1.0, math.inf)])
    def test_bad_inputs_not_live(self, bid, ask):
        assert not quote_summary(bid, ask).is_live


class TestNearestStrike:
    def test_exact_match(self):
        assert nearest_strike([145, 150, 155], 150) == 150

    def test_nearest(self):
        assert nearest_strike([145, 150, 155], 152) == 150
        assert nearest_strike([145, 150, 155], 153) == 155

    def test_tie_goes_lower(self):
        assert nearest_strike([145, 150, 155], 152.5) == 150

    def test_outside_range(self):
        assert nearest_strike([145, 150, 155], 10) == 145
        assert nearest_strike([145, 150, 155], 999) == 155

    def test_unsorted_and_dirty(self):
        assert nearest_strike([155, None, "x", -5, math.nan, 145.0], 146) == 145

    def test_empty(self):
        assert nearest_strike([], 150) is None
        assert nearest_strike(None, 150) is None
