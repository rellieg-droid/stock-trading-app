#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_stop_source_label.py

מטרה: מוסיף תווית קטנה "(שמור)" + tooltip לשדה הסטופ ב-render_position_manager
(rr_tab.py), במקרה שבו הערך המוצג הגיע מ-stop_price השמור בפוזיציה
(paper_portfolio.json) ולא נגזר מ-ATR. עד כה השדה הזה הציג רק "סטופ" בלי
שום אינדיקציה למקור הערך, בעוד שהמקרה השני (fallback ל-ATR) כבר הציג
תווית + הסבר ברור. זה משלים את הסימטריה בין שני המצבים.

שימוש:
    python patch_stop_source_label.py                 # dry-run (ברירת מחדל)
    python patch_stop_source_label.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: rr_tab.py (שים לב: קובץ זה ב-LF, לא CRLF כמו alpha_paper_trading.py)
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    '    if p["stop"]:\n'
    '        stop = c2.number_input("\u05e1\u05d8\u05d5\u05e4", min_value=0.01, value=float(p["stop"]),\n'
    '                               step=0.01, format="%.2f", key=f"{key_prefix}_stop")\n'
)

NEW_BLOCK = (
    '    if p["stop"]:\n'
    '        stop = c2.number_input("\u05e1\u05d8\u05d5\u05e4 (\u05e9\u05de\u05d5\u05e8)", min_value=0.01, value=float(p["stop"]),\n'
    '                               step=0.01, format="%.2f", key=f"{key_prefix}_stop",\n'
    '                               help="\u05de\u05e7\u05d5\u05e8: \u05e9\u05de\u05d5\u05e8 \u05de\u05d4\u05e4\u05d5\u05d6\u05d9\u05e6\u05d9\u05d4 "\n'
    '                                    "(\u05e0\u05e7\u05d1\u05e2 \u05d1\u05e2\u05ea \u05d4\u05db\u05e0\u05d9\u05e1\u05d4, \u05dc\u05d0 \u05de\u05d7\u05d5\u05e9\u05d1 "\n'
    '                                    "\u05de\u05d7\u05d3\u05e9 \u05de-ATR \u05d1\u05db\u05dc rerun). \u05e0\u05d9\u05ea\u05df \u05dc\u05e2\u05e8\u05d9\u05db\u05d4 \u05d9\u05d3\u05e0\u05d9\u05ea.")\n'
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
