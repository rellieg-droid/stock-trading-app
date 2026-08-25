"""
patch_macro_dynamic_sync.py

מטרה: לתקן את שדה "אירוע מאקרו ידוע" כך שהוא באמת מתעדכן כשמזיזים
את סליידר "חלון חסימה לפני דוח" -- לא רק בטעינה הראשונה.

הבעיה: text_input עם key זוכר את הערך שלו ב-session_state ומתעלם
מ-value= בהרצות הבאות (בדיוק כמו הבאג הידוע עם pt_cost).

הפתרון: לעדכן את st.session_state["strat_macro"] ישירות *לפני* יצירת
ה-widget, אבל רק אם המשתמשת עוד לא ערכה את השדה ידנית (מזוהה לפי
דגל נפרד _strat_macro_auto_val שמשווה לערך הנוכחי).

דורש שהפאץ' patch_wire_macro_events.py כבר הוחל.

שימוש:
    python patch_macro_dynamic_sync.py                 # dry-run (ברירת מחדל)
    python patch_macro_dynamic_sync.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "strategy_tab.py"

OLD_LINES = [
    'from macro_events import macro_event_within, get_macro_events',
    'from datetime import date as _mdate, timedelta as _mtd',
    '_macro_default = macro_event_within(blackout)',
    'macro = e6.text_input("אירוע מאקרו ידוע", value=_macro_default, key="strat_macro",',
]
# השורה השנייה (placeholder) לא נכללת ב-OLD_LINES כי אנחנו מזהים לפי הרישא בלבד

NEW_LINES = [
    'from macro_events import macro_event_within, get_macro_events',
    'from datetime import date as _mdate, timedelta as _mtd',
    '_macro_computed = macro_event_within(blackout)',
    'if "strat_macro" not in st.session_state:',
    '    st.session_state["strat_macro"] = _macro_computed',
    '    st.session_state["_strat_macro_auto_val"] = _macro_computed',
    'elif st.session_state.get("_strat_macro_auto_val") == st.session_state.get("strat_macro"):',
    '    st.session_state["strat_macro"] = _macro_computed',
    '    st.session_state["_strat_macro_auto_val"] = _macro_computed',
    'macro = e6.text_input("אירוע מאקרו ידוע", key="strat_macro",',
]


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

    raw_bytes = target.read_bytes()
    uses_crlf = b"\r\n" in raw_bytes
    text = raw_bytes.decode("utf-8")

    anchor = OLD_LINES[0]
    if text.count(anchor) != 1:
        print(f"שגיאה: העוגן {anchor!r} נמצא {text.count(anchor)} פעמים (צריך 1). לא בוצע שינוי.")
        print("(ייתכן שהפאץ' הקודם, patch_wire_macro_events.py, עוד לא הוחל)")
        sys.exit(1)

    indent = get_indent(text, anchor)
    eol = "\r\n" if uses_crlf else "\n"

    old_full_block = eol.join(indent + l for l in OLD_LINES)
    if old_full_block not in text:
        print("שגיאה: הבלוק הישן לא נמצא ברצף מדויק כמו שציפינו. לא בוצע שינוי.")
        sys.exit(1)
    if text.count(old_full_block) != 1:
        print(f"שגיאה: הבלוק נמצא {text.count(old_full_block)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    new_full_block = "\n".join(indent + l for l in NEW_LINES)

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
    print("לבדוק: הזזת סליידר 'חלון חסימה' אמורה לעדכן את שדה המאקרו מיד,")
    print("כל עוד לא ערכת אותו ידנית. אחרי עריכה ידנית, השדה אמור להישאר כמו שכתבת.")


if __name__ == "__main__":
    main()
