"""
fix_pill_white.py — Alpha Charts Pro

מנסה לתקן את הרקע הלבן של סרגל הפילס.

הרקע הלבן אינו באג CSS רגיל. streamlit_option_menu הוא קומפוננטה
שמרונדרת בתוך iframe, ולכן הכלל הקיים בשורה 2249:

    .top-pill-wrap nav[role="tablist"] { background: transparent }

לא יכול להגיע אליה. CSS לא חוצה גבול iframe. הלבן הוא רקע ה-body
של המסמך הפנימי, ובגלל זה הוא נמשך לרוחב מלא ולא מוגבל לפילס.

מה שהסקריפט מנסה:
  1. CSS על אלמנט ה-iframe עצמו בעמוד ההורה. אם ה-body הפנימי
     שקוף, הרקע של האלמנט הוא מה שנראה, וזה כן ניתן לשליטה.
  2. container שקוף בהגדרות ה-option_menu, עם הרקע והמסגרת
     עוברים לעטיפה החיצונית שבשליטתנו.

אזהרה: לא בדקתי את זה בסביבה חיה, כי צריך דפדפן ו-Streamlit רץ.
זה ניסיון מבוסס על איך Streamlit מרנדר קומפוננטות, לא על אימות.
אם הלבן נשאר, הפתרון הוא להחליף את הפילס בכפתורים כמו בטופ-נאב,
דפוס שכבר עובד באפליקציה.

שימוש:
    py fix_pill_white.py            <- תצוגה מקדימה
    py fix_pill_white.py --apply    <- ביצוע + גיבוי
    py fix_pill_white.py --revert   <- ביטול, חזרה למצב הקודם
"""

import re
import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv
REVERT = "--revert" in sys.argv

MARK = "PILL_IFRAME_FIX"

# ── עוגן 1: כלל ה-CSS שלא עובד, מוחלף בגרסה שמכוונת ל-iframe ────────
OLD_CSS = '''.top-pill-wrap nav[role="tablist"] { background: transparent !important; }'''

NEW_CSS = '''/* ''' + MARK + ''' — הכלל הקודם כיוון ל-nav שנמצא בתוך iframe
   ולכן לא יכול היה לעבוד. כאן מכוונים לאלמנט ה-iframe עצמו
   בעמוד ההורה, ומעבירים את הרקע והמסגרת לעטיפה החיצונית. */
.top-pill-wrap nav[role="tablist"] { background: transparent !important; }

iframe[title^="streamlit_option_menu"] {
    background: transparent !important;
    color-scheme: dark;
}
.top-pill-wrap {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 999px;
    padding: 2px 4px;
    margin: 0 0 0.9rem 0;
    overflow: hidden;
}
.top-pill-wrap iframe { display: block; }'''

# ── עוגן 2: container שקוף, הרקע עבר לעטיפה ─────────────────────────
OLD_STYLES = '''            "container": {"padding": "4px", "background-color": "rgba(255,255,255,0.035)",
                          "border": "1px solid rgba(255,255,255,0.08)", "border-radius": "999px",
                          "margin": "0 0 0.9rem 0"},'''

NEW_STYLES = '''            "container": {"padding": "0px", "background-color": "transparent",
                          "border": "none", "border-radius": "999px",
                          "margin": "0px"},'''


def read():
    try:
        with open(TARGET, "r", encoding="utf-8", newline="") as fh:
            return fh.read()
    except FileNotFoundError:
        print(f"[עצירה] {TARGET} לא נמצא. מריצים מתיקיית הפרויקט.")
        return None


def write(text, note):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)
    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("\n" + "-" * 62)
    print(f"{note} גיבוי: {backup}")


def main():
    src = read()
    if src is None:
        return 1
    newline = "\r\n" if "\r\n" in src else "\n"

    def norm(s):
        return s.replace("\n", newline)

    # ── revert ────────────────────────────────────────────────────────
    if REVERT:
        if MARK not in src:
            print("[עצירה] הסימון לא נמצא. אין מה לבטל.")
            return 1
        out = src.replace(norm(NEW_CSS), norm(OLD_CSS), 1)
        out = out.replace(norm(NEW_STYLES), norm(OLD_STYLES), 1)
        if MARK in out:
            print("[עצירה] הביטול לא הצליח. הקובץ נערך ידנית מאז.")
            return 1
        write(out, "בוטל, חזרה למצב הקודם.")
        print("\nהפתרון החלופי: להחליף את הפילס בכפתורים כמו בטופ-נאב.")
        return 0

    # ── apply ─────────────────────────────────────────────────────────
    if MARK in src:
        print("[עצירה] התיקון כבר הוחל.")
        print("        לביטול:  py fix_pill_white.py --revert")
        return 1

    edits = [
        ("CSS שמכוון ל-iframe במקום ל-nav", norm(OLD_CSS), norm(NEW_CSS)),
        ("container שקוף ב-option_menu", norm(OLD_STYLES), norm(NEW_STYLES)),
    ]
    for label, anchor, _ in edits:
        cnt = src.count(anchor)
        if cnt == 0:
            print(f"[עצירה] לא נמצא עוגן עבור: {label}")
            return 1
        if cnt > 1:
            print(f"[עצירה] העוגן עבור '{label}' מופיע {cnt} פעמים.")
            return 1

    print("=" * 62)
    print("רקע לבן בסרגל הפילס"
          + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print("\nשני עוגנים נמצאו, כל אחד פעם אחת בדיוק.\n")
    print("  הסיבה: option_menu מרונדר בתוך iframe.")
    print("  הלבן הוא רקע ה-body הפנימי, ו-CSS מהעמוד לא מגיע אליו.\n")
    print("  הניסיון:")
    print("    1. background:transparent על אלמנט ה-iframe")
    print("    2. color-scheme:dark כדי שברירת המחדל לא תהיה לבנה")
    print("    3. הרקע והמסגרת עוברים ל-.top-pill-wrap שבשליטתנו")
    print("    4. container של option_menu הופך לשקוף\n")
    print("  לא נבדק בסביבה חיה. אם הלבן נשאר:")
    print("    py fix_pill_white.py --revert")
    print("  ואז נחליף את הפילס בכפתורים.")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_pill_white.py --apply")
        return 0

    out = src
    for label, anchor, replacement in edits:
        out = out.replace(anchor, replacement, 1)
        print(f"  [בוצע] {label}")

    write(out, "עודכן.")
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    print("  ואז Ctrl+F5. לעבור לטאב ניתוח או מסחר כדי לראות פילס.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
