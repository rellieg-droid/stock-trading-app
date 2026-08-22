#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_gap_span_selectbox.py

מטרה: מחליף את ה-slider "טווח פערים לבדיקה (%)" ב-selectbox עם ערכים
קבועים (5..40 בקפיצות 5), ומחזיר אותו לאותה שורה עם "מחיר סגירה לפני
הדוח" (במקום השורה הנפרדת שנוצרה בפאץ' הקודם, patch_fix_gap_slider_overlap.py).

למה: ה-slider גרם לבועה הצפה מעל הידית לחשב מיקום שגוי ולפלוש לתיבת
הקלט השכנה בעמודה צרה (Streamlit, אומת ב-repro - לא קשור ל-CSS RTL).
selectbox לא סובל מהבעיה הזו כלל (אין בועה צפה), ותמיד מציג את הערך
הנבחר בבירור - כך שאפשר לחזור לפריסה הצפופה בלי הבאג, וגם בלי הצורך
לגרור כדי לראות איזה ערך נבחר.

שימוש:
    python patch_gap_span_selectbox.py                 # dry-run (ברירת מחדל)
    python patch_gap_span_selectbox.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: rr_tab.py (LF)
דורש: patch_fix_gap_slider_overlap.py כבר הורץ (--apply) קודם.
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    "    if interactive:\n"
    "        ref_price = st.number_input(\n"
    '            "\u05de\u05d7\u05d9\u05e8 \u05e1\u05d2\u05d9\u05e8\u05d4 \u05dc\u05e4\u05e0\u05d9 \u05d4\u05d3\u05d5\u05d7", min_value=0.01, value=float(plan.entry),\n'
    '            step=0.01, format="%.2f", key=f"{key_prefix}_ref",\n'
    '            help="\u05e9\u05e0\u05d9 \u05d0\u05dd \u05d4\u05e4\u05d5\u05d6\u05d9\u05e6\u05d9\u05d4 \u05db\u05d1\u05e8 \u05d1\u05e8\u05d5\u05d5\u05d7 \u2014 \u05d4\u05e4\u05e2\u05e8 \u05e0\u05de\u05d3\u05d3 \u05de\u05d4\u05e1\u05d2\u05d9\u05e8\u05d4, \u05dc\u05d0 \u05de\u05d4\u05db\u05e0\u05d9\u05e1\u05d4.")\n'
    "        # \u05d4-slider \u05de\u05e7\u05d1\u05dc \u05e9\u05d5\u05e8\u05d4 \u05e0\u05e4\u05e8\u05d3\u05ea \u05d1\u05e8\u05d5\u05d7\u05d1 \u05de\u05dc\u05d0 \u05d1\u05db\u05d5\u05d5\u05e0\u05d4: \u05db\u05e9\u05d4\u05d5\u05d0 \u05d4\u05d9\u05d4\n"
    "        # \u05d1-st.columns(2) \u05dc\u05e6\u05d3 number_input, \u05d4\u05d1\u05d5\u05e2\u05d4 \u05d4\u05e6\u05e4\u05d4 \u05de\u05e2\u05dc \u05d4\u05d9\u05d3\u05d9\u05ea\n"
    "        # \u05d7\u05d9\u05e9\u05d1\u05d4 \u05de\u05d9\u05e7\u05d5\u05dd \u05dc\u05e4\u05d9 \u05d4\u05e8\u05d5\u05d7\u05d1 \u05d4\u05e6\u05e8 \u05e9\u05dc \u05d4\u05e2\u05de\u05d5\u05d3\u05d4 \u05d5\u05e4\u05dc\u05e9\u05d4 \u05d7\u05d6\u05d5\u05ea\u05d9\u05ea \u05dc\u05ea\u05d9\u05d1\u05ea\n"
    "        # \u05d4\u05e7\u05dc\u05d8 \u05d4\u05e9\u05db\u05e0\u05d4 (Streamlit, \u05dc\u05d0 \u05e7\u05e9\u05d5\u05e8 \u05dc-CSS \u05e9\u05dc RTL - \u05d0\u05d5\u05de\u05ea \u05d1-repro).\n"
    '        span = st.slider("\u05d8\u05d5\u05d5\u05d7 \u05e4\u05e2\u05e8\u05d9\u05dd \u05dc\u05d1\u05d3\u05d9\u05e7\u05d4 (%)", 5, 40, 20, 5,\n'
    '                         key=f"{key_prefix}_span")\n'
)

