# -*- coding: utf-8 -*-
"""
fix_tab_gap2.py
===============
מחליף את TAB_GAP_FIX שנכשל, בכלל שמכוון להורה במקום לילד.

הרצה:
    py fix_tab_gap2.py            # יבש
    py fix_tab_gap2.py --apply    # מבצע, אחרי גיבוי

האבחנה, הפעם על סמך מדידה:
    הגשש מצא stVerticalBlock עם gap של 14 פיקסל.
    st.container(key="X") שם את המחלקה st-key-X על div פנימי,
    והעטיפה שמעליו נשארת גלויה. display:none על הילד לא מוציא
    את ההורה מזרימת ה-flex, וההורה ממשיך לתרום 14 פיקסל.
    שלושה עשר טאבים מוסתרים מייצרים כך מאות פיקסלים של חלל.

    התיקון: להסתיר את ההורה עצמו דרך :has, ואז הוא יוצא מהזרימה
    יחד עם ה-gap שלו.
"""

from __future__ import annotations

import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")
MARKER = "TAB_GAP_FIX_V2"

OLD = '''    # TAB_GAP_FIX — הכלל הראשון מסתיר את הקונטיינר, השני מאפס את
    # העטיפה הריקה שסטרימליט משאיר אחריו ושממשיכה לתפוס גובה.
    "<style>" + "\\n".join(f".st-key-{k} {{ display: none !important; }}\\n"
                           f".st-key-{k} + div:empty {{ display:none !important; }}\\n"
                           f"div:has(> .st-key-{k}) {{ gap:0 !important; }}"
                           for k in _TAB_KEYS if k != _active_key) + "</style>",'''

NEW = '''    # TAB_GAP_FIX_V2 — לא מספיק להסתיר את הקונטיינר. st.container שם את
    # st-key-X על div פנימי, וההורה נשאר בזרימת ה-flex ותורם 14px של gap
    # לכל טאב מוסתר. הכלל השני מסתיר את ההורה עצמו ומוציא אותו מהזרימה.
    "<style>" + "\\n".join(f".st-key-{k} {{ display: none !important; }}\\n"
                           f"div[data-testid=\\"stVerticalBlock\\"] "
                           f"> div:has(> .st-key-{k}) {{ display:none !important; }}\\n"
                           f"div[data-testid=\\"stElementContainer\\"]:has(.st-key-{k}) "
                           f"{{ display:none !important; }}"
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
        print("לא נמצא הבלוק של TAB_GAP_FIX. ייתכן שהקובץ נערך ידנית.")
        print("הריצי:  Select-String -Path alpha_paper_trading.py -Pattern 'TAB_GAP_FIX'")
        return 1

    out = src.replace(OLD, NEW, 1)

    print("".join(difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile="לפני", tofile="אחרי", n=1)))

    if not apply:
        print("\nריצה יבשה בלבד. להחיל בפועל:  py fix_tab_gap2.py --apply")
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
