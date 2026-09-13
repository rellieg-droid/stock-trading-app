"""
patch_fix_compare_table_timing.py
====================================
מתקן באג תזמון: בלוק התצוגה של טבלת ההשוואה (כולל מחיקה וייצוא) קרא
את הרשימה *לפני* שהשורה הממתינה (Fat-tail/RV Rank) נבנתה בפועל באותה
ריצה - מה שגרם לטבלה "לפגר" ריצה אחת מאחורי הלחיצה על "הוסף שורה".

הפתרון: מעבירים את כל בלוק התצוגה (סינון לפי טיקר, טבלת HTML, מחיקה,
ייצוא) למקום אחרי שהשורה הממתינה כבר נבנתה - כך שהתצוגה תמיד עדכנית
לאותה ריצה בדיוק.

שימוש:
    python patch_fix_compare_table_timing.py            # dry-run
    python patch_fix_compare_table_timing.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: הסרת בלוק התצוגה מהמקום הישן (אחרי הכפתור, לפני סטרס טסט) ---
OLD_DISPLAY_BLOCK = (
    '\n'
    '            _rows_for_ticker = sorted(\n'
    '                [r for r in st.session_state[_compare_key] if r["טיקר"] == ticker],\n'
    '                key=lambda r: r["סטרייק"],\n'
    '            )\n'
    '            if _rows_for_ticker:\n'
    '                import pandas as pd\n'
    '                _df = pd.DataFrame(_rows_for_ticker)\n'
    '                with export_col:\n'
    '                    st.download_button(\n'
    '                        "⬇️ CSV", data=_df.to_csv(index=False).encode("utf-8-sig"),\n'
    '                        file_name=f"riskshield_{ticker}.csv", mime="text/csv",\n'
    '                        key=f"{key_prefix}_compare_export",\n'
    '                    )\n'
    '                st.markdown(\n'
    '                    f\'<div class="rs-explain" style="margin-top:8px;">\'\n'
    '                    f\'טבלת השוואה - {ticker} (לפי סטרייק, לא לפי "כדאיות").</div>\',\n'
    '                    unsafe_allow_html=True,\n'
    '                )\n'
    '\n'
    '                _metric_rows = [\n'
    '                    ("פרמיה", lambda r: f"${r[\'פרמיה\']:.2f}"),\n'
    '                    ("IV (%)", lambda r: f"{r[\'IV (%)\']:.1f}%"),\n'
    '                    ("הסתברות מודל OTM", lambda r: (\n'
    '                        f"{r[\'הסתברות מודל (%)\']:.1f}%" if r["הסתברות מודל (%)"] is not None else "—"\n'
    '                    )),\n'
    '                    ("הסתברות Fat-tail OTM", lambda r: (\n'
    '                        f"{r.get(\'Fat-tail (%)\'):.1f}%" if r.get("Fat-tail (%)") is not None else "—"\n'
    '                    )),\n'
    '                    ("RV Rank", lambda r: (\n'
    '                        f"{r.get(\'RV Rank\'):.0f}" if r.get("RV Rank") is not None else "—"\n'
    '                    )),\n'
    '                    ("Breakeven", lambda r: f"${r[\'Breakeven\']:.2f}"),\n'
    '                    ("מרחק (xEM)", lambda r: (\n'
    '                        f"{r[\'מרחק (xEM)\']:.2f}x" if r["מרחק (xEM)"] is not None else "—"\n'
    '                    )),\n'
    '                    ("עניין פתוח / נפח", lambda r: (\n'
    '                        f"{\'✅\' if r[\'נזילות\'] == \'תקינה\' else \'⚠️\'} "\n'
    '                        f"{int(r[\'עניין פתוח\'])} / {int(r[\'נפח\'])}"\n'
    '                    )),\n'
    '                ]\n'
    '                _thead = "<th></th>" + "".join(\n'
    '                    f"<th>סטרייק {r[\'סטרייק\']:g}</th>" for r in _rows_for_ticker\n'
    '                )\n'
    '                _trs = ""\n'
    '                for _label, _fmt in _metric_rows:\n'
    '                    _tds = "".join(f"<td>{_fmt(r)}</td>" for r in _rows_for_ticker)\n'
    '                    _trs += f"<tr><td>{_label}</td>{_tds}</tr>"\n'
    '                st.markdown(\n'
    '                    f\'<table class="rs-table"><thead><tr>{_thead}</tr></thead>\'\n'
    '                    f\'<tbody>{_trs}</tbody></table>\',\n'
    '                    unsafe_allow_html=True,\n'
    '                )\n'
    '\n'
    '                del_col1, del_col2 = st.columns([3, 1])\n'
    '                with del_col1:\n'
    '                    _strike_to_delete = st.selectbox(\n'
    '                        "מחיקת שורה - בחרי סטרייק",\n'
    '                        options=[r["סטרייק"] for r in _rows_for_ticker],\n'
    '                        key=f"{key_prefix}_compare_del_select",\n'
    '                    )\n'
    '                with del_col2:\n'
    '                    st.markdown(\'<div style="height:28px;"></div>\', unsafe_allow_html=True)\n'
    '                    if st.button("🗑️ מחק", key=f"{key_prefix}_compare_del_btn"):\n'
    '                        st.session_state[_compare_key] = [\n'
    '                            r for r in st.session_state[_compare_key]\n'
    '                            if not (r["טיקר"] == ticker and r["סטרייק"] == _strike_to_delete)\n'
    '                        ]\n'
    '                        st.rerun()\n'
    '\n'
    '            # --- סטרס טסט - תרחישי % קבועים, לא תלוי בהיסטוריה --------------\n'
)
NEW_AFTER_REMOVAL = (
    '\n'
    '            # --- סטרס טסט - תרחישי % קבועים, לא תלוי בהיסטוריה --------------\n'
)

# --- עוגן 2: הוספת בלוק התצוגה במקום החדש - אחרי בניית השורה הממתינה ------
BUILD_ROW_END_OLD = (
    '                st.session_state[f"{key_prefix}_compare_pending"] = False\n'
    '\n'
    '            # --- פערי מודלים - עובדה, לא ציון ------------------------------\n'
)
BUILD_ROW_END_NEW = (
    '                st.session_state[f"{key_prefix}_compare_pending"] = False\n'
    '\n'
    '            _rows_for_ticker = sorted(\n'
    '                [r for r in st.session_state[_compare_key] if r["טיקר"] == ticker],\n'
    '                key=lambda r: r["סטרייק"],\n'
    '            )\n'
    '            if _rows_for_ticker:\n'
    '                import pandas as pd\n'
    '                _df = pd.DataFrame(_rows_for_ticker)\n'
    '                with export_col:\n'
    '                    st.download_button(\n'
    '                        "⬇️ CSV", data=_df.to_csv(index=False).encode("utf-8-sig"),\n'
    '                        file_name=f"riskshield_{ticker}.csv", mime="text/csv",\n'
    '                        key=f"{key_prefix}_compare_export",\n'
    '                    )\n'
    '                st.markdown(\n'
    '                    f\'<div class="rs-explain" style="margin-top:8px;">\'\n'
    '                    f\'טבלת השוואה - {ticker} (לפי סטרייק, לא לפי "כדאיות").</div>\',\n'
    '                    unsafe_allow_html=True,\n'
    '                )\n'
    '\n'
    '                _metric_rows = [\n'
    '                    ("פרמיה", lambda r: f"${r[\'פרמיה\']:.2f}"),\n'
    '                    ("IV (%)", lambda r: f"{r[\'IV (%)\']:.1f}%"),\n'
    '                    ("הסתברות מודל OTM", lambda r: (\n'
    '                        f"{r[\'הסתברות מודל (%)\']:.1f}%" if r["הסתברות מודל (%)"] is not None else "—"\n'
    '                    )),\n'
    '                    ("הסתברות Fat-tail OTM", lambda r: (\n'
    '                        f"{r.get(\'Fat-tail (%)\'):.1f}%" if r.get("Fat-tail (%)") is not None else "—"\n'
    '                    )),\n'
    '                    ("RV Rank", lambda r: (\n'
    '                        f"{r.get(\'RV Rank\'):.0f}" if r.get("RV Rank") is not None else "—"\n'
    '                    )),\n'
    '                    ("Breakeven", lambda r: f"${r[\'Breakeven\']:.2f}"),\n'
    '                    ("מרחק (xEM)", lambda r: (\n'
    '                        f"{r[\'מרחק (xEM)\']:.2f}x" if r["מרחק (xEM)"] is not None else "—"\n'
    '                    )),\n'
    '                    ("עניין פתוח / נפח", lambda r: (\n'
    '                        f"{\'✅\' if r[\'נזילות\'] == \'תקינה\' else \'⚠️\'} "\n'
    '                        f"{int(r[\'עניין פתוח\'])} / {int(r[\'נפח\'])}"\n'
    '                    )),\n'
    '                ]\n'
    '                _thead = "<th></th>" + "".join(\n'
    '                    f"<th>סטרייק {r[\'סטרייק\']:g}</th>" for r in _rows_for_ticker\n'
    '                )\n'
    '                _trs = ""\n'
    '                for _label, _fmt in _metric_rows:\n'
    '                    _tds = "".join(f"<td>{_fmt(r)}</td>" for r in _rows_for_ticker)\n'
    '                    _trs += f"<tr><td>{_label}</td>{_tds}</tr>"\n'
    '                st.markdown(\n'
    '                    f\'<table class="rs-table"><thead><tr>{_thead}</tr></thead>\'\n'
    '                    f\'<tbody>{_trs}</tbody></table>\',\n'
    '                    unsafe_allow_html=True,\n'
    '                )\n'
    '\n'
    '                del_col1, del_col2 = st.columns([3, 1])\n'
    '                with del_col1:\n'
    '                    _strike_to_delete = st.selectbox(\n'
    '                        "מחיקת שורה - בחרי סטרייק",\n'
    '                        options=[r["סטרייק"] for r in _rows_for_ticker],\n'
    '                        key=f"{key_prefix}_compare_del_select",\n'
    '                    )\n'
    '                with del_col2:\n'
    '                    st.markdown(\'<div style="height:28px;"></div>\', unsafe_allow_html=True)\n'
    '                    if st.button("🗑️ מחק", key=f"{key_prefix}_compare_del_btn"):\n'
    '                        st.session_state[_compare_key] = [\n'
    '                            r for r in st.session_state[_compare_key]\n'
    '                            if not (r["טיקר"] == ticker and r["סטרייק"] == _strike_to_delete)\n'
    '                        ]\n'
    '                        st.rerun()\n'
    '\n'
    '            # --- פערי מודלים - עובדה, לא ציון ------------------------------\n'
)


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
        text = apply_single_anchor(text, OLD_DISPLAY_BLOCK, NEW_AFTER_REMOVAL, "remove-old-display")
        text = apply_single_anchor(text, BUILD_ROW_END_OLD, BUILD_ROW_END_NEW, "add-new-display")
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
