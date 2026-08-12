"""
fix_nav_rebalance.py — Alpha Charts Pro
מאזן מחדש את חלוקת הטאבים ל-5 כפתורי הניווט (אפשרות A).

Backtest עובר מ"עוד" ל"ניתוח".
Watchlist עובר מ"עוד" ל"מסחר".
"עוד" יורד מ-5 פילס ל-3.

לא נוגע בתוכן הטאבים, רק ב-NAV_GROUPS. המיפוי ב-_active_map
ומנגנון ה-display:none עובדים לפי שם התת-טאב ולא לפי הקבוצה,
ולכן העברת פריט בין קבוצות לא דורשת שום שינוי נוסף.

שימוש:
    py fix_nav_rebalance.py            <- תצוגה מקדימה
    py fix_nav_rebalance.py --apply    <- ביצוע + גיבוי
"""

import re
import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

NEW_BLOCK = '''NAV_GROUPS = {
    "בית":   {"icon": "house",      "subs": ["🏠 Home"]},
    "גרף":   {"icon": "graph-up",   "subs": ["📈 גרף"]},
    "ניתוח": {"icon": "cpu",        "subs": ["🎯 ניתוח", "⚖️ השוואה", "⏳ Backtest"]},
    "מסחר":  {"icon": "cart",       "subs": ["🛒 מסחר", "💼 תיק", "👁️ Watchlist"]},
    "עוד":   {"icon": "three-dots", "subs": ["🔔 התראות", "📅 דוחות", "📖 מדריך"]},
}'''


def main():
    try:
        with open(TARGET, "r", encoding="utf-8", newline="") as fh:
            src = fh.read()
    except FileNotFoundError:
        print(f"[עצירה] {TARGET} לא נמצא. מריצים מתיקיית הפרויקט.")
        return 1

    # ── איתור הבלוק הקיים ────────────────────────────────────────────
    pattern = re.compile(r"NAV_GROUPS\s*=\s*\{.*?\n\}", re.DOTALL)
    matches = pattern.findall(src)

    if len(matches) == 0:
        print("[עצירה] לא נמצא בלוק NAV_GROUPS. הקובץ השתנה מאז הבדיקה.")
        return 1
    if len(matches) > 1:
        print(f"[עצירה] נמצאו {len(matches)} בלוקים של NAV_GROUPS. "
              "צריך לבדוק ידנית איזה מהם פעיל.")
        return 1

    old_block = matches[0]

    # ── בדיקת שפיות: כל 11 התת-טאבים קיימים גם אחרי השינוי ──────────
    old_subs = set(re.findall(r'"([^"]*(?:Home|גרף|ניתוח|השוואה|מסחר|תיק|'
                              r'Backtest|התראות|דוחות|Watchlist|מדריך))"', old_block))
    new_subs = set(re.findall(r'"([^"]*(?:Home|גרף|ניתוח|השוואה|מסחר|תיק|'
                              r'Backtest|התראות|דוחות|Watchlist|מדריך))"', NEW_BLOCK))
    lost = old_subs - new_subs
    if lost:
        print(f"[עצירה] תת-טאבים שנעלמו בגרסה החדשה: {lost}")
        return 1

    newline = "\r\n" if "\r\n" in src else "\n"
    new_block = NEW_BLOCK.replace("\n", newline)

    print("=" * 62)
    print("איזון ניווט" + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print("\nלפני:\n")
    print(old_block)
    print("\nאחרי:\n")
    print(NEW_BLOCK)
    print(f"\nתת-טאבים לפני: {len(old_subs)} | אחרי: {len(new_subs)} | אבודים: 0")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_nav_rebalance.py --apply")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(src.replace(old_block, new_block, 1))

    print("\n" + "-" * 62)
    print(f"עודכן. גיבוי: {backup}")
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    print("  לבדוק שהפילס של ניתוח/מסחר/עוד מתחלפים ושכל 11 העמודים נגישים.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
