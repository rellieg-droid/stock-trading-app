"""
patch_compact_compare_table.py
=================================
מחליף את טבלת ההשוואה (כרטיסים גדולים + כפתורי מחיקה מפוזרים) בטבלה
אמיתית קומפקטית אחת (st.data_editor) עם מחיקת שורה מובנית בטבלה עצמה
(בוחרים שורה, לוחצים על סמל הפח שכבר קיים ברכיב) - בלי כפתור נפרד
לכל שורה. כפתורי "הוסף" ו"ייצוא ל-CSV" קטנים וצמודים זה לזה למעלה,
לא כפתורים גדולים מפוזרים.

גם: הוספת אותו סטרייק פעמיים מעדכנת את השורה הקיימת במקום ליצור כפילות
(זה מה שיצר את התחושה של "יש בלבול, מחק שורה מופיע כמה פעמים").

שימוש:
    python patch_compact_compare_table.py            # dry-run
    python patch_compact_compare_table.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

OLD_BLOCK = (
    '            # --- טבלת השוואה - נפרדת לכל טיקר, כרטיסים ממורכזים ------------\n'
    '            _compare_key = f"{key_prefix}_compare_rows"\n'
    '            if _compare_key not in st.session_state:\n'
    '                st.session_state[_compare_key] = []\n'
    '            if st.button("➕ הוסף שורה לטבלת ההשוואה", key=f"{key_prefix}_compare_add"):\n'
    '                st.session_state[_compare_key].append({\n'
    '                    "טיקר": ticker, "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,\n'
    '                    "נפח": prob_volume, "עניין פתוח": prob_oi,\n'
    '                    "Breakeven": breakeven,\n'
    '                    "הסתברות מודל": normal_prob,\n'
    '                    "מרחק (Expected Moves)": em_distance,\n'
    '                })\n'
    '\n'
    '            _rows_for_ticker = [\n'
    '                (i, r) for i, r in enumerate(st.session_state[_compare_key]) if r["טיקר"] == ticker\n'
    '            ]\n'
    '            if _rows_for_ticker:\n'
    '                st.markdown(\n'
    '                    f\'<div class="rs-title" style="margin:16px 0 8px;">טבלת השוואה - {ticker} \'\n'
    '                    \'(לפי סטרייק, לא לפי "כדאיות")</div>\',\n'
    '                    unsafe_allow_html=True,\n'
    '                )\n'
    '                for orig_idx, r in sorted(_rows_for_ticker, key=lambda pair: pair[1]["סטרייק"]):\n'
    '                    liquidity_flag = (\n'
    '                        "⚠️ נמוכה" if (0 < r["נפח"] < 50 or 0 < r["עניין פתוח"] < 50) else "תקינה"\n'
    '                    )\n'
    '                    row_grid = "".join([\n'
    '                        _metric("פרמיה", f"${r[\'פרמיה\']:,.2f}"),\n'
    '                        _metric("IV", f"{r[\'IV (%)\']:.1f}%"),\n'
    '                        _metric("Breakeven", f"${r[\'Breakeven\']:,.2f}"),\n'
    '                        _metric("הסתברות מודל", f"{r[\'הסתברות מודל\']:.1%}" if r["הסתברות מודל"] is not None else "—"),\n'
    '                        _metric("מרחק", f"{r[\'מרחק (Expected Moves)\']:.2f}x" if r["מרחק (Expected Moves)"] is not None else "—"),\n'
    '                        _metric("נפח / עניין פתוח", f"{int(r[\'נפח\'])} / {int(r[\'עניין פתוח\'])}"),\n'
    '                        _metric("נזילות", liquidity_flag),\n'
    '                    ])\n'
    '                    _card(f"סטרייק {r[\'סטרייק\']:g}", f\'<div class="rs-grid">{row_grid}</div>\')\n'
    '                    if st.button("🗑️ מחק שורה זו", key=f"{key_prefix}_compare_del_{orig_idx}"):\n'
    '                        st.session_state[_compare_key].pop(orig_idx)\n'
    '                        st.rerun()\n'
    '\n'
    '                import pandas as pd\n'
    '                export_df = pd.DataFrame([r for _, r in _rows_for_ticker]).sort_values("סטרייק")\n'
    '                csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")\n'
    '                st.download_button(\n'
    '                    f"⬇️ ייצוא ל-CSV ({ticker}, נפתח באקסל)", data=csv_bytes,\n'
    '                    file_name=f"riskshield_compare_{ticker}.csv", mime="text/csv",\n'
    '                    key=f"{key_prefix}_compare_export",\n'
    '                )\n'
    '                if st.button("🗑️ נקה את כל הטבלה של " + ticker, key=f"{key_prefix}_compare_clear"):\n'
    '                    st.session_state[_compare_key] = [\n'
    '                        r for r in st.session_state[_compare_key] if r["טיקר"] != ticker\n'
    '                    ]\n'
    '                    st.rerun()\n'
)

NEW_BLOCK = '''            # --- טבלת השוואה - קומפקטית, לכל טיקר בנפרד, מחיקה מובנית בטבלה ---
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

            _rows_for_ticker = [r for r in st.session_state[_compare_key] if r["טיקר"] == ticker]
            if _rows_for_ticker:
                import pandas as pd
                _df = pd.DataFrame(_rows_for_ticker).sort_values("סטרייק").reset_index(drop=True)
                with export_col:
                    st.download_button(
                        "⬇️ CSV", data=_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"riskshield_{ticker}.csv", mime="text/csv",
                        key=f"{key_prefix}_compare_export",
                    )
                st.caption(
                    f'טבלת השוואה - {ticker} (לפי סטרייק, לא לפי "כדאיות"). '
                    "למחיקת שורה: סמני אותה בטבלה ולחצי על סמל הפח."
                )
                _edited = st.data_editor(
                    _df, num_rows="dynamic", hide_index=True, use_container_width=True,
                    key=f"{key_prefix}_compare_editor_{ticker}",
                )
                _other_tickers_rows = [r for r in st.session_state[_compare_key] if r["טיקר"] != ticker]
                st.session_state[_compare_key] = _other_tickers_rows + [
                    {**rec, "טיקר": ticker} for rec in _edited.to_dict("records")
                ]
'''


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    count = text.count(OLD_BLOCK)
    if count != 1:
        print(f"עוגן נמצא {count} פעמים (צריך בדיוק 1). לא בוצע שינוי.")
        return 1

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("עוגן נמצא פעם אחת. ast.parse עבר בהצלחה.")

    if not args.apply:
        print("Dry-run בלבד. הרץ עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(f".py.{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נוצר: {backup}")

    out_bytes = new_text.replace("\n", line_style).encode("utf-8")
    TARGET.write_bytes(out_bytes)
    print(f"נכתב בהצלחה: {TARGET.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
