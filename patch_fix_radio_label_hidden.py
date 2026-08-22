#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fix_radio_label_hidden.py

מטרה: תיקון CSS שהסתיר את הטקסט של כל אפשרויות ה-radio בכל האפליקציה
(למשל "🟢 קנייה" / "🔴 מכירה" בטאב מסחר, ו-"כן"/"לא" שהוספנו היום
למודול הפסיכולוגי).

אבחון: הכלל היה
    div[role="radiogroup"] input:checked + div,
    div[role="radiogroup"] [data-testid="stMarkdownContainer"] { display: none !important; }
שני סלקטורים מחוברים בפסיק, שניהם מקבלים display:none. הסלקטור השני
מסתיר את תיבת הטקסט של כל אפשרות radio, תמיד — בסתירה ישירה לכללי
העיצוב מיד מעליו (שורות 201-219) שמעצבים את הצבע/גופן של אותו טקסט
בדיוק. זו כנראה תקלת הקלדה (פסיק שלא היה אמור להיות שם, או כוונה
להסתיר רק אלמנט קישוט אחד).

הפתרון: מסירים את הסלקטור השני, משאירים רק input:checked + div
(שלא נראה שפוגע בתצוגה בפועל).

שימוש:
    python patch_fix_radio_label_hidden.py                 # dry-run (ברירת מחדל)
    python patch_fix_radio_label_hidden.py --apply          # מבצע בפועל + גיבוי אוטומטי
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    'div[role="radiogroup"] input:checked + div,\r\n'
    'div[role="radiogroup"] [data-testid="stMarkdownContainer"] { display: none !important; }\r\n'
)

NEW_BLOCK = (
    "/* \u05d4\u05d5\u05e1\u05e8 \u05d4\u05e1\u05dc\u05e7\u05d8\u05d5\u05e8 \u05d4\u05e9\u05e0\u05d9 \u05e9\u05d4\u05d9\u05d4 \u05de\u05d7\u05d5\u05d1\u05e8 \u05d1\u05e4\u05e1\u05d9\u05e7 \u05dc\u05db\u05dc\u05dc \u05d6\u05d4: \u05d4\u05d5\u05d0 \u05d4\u05e1\u05ea\u05d9\u05e8 \u05d0\u05ea\r\n"
    "   \u05d8\u05e7\u05e1\u05d8 \u05db\u05dc \u05d0\u05e4\u05e9\u05e8\u05d5\u05ea \u05d4-radio \u05d1\u05db\u05dc \u05d4\u05d0\u05e4\u05dc\u05d9\u05e7\u05e6\u05d9\u05d4 (\u05d1\u05e1\u05ea\u05d9\u05e8\u05d4 \u05dc\u05e2\u05d9\u05e6\u05d5\u05d1 \u05d1\u05e9\u05d5\u05e8\u05d5\u05ea\r\n"
    "   201-219 \u05de\u05de\u05e9). \u05e0\u05de\u05e9\u05da \u05e8\u05e7 input:checked + div \u05e9\u05dc\u05d0 \u05e0\u05e8\u05d0\u05d4 \u05e9\u05e4\u05d5\u05d2\u05e2 \u05d1\u05ea\u05e6\u05d5\u05d2\u05d4. */\r\n"
    'div[role="radiogroup"] input:checked + div { display: none !important; }\r\n'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="לבצע בפועל (ברירת מחדל: dry-run בלבד)")
    ap.add_argument("--file", default="alpha_paper_trading.py", help="נתיב לקובץ")
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
