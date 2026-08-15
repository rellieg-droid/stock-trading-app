# -*- coding: utf-8 -*-
"""
fix_tab_gap.py
==============
מסלק את המרווח הלבן שנוצר מהקונטיינרים המוסתרים של הטאבים.

הרצה:
    py fix_tab_gap.py            # יבש. מראה diff, לא נוגע בכלום
    py fix_tab_gap.py --apply    # מבצע, אחרי גיבוי אוטומטי עם חותמת זמן

מה זה עושה:
    הכלל הקיים מסתיר את הקונטיינר עצמו, אבל סטרימליט משאיר אחריו
    אלמנט עטיפה ריק שממשיך לתפוס גובה ומרווח. שלושה עשר טאבים
    מוסתרים מייצרים שלושה עשר מרווחים כאלה, וזה החלל שנראה על המסך.
    הכלל החדש מאפס גובה, מרווחים ופער גם לעטיפות האלה.

בטיחות:
    * ריצה חוזרת לא תעשה כלום. הסקריפט מזהה שהתיקון כבר קיים.
    * אם התבנית לא נמצאה, הוא נעצר ולא כותב דבר.
    * הגיבוי נשמר לצד הקובץ המקורי.
"""

from __future__ import annotations

import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")
MARKER = "TAB_GAP_FIX"

OLD = '''    "<style>" + "\\n".join(f".st-key-{k} {{ display: none !important; }}"
                           for k in _TAB_KEYS if k != _active_key) + "</style>",'''

NEW = '''    # TAB_GAP_FIX — הכלל הראשון מסתיר את הקונטיינר, השני מאפס את
    # העטיפה הריקה שסטרימליט משאיר אחריו ושממשיכה לתפוס גובה.
    "<style>" + "\\n".join(f".st-key-{k} {{ display: none !important; }}\\n"
                           f".st-key-{k} + div:empty {{ display:none !important; }}\\n"
                           f"div:has(> .st-key-{k}) {{ gap:0 !important; }}"
                           for k in _TAB_KEYS if k != _active_key) + "</style>",'''


def main() -> int:
    apply = "--apply" in sys.argv

    if not TARGET.exists():
        print(f"לא נמצא {TARGET}. הריצי מתוך תיקיית הפרויקט.")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print("התיקון כבר קיים בקובץ. לא נעשה דבר.")
        return 0

    if OLD not in src:
        print("התבנית לא נמצאה. הקובץ כנראה נערך ידנית מאז.")
        print("הריצי:  Select-String -Path alpha_paper_trading.py -Pattern 'display: none'")
        return 1

    out = src.replace(OLD, NEW, 1)

    diff = difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile="לפני", tofile="אחרי", n=2)
    print("".join(diff) or "(אין הבדל)")

    if not apply:
        print("\nריצה יבשה בלבד. להחיל בפועל:  py fix_tab_gap.py --apply")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}.backup_{stamp}{TARGET.suffix}")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(out, encoding="utf-8")

    print(f"\nבוצע. גיבוי: {backup.name}")
    print("לביטול:  git checkout alpha_paper_trading.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
