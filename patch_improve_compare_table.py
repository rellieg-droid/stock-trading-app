"""
patch_improve_compare_table.py
=================================
משפר את טבלת ההשוואה מהפאץ' הקודם, לפי הבקשות:

1. לכל טיקר טבלה נפרדת משלו - שורות עכשיו מתויגות בטיקר, והתצוגה
   מסננת רק לטיקר הנוכחי. אין יותר ערבוב בין מניות שונות.
2. הטבלה זזה למיקום מתחת ל"תזוזה צפויה" (Expected Move), לפני הסטרס
   טסט - כפי שביקשת.
3. תצוגה ככרטיסים ממורכזים (rs-card/rs-grid, אותה שפה עיצובית שכבר
   עובדת בכל שאר האפליקציה) במקום טבלת st.dataframe - פותר את בעיית
   היישור/הריכוז שלא עבדה טוב ב-RTL.
4. כפתור מחיקה לכל שורה בנפרד (לא רק "נקה הכל").
5. כפתור ייצוא ל-CSV (נפתח ישירות באקסל) לטיקר הנוכחי.

שימוש:
    python patch_improve_compare_table.py            # dry-run
    python patch_improve_compare_table.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: הכנסת "הוסף שורה" + תצוגה, מייד אחרי כרטיס Expected Move ----
INSERT_AFTER_OLD = (
    "            _card(\"תזוזה צפויה (Expected Move)\", f'<div class=\"rs-grid\">{grid_em}</div>{em_explain}')\n"
)
INSERT_AFTER_NEW = INSERT_AFTER_OLD + '''
            # --- טבלת השוואה - נפרדת לכל טיקר, כרטיסים ממורכזים ------------
            _compare_key = f"{key_prefix}_compare_rows"
            if _compare_key not in st.session_state:
                st.session_state[_compare_key] = []
            if st.button("➕ הוסף שורה לטבלת ההשוואה", key=f"{key_prefix}_compare_add"):
                st.session_state[_compare_key].append({
                    "טיקר": ticker, "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,
                    "נפח": prob_volume, "עניין פתוח": prob_oi,
                    "Breakeven": breakeven,
                    "הסתברות מודל": normal_prob,
                    "מרחק (Expected Moves)": em_distance,
                })

            _rows_for_ticker = [
                (i, r) for i, r in enumerate(st.session_state[_compare_key]) if r["טיקר"] == ticker
            ]
            if _rows_for_ticker:
                st.markdown(
                    f'<div class="rs-title" style="margin:16px 0 8px;">טבלת השוואה - {ticker} '
                    '(לפי סטרייק, לא לפי "כדאיות")</div>',
                    unsafe_allow_html=True,
                )
                for orig_idx, r in sorted(_rows_for_ticker, key=lambda pair: pair[1]["סטרייק"]):
                    liquidity_flag = (
                        "⚠️ נמוכה" if (0 < r["נפח"] < 50 or 0 < r["עניין פתוח"] < 50) else "תקינה"
                    )
                    row_grid = "".join([
                        _metric("פרמיה", f"${r['פרמיה']:,.2f}"),
                        _metric("IV", f"{r['IV (%)']:.1f}%"),
                        _metric("Breakeven", f"${r['Breakeven']:,.2f}"),
                        _metric("הסתברות מודל", f"{r['הסתברות מודל']:.1%}" if r["הסתברות מודל"] is not None else "—"),
                        _metric("מרחק", f"{r['מרחק (Expected Moves)']:.2f}x" if r["מרחק (Expected Moves)"] is not None else "—"),
                        _metric("נפח / עניין פתוח", f"{int(r['נפח'])} / {int(r['עניין פתוח'])}"),
                        _metric("נזילות", liquidity_flag),
                    ])
                    _card(f"סטרייק {r['סטרייק']:g}", f'<div class="rs-grid">{row_grid}</div>')
                    if st.button("🗑️ מחק שורה זו", key=f"{key_prefix}_compare_del_{orig_idx}"):
                        st.session_state[_compare_key].pop(orig_idx)
                        st.rerun()

                import pandas as pd
                export_df = pd.DataFrame([r for _, r in _rows_for_ticker]).sort_values("סטרייק")
                csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    f"⬇️ ייצוא ל-CSV ({ticker}, נפתח באקסל)", data=csv_bytes,
                    file_name=f"riskshield_compare_{ticker}.csv", mime="text/csv",
                    key=f"{key_prefix}_compare_export",
                )
                if st.button("🗑️ נקה את כל הטבלה של " + ticker, key=f"{key_prefix}_compare_clear"):
                    st.session_state[_compare_key] = [
                        r for r in st.session_state[_compare_key] if r["טיקר"] != ticker
                    ]
                    st.rerun()
'''

# --- עוגן 2: הסרת כפתור "הוסף שורה" הישן (אחרי badge פערי המודלים) -------
REMOVE_OLD_BUTTON_OLD = (
    "\n"
    '            _compare_key = f"{key_prefix}_compare_rows"\n'
    '            if _compare_key not in st.session_state:\n'
    '                st.session_state[_compare_key] = []\n'
    '            if st.button("➕ הוסף שורה לטבלת ההשוואה", key=f"{key_prefix}_compare_add"):\n'
    '                st.session_state[_compare_key].append({\n'
    '                    "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,\n'
    '                    "נפח": prob_volume, "עניין פתוח": prob_oi,\n'
    '                    "Breakeven": breakeven,\n'
    '                    "הסתברות מודל": normal_prob,\n'
    '                    "מרחק (Expected Moves)": em_distance,\n'
    '                })\n'
)
REMOVE_OLD_BUTTON_NEW = "\n"

# --- עוגן 3: הסרת התצוגה הישנה (הטבלה בתחתית, אחרי ה-hr) -----------------
REMOVE_OLD_DISPLAY_OLD = (
    '        if st.session_state.get(f"{key_prefix}_compare_rows"):\n'
    '            st.markdown(\'<div class="rs-title" style="margin-bottom:8px;">טבלת השוואה (לפי סטרייק, לא לפי \\"כדאיות\\")</div>\', unsafe_allow_html=True)\n'
    '            import pandas as pd\n'
    '            rows = st.session_state[f"{key_prefix}_compare_rows"]\n'
    '            df = pd.DataFrame(rows).sort_values("סטרייק").reset_index(drop=True)\n'
    '            df["הסתברות מודל"] = df["הסתברות מודל"].map(lambda v: f"{v:.1%}" if v is not None else "—")\n'
    '            df["מרחק (Expected Moves)"] = df["מרחק (Expected Moves)"].map(lambda v: f"{v:.2f}x" if v is not None else "—")\n'
    '            df["נזילות"] = [\n'
    '                "⚠️ נמוכה" if (0 < r["נפח"] < 50 or 0 < r["עניין פתוח"] < 50) else "—"\n'
    '                for _, r in df.iterrows()\n'
    '            ]\n'
    '            st.dataframe(df, use_container_width=True, hide_index=True)\n'
    '            if st.button("🗑️ נקה טבלה", key=f"{key_prefix}_compare_clear"):\n'
    '                st.session_state[f"{key_prefix}_compare_rows"] = []\n'
    '                st.rerun()\n'
)
REMOVE_OLD_DISPLAY_NEW = ""


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
        text = apply_single_anchor(text, INSERT_AFTER_OLD, INSERT_AFTER_NEW, "insert-new-table")
        text = apply_single_anchor(text, REMOVE_OLD_BUTTON_OLD, REMOVE_OLD_BUTTON_NEW, "remove-old-button")
        text = apply_single_anchor(text, REMOVE_OLD_DISPLAY_OLD, REMOVE_OLD_DISPLAY_NEW, "remove-old-display")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("כל שלושת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
