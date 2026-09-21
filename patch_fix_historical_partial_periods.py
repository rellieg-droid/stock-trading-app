"""
patch_fix_historical_partial_periods.py
========================================
מתקן באג ב-historical_put_otm_probability: כשאין מספיק היסטוריה לתקופה
מסוימת (למשל 10 שנים), הקוד היה נופל בחזרה לכל הדאטה הזמין ומחשב איתו
כאילו זו התקופה המבוקשת - במקום להחזיר None כמו שהתיעוד של הפונקציה
עצמו מבטיח ("אם אין מספיק היסטוריה לתקופה מסוימת - היא None, לא מומצאת").

התוצאה בפועל: תקופות שונות (1 שנה מול 10 שנים) יצאו זהות כשאין מספיק
היסטוריה, כי שתיהן בעצם חישבו על אותו דאטה מצומצם בלי שהמשתמשת תדע.

שימוש:
    python patch_fix_historical_partial_periods.py                 # dry-run
    python patch_fix_historical_partial_periods.py --apply          # מבצע בפועל
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("options_engine.py")

OLD_BLOCK = (
    "    for years in periods_years:\n"
    "        window_days = years * trading_days_per_year\n"
    "        needed = window_days + dte_days\n"
    "        tail = list(closes[-needed:]) if n >= needed else list(closes)\n"
    "        total = len(tail) - dte_days\n"
    "        if total <= 0:\n"
    "            by_period[years] = None\n"
    "            continue\n"
    "        breaches = sum(1 for i in range(total) if tail[i + dte_days] <= strike)\n"
    "        by_period[years] = 1.0 - (breaches / total)\n"
)

NEW_BLOCK = (
    "    for years in periods_years:\n"
    "        window_days = years * trading_days_per_year\n"
    "        needed = window_days + dte_days\n"
    "        if n < needed:\n"
    "            # תיקון: אין מספיק היסטוריה לתקופה הזו - None, לא נפילה חזרה\n"
    "            # לדאטה חלקי שמתחזה לתקופה שלא קיימת בפועל.\n"
    "            by_period[years] = None\n"
    "            continue\n"
    "        tail = closes[-needed:]\n"
    "        total = len(tail) - dte_days\n"
    "        breaches = sum(1 for i in range(total) if tail[i + dte_days] <= strike)\n"
    "        by_period[years] = 1.0 - (breaches / total)\n"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="מבצע בפועל. בלי הדגל הזה - dry-run בלבד.")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} בתיקייה הנוכחית.", file=sys.stderr)
        return 1

    raw = TARGET.read_bytes()
    used_crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")

    old_normalized = OLD_BLOCK.replace("\r\n", "\n")
    count = text.count(old_normalized)
    if count == 0:
        print("הבלוק לתיקון לא נמצא. ייתכן שהקובץ השתנה - יש לעדכן ידנית.", file=sys.stderr)
        return 1
    if count > 1:
        print(f"הבלוק נמצא {count} פעמים - לא ייחודי, עוצר.", file=sys.stderr)
        return 1

    new_text = text.replace(old_normalized, NEW_BLOCK.replace("\r\n", "\n"), 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת תחביר בקוד המתוקן: {e}", file=sys.stderr)
        return 1

    print("--- לפני ---")
    print(OLD_BLOCK)
    print("--- אחרי ---")
    print(NEW_BLOCK)

    if not args.apply:
        print("\nDry-run בלבד. הריצי עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(TARGET.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נשמר: {backup}")

    out_text = new_text.replace("\n", "\r\n") if used_crlf else new_text
    TARGET.write_bytes(out_text.encode("utf-8"))
    print(f"בוצע. {TARGET} עודכן.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
