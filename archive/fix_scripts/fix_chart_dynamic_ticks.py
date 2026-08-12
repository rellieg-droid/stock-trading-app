"""
Stage 4e fix script — makes x-axis ticks DYNAMIC (respond to zoom) instead
of a fixed set of ~6 static positions. The previous fix (fix_chart_ticks.py)
locked tick positions to 6 fixed spots for the whole visible range —
which is why zooming in didn't reveal more labels (they just weren't
there). This switches to tickmode="auto" + tickformat, so Plotly places
as many ticks as fit at the current zoom level, always formatted per
the active timeframe (e.g. 1D still shows "02:30 PM" style, but now at
every zoom level, not just 6 fixed spots).
Run from the project folder:  python fix_chart_dynamic_ticks.py
Run this AFTER fix_chart_ticks.py (replaces part of what it added).
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    # ── Per-timeframe tick formatting — same pattern as mobile_layout_test.py ──
    # AM/PM for 1D, date for 5D/1M, month+year for 6M/1Y/YTD, year for 5Y/MAX.
    # Ticks are placed explicitly on real candle dates only (never on the
    # padded empty range from the density fix above) — letting Plotly
    # auto-place ticks across mostly-empty padding triggers its date-axis
    # fallback to an inconsistent two-row format that changes tick to tick.
    _tick_fmt_map = {
        "1D": "%I:%M %p", "5D": "%d %b", "1M": "%d %b",
        "6M": "%b %y", "YTD": "%b %y", "1Y": "%b %y",
        "5Y": "%Y", "MAX": "%Y",
    }
    _tfmt = _tick_fmt_map.get(_cur_period, "%d %b")
    _idx_series = pd.to_datetime(pd.Series(idx)).reset_index(drop=True)
    _n_idx = len(_idx_series)
    if _n_idx == 0:
        _x_tickvals, _x_ticktext = [], []
    elif _cur_period == "5D":
        _day_starts = _idx_series.groupby(_idx_series.dt.date).head(1)
        _x_tickvals = list(_day_starts)
        _x_ticktext = [d.strftime(_tfmt) for d in _x_tickvals]
    else:
        _k = max(1, min(6, _n_idx))
        if _k == 1:
            _tick_idx = [_n_idx - 1]
        else:
            _tick_idx = sorted({round(i * (_n_idx - 1) / (_k - 1)) for i in range(_k)})
        _x_tickvals = [_idx_series.iloc[i] for i in _tick_idx]
        _x_ticktext = [d.strftime(_tfmt) for d in _x_tickvals]

    # crosshair — קו אנכי ואופקי מקווקו
    spike_x = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikemode='across', spikesnap='cursor',
        rangebreaks=_x_rangebreaks,
        range=_x_padded_range, autorange=(_x_padded_range is None),
        tickmode="array", tickvals=_x_tickvals, ticktext=_x_ticktext,
    )'''

NEW_BLOCK = '''    # ── Per-timeframe tick FORMAT, with DYNAMIC tick placement ──
    # tickmode="auto" (Plotly's default) lets Plotly decide how many ticks
    # fit at the CURRENT zoom level and re-place them live as the person
    # zooms/pans — this is what makes zooming into 1D reveal per-hour (then
    # per-minute) labels instead of staying stuck at ~6 fixed spots. We only
    # fix the FORMAT per timeframe, never the positions.
    _tick_fmt_map = {
        "1D": "%I:%M %p", "5D": "%d %b", "1M": "%d %b",
        "6M": "%b %y", "YTD": "%b %y", "1Y": "%b %y",
        "5Y": "%Y", "MAX": "%Y",
    }
    _tfmt = _tick_fmt_map.get(_cur_period, "%d %b")

    # crosshair — קו אנכי ואופקי מקווקו
    spike_x = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikemode='across', spikesnap='cursor',
        rangebreaks=_x_rangebreaks,
        range=_x_padded_range, autorange=(_x_padded_range is None),
        tickformat=_tfmt, nticks=12,
    )'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written. Block not found.")
        print("Make sure fix_chart_ticks.py was applied first (this replaces part of it).")
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1).")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — ticks are now dynamic: more labels appear automatically when zooming in.")


if __name__ == "__main__":
    main()
