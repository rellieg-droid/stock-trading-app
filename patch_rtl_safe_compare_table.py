"""
patch_rtl_safe_compare_table.py
==================================
שני widgets מובנים של Streamlit (dataframe, data_editor) לא מרנדרים נכון
כותרות עברית/RTL - כותרות מתערבבות, שם הטיקר נחתך. הפאץ' הזה מחליף
אותם בטבלת HTML מותאמת אישית עם CSS אמיתי (טבלה ממורכזת, כותרות ברורות),
מחיקת שורה דרך תיבת בחירה פשוטה (לא תלויה ברינדור פנימי של widget),
וטקסט ההסבר בלבן ברור (לא אפור דהוי כמו st.caption).

שימוש:
    python patch_rtl_safe_compare_table.py            # dry-run
    python patch_rtl_safe_compare_table.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: CSS לטבלה חדשה -------------------------------------------------
CSS_OLD = (
    ".rs-btn-help {\n"
    "  display: inline-block; cursor: help; font-size: 0.78rem;\n"
    "  color: var(--c-text-2, #8B93A7); margin-bottom: 6px;\n"
    "}\n"
)
CSS_NEW = CSS_OLD + (
    ".rs-table { width:100%; border-collapse:collapse; direction:rtl; margin-top:8px; }\n"
    ".rs-table th, .rs-table td { padding:8px 10px; text-align:center; "
    "border-bottom:1px solid rgba(255,255,255,.08); white-space:nowrap; }\n"
    ".rs-table th { color: var(--c-text-2, #8B93A7); font-weight:600; font-size:.82rem; }\n"
    ".rs-table td { font-weight:600; font-size:.9rem; }\n"
    ".rs-table tr:hover td { background: rgba(255,255,255,.03); }\n"
)

# --- עוגן 2: הבלוק המלא של הטבלה, החלפה מלאה -------------------------------
OLD_BLOCK = (
    '            # --- טבלת השוואה - קומפקטית, לכל טיקר בנפרד, מחיקה מובנית בטבלה ---\n'
    '            _compare_key = f"{key_prefix}_compare_rows"\n'
    '            if _compare_key not in st.session_state:\n'
    '                st.session_state[_compare_key] = []\n'
    '\n'
    '            add_col, export_col = st.columns([1, 1])\n'
    '            with add_col:\n'
    '                add_clicked = st.button("➕ הוסף שורה", key=f"{key_prefix}_compare_add")\n'
    '            if add_clicked:\n'
    '                new_row = {\n'
    '                    "טיקר": ticker, "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,\n'
    '                    "נפח": prob_volume, "עניין פתוח": prob_oi,\n'
    '                    "Breakeven": round(breakeven, 2),\n'
    '                    "הסתברות מודל (%)": round(normal_prob * 100, 1) if normal_prob is not None else None,\n'
    '                    "מרחק (xEM)": round(em_distance, 2) if em_distance is not None else None,\n'
    '                    "נזילות": "⚠️ נמוכה" if (0 < prob_volume < 50 or 0 < prob_oi < 50) else "תקינה",\n'
    '                }\n'
    '                existing = next(\n'
    '                    (r for r in st.session_state[_compare_key]\n'
    '                     if r["טיקר"] == ticker and r["סטרייק"] == prob_K),\n'
    '                    None,\n'
    '                )\n'
    '                if existing is not None:\n'
    '                    existing.update(new_row)\n'
    '                else:\n'
    '                    st.session_state[_compare_key].append(new_row)\n'
    '\n'
    '            _rows_for_ticker = [r for r in st.session_state[_compare_key] if r["טיקר"] == ticker]\n'
    '            if _rows_for_ticker:\n'
    '                import pandas as pd\n'
    '                _df = pd.DataFrame(_rows_for_ticker).sort_values("סטרייק").reset_index(drop=True)\n'
    '                with export_col:\n'
    '                    st.download_button(\n'
    '                        "⬇️ CSV", data=_df.to_csv(index=False).encode("utf-8-sig"),\n'
    '                        file_name=f"riskshield_{ticker}.csv", mime="text/csv",\n'
    '                        key=f"{key_prefix}_compare_export",\n'
    '                    )\n'
    '                st.caption(\n'
    '                    f\'טבלת השוואה - {ticker} (לפי סטרייק, לא לפי "כדאיות"). \'\n'
    '                    "למחיקת שורה: סמני אותה בטבלה ולחצי על סמל הפח."\n'
    '                )\n'
    '                _edited = st.data_editor(\n'
    '                    _df, num_rows="dynamic", hide_index=True, use_container_width=True,\n'
    '                    key=f"{key_prefix}_compare_editor_{ticker}",\n'
    '                )\n'
    '                _other_tickers_rows = [r for r in st.session_state[_compare_key] if r["טיקר"] != ticker]\n'
    '                st.session_state[_compare_key] = _other_tickers_rows + [\n'
    '                    {**rec, "טיקר": ticker} for rec in _edited.to_dict("records")\n'
    '                ]\n'
)

NEW_BLOCK = '''            # --- טבלת השוואה - HTML מותאם אישית, בטוח ל-RTL -----------------
            _compare_key = f"{key_prefix}_compare_rows"
            if _compare_key not in st.session_state:
                st.session_state[_compare_key] = []

            add_col, export_col = st.columns([1, 1])
            with add_col:
                add_clicked = st.button("➕ הוסף שורה", key=f"{key_prefix}_compare_add")
            if add_clicked:
                new_row = {
                    "טיקר": ticker, "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,
                    "נפח": prob_volume, "עניין פתוח": prob_oi,
                    "Breakeven": round(breakeven, 2),
                    "הסתברות מודל (%)": round(normal_prob * 100, 1) if normal_prob is not None else None,
                    "מרחק (xEM)": round(em_distance, 2) if em_distance is not None else None,
                    "נזילות": "⚠️ נמוכה" if (0 < prob_volume < 50 or 0 < prob_oi < 50) else "תקינה",
                }
                existing = next(
                    (r for r in st.session_state[_compare_key]
                     if r["טיקר"] == ticker and r["סטרייק"] == prob_K),
                    None,
                )
                if existing is not None:
                    existing.update(new_row)
                else:
                    st.session_state[_compare_key].append(new_row)

            _rows_for_ticker = sorted(
                [r for r in st.session_state[_compare_key] if r["טיקר"] == ticker],
                key=lambda r: r["סטרייק"],
            )
            if _rows_for_ticker:
                import pandas as pd
                _df = pd.DataFrame(_rows_for_ticker)
                with export_col:
                    st.download_button(
                        "⬇️ CSV", data=_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"riskshield_{ticker}.csv", mime="text/csv",
                        key=f"{key_prefix}_compare_export",
                    )
                st.markdown(
                    f'<div class="rs-explain" style="margin-top:8px;">'
                    f'טבלת השוואה - {ticker} (לפי סטרייק, לא לפי "כדאיות").</div>',
                    unsafe_allow_html=True,
                )

                _cols = ["סטרייק", "פרמיה", "IV (%)", "Breakeven",
                         "הסתברות מודל (%)", "מרחק (xEM)", "נפח", "עניין פתוח", "נזילות"]
                _thead = "".join(f"<th>{c}</th>" for c in _cols)
                _trs = ""
                for r in _rows_for_ticker:
                    _tds = "".join(
                        f"<td>{r[c]:.2f}</td>" if isinstance(r.get(c), float) else f"<td>{r.get(c, '—')}</td>"
                        for c in _cols
                    )
                    _trs += f"<tr>{_tds}</tr>"
                st.markdown(
                    f'<table class="rs-table"><thead><tr>{_thead}</tr></thead>'
                    f'<tbody>{_trs}</tbody></table>',
                    unsafe_allow_html=True,
                )

                del_col1, del_col2 = st.columns([3, 1])
                with del_col1:
                    _strike_to_delete = st.selectbox(
                        "מחיקת שורה - בחרי סטרייק",
                        options=[r["סטרייק"] for r in _rows_for_ticker],
                        key=f"{key_prefix}_compare_del_select",
                    )
                with del_col2:
                    st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
                    if st.button("🗑️ מחק", key=f"{key_prefix}_compare_del_btn"):
                        st.session_state[_compare_key] = [
                            r for r in st.session_state[_compare_key]
                            if not (r["טיקר"] == ticker and r["סטרייק"] == _strike_to_delete)
                        ]
                        st.rerun()
'''


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def apply_single_anchor(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"עוגן '{label}' נמצא {count} פעמים (צריך בדיוק 1)")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    try:
        text = apply_single_anchor(text, CSS_OLD, CSS_NEW, "css")
        text = apply_single_anchor(text, OLD_BLOCK, NEW_BLOCK, "table-block")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("שני העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

    if not args.apply:
        print("Dry-run בלבד. הרץ עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(f".py.{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נוצר: {backup}")

    out_bytes = text.replace("\n", line_style).encode("utf-8")
    TARGET.write_bytes(out_bytes)
    print(f"נכתב בהצלחה: {TARGET.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