NEW_BLOCK = (
    "    if interactive:\n"
    "        i1, i2 = st.columns(2)\n"
    "        ref_price = i1.number_input(\n"
    '            "\u05de\u05d7\u05d9\u05e8 \u05e1\u05d2\u05d9\u05e8\u05d4 \u05dc\u05e4\u05e0\u05d9 \u05d4\u05d3\u05d5\u05d7", min_value=0.01, value=float(plan.entry),\n'
    '            step=0.01, format="%.2f", key=f"{key_prefix}_ref",\n'
    '            help="\u05e9\u05e0\u05d9 \u05d0\u05dd \u05d4\u05e4\u05d5\u05d6\u05d9\u05e6\u05d9\u05d4 \u05db\u05d1\u05e8 \u05d1\u05e8\u05d5\u05d5\u05d7 \u2014 \u05d4\u05e4\u05e2\u05e8 \u05e0\u05de\u05d3\u05d3 \u05de\u05d4\u05e1\u05d2\u05d9\u05e8\u05d4, \u05dc\u05d0 \u05de\u05d4\u05db\u05e0\u05d9\u05e1\u05d4.")\n'
    "        # selectbox \u05d5\u05dc\u05d0 slider \u05d1\u05db\u05d5\u05d5\u05e0\u05d4: \u05dc-st.slider \u05d9\u05e9 \u05d1\u05d5\u05e2\u05d4 \u05e6\u05e4\u05d4 \u05de\u05e2\u05dc\n"
    "        # \u05d4\u05d9\u05d3\u05d9\u05ea \u05e9\u05d7\u05d9\u05e9\u05d1\u05d4 \u05de\u05d9\u05e7\u05d5\u05dd \u05dc\u05e4\u05d9 \u05d4\u05e8\u05d5\u05d7\u05d1 \u05d4\u05e6\u05e8 \u05e9\u05dc \u05d4\u05e2\u05de\u05d5\u05d3\u05d4 \u05d5\u05e4\u05dc\u05e9\u05d4\n"
    "        # \u05d7\u05d6\u05d5\u05ea\u05d9\u05ea \u05dc\u05ea\u05d9\u05d1\u05ea \u05d4\u05e7\u05dc\u05d8 \u05d4\u05e9\u05db\u05e0\u05d4 (Streamlit, \u05d0\u05d5\u05de\u05ea \u05d1-repro).\n"
    "        # selectbox \u05dc\u05d0 \u05e1\u05d5\u05d1\u05dc \u05de\u05d4\u05d1\u05d0\u05d2 \u05d4\u05d6\u05d4, \u05d5\u05d4\u05e2\u05e8\u05da \u05d4\u05e0\u05d1\u05d7\u05e8 \u05ea\u05de\u05d9\u05d3 \u05d2\u05dc\u05d5\u05d9 \u05d1\u05d1\u05d9\u05e8\u05d5\u05e8.\n"
    "        span = i2.selectbox(\n"
    '            "\u05d8\u05d5\u05d5\u05d7 \u05e4\u05e2\u05e8\u05d9\u05dd \u05dc\u05d1\u05d3\u05d9\u05e7\u05d4 (%)", [5, 10, 15, 20, 25, 30, 35, 40],\n'
    '            index=3, key=f"{key_prefix}_span",\n'
    '            help="\u05d8\u05d5\u05d5\u05d7 \u05e8\u05d7\u05d1 \u05d9\u05d5\u05ea\u05e8 \u05d1\u05d5\u05d3\u05e7 \u05d9\u05d5\u05ea\u05e8 \u05ea\u05e8\u05d7\u05d9\u05e9\u05d9 \u05e4\u05e2\u05e8 (\u05db\u05d5\u05dc\u05dc \u05e7\u05d9\u05e6\u05d5\u05e0\u05d9\u05d9\u05dd \u05d9\u05d5\u05ea\u05e8) \u05d1\u05d8\u05d1\u05dc\u05ea \u05d4\u05e1\u05d9\u05de\u05d5\u05dc\u05e6\u05d9\u05d4.")\n'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="לבצע בפועל (ברירת מחדל: dry-run בלבד)")
    ap.add_argument("--file", default="rr_tab.py", help="נתיב לקובץ")
    args = ap.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"❌ הקובץ לא נמצא: {target.resolve()}")
        sys.exit(1)

    raw = target.read_bytes()
    text = raw.decode("utf-8")

    count = text.count(OLD_BLOCK)
    if count == 0:
        print("❌ לא נמצא ה-anchor הצפוי בקובץ. ייתכן ש-patch_fix_gap_slider_overlap.py "
              "עדיין לא הורץ, או שהקוד שונה. לא בוצע שינוי.")
        sys.exit(1)
    if count > 1:
        print(f"❌ ה-anchor מופיע {count} פעמים (צריך בדיוק פעם אחת). לא בוצע שינוי.")
        sys.exit(1)

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK)

    diff = difflib.unified_diff(
        text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=str(target),
        tofile=str(target) + " (after patch)",
    )
    print("".join(diff))

    if not args.apply:
        print("\n🔎 זהו dry-run. שום דבר לא נכתב. הריצי עם --apply כדי לבצע בפועל.")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = target.with_suffix(target.suffix + f".bak_{ts}")
    backup.write_bytes(raw)
    print(f"\n💾 גיבוי נשמר: {backup}")

    target.write_bytes(new_text.encode("utf-8"))
    print(f"✅ הקובץ עודכן: {target}")


if __name__ == "__main__":
    main()
