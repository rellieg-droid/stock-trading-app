"""
fix_upside_dedup.py — Alpha Charts Pro

מסיר שתי התראות אפסייד כפולות.

אותו נתון מוצג היום בארבעה מקומות עם ארבעה ספים שונים:

  שורה 1119  כרטיס אנליסטים   ללא סף    "▲ 35.7% אפסייד" בקופסה ירוקה
  שורה 1375  ניקוד            30/20/10  50 נקודות לפוטנציאל
  שורה 1841  התראות           > 20      רמה low          <- מוסר
  שורה 3974  התראות אחרות     > 25      רמה low, 🎯      <- מוסר
  שורה 4307  רשימת drivers    > 10      טקסט

מניה עם 22% אפסייד מקבלת התראה במקום אחד ולא באחר, וזה נראה
כמו תקלה ולא כמו החלטה. הקופסה הירוקה בכרטיס האנליסטים כבר
מציגה את המספר בבירור, ולכן שתי ההתראות ברמה low הן רעש.

חשוב: התראות הדאונסייד נשארות. אזהרה שחוזרת פעמיים פחות מזיקה
מהזדמנות שחוזרת פעמיים. הן פשוט משנות מ-elif ל-if.

זה תיקון תצוגה בלבד. אף חישוב, ניקוד או המלצה לא משתנים.

שימוש:
    py fix_upside_dedup.py            <- תצוגה מקדימה
    py fix_upside_dedup.py --apply    <- ביצוע + גיבוי
"""

import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

EDITS = [
    (
        "התראת אפסייד ב-ThesisPanel (סף 20%)",
        '''            if upside > 20:
                alerts.append({"level": "low", "text": f"אפסייד של {upside:.0f}% לפי קונצנזוס אנליסטים"})
            elif upside < -10:''',
        '''            if upside < -10:''',
    ),
    (
        "התראת אפסייד בפאנל הסיכום (סף 25%)",
        '''            if upside and upside > 25:
                alerts.append({"level":"low","icon":"🎯","text":f"אפסייד גבוה — {upside:.0f}% לפי קונצנזוס אנליסטים"})
            elif upside and upside < -10:''',
        '''            if upside and upside < -10:''',
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
            print("        לא נכתב כלום.")
            return 1
        if cnt > 1:
            print(f"[עצירה] העוגן עבור '{label}' מופיע {cnt} פעמים.")
            return 1
        checked.append((label, o, n))

    print("=" * 62)
    print("הסרת אפסייד כפול"
          + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print("\nשני עוגנים נמצאו, כל אחד פעם אחת בדיוק.\n")
    print("  מוסר:  שתי התראות ברמה low על אפסייד חיובי")
    print("  נשאר:  הקופסה הירוקה בכרטיס האנליסטים")
    print("         הניקוד, ה-drivers, וכל התראות הדאונסייד\n")
    print("  ה-elif של הדאונסייד הופך ל-if, אחרת הוא נשאר יתום.")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_upside_dedup.py --apply")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)

    out = src
    for label, o, n in checked:
        out = out.replace(o, n, 1)
        print(f"  [בוצע] {label}")

    # בדיקה שלא נשארו התראות אפסייד חיובי
    leftover = out.count("אפסייד של {upside") + out.count("אפסייד גבוה — {upside")
    if leftover:
        print(f"\n[אזהרה] נשארו {leftover} מופעים לא צפויים.")

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print("\n" + "-" * 62)
    print(f"עודכן. גיבוי: {backup}")
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    print("  לבדוק שההתראות החכמות עדיין מוצגות, בלי שורת האפסייד.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
