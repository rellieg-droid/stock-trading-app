"""
fix_consistency.py — Alpha Charts Pro
שני תיקוני עקביות. שניהם מקרים של אותו נתון שמוצג בשתי דרכים
שונות בשני מקומות, מה שגורם למשתמשת לא לסמוך על המספרים.

  1. סתירת ספירת אנליסטים
     הכרטיס מציג 58 (numberOfAnalystOpinions מ-.info)
     הבר מציג 61 (סכום recommendations)
     שני מקורות של יאהו עם ספירות שונות. הפתרון: להסיר את
     המספר מכותרת הבר. הוא כבר מוצג למעלה בכרטיס.

  2. סתירת ספי צבע לתאריך דוח
     הבאדג' בכותרת: אדום ב-14 יום ומטה
     הטבלה בטאב דוחות: אדום ב-7 יום ומטה
     אותו נתון, שני צבעים. מיישרים את הטבלה לבאדג'.

שימוש:
    py fix_consistency.py            <- תצוגה מקדימה
    py fix_consistency.py --apply    <- ביצוע + גיבוי
"""

import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

EDITS = [
    (
        "הסרת ספירת האנליסטים מכותרת הבר",
        '''margin-bottom:6px;">פילוח המלצות ({total} אנליסטים)</div>''',
        '''margin-bottom:6px;">פילוח המלצות</div>''',
    ),
    (
        "יישור סף האדום בטבלת הדוחות ל-14 יום",
        '''            if days <= 7:    dc = "#f85149"; dtxt = f"⚠️ {days} ימים"''',
        '''            if days <= 14:   dc = "#f85149"; dtxt = f"⚠️ {days} ימים"''',
    ),
]


def main():
    try:
        with open(TARGET, "r", encoding="utf-8", newline="") as fh:
            src = fh.read()
    except FileNotFoundError:
        print(f"[עצירה] {TARGET} לא נמצא. מריצים מתיקיית הפרויקט.")
        return 1

    newline = "\r\n" if "\r\n" in src else "\n"

    def norm(s):
        return s.replace("\n", newline)

    checked = []
    for label, old, new in EDITS:
        o, n = norm(old), norm(new)
        cnt = src.count(o)
        if cnt == 0:
            print(f"[עצירה] לא נמצא עוגן עבור: {label}")
            print("        אם כבר תיקנת ידנית, הסירי את הסעיף מהסקריפט.")
            return 1
        if cnt > 1:
            print(f"[עצירה] העוגן עבור '{label}' מופיע {cnt} פעמים.")
            return 1
        checked.append((label, o, n))

    print("=" * 62)
    print("תיקוני עקביות" + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print("\nשני עוגנים נמצאו, כל אחד פעם אחת בדיוק.\n")
    print("  1. כותרת הבר:  'פילוח המלצות (61 אנליסטים)' -> 'פילוח המלצות'")
    print("     המספר סותר את ה-58 שמוצג למעלה באותו כרטיס.\n")
    print("  2. טבלת דוחות: סף האדום 7 ימים -> 14 ימים")
    print("     מיושר לבאדג' בכרטיס העליון.")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_consistency.py --apply")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)

    out = src
    for label, o, n in checked:
        out = out.replace(o, n, 1)
        print(f"  [בוצע] {label}")

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print("\n" + "-" * 62)
    print(f"עודכן. גיבוי: {backup}")
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    print("  לבדוק: כרטיס אנליסטים בטאב גרף, וטבלה בטאב דוחות.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
