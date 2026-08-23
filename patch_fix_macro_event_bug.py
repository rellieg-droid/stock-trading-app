"""
patch_fix_macro_event_bug.py

מטרה: לתקן באג ב-build_events_criterion (strategy_engine.py) שבו
macro_event מתעלם לגמרי כאשר יש תאריך דוחות ידוע (days_to_earnings
is not None). במצב הזה, הקריטריון "עובר" (passed=True) גם אם יש
אירוע מאקרו קרוב, כל עוד הדוח עצמו רחוק מספיק -- למרות שה-meaning
הטקסטואלי כן מזהיר על אירוע המאקרו. אחרי התיקון, macro_event תמיד
פוסל את הקריטריון כשהוא לא ריק, גם אם days_to_earnings אינו None.

שימוש:
    python patch_fix_macro_event_bug.py                 # dry-run (ברירת מחדל)
    python patch_fix_macro_event_bug.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "strategy_engine.py"

OLD_BLOCK = (
    "    passed = None\n"
    "    if days_to_earnings is None:\n"
    "        passed = True if macro_event is None else False\n"
    "    else:\n"
    "        passed = days_to_earnings > cfg.earnings_blackout_days\n"
)

NEW_BLOCK = (
    "    passed = None\n"
    "    if days_to_earnings is None:\n"
    "        passed = True if macro_event is None else False\n"
    "    else:\n"
    "        passed = (days_to_earnings > cfg.earnings_blackout_days) and (macro_event is None)\n"
)


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

    occurrences = text.count(OLD_BLOCK)
    if occurrences == 0:
        print("שגיאה: הבלוק המקורי לא נמצא בקובץ בדיוק כמו שציפינו.")
        print("ייתכן שהקוד כבר שונה, או שיש הבדל ברווחים/שורות. לא בוצע שינוי.")
        print("\nמחפשת את השורה עם 'passed = days_to_earnings >' לאבחון:\n")
        for i, line in enumerate(text.splitlines(), start=1):
            if "passed = days_to_earnings" in line or "passed = (days_to_earnings" in line:
                print(f"  שורה {i}: {line!r}")
        sys.exit(1)
    if occurrences > 1:
        print(f"שגיאה: הבלוק נמצא {occurrences} פעמים (צריך פעם אחת). לא בוצע שינוי, כדי למנוע טעות.")
        sys.exit(1)

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        diff = difflib.unified_diff(
            OLD_BLOCK.splitlines(keepends=True),
            NEW_BLOCK.splitlines(keepends=True),
            fromfile="לפני", tofile="אחרי", lineterm=""
        )
        print("".join(diff))
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
    print("מומלץ להריץ python.exe -m pytest test_strategy_engine.py כדי לוודא שהכל עדיין ירוק,")
    print("ולבדוק ידנית בטאב האסטרטגיה שמילוי 'אירוע מאקרו ידוע' יחד עם דוח רחוק גורם לקריטריון להיכשל.")


if __name__ == "__main__":
    main()
