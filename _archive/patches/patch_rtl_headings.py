#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
patch_rtl_headings.py
=====================
מרחיב את כלל ה-RTL הגלובלי כך שיכלול גם כותרות.

המצב היום, שורה 125 ב-alpha_paper_trading.py:

    div, p, span, label { direction: rtl !important; }

התגיות h1 עד h6 לא ברשימה. לכן כל st.title, st.header, st.subheader
וכל <h3> ידני נשארים LTR ונצמדים לשמאל, בזמן ששאר העמוד מיושר לימין.

השינוי: הוספת h1-h6 לאותו כלל, ויישור מפורש לימין עבורם.

זהו שינוי גלובלי שנוגע בכל 14 הטאבים. שווה להריץ אותו בנפרד מכל פאץ' אחר,
ולעבור על הטאבים אחריו, כדי שאם משהו זז יהיה ברור מה גרם לזה.

הרצה:
    py patch_rtl_headings.py                # דמה בלבד
    py patch_rtl_headings.py --apply        # ביצוע, אחרי גיבוי עם חותמת זמן
    py patch_rtl_headings.py --revert       # החזרה לכלל המקורי
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = "alpha_paper_trading.py"

OLD_RULE = '''div, p, span, label { direction: rtl !important; }
.stMarkdown, .stText { text-align: right !important; }
'''

NEW_RULE = '''div, p, span, label { direction: rtl !important; }
/* RTL_HEADINGS — h1-h6 לא נכללו בכלל שמעל, ולכן כל כותרת נשארה LTR
   ונצמדה לשמאל. היישור המפורש נדרש כי text-align לא יורש מ-direction
   כשסטרימליט מגדיר אותו על אלמנט ההורה. */
h1, h2, h3, h4, h5, h6 {
  direction: rtl !important;
  text-align: right !important;
}
.stMarkdown, .stText { text-align: right !important; }
'''


def fail(msg: str) -> None:
    print(f"\n[עצירה] {msg}")
    print("לא בוצע שום שינוי בקובץ.")
    sys.exit(1)


def read_keep_eol(path: Path) -> tuple[str, str]:
    with open(path, encoding="utf-8", newline="") as f:
        raw = f.read()
    crlf = raw.count("\r\n")
    eol = "\r\n" if crlf > (raw.count("\n") - crlf) else "\n"
    return raw.replace("\r\n", "\n"), eol


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="בצע בפועל")
    ap.add_argument("--revert", action="store_true", help="החזר את הכלל המקורי")
    ap.add_argument("--path", default=TARGET)
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        fail(f"הקובץ לא נמצא: {path.resolve()}")

    original, eol = read_keep_eol(path)
    src, dst = (NEW_RULE, OLD_RULE) if args.revert else (OLD_RULE, NEW_RULE)
    action = "החזרה" if args.revert else "הוספה"

    if dst.strip() in original and not args.revert:
        print("\nאין מה לשנות. הכותרות כבר כלולות בכלל.")
        return

    count = original.count(src)
    if count == 0:
        fail(f"הכלל לא נמצא בקובץ. ייתכן שנערך ידנית, או ש-{action} כבר בוצעה.")
    if count > 1:
        fail(f"הכלל מופיע {count} פעמים. החלפה לא חד-משמעית.")

    text = original.replace(src, dst, 1)

    diff = difflib.unified_diff(
        original.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=f"a/{path.name}", tofile=f"b/{path.name}", n=3,
    )
    print("\n" + "".join(diff))
    print(f"פעולה: {action} של h1-h6 לכלל ה-RTL הגלובלי")

    if not args.apply:
        print("\nזו הרצת דמה. להחלה בפועל:  py patch_rtl_headings.py --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.{stamp}.bak")
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", eol))
    print(f"\nבוצע. גיבוי נשמר ב: {backup.name}")
    print("להחזרה מהירה:  py patch_rtl_headings.py --revert --apply")


if __name__ == "__main__":
    main()
