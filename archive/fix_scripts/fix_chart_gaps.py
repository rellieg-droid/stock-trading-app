"""
Stage 4 fix script — eliminates chart gaps (overnight hours + weekends)
by porting the exact rangebreaks logic already solved and validated in
mobile_layout_test.py into the real chart's Plotly figure.
Run from the project folder:  python fix_chart_gaps.py

Why 5D (and similar) showed gaps: the real chart's x-axis was a plain
datetime axis with no rangebreaks, so Plotly stretched blank space
across every night and weekend with no trading data — exactly the
"stretched candles with big blank gaps" look. mobile_layout_test.py
solved this already: hide non-trading hours + weekends via
`rangebreaks`, with different rules depending on the active period
(1D needs none — single session; 5D needs hours+weekends since it's
intraday across several days; everything daily+ only needs weekends).
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    axis_s = dict(gridcolor=GR, zeroline=False, color='#8b949e', showgrid=True, linecolor=GR)

    # crosshair — קו אנכי ואופקי מקווקו
    spike_x = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikemode='across', spikesnap='cursor',
    )'''

NEW_BLOCK = '''    axis_s = dict(gridcolor=GR, zeroline=False, color='#8b949e', showgrid=True, linecolor=GR)

    # ── Gap elimination — same logic already solved in mobile_layout_test.py ──
    # 1D = single session, no gaps to hide. 5D = intraday across several
    # sessions, needs both overnight hours AND weekends hidden. Daily+ views
    # only need weekends hidden (no intraday hour gaps to worry about).
    _cur_period = st.session_state.period
    if _cur_period == "1D":
        _x_rangebreaks = []
    elif _cur_period == "5D":
        _x_rangebreaks = [dict(bounds=[16, 9.5], pattern="hour"), dict(bounds=["sat", "mon"])]
    else:
        _x_rangebreaks = [dict(bounds=["sat", "mon"])]

    # crosshair — קו אנכי ואופקי מקווקו
    spike_x = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikemode='across', spikesnap='cursor',
        rangebreaks=_x_rangebreaks,
    )'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written. Block not found (maybe already changed).")
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1).")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — rangebreaks added to all 3 chart x-axes (price/volume/RSI-MACD).")
    print("5D and other multi-day intraday views should no longer show overnight/weekend gaps.")


if __name__ == "__main__":
    main()
