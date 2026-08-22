#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fix_gap_slider_overlap.py

מטרה: מתקן את החפיפה הוויזואלית בין הבועה הצפה של ה-slider "טווח פערים
לבדיקה (%)" לבין תיבת הקלט "מחיר סגירה לפני הדוח" (rr_tab.py, סקשן
"סימולציית פערים").

אבחון (מאומת ידנית ע"י המשתמשת עם repro_slider_overlap.py): הבאג משוחזר
גם בלי ה-CSS הגלובלי של RTL, ולכן הוא לא קשור ל-direction:rtl. זו התנהגות
מוכרת ב-Streamlit: הבועה הצפה מעל ידית ה-slider מחשבת מיקום לפי רוחב
container צר (st.columns(2)), והחישוב נשבר ופולש לעמודה השכנה.

הפתרון: להוציא את ה-slider מהעמודות ולתת לו שורה מלאה משלו, מתחת לשדה
המחיר. ה-slider מקבל רוחב מלא כך שהבועה לא פולשת לשום מקום.

שימוש:
    python patch_fix_gap_slider_overlap.py                 # dry-run (ברירת מחדל)
    python patch_fix_gap_slider_overlap.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: rr_tab.py (LF, לא CRLF)
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    "    if interactive:\n"
    "        i1, i2 = st.columns(2)\n"
    "        ref_price = i1.number_input(\n"
    '            "\u05de\u05d7\u05d9\u05e8 \u05e1\u05d2\u05d9\u05e8\u05d4 \u05dc\u05e4\u05e0\u05d9 \u05d4\u05d3\u05d5\u05d7", min_value=0.01, value=float(plan.entry),\n'
    '            step=0.01, format="%.2f", key=f"{key_prefix}_ref",\n'
    '            help="\u05e9\u05e0\u05d9 \u05d0\u05dd \u05d4\u05e4\u05d5\u05d6\u05d9\u05e6\u05d9\u05d4 \u05db\u05d1\u05e8 \u05d1\u05e8\u05d5\u05d5\u05d7 \u2014 \u05d4\u05e4\u05e2\u05e8 \u05e0\u05de\u05d3\u05d3 \u05de\u05d4\u05e1\u05d2\u05d9\u05e8\u05d4, \u05dc\u05d0 \u05de\u05d4\u05db\u05e0\u05d9\u05e1\u05d4.")\n'
    '        span = i2.slider("\u05d8\u05d5\u05d5\u05d7 \u05e4\u05e2\u05e8\u05d9\u05dd \u05dc\u05d1\u05d3\u05d9\u05e7\u05d4 (%)", 5, 40, 20, 5,\n'
    '                         key=f"{key_prefix}_span")\n'
)

NEW_BLOCK = (
    "    if interactive:\n"
    "        ref_price = st.number_input(\n"
    '            "\u05de\u05d7\u05d9\u05e8 \u05e1\u05d2\u05d9\u05e8\u05d4 \u05dc\u05e4\u05e0\u05d9 \u05d4\u05d3\u05d5\u05d7", min_value=0.01, value=float(plan.entry),\n'
    '            step=0.01, format="%.2f", key=f"{key_prefix}_ref",\n'
    '            help="\u05e9\u05e0\u05d9 \u05d0\u05dd \u05d4\u05e4\u05d5\u05d6\u05d9\u05e6\u05d9\u05d4 \u05db\u05d1\u05e8 \u05d1\u05e8\u05d5\u05d5\u05d7 \u2014 \u05d4\u05e4\u05e2\u05e8 \u05e0\u05de\u05d3\u05d3 \u05de\u05d4\u05e1\u05d2\u05d9\u05e8\u05d4, \u05dc\u05d0 \u05de\u05d4\u05db\u05e0\u05d9\u05e1\u05d4.")\n'
    "        # ה-slider מקבל שורה נפרדת ברוחב מלא בכוונה: כשהוא היה\n"
    "        # ב-st.columns(2) לצד number_input, הבועה הצפה מעל הידית\n"
    "        # חישבה מיקום לפי הרוחב הצר של העמודה ופלשה חזותית לתיבת\n"
    "        # הקלט השכנה (Streamlit, לא קשור ל-CSS של RTL - אומת ב-repro).\n"
    '        span = st.slider("\u05d8\u05d5\u05d5\u05d7 \u05e4\u05e2\u05e8\u05d9\u05dd \u05dc\u05d1\u05d3\u05d9\u05e7\u05d4 (%)", 5, 40, 20, 5,\n'
    '                         key=f"{key_prefix}_span")\n'
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
        print("❌ לא נמצא ה-anchor הצפוי בקובץ. ייתכן שהקוד כבר שונה. לא בוצע שינוי.")
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
