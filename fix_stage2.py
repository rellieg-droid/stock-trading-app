"""
One-time fix script for alpha_paper_trading.py — matches the CURRENT
verified state of the file (Stage A + B done, Stage C not yet applied:
headers are still "with thome:", "with t1:", etc.)

Run this ONCE from the project folder:  python fix_stage2.py

What it does:
- Replaces the 11 "with tX:" tab headers with "with st.container(key=...):"
  so every tab's code still runs every rerun (matching how st.tabs()
  originally behaved) — fixes functions/variables defined in one tab
  but used in another.
- Inserts the CSS block that hides inactive tab containers, right after
  "active_sub = render_top_pill(active_group)".

Safe by design: each replacement is checked to occur EXACTLY ONCE.
If anything doesn't match, the script stops and tells you exactly
which one, without touching the file.
"""

import sys

FILE = "alpha_paper_trading.py"

REPLACEMENTS = [
    ('with thome:', 'with st.container(key="tabbody_home"):'),
    ('with t1:',    'with st.container(key="tabbody_chart"):'),
    ('with t2:',    'with st.container(key="tabbody_analysis"):'),
    ('with t3:',    'with st.container(key="tabbody_backtest"):'),
    ('with t4:',    'with st.container(key="tabbody_trade"):'),
    ('with t7:',    'with st.container(key="tabbody_guide"):'),
    ('with t9:',    'with st.container(key="tabbody_compare"):'),
    ('with t10:',   'with st.container(key="tabbody_portfolio"):'),
    ('with t11:',   'with st.container(key="tabbody_alerts"):'),
    ('with t12:',   'with st.container(key="tabbody_reports"):'),
    ('with t13:',   'with st.container(key="tabbody_watchlist"):'),
]

ANCHOR = 'active_sub = render_top_pill(active_group)'

CSS_BLOCK = '''
_TAB_KEYS = ["tabbody_home", "tabbody_chart", "tabbody_analysis", "tabbody_backtest",
             "tabbody_trade", "tabbody_guide", "tabbody_compare", "tabbody_portfolio",
             "tabbody_alerts", "tabbody_reports", "tabbody_watchlist"]
_active_map = {"🏠 Home": "tabbody_home", "📈 גרף": "tabbody_chart", "🎯 ניתוח": "tabbody_analysis",
               "⏳ Backtest": "tabbody_backtest", "🛒 מסחר": "tabbody_trade", "📖 מדריך": "tabbody_guide",
               "⚖️ השוואה": "tabbody_compare", "💼 תיק": "tabbody_portfolio", "🔔 התראות": "tabbody_alerts",
               "📅 דוחות": "tabbody_reports", "👁️ Watchlist": "tabbody_watchlist"}
_active_key = _active_map.get(active_sub)
st.markdown(
    "<style>" + "\\n".join(f".st-key-{k} {{ display: none !important; }}"
                           for k in _TAB_KEYS if k != _active_key) + "</style>",
    unsafe_allow_html=True,
)
'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []

    for old, new in REPLACEMENTS:
        count = content.count(old)
        if count == 0:
            errors.append(f"NOT FOUND: {old!r}")
        elif count > 1:
            errors.append(f"FOUND {count} TIMES (expected exactly 1): {old!r}")
        else:
            content = content.replace(old, new, 1)

    if CSS_BLOCK.strip().split("\n")[0] in content:
        errors.append("CSS block already present — skipping insert to avoid duplicating it")
    else:
        anchor_count = content.count(ANCHOR)
        if anchor_count == 0:
            errors.append(f"NOT FOUND: anchor line {ANCHOR!r}")
        elif anchor_count > 1:
            errors.append(f"FOUND {anchor_count} TIMES (expected exactly 1): anchor line {ANCHOR!r}")
        else:
            content = content.replace(ANCHOR, ANCHOR + "\n" + CSS_BLOCK, 1)

    if errors:
        print("STOPPED — nothing was written. Problems found:\n")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — all 11 headers replaced, CSS visibility block inserted.")


if __name__ == "__main__":
    main()
