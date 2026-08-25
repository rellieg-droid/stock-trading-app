"""
patch_fetch_atm_iv_bid_filter.py

מטרה: בפונקציה fetch_atm_iv (strategy_data.py), לפני בחירת 3 האופציות
הקרובות ביותר לספוט (לכל צד - קולים/פוטים), לסנן רק אופציות עם bid > 0.
אופציה עם bid=0 היא לא נזילה (אין קונים בשוק), וה-impliedVolatility
שלה יכול להיות לא אמין / מיושן.

שימוש:
    python patch_fetch_atm_iv_bid_filter.py                 # dry-run (ברירת מחדל)
    python patch_fetch_atm_iv_bid_filter.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "strategy_data.py"

OLD_BLOCK_LINES = [
    'side = side.copy()',
    'side["_dist"] = (side["strike"] - spot).abs()',
    'frames.append(side.nsmallest(3, "_dist")["impliedVolatility"])',
]

NEW_BLOCK_LINES = [
    'side = side.copy()',
    'if "bid" in side:',
    '    side = side[side["bid"] > 0]',
    'if side.empty:',
    '    continue',
    'side["_dist"] = (side["strike"] - spot).abs()',
    'frames.append(side.nsmallest(3, "_dist")["impliedVolatility"])',
]


def get_indent(text, anchor):
    idx = text.index(anchor)
    line_start = text.rfind("\n", 0, idx) + 1
    return text[line_start:idx]


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

    anchor = OLD_BLOCK_LINES[0]  # 'side = side.copy()'
    occurrences = text.count(anchor)
    if occurrences == 0:
        print(f"שגיאה: העוגן {anchor!r} לא נמצא בקובץ. לא בוצע שינוי.")
        sys.exit(1)
    if occurrences > 1:
        print(f"שגיאה: העוגן {anchor!r} נמצא {occurrences} פעמים (צריך פעם אחת). לא בוצע שינוי.")
        sys.exit(1)

    indent = get_indent(text, anchor)

    old_full_block = "\n".join(indent + line for line in OLD_BLOCK_LINES)
    if old_full_block not in text:
        print("שגיאה: הבלוק המלא (3 השורות) לא נמצא ברצף מדויק כמו שציפינו.")
        print("ייתכן שהקוד כבר שונה, או שיש הבדל ברווחים. לא בוצע שינוי.")
        sys.exit(1)

    new_full_block = "\n".join(indent + line for line in NEW_BLOCK_LINES)

    new_text = text.replace(old_full_block, new_full_block, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        diff = difflib.unified_diff(
            old_full_block.splitlines(keepends=True),
            new_full_block.splitlines(keepends=True),
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
    print("ולבדוק ידנית שה-IV badge בכותרת עדיין מציג ערכים סבירים למניות פעילות.")


if __name__ == "__main__":
    main()
