"""
patch_add_missing_re_import.py

מטרה: תיקון NameError: name 're' is not defined -- הפאץ' הקודם
(patch_fix_view_window.py) הוסיף פונקציה שמשתמשת ב-re.match, אבל
הזיהוי האוטומטי טעה וחשב בטעות ש-'import re' כבר קיים בקובץ,
אז לא הוסיף אותו. הפאץ' הזה מוסיף אותו בוודאות, ממש לפני
def _view_window_start.

שימוש:
    python patch_add_missing_re_import.py                 # dry-run (ברירת מחדל)
    python patch_add_missing_re_import.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

ANCHOR = "def _view_window_start(period_str, last_ts):"


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

    occurrences = text.count(ANCHOR)
    if occurrences == 0:
        print(f"שגיאה: העוגן {ANCHOR!r} לא נמצא בקובץ. לא בוצע שינוי.")
        print("(ייתכן שהפאץ' הקודם, patch_fix_view_window.py, עוד לא הוחל)")
        sys.exit(1)
    if occurrences > 1:
        print(f"שגיאה: העוגן נמצא {occurrences} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    # בדיקה מדויקת (לא סובלנית לזיהוי שגוי): האם יש שורה שהיא בדיוק "import re"
    # לפני העוגן, ברמת המודול (בלי הזחה)?
    before_anchor = text[: text.index(ANCHOR)]
    lines_before = before_anchor.replace("\r\n", "\n").split("\n")
    already_imported = any(line.strip() == "import re" for line in lines_before)
    if already_imported:
        print("נמצאה שורת 'import re' אמיתית לפני הפונקציה -- אין צורך בשינוי.")
        sys.exit(0)

    indent = get_indent(text, ANCHOR)
    new_block = indent + "import re\n" + indent + ANCHOR

    new_text = text.replace(indent + ANCHOR, new_block, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        diff = difflib.unified_diff(
            [indent + ANCHOR], [new_block],
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
    print("הריצי מחדש את Streamlit ובדקי שה-NameError נעלם ושהגרף עובד תקין.")


if __name__ == "__main__":
    main()
