"""Tests for rr_tab._default_position_index (after patch_position_manager_default.py)."""
from rr_tab import _default_position_index

POS = [{"ticker": "AAPL"}, {"ticker": "NVDA"}, {"ticker": "POLI.TA"}]


def test_selects_top_ticker_when_held():
    assert _default_position_index(POS, "NVDA") == (1, False)


def test_match_is_case_insensitive_and_trims():
    assert _default_position_index(POS, " nvda ") == (1, False)


def test_falls_back_to_first_and_flags_missing():
    assert _default_position_index(POS, "TSLA") == (0, True)


def test_no_default_symbol_keeps_old_behavior():
    assert _default_position_index(POS, None) == (0, False)
    assert _default_position_index(POS, "") == (0, False)


def test_works_with_suffix_tickers():
    assert _default_position_index(POS, "POLI.TA") == (2, False)
