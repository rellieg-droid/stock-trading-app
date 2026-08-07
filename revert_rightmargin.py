"""
Revert script — undoes ONLY fix_chart_rightmargin.py, restores the
symmetric (both-sides) padding from before it.
Run from the project folder:  python revert_rightmargin.py
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    _n_bars = len(idx)
    _min_visible_slots = 100
    _x_padded_range = None
    if 2 <= _n_bars < _min_visible_slots and _cur_period != "1D":
        _missing = _min_visible_slots - _n_bars
        # Right-biased: the latest candle gets most of the breathing room
        # ahead of it (professional-platform convention), left side stays
        # close to tight so the view doesn't feel like it's floating.
        _pad_right = max(1, round(_missing * 0.85))
        _pad_left  = max(0, _missing - _pad_right)
        if _pad_right >= 1:
            _idx_dt = pd.to_datetime(pd.Series(idx))
            _left_bound = (_idx_dt.iloc[0] - pd.tseries.offsets.BDay(_pad_left)) if _pad_left >= 1 else _idx_dt.iloc[0]
            _right_bound = _idx_dt.iloc[-1] + pd.tseries.offsets.BDay(_pad_right)
            _x_padded_range = [_left_bound, _right_bound]'''

NEW_BLOCK = '''    _n_bars = len(idx)
    _min_visible_slots = 100
    _x_padded_range = None
    if 2 <= _n_bars < _min_visible_slots and _cur_period != "1D":
        _missing = _min_visible_slots - _n_bars
        _pad_each_side = _missing // 2
        if _pad_each_side >= 1:
            _bday = pd.tseries.offsets.BDay(_pad_each_side)
            _idx_dt = pd.to_datetime(pd.Series(idx))
            _x_padded_range = [_idx_dt.iloc[0] - _bday, _idx_dt.iloc[-1] + _bday]'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written. The right-margin change doesn't seem to be")
        print("in the file (maybe it was never applied, or already reverted).")
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1).")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — right-margin change reverted, back to symmetric padding.")


if __name__ == "__main__":
    main()
