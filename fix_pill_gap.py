# -*- coding: utf-8 -*-
"""
fix_pill_gap.py
===============
מצמצם את המרווח בין תפריט הפילים לתוכן הטאב.

הרצה:
    py fix_pill_gap.py            # יבש. מראה diff, לא נוגע בכלום
    py fix_pill_gap.py --apply    # מבצע, אחרי גיבוי אוטומטי

האבחנה:
    streamlit_option_menu מרונדר בתוך iframe, וסטרימליט נותן ל-iframe
    גובה קבוע שלא קשור לגובה התוכן. הפילים תופסים כ-46 פיקסל,
    והמכל שסביבם מזמין הרבה יותר. זה החלל.

    בנוסף, .top-pill-wrap הוא div ריק. st.markdown לא עוטף את מה שבא
    אחריו, ולכן הכללים שכוונו אליו מעולם לא נגעו ב-iframe.

מה מתווסף:
    שלושה כללים בגיליון הראשי: גובה קבוע למכל ה-iframe, גובה קבוע
    ל-iframe עצמו, והסתרה של ה-div הריק.

בטיחות:
    ריצה חוזרת לא תעשה כלום. אם התבנית לא נמצאה, לא נכתב דבר.
    גיבוי עם חותמת זמן לפני כל כתיבה.
"""

from __future__ import annotations

import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")
MARKER = "PILL_GAP_FIX"
ANCHOR = ".st-key-top_nav {"

CSS = """/* PILL_GAP_FIX — ה-iframe של option_menu מקבל גובה קבוע מסטרימליט,
   הרבה מעבר ל-46 הפיקסלים שהפילים באמת צריכים. כאן מקבעים אותו
   לגובה האמיתי. .top-pill-wrap הוא div ריק ולכן מוסתר. */
div:has(> iframe[title^="streamlit_option_menu"]),
div[data-testid="stCustomComponentV1"]:has(iframe[title^="streamlit_option_menu"]) {
    height: 46px !important;
    min-height: 0 !important;
    overflow: hidden !important;
}
iframe[title^="streamlit_option_menu"] {
    height: 46px !important;
    display: block !important;
}
.top-pill-wrap:empty { display: none !important; }

"""


def main() -> int:
    apply = "--apply" in sys.argv

    if not TARGET.exists():
        print(f"לא נמצא {TARGET}. הריצי מתוך תיקיית הפרויקט.")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print("התיקון כבר קיים בקובץ. לא נעשה דבר.")
        return 0

    if ANCHOR not in src:
        print(f"לא נמצאה העוגן '{ANCHOR}'. הקובץ כנראה השתנה.")
        return 1

    out = src.replace(ANCHOR, CSS + ANCHOR, 1)

    diff = difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile="לפני", tofile="אחרי", n=1)
    print("".join(diff))

    if not apply:
        print("\nריצה יבשה בלבד. להחיל בפועל:  py fix_pill_gap.py --apply")
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
