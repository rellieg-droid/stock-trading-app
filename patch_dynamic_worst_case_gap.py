#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_dynamic_worst_case_gap.py

מטרה: הקופסה האדומה "הסטופ אינו מגן מעבר לדוח..." הייתה מחושבת עם ערך
קבוע gap_pct=0.15 (15%), בלי קשר לבחירה בתפריט "טווח פערים לבדיקה (%)".
כשבוחרים 20% או 40%, הקופסה נשארה מקובעת על תרחיש ה-15% ולא השתקפה
הבחירה, מה שבלבל.

הפתרון: הקופסה מחושבת עכשיו לפי הערך שנבחר בפועל בתפריט (span), ולא
לפי קבוע. כשהאפליקציה לא אינטראקטיבית (interactive=False, למשל בדוח
PDF), נשמרת ברירת המחדל הישנה של 15%.

שימוש:
    python patch_dynamic_worst_case_gap.py                 # dry-run (ברירת מחדל)
    python patch_dynamic_worst_case_gap.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: rr_tab.py (LF)
דורש: patch_gap_span_selectbox.py כבר הורץ (--apply) קודם.
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    "        gaps = tuple(round(x / 100, 4) for x in range(-span, span + 1, 5))\n"
    "\n"
    "    outcomes = rr.gap_scenario_table(plan, gaps=gaps, ref_price=ref_price)\n"
    "    wc = rr.worst_case_gap_loss(plan, gap_pct=0.15, ref_price=ref_price)\n"
    "\n"
    '    st.markdown(\'<div dir="rtl" style="text-align:right;font-weight:700;margin:.6rem 0 .2rem;">\'\n'
    "                '\u05e1\u05d9\u05de\u05d5\u05dc\u05e6\u05d9\u05d9\u05ea \u05e4\u05e2\u05e8 \u05d1\u05e4\u05ea\u05d9\u05d7\u05d4 \u05e9\u05d0\u05d7\u05e8\u05d9 \u05d4\u05d3\u05d5\u05d7</div>', unsafe_allow_html=True)\n"
    "    st.markdown(\n"
    '        f\'<div dir="rtl" style="border-right:3px solid {_C["red"]};\'\n'
    '        f\'background:{_C["red"]}12;border-radius:10px;padding:.7rem .95rem;\'\n'
    '        f\'margin:.2rem 0 .7rem;font-size:.87rem;line-height:1.65;color:{_C["text"]};">\'\n'
    "        f'<b>\u05d4\u05e1\u05d8\u05d5\u05e4 \u05d0\u05d9\u05e0\u05d5 \u05de\u05d2\u05df \u05de\u05e2\u05d1\u05e8 \u05dc\u05d3\u05d5\u05d7.</b> \u05d1\u05e4\u05e2\u05e8 \u05e0\u05d2\u05d3\u05d9 \u05e9\u05dc 15% \u05d4\u05e4\u05d5\u05d6\u05d9\u05e6\u05d9\u05d4 \u05e0\u05e1\u05d2\u05e8\u05ea \u05d1-'\n"
)

NEW_BLOCK = (
    "        gaps = tuple(round(x / 100, 4) for x in range(-span, span + 1, 5))\n"
    "\n"
    "    # \u05d4\u05e7\u05d5\u05e4\u05e1\u05d4 \u05de\u05e9\u05ea\u05de\u05e9\u05ea \u05d1\u05d0\u05d5\u05ea\u05d5 \u05d0\u05d7\u05d5\u05d6 \u05e9\u05e0\u05d1\u05d7\u05e8 \u05d1\u05ea\u05e4\u05e8\u05d9\u05d8 (span), \u05dc\u05d0 \u05e7\u05d1\u05d5\u05e2, \u05db\u05d3\u05d9\n"
    "    # \u05e9\u05d4\u05d4\u05e1\u05d1\u05e8 \u05d9\u05e9\u05ea\u05e0\u05d4 \u05dc\u05d1\u05d7\u05d9\u05e8\u05d4. \u05db\u05e9\u05dc\u05d0 \u05d0\u05d9\u05e0\u05d8\u05e8\u05d0\u05e7\u05d8\u05d9\u05d1\u05d9 span \u05dc\u05d0 \u05e7\u05d9\u05d9\u05dd, \u05d5\u05de\u05e9\u05ea\u05de\u05e9\u05d9\u05dd\n"
    "    # \u05d1\u05d1\u05e8\u05d9\u05e8\u05ea \u05de\u05d7\u05d3\u05dc \u05e9\u05dc 15%.\n"
    "    worst_pct = span if interactive else 15\n"
    "    outcomes = rr.gap_scenario_table(plan, gaps=gaps, ref_price=ref_price)\n"
    "    wc = rr.worst_case_gap_loss(plan, gap_pct=worst_pct / 100, ref_price=ref_price)\n"
    "\n"
    '    st.markdown(\'<div dir="rtl" style="text-align:right;font-weight:700;margin:.6rem 0 .2rem;">\'\n'
    "                '\u05e1\u05d9\u05de\u05d5\u05dc\u05e6\u05d9\u05d9\u05ea \u05e4\u05e2\u05e8 \u05d1\u05e4\u05ea\u05d9\u05d7\u05d4 \u05e9\u05d0\u05d7\u05e8\u05d9 \u05d4\u05d3\u05d5\u05d7</div>', unsafe_allow_html=True)\n"
    "    st.markdown(\n"
    '        f\'<div dir="rtl" style="border-right:3px solid {_C["red"]};\'\n'
    '        f\'background:{_C["red"]}12;border-radius:10px;padding:.7rem .95rem;\'\n'
    '        f\'margin:.2rem 0 .7rem;font-size:.87rem;line-height:1.65;color:{_C["text"]};">\'\n'
    "        f'<b>\u05d4\u05e1\u05d8\u05d5\u05e4 \u05d0\u05d9\u05e0\u05d5 \u05de\u05d2\u05df \u05de\u05e2\u05d1\u05e8 \u05dc\u05d3\u05d5\u05d7.</b> \u05d1\u05e4\u05e2\u05e8 \u05e0\u05d2\u05d3\u05d9 \u05e9\u05dc {worst_pct}% \u05d4\u05e4\u05d5\u05d6\u05d9\u05e6\u05d9\u05d4 \u05e0\u05e1\u05d2\u05e8\u05ea \u05d1-'\n"
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
        print("❌ לא נמצא ה-anchor הצפוי בקובץ. ייתכן ש-patch_gap_span_selectbox.py "
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
