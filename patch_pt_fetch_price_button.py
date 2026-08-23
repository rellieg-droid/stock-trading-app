"""
patch_pt_fetch_price_button.py

מטרה: להוסיף כפתור נפרד לצד שדה הסימול בטופס "הוסף מניה לתיק"
שמאפשר לשלוף את המחיר הנוכחי (get_live_price) וללחוץ עליו כדי למלא
אותו בשדה "מחיר קנייה ($)" -- בלי on_change על שדה הטקסט עצמו,
כדי לא לחזור על הבאג שבו שדה הסימול הפסיק להגיב.

שימוש:
    python patch_pt_fetch_price_button.py                 # dry-run (ברירת מחדל)
    python patch_pt_fetch_price_button.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

# מזהה ייחודי (ASCII-safe) שאמור להופיע פעם אחת בדיוק בקובץ המקורי (ללא פאצ'ים קודמים)
ANCHOR = 'key="pt_sym"'

NEW_BLOCK_TEMPLATE = (
    '{indent}with pa1:\n'
    '{indent}    _sym_col, _fetch_col = st.columns([4, 1])\n'
    '{indent}    with _sym_col:\n'
    '{indent}        pt_sym = st.text_input("\u05e1\u05d9\u05de\u05d5\u05dc", placeholder="AAPL", key="pt_sym").upper().strip()\n'
    '{indent}    with _fetch_col:\n'
    '{indent}        st.markdown(\'<div style="height:28px;"></div>\', unsafe_allow_html=True)\n'
    '{indent}        if st.button("\U0001f504", key="pt_fetch_price", help="\u05e9\u05dc\u05d5\u05e3 \u05de\u05d7\u05d9\u05e8 \u05e0\u05d5\u05db\u05d7\u05d9"):\n'
    '{indent}            if pt_sym:\n'
    '{indent}                _price = get_live_price(pt_sym)\n'
    '{indent}                if _price:\n'
    '{indent}                    st.session_state["pt_cost"] = round(float(_price), 2)\n'
    '{indent}                    st.rerun()\n'
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
        print("ייתכן שהפאץ' כבר הוחל בעבר -- בדקי את הקובץ ידנית לפני שממשיכים.")
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

    # ודאי שזו שורת ה-widget המצופה ולא, למשל, "if pt_sym:"
    if "st.text_input" not in original_line:
        print("שגיאה: השורה שנמצאה לא מכילה st.text_input כצפוי. לא בוצע שינוי.")
        print(f"תוכן השורה: {original_line!r}")
        sys.exit(1)

    stripped = original_line.lstrip(" ")
    indent = original_line[: len(original_line) - len(stripped)]

    new_block = NEW_BLOCK_TEMPLATE.format(indent=indent)
    new_lines = lines[:target_idx] + [new_block] + lines[target_idx + 1:]
    new_text = "".join(new_lines)

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

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"גיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן.")
    print("הריצי מחדש את Streamlit ובדקי: הקלדה בשדה הסימול אמורה לעבוד רגיל,")
    print("ולחיצה על כפתור 🔄 תמלא את מחיר הקנייה לפי המחיר הנוכחי.")


if __name__ == "__main__":
    main()
