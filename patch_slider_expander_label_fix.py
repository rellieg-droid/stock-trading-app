"""
patch_slider_expander_label_fix.py

מטרה: לתקן היעלמות תווית הערך מעל הסליידרים -- אובחן כבאג מאושר
רשמית ב-Streamlit (GitHub issue #3555: "Long values on slider get
cut off or overlap"), שקורה כשסליידר נמצא בתוך st.expander: גבול
ה-expander "חותך" את תווית הערך שאמורה להופיע מעל הסליידר.

הפתרון: תוספת padding-top ל-slider כשהוא בתוך expander, כדי לתת
לתווית מקום להופיע בלי שהגבול יחתוך אותה.

שימוש:
    python patch_slider_expander_label_fix.py                 # dry-run (ברירת מחדל)
    python patch_slider_expander_label_fix.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

ANCHOR = '.stSlider [data-baseweb="slider"] div[role="slider"] { background: var(--c-blue) !important; }'

NEW_CSS_LINES = [
    ANCHOR,
    '/* תיקון לבאג מאושר ב-Streamlit (GitHub #3555): גבול expander חותך',
    '   את תווית הערך מעל הסליידר. מוסיפים מרווח עליון כדי שתהיה נראית. */',
    '.streamlit-expanderContent .stSlider { padding-top: 22px !important; }',
    '.streamlit-expanderContent .stSlider [data-testid="stTickBar"] { top: -20px !important; }',
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="בצע בפועל (במקום dry-run)")
    args = parser.parse_args()

    target = Path(TARGET_FILE)
    if not target.exists():
        print(f"שגיאה: לא נמצא הקובץ {TARGET_FILE} בתיקייה הנוכחית.")
        sys.exit(1)

    raw_bytes = target.read_bytes()
    uses_crlf = b"\r\n" in raw_bytes
    text = raw_bytes.decode("utf-8")

    if text.count(ANCHOR) != 1:
        print(f"שגיאה: העוגן נמצא {text.count(ANCHOR)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    new_css_block = "\n".join(NEW_CSS_LINES)
    new_text = text.replace(ANCHOR, new_css_block, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        diff = difflib.unified_diff(
            [ANCHOR], NEW_CSS_LINES,
            fromfile="לפני", tofile="אחרי", lineterm=""
        )
        print("\n".join(diff))
        print("\nלביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"גיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן.")
    print("לבדוק: תוויות הערך אמורות להופיע מעל כל 5 הסליידרים בטאב אסטרטגיה.")
    print("אם המספרים עדיין לא נראים, ייתכן שצריך לכוונן את הערכים -20px / 22px.")


if __name__ == "__main__":
    main()
