"""
patch_add_screener_tab.py
===========================
מוסיפה טאב חמישי ל-RiskShield: "סורק רב-מניות". שני שינויים בקובץ אחד
(שני אנקורים נפרדים, כל אחד מאומת בנפרד לפני שנוגעים בקובץ):

1. הוספת tab_screener לרשימת הטאבים הקיימת.
2. גוף הטאב - קלט טיקרים, דלתא/DTE, כפתור סריקה, טבלת HTML (לא
   st.dataframe - הוא לא מכבד RTL/CSS variables, בדיוק כמו טבלת
   ההשוואה הקיימת בקובץ), עם מיון וסינון בסיסי (RV Rank, הסתרת נכשלים).

put_premium בטבלה תיאורטי (Black-Scholes) - כבר מוצהר ב-note של כל שורה.

שימוש:
    python patch_add_screener_tab.py                 # dry-run
    python patch_add_screener_tab.py --apply          # מבצע בפועל
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR_1 = (
    '    tab_bs, tab_iv, tab_rv, tab_prob = st.tabs(\n'
    '        ["מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)", "הסתברות OTM (Put)"]\n'
    '    )\n'
)
NEW_1 = (
    '    tab_bs, tab_iv, tab_rv, tab_prob, tab_screener = st.tabs(\n'
    '        ["מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)", '
    '"הסתברות OTM (Put)", "סורק רב-מניות"]\n'
    '    )\n'
)

ANCHOR_2 = (
    '            _card("טבלת הגנה", f\'<div class="rs-grid">{"".join(grid_prot)}</div>{prot_explain}\')\n'
    '\n'
    '    st.markdown(\'</div>\', unsafe_allow_html=True)\n'
)

NEW_2_BLOCK = '''            _card("טבלת הגנה", f'<div class="rs-grid">{"".join(grid_prot)}</div>{prot_explain}')

    with tab_screener:
        st.markdown(
            '<div class="rs-explain" style="margin-bottom:12px;">'
            'מריץ את המודל, ההסתברויות, ה-CVaR וה-RV Rank על רשימת טיקרים בבת אחת, '
            'בדלתא יעד אחידה לכולם (כך ההשוואה בין מניות שונות הוגנת - אותו "עומק" '
            'יחסי, לא סטרייק דולרי קבוע). פרמיית הפוט בטבלה תיאורטית (Black-Scholes), '
            'לא מחיר שוק בפועל.'
            '</div>',
            unsafe_allow_html=True,
        )

        scr_tickers_raw = st.text_area(
            "טיקרים (מופרדים בפסיק או בשורות נפרדות)",
            value="AAPL, MSFT, NVDA",
            key=f"{key_prefix}_scr_tickers",
        )
        scr_cols = st.columns(3)
        with scr_cols[0]:
            scr_delta = st.number_input(
                "דלתא יעד לפוט", min_value=0.05, max_value=0.50, value=0.20, step=0.05,
                key=f"{key_prefix}_scr_delta",
                help="דלתא אחידה לכל הטיקרים - סטרייק שונה לכל מניה, אבל אותו 'עומק' יחסי.",
            )
        with scr_cols[1]:
            scr_dte = st.number_input(
                "ימים לפקיעה", min_value=1, value=30, key=f"{key_prefix}_scr_dte",
            )
        with scr_cols[2]:
            scr_period = st.selectbox(
                "עומק היסטוריה (RV/CVaR)", ["5y", "10y", "max"], index=1,
                key=f"{key_prefix}_scr_period",
            )

        _scr_key = f"{key_prefix}_scr_results"
        if st.button("🔍 סרוק", key=f"{key_prefix}_scr_run"):
            raw_list = [t for chunk in scr_tickers_raw.split("\\n") for t in chunk.split(",")]
            with st.spinner("סורקת..."):
                st.session_state[_scr_key] = _run_screener(
                    raw_list, target_put_delta=scr_delta,
                    dte_days=int(scr_dte), closes_period=scr_period,
                )

        if _scr_key in st.session_state:
            import pandas as pd
            scr_df = st.session_state[_scr_key]
            if scr_df.empty:
                st.info("לא הוזנו טיקרים תקינים.")
            else:
                filt_cols = st.columns(2)
                with filt_cols[0]:
                    hide_failed = st.checkbox(
                        "הסתר טיקרים שנכשלו", value=True, key=f"{key_prefix}_scr_hide_failed",
                    )
                with filt_cols[1]:
                    rv_range = st.slider(
                        "RV Rank (טווח)", 0, 100, (0, 100), key=f"{key_prefix}_scr_rv_range",
                        help="מסנן לפי rv_rank. טיקרים ללא ערך (למשל נכשלו) לא מודרים בגלל הטווח.",
                    )

                scr_view = scr_df.copy()
                if hide_failed and "strike" in scr_view.columns:
                    scr_view = scr_view[scr_view["strike"].notna()]
                if "rv_rank" in scr_view.columns:
                    scr_view = scr_view[
                        scr_view["rv_rank"].isna()
                        | scr_view["rv_rank"].between(rv_range[0], rv_range[1])
                    ]

                _sortable = [c for c in [
                    "ticker", "spot", "strike", "iv", "rv_rank", "rv_percentile",
                    "iv_rv_spread", "expected_move_pct", "put_premium", "put_delta",
                    "breakeven", "prob_otm_model", "prob_otm_fat_tail",
                    "prob_otm_historical", "xem_distance", "cvar_5pct", "max_loss",
                ] if c in scr_view.columns]
                sort_ui = st.columns([2, 1])
                with sort_ui[0]:
                    sort_by = st.selectbox("מיין לפי", _sortable, index=0, key=f"{key_prefix}_scr_sort_by")
                with sort_ui[1]:
                    sort_desc = st.checkbox("יורד", value=False, key=f"{key_prefix}_scr_sort_desc")
                scr_view = scr_view.sort_values(sort_by, ascending=not sort_desc, na_position="last")

                st.download_button(
                    "⬇️ CSV", data=scr_view.to_csv(index=False).encode("utf-8-sig"),
                    file_name="riskshield_screener.csv", mime="text/csv",
                    key=f"{key_prefix}_scr_export",
                )

                _scr_headers = {
                    "ticker": "טיקר", "spot": "מחיר", "strike": "סטרייק", "iv": "IV",
                    "rv_rank": "RV Rank", "rv_percentile": "RV %", "iv_rv_spread": "IV-RV",
                    "expected_move_pct": "EM %", "put_premium": "פרמיה", "put_delta": "דלתא",
                    "breakeven": "Breakeven", "prob_otm_model": "OTM מודל",
                    "prob_otm_fat_tail": "OTM Fat-tail", "prob_otm_historical": "OTM היסטורי",
                    "xem_distance": "xEM", "cvar_5pct": "CVaR", "max_loss": "Max Loss",
                    "note": "הערה",
                }
                _shown = [c for c in _scr_headers if c in scr_view.columns]
                _thead = "".join(f"<th>{_scr_headers[c]}</th>" for c in _shown)

                def _scr_fmt(col, val):
                    if val is None or (isinstance(val, float) and pd.isna(val)):
                        return "—"
                    if col in ("spot", "strike", "put_premium", "breakeven", "cvar_5pct", "max_loss"):
                        return f"${val:,.2f}"
                    if col in ("iv", "expected_move_pct", "prob_otm_model",
                               "prob_otm_fat_tail", "prob_otm_historical"):
                        return f"{val:.1%}"
                    if col in ("rv_rank", "rv_percentile"):
                        return f"{val:.0f}"
                    if col == "iv_rv_spread":
                        return f"{val:+.1%}"
                    if col in ("put_delta", "xem_distance"):
                        return f"{val:.2f}"
                    return str(val)

                _trs = ""
                for _, _r in scr_view.iterrows():
                    _tds = "".join(f"<td>{_scr_fmt(c, _r.get(c))}</td>" for c in _shown)
                    _trs += f"<tr>{_tds}</tr>"

                st.markdown(
                    f'<div style="overflow-x:auto;"><table class="rs-table">'
                    f'<thead><tr>{_thead}</tr></thead><tbody>{_trs}</tbody></table></div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"{len(scr_view)} מתוך {len(scr_df)} טיקרים מוצגים.")

    st.markdown('</div>', unsafe_allow_html=True)
'''


def _apply_edit(text: str, anchor: str, new_block: str, label: str) -> str:
    count = text.count(anchor)
    if count == 0:
        print(f"[{label}] האנקור לא נמצא. עוצר בלי לגעת בקובץ.", file=sys.stderr)
        sys.exit(1)
    if count > 1:
        print(f"[{label}] האנקור נמצא {count} פעמים - לא ייחודי, עוצר.", file=sys.stderr)
        sys.exit(1)
    return text.replace(anchor, new_block, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="מבצע בפועל. בלי הדגל הזה - dry-run בלבד.")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} בתיקייה הנוכחית.", file=sys.stderr)
        return 1

    raw = TARGET.read_bytes()
    used_crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")

    text = _apply_edit(text, ANCHOR_1.replace("\r\n", "\n"), NEW_1.replace("\r\n", "\n"), "1/2 - רשימת טאבים")
    text = _apply_edit(text, ANCHOR_2.replace("\r\n", "\n"), NEW_2_BLOCK.replace("\r\n", "\n"), "2/2 - גוף הטאב")

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת תחביר בקוד החדש: {e}", file=sys.stderr)
        return 1

    print("שני האנקורים נמצאו ותוקנו בהצלחה. שני העריכות עברו ast.parse.")

    if not args.apply:
        print("\nDry-run בלבד. הריצי עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(TARGET.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נשמר: {backup}")

    out_text = text.replace("\n", "\r\n") if used_crlf else text
    TARGET.write_bytes(out_text.encode("utf-8"))
    print(f"בוצע. {TARGET} עודכן.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
