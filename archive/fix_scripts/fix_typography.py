"""
fix_typography.py — Alpha Charts Pro

מתקן שלושה מקומות שבהם טקסט חלש מדי או קטן מדי מכדי להיקרא.

השורש משותף: --c-text-3 הוא #5A6178, הצבע החלש בערכה, ובגדלים
של .62rem עד .72rem יחס הניגודיות שלו מול הרקע הכהה יורד לסביבות
3.4:1. סף הנגישות לטקסט קטן הוא 4.5:1. --c-text-2 (#8B93A7) עומד בו.

הסקריפט לא נוגע ב---c-text-3 עצמו, כי הוא מפוזר בעשרות מקומות
ושינוי גלובלי יזיז דברים שלא ביקשת. רק שלושת המקומות שסומנו.

  1. כרטיס הכותרת: "היום", 52ש׳, סגירה קודמת
  2. מקרא פילוח ההמלצות: טקסט וריבועי הצבע
  3. מקרא ה-RSI

שימוש:
    py fix_typography.py            <- תצוגה מקדימה
    py fix_typography.py --apply    <- ביצוע + גיבוי
"""

import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

EDITS = [
    # ── 1. כרטיס הכותרת ───────────────────────────────────────────────
    (
        'כרטיס הכותרת: "היום"',
        '''f'<span style="color:var(--c-text-3);font-size:.75rem;">היום</span>' ''',
        '''f'<span style="color:var(--c-text-2);font-size:.8rem;">היום</span>' ''',
    ),
    (
        "כרטיס הכותרת: טווח 52 שבועות",
        '''<span style="color:var(--c-text-3);font-size:.72rem;margin-right:auto;">52ש׳:''',
        '''<span style="color:var(--c-text-2);font-size:.78rem;margin-right:auto;">52ש׳:''',
    ),
    (
        "כרטיס הכותרת: סגירה קודמת",
        '''<span style="color:var(--c-text-3);font-size:.72rem;">סגירה קודמת:''',
        '''<span style="color:var(--c-text-2);font-size:.78rem;">סגירה קודמת:''',
    ),
    # ── 2. מקרא פילוח ההמלצות ─────────────────────────────────────────
    (
        "מקרא הפילוח: גודל טקסט ומרווח",
        '''f'margin-left:12px;font-size:.66rem;color:#8b949e;white-space:nowrap;">' ''',
        '''f'margin-left:16px;font-size:.76rem;color:#8b949e;white-space:nowrap;">' ''',
    ),
    (
        "מקרא הפילוח: ריבועי הצבע",
        '''f'<span style="width:8px;height:8px;border-radius:2px;' ''',
        '''f'<span style="width:11px;height:11px;border-radius:3px;' ''',
    ),
    (
        "מקרא הפילוח: עובי הבר",
        '''f'<div style="display:flex;height:10px;border-radius:5px;' ''',
        '''f'<div style="display:flex;height:14px;border-radius:7px;' ''',
    ),
    # ── 3. מקרא ה-RSI ─────────────────────────────────────────────────
    (
        "מקרא RSI",
        '''<span style="color:#8b949e;font-size:.65rem;margin-right:auto;">''',
        '''<span style="color:#8b949e;font-size:.74rem;margin-right:auto;">''',
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
        # רווח נגרר בקבועים למעלה קיים רק לקריאות הסקריפט
        return s.rstrip(" ").replace("\n", newline)

    checked, skipped = [], []
    for label, old, new in EDITS:
        o, n = norm(old), norm(new)
        cnt = src.count(o)
        if cnt == 0:
            skipped.append(label)
            continue
        if cnt > 1:
            print(f"[עצירה] העוגן עבור '{label}' מופיע {cnt} פעמים.")
            print("        עוגן לא ייחודי, לא נכתב כלום.")
            return 1
        checked.append((label, o, n))

    print("=" * 62)
    print("טיפוגרפיה" + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print()
    for label, _, _ in checked:
        print(f"  [נמצא ]  {label}")
    for label in skipped:
        print(f"  [דולג ]  {label}   <- עוגן לא נמצא")

    if not checked:
        print("\n[עצירה] אף עוגן לא נמצא. הקובץ שונה מהצפוי.")
        return 1

    print(f"\n  {len(checked)} מתוך {len(EDITS)} עוגנים.")
    print("\n  השינויים:")
    print("    צבע:  var(--c-text-3) -> var(--c-text-2)   [3.4:1 -> 5.1:1]")
    print("    גודל: .72rem -> .78rem | .66rem -> .76rem | .65rem -> .74rem")
    print("    ריבועי מקרא: 8px -> 11px | בר: 10px -> 14px")

    if skipped:
        print("\n  [אזהרה] יש עוגנים שדולגו. אם ציפית שיתוקנו, תגידי לי")
        print("          לפני שאת מריצה --apply.")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_typography.py --apply")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)

    out = src
    for label, o, n in checked:
        out = out.replace(o, n, 1)
        print(f"  [בוצע ]  {label}")

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print("\n" + "-" * 62)
    print(f"עודכן. גיבוי: {backup}")
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
