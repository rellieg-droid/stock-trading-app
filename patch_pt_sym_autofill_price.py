"""
patch_pt_sym_autofill_price.py

מטרה: כשמקלידים סימול בטופס "הוסף מניה לתיק" (Portfolio Tracker),
המחיר הנוכחי (get_live_price) יתמלא אוטומטית בשדה "מחיר קנייה ($)".
עדיין ניתן לערוך את המחיר ידנית לפני לחיצה על "הוסף".

שימוש:
    python patch_pt_sym_autofill_price.py                 # dry-run (ברירת מחדל) - מציג diff בלבד
    python patch_pt_sym_autofill_price.py --apply          # מבצע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

# מזהה ייחודי (ASCII-safe, לא תלוי בקידוד עברית) שאמור להופיע פעם אחת בדיוק
ANCHOR = 'key="pt_sym"'

NEW_BLOCK_TEMPLATE = (
    '{indent}with pa1:\n'
    '{indent}    def _pt_sym_autofill():\n'
    '{indent}        _sym = st.session_state.get("pt_sym", "").upper().strip()\n'
    '{indent}        if _sym:\n'
    '{indent}            _price = get_live_price(_sym)\n'
    '{indent}            if _price:\n'
    '{indent}                st.session_state["pt_cost"] = round(float(_price), 2)\n'
    '{indent}    pt_sym = st.text_input("\u05e1\u05d9\u05de\u05d5\u05dc", placeholder="AAPL", '
    'key="pt_sym", on_change=_pt_sym_autofill).upper().strip()\n'
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

    occurrences = text.count(ANCHOR)
    if occurrences == 0:
        print("שגיאה: העוגן (anchor) לא נמצא בקובץ. לא בוצע שינוי.")
        print("\nמחפש שורות עם 'pt_sym' כדי לעזור באבחון:\n")
        for i, line in enumerate(text.splitlines(), start=1):
            if "pt_sym" in line:
                print(f"  שורה {i}: {line!r}")
        print("\nהעתיקי את השורות שהודפסו כאן חזרה לצ'אט כדי שנוכל להתאים את העוגן.")
        sys.exit(1)
    if occurrences > 1:
        print(f"שגיאה: העוגן נמצא {occurrences} פעמים (צריך בדיוק פעם אחת). לא בוצע שינוי, כדי למנוע טעות.")
        sys.exit(1)

    lines = text.splitlines(keepends=True)
    target_idx = None
    for i, line in enumerate(lines):
        if ANCHOR in line:
            target_idx = i
            break

    if target_idx is None:
        print("שגיאה לא צפויה: לא אותר מיקום השורה.")
        sys.exit(1)

    original_line = lines[target_idx]
    stripped = original_line.lstrip(" ")
    indent = original_line[: len(original_line) - len(stripped)]

    new_block = NEW_BLOCK_TEMPLATE.format(indent=indent)
    new_lines = lines[:target_idx] + [new_block] + lines[target_idx + 1:]
    new_text = "".join(new_lines)

    # אימות syntax
    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        diff = difflib.unified_diff(
            [original_line], [new_block],
            fromfile="לפני", tofile="אחרי", lineterm=""
        )
        print("".join(diff))
        print("\nלביצוע בפועל, הריצי עם --apply")
        return

    # גיבוי עם timestamp
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"גיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        # שימור CRLF (הקובץ המקורי נשמר עם CRLF)
        # ה-splitlines(keepends=True) כבר שימר את סופי השורות המקוריים בכל שורה שלא נגענו בה,
        # והבלוק החדש כתוב עם \n בלבד — נמיר ל-CRLF כדי לשמור עקביות בכל הקובץ.
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן.")
    print("מומלץ להריץ את האפליקציה ולבדוק שהמחיר מתמלא אוטומטית בעת הקלדת סימול.")


if __name__ == "__main__":
    main()
