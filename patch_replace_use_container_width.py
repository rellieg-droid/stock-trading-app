"""
patch_replace_use_container_width.py

מטרה: להחליף את כל המופעים המיושנים (deprecated) של use_container_width
בפרמטר width החדש, לפי הנחיית Streamlit:
    use_container_width=True   ->  width="stretch"
    use_container_width=False  ->  width="content"

שימוש:
    python patch_replace_use_container_width.py                 # dry-run (ברירת מחדל)
    python patch_replace_use_container_width.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

REPLACEMENTS = [
    ("use_container_width=True", 'width="stretch"'),
    ("use_container_width=False", 'width="content"'),
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

    total_found = sum(text.count(old) for old, _ in REPLACEMENTS)
    if total_found == 0:
        print("לא נמצאו מופעים של use_container_width בקובץ. אין מה לתקן.")
        sys.exit(0)

    print("נמצאו המופעים הבאים:")
    for old, new in REPLACEMENTS:
        c = text.count(old)
        if c:
            print(f"  {old}  ->  {new}   ({c} מופעים)")

    new_text = text
    for old, new in REPLACEMENTS:
        new_text = new_text.replace(old, new)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("\n=== DRY RUN (לא בוצע שינוי) ===\n")
        old_lines = text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="לפני", tofile="אחרי", lineterm="")
        # מדפיסים רק שורות שינוי (+/-), לא את כל הקובץ
        for line in diff:
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                print(line)
        print(f"\nסה\"כ {total_found} מופעים ישונו. לביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"\nגיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן ({total_found} מופעים הוחלפו).")
    print("מומלץ להריץ את האפליקציה ולעבור על הטאבים המרכזיים (טבלאות, כפתורים, גרפים) לוודא שהעימוד לא נשבר.")


if __name__ == "__main__":
    main()
