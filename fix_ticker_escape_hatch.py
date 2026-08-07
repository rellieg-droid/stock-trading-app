"""
Emergency fix — adds clickable ticker buttons directly on the "couldn't
load data" error screen. Root cause found: the ticker search box sits
AFTER the data-load-and-st.stop() block in the script, so whenever the
CURRENT ticker fails to load, the app halts before the search box code
ever runs — leaving no way to switch tickers through the UI. This adds
working buttons right on the error screen itself as an immediate
escape hatch, using the same st.stop() location.
Run from the project folder:  python fix_ticker_escape_hatch.py
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''# Error state
if df is None:
    st.markdown(
        f'<div style="text-align:center;padding:60px 20px;">'
        f'<div style="font-size:3rem;">⚠️</div>'
        f'<div style="font-size:1.2rem;font-weight:600;color:#e6edf3;margin:10px 0;">'
        f'לא ניתן לטעון נתונים עבור \\'{ticker}\\'</div>'
        f'<div style="color:#8b949e;">בדקי שהסימול נכון ונסי שוב</div>'
        f'</div>', unsafe_allow_html=True
    )
    st.info("💡 נסי: AAPL · TSLA · MSFT · GOOGL · NVDA · TEVA · CHKP")
    st.stop()'''

NEW_BLOCK = '''# Error state
if df is None:
    st.markdown(
        f'<div style="text-align:center;padding:60px 20px;">'
        f'<div style="font-size:3rem;">⚠️</div>'
        f'<div style="font-size:1.2rem;font-weight:600;color:#e6edf3;margin:10px 0;">'
        f'לא ניתן לטעון נתונים עבור \\'{ticker}\\'</div>'
        f'<div style="color:#8b949e;">בדקי שהסימול נכון ונסי שוב, או בחרי טיקר למטה</div>'
        f'</div>', unsafe_allow_html=True
    )
    st.info("💡 בעיה זמנית מול Yahoo Finance קורית לפעמים. לחיצה על אחד מהכפתורים מטה מנסה טיקר אחר:")
    _esc_cols = st.columns(7)
    for _esc_sym, _esc_col in zip(["AAPL", "TSLA", "MSFT", "GOOGL", "NVDA", "TEVA", "CHKP.TA"], _esc_cols):
        with _esc_col:
            if st.button(_esc_sym, key=f"esc_{_esc_sym}", use_container_width=True):
                st.session_state.ticker = _esc_sym
                st.rerun()
    st.stop()'''


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

    print("SUCCESS — emergency ticker buttons added to the error screen.")


if __name__ == "__main__":
    main()
