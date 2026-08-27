"""
patch_add_ftr_tooltips.py

מטרה: להוסיף tooltip הסבר (native HTML title attribute, עובד בכל
דפדפן ללא JS) על כל אחד משלושת מדדי הניקוד בטאב Watchlist:
    F (פונדמנטלי) -- צמיחה, רווחיות, EPS, שולי רווח, מכפילים
    T (טכני)      -- מגמה, נר אחרון, ממוצעים נעים, נפח, תמיכה/התנגדות
    R (סיכון)     -- מבוסס ATR: 100 - (ATR% / 8 * 100), 8% ATR = ציון 0

שימוש:
    python patch_add_ftr_tooltips.py                 # dry-run (ברירת מחדל)
    python patch_add_ftr_tooltips.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

REPLACEMENTS = [
    (
        '<span>פונדמנטלי (F)</span>',
        '<span title="ציון פונדמנטלי (0-100): מבוסס על צמיחה, רווחיות, EPS, '
        'שולי רווח ומכפילים" style="cursor:help;">פונדמנטלי (F)</span>',
    ),
    (
        '<span>טכני (T)</span>',
        '<span title="ציון טכני (0-100): מבוסס על מגמה, נר אחרון, ממוצעים נעים, '
        'נפח מסחר ורמות תמיכה/התנגדות" style="cursor:help;">טכני (T)</span>',
    ),
    (
        '<span>סיכון (R)</span>',
        '<span title="ציון סיכון (0-100): מבוסס על ATR יחסי למחיר. '
        'ATR של 8% ומעלה = ציון 0 (סיכון מרבי)" style="cursor:help;">סיכון (R)</span>',
    ),
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

    for old, _ in REPLACEMENTS:
        c = text.count(old)
        if c != 1:
            print(f"שגיאה: {old!r} נמצא {c} פעמים (צריך פעם אחת בדיוק). לא בוצע שינוי.")
            sys.exit(1)

    new_text = text
    for old, new in REPLACEMENTS:
        new_text = new_text.replace(old, new, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        old_lines = text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="לפני", tofile="אחרי", lineterm="")
        for line in diff:
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                print(line)
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
    print("לבדוק ב-Watchlist: ריחוף עכבר מעל 'פונדמנטלי (F)', 'טכני (T)', 'סיכון (R)'")
    print("אמור להציג הסבר (tooltip) אחרי כשנייה, וסמן העכבר משתנה ל-'?' מעל הטקסט.")


if __name__ == "__main__":
    main()
