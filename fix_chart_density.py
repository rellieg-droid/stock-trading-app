"""
Stage 4b fix script — fixes 1M looking sparse/empty compared to other
timeframes. Same fix already solved in mobile_layout_test.py
(get_x_axis_padded_range): 1M has ~21 daily candles vs 6M's ~126, so
Plotly's autorange stretches those 21 candles across the FULL chart
width, leaving huge gaps between them. This pads empty margin on both
sides of the x-axis range (using business days) so the candle spacing
stays visually consistent with denser timeframes, instead of 1M
looking "thinner" on information.
Run from the project folder:  python fix_chart_density.py
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    # crosshair — קו אנכי ואופקי מקווקו
    spike_x = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikemode='across', spikesnap='cursor',
        rangebreaks=_x_rangebreaks,
    )'''

NEW_BLOCK = '''    # ── Density fix for sparse timeframes (e.g. 1M's ~21 candles vs 6M's ~126) ──
    # Same fix already used in mobile_layout_test.py: pad the x-axis range with
    # empty margin on both sides so few-candle timeframes don't stretch their
    # candles apart with big gaps — keeps spacing visually consistent across
    # timeframes instead of 1M looking sparser/emptier than the others.
    _n_bars = len(idx)
    _min_visible_slots = 100
    _x_padded_range = None
    if 2 <= _n_bars < _min_visible_slots and _cur_period != "1D":
        _missing = _min_visible_slots - _n_bars
        _pad_each_side = _missing // 2
        if _pad_each_side >= 1:
            _bday = pd.tseries.offsets.BDay(_pad_each_side)
            _idx_dt = pd.to_datetime(pd.Series(idx))
            _x_padded_range = [_idx_dt.iloc[0] - _bday, _idx_dt.iloc[-1] + _bday]

    # crosshair — קו אנכי ואופקי מקווקו
    spike_x = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikemode='across', spikesnap='cursor',
        rangebreaks=_x_rangebreaks,
        range=_x_padded_range, autorange=(_x_padded_range is None),
    )'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written. Block not found (maybe already changed,")
        print("or Stage 4 (fix_chart_gaps.py) hasn't been applied yet — run that first).")
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1).")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — x-axis padding added. 1M (and other sparse timeframes) should now")
    print("show candle spacing consistent with denser timeframes like 6M.")


if __name__ == "__main__":
    main()
