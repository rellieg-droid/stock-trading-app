"""
patch_wire_macro_events.py

מטרה: לחבר את macro_events.py לטאב האסטרטגיה:
1. שדה "אירוע מאקרו ידוע" מתמלא אוטומטית אם יש אירוע מאקרו ידוע
   (FOMC/CPI) בתוך חלון החסימה שנבחר (blackout) -- עדיין ניתן לערוך/
   למחוק ידנית, והעריכה נשמרת (כמו כל text_input עם key).
2. מוצגת רשימת אירועי מאקרו קרובים ל-30 הימים הבאים מתחת לשדה.

דורש: macro_events.py באותה תיקייה.

שימוש:
    python patch_wire_macro_events.py                 # dry-run (ברירת מחדל)
    python patch_wire_macro_events.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "strategy_tab.py"

ANCHOR = 'macro = e6.text_input("אירוע מאקרו ידוע", value="", key="strat_macro",'

NEW_LINES = [
    'from macro_events import macro_event_within, get_macro_events',
    'from datetime import date as _mdate, timedelta as _mtd',
    '_macro_default = macro_event_within(blackout)',
    'macro = e6.text_input("אירוע מאקרו ידוע", value=_macro_default, key="strat_macro",',
    '                      placeholder="למשל: החלטת ריבית בשבוע הבא")',
    '_upcoming_macro = get_macro_events(start=_mdate.today(), end=_mdate.today() + _mtd(days=30))',
    'if _upcoming_macro:',
    '    _macro_lines = "  \\n".join(f"{d.strftime(\'%d/%m\')} - {lbl}" for d, lbl in _upcoming_macro[:5])',
    '    e6.caption(f"אירועים קרובים (30 יום):  \\n{_macro_lines}")',
]

# השורה השנייה של הקריאה המקורית (ה-placeholder) -- נמחקת כי היא כלולה כבר ב-NEW_LINES
SECOND_LINE_OF_ORIGINAL = 'placeholder="למשל: החלטת ריבית בשבוע הבא")'


def get_indent(text, anchor):
    idx = text.index(anchor)
    line_start = text.rfind("\n", 0, idx) + 1
    return text[line_start:idx]


def build_block_continue(indent, lines):
    first, rest = lines[0], lines[1:]
    parts = [first] + [indent + line for line in rest]
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="בצע בפועל (במקום dry-run)")
    args = parser.parse_args()

    target = Path(TARGET_FILE)
    if not target.exists():
        print(f"שגיאה: לא נמצא הקובץ {TARGET_FILE} בתיקייה הנוכחית.")
        sys.exit(1)

    if not Path("macro_events.py").exists():
        print("שגיאה: macro_events.py לא נמצא בתיקייה הנוכחית. יש להוריד אותו קודם.")
        sys.exit(1)

    raw_bytes = target.read_bytes()
    uses_crlf = b"\r\n" in raw_bytes
    text = raw_bytes.decode("utf-8")

    if text.count(ANCHOR) != 1:
        print(f"שגיאה: העוגן נמצא {text.count(ANCHOR)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    indent = get_indent(text, ANCHOR)

    # השורה השנייה המקורית (עם ה-placeholder) -- נצפה שהיא מיד אחרי העוגן, בהזחה עמוקה יותר
    idx_after_anchor = text.index(ANCHOR) + len(ANCHOR)
    rest_of_text = text[idx_after_anchor:]
    if SECOND_LINE_OF_ORIGINAL not in rest_of_text[:200]:
        print("שגיאה: השורה השנייה הצפויה (עם ה-placeholder) לא נמצאה מיד אחרי העוגן.")
        print("לא בוצע שינוי, כדי לא לפגוע בקוד בטעות.")
        sys.exit(1)

    # בונים את הבלוק הישן המלא (שתי השורות) להחלפה
    second_line_end_idx = rest_of_text.index(SECOND_LINE_OF_ORIGINAL) + len(SECOND_LINE_OF_ORIGINAL)
    old_full_block = text[text.index(ANCHOR): idx_after_anchor + second_line_end_idx]

    new_block = build_block_continue(indent, NEW_LINES).rstrip("\n")

    new_text = text.replace(old_full_block, new_block, 1)

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
            (new_block + "\n").splitlines(keepends=True),
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
    print("לבדוק ידנית בטאב 'אסטרטגיה': שדה 'אירוע מאקרו ידוע' מתמלא לבד אם")
    print("יש FOMC/CPI קרוב, ומתחתיו מופיעה רשימת אירועים ל-30 הימים הקרובים.")


if __name__ == "__main__":
    main()
