"""Tests for consequences.py (plain-language 'what happens if I click')."""
import pytest
from consequences import build_consequences, render_consequences_html


def _values(c):
    return {label: (value, tone) for label, value, tone in c.lines}


# ---------- BUY ----------
def test_buy_headline_shows_shares_symbol_price_and_cash_out():
    c = build_consequences("BUY", "AAPL", shares=10, price=100.0)
    assert "10" in c.headline and "AAPL" in c.headline
    assert "$100.00" in c.headline
    assert "$1,000.00" in c.headline


def test_buy_up_scenario_is_positive_10_percent_of_total():
    v = _values(build_consequences("BUY", "AAPL", shares=10, price=100.0))
    assert v["אם המניה עולה 10%"] == ("+$100.00", "pos")


def test_buy_down_scenario_is_negative_10_percent_of_total():
    v = _values(build_consequences("BUY", "AAPL", shares=10, price=100.0))
    assert v["אם המניה יורדת 10%"] == ("-$100.00", "neg")


def test_custom_scenario_pct_changes_label_and_amount():
    v = _values(build_consequences("BUY", "X", shares=1, price=200.0, scenario_pct=0.05))
    assert v["אם המניה עולה 5%"] == ("+$10.00", "pos")


def test_currency_symbol_is_used():
    c = build_consequences("BUY", "POLI.TA", shares=2, price=50.0, currency="₪")
    assert "₪100.00" in c.headline


# ---------- SELL ----------
def test_sell_realized_gain_is_positive():
    v = _values(build_consequences("SELL", "AAPL", shares=10, price=120.0,
                                   held_shares=10, avg_price=100.0))
    assert v["רווח/הפסד ממומש"] == ("+$200.00", "pos")


def test_sell_realized_loss_is_negative():
    v = _values(build_consequences("SELL", "AAPL", shares=5, price=90.0,
                                   held_shares=10, avg_price=100.0))
    assert v["רווח/הפסד ממומש"] == ("-$50.00", "neg")


def test_sell_shows_both_after_sale_scenarios_neutrally():
    v = _values(build_consequences("SELL", "AAPL", shares=10, price=100.0,
                                   held_shares=10, avg_price=100.0))
    assert v["אם תעלה עוד 10% אחרי המכירה, רווח שלא יתקבל"] == ("$100.00", "neutral")
    assert v["אם תרד 10% אחרי המכירה, הפסד שנחסך"] == ("$100.00", "neutral")


def test_sell_more_than_held_warns_and_uses_held_quantity():
    c = build_consequences("SELL", "AAPL", shares=20, price=100.0,
                           held_shares=5, avg_price=100.0)
    tones = [t for _, _, t in c.lines]
    assert "warn" in tones
    assert "$500.00" in c.headline  # 5 * 100, not 20 * 100


def test_sell_without_position_returns_warning_only():
    c = build_consequences("SELL", "AAPL", shares=3, price=100.0, held_shares=0)
    assert [t for _, _, t in c.lines] == ["warn"]


def test_sell_without_avg_price_skips_realized_line():
    v = _values(build_consequences("SELL", "AAPL", shares=1, price=100.0,
                                   held_shares=1, avg_price=None))
    assert "רווח/הפסד ממומש" not in v


# ---------- validation ----------
@pytest.mark.parametrize("kwargs", [
    dict(action="BUY", symbol="A", shares=0, price=10.0),
    dict(action="BUY", symbol="A", shares=1, price=0.0),
    dict(action="BUY", symbol="A", shares=1, price=None),
    dict(action="HOLD", symbol="A", shares=1, price=10.0),
])
def test_invalid_inputs_raise_value_error(kwargs):
    with pytest.raises(ValueError):
        build_consequences(**kwargs)


# ---------- HTML ----------
def test_html_has_title_rtl_and_ltr_numbers():
    html = render_consequences_html(build_consequences("BUY", "AAPL", 1, 100.0))
    assert "מה יקרה אם אלחץ" in html
    assert "direction:rtl" in html
    assert 'dir="ltr"' in html


def test_html_escapes_symbol():
    html = render_consequences_html(build_consequences("BUY", "<b>X</b>", 1, 10.0))
    assert "<b>X</b>" not in html
    assert "&lt;b&gt;" in html


# ---------- v2: RTL sign fix + singular ----------
def test_html_forces_ltr_numbers_via_css_not_only_attribute():
    html = render_consequences_html(build_consequences("BUY", "AAPL", 1, 100.0))
    assert "direction:ltr" in html and "unicode-bidi:isolate" in html


def test_html_wraps_numbers_in_unicode_isolates():
    html = render_consequences_html(build_consequences("BUY", "AAPL", 1, 100.0))
    assert "\u2066+$10.00\u2069" in html


def test_buy_one_share_uses_singular():
    c = build_consequences("BUY", "NVDA", shares=1, price=100.0)
    assert "מניה אחת" in c.headline and "1 מניות" not in c.headline


def test_sell_one_share_uses_singular():
    c = build_consequences("SELL", "NVDA", shares=1, price=100.0,
                           held_shares=3, avg_price=90.0)
    assert "מניה אחת" in c.headline
