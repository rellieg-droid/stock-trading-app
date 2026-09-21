"""
patch_add_delta_help.py
=========================
מרחיבה את ה-help של שדה "דלתא יעד לפוט" בטאב הסורק - במקום המשפט
הטכני הקצר, הסבר מלא על מה דלתא אומרת ומה השיקולים בבחירתה (בלי
להמליץ על ערך ספציפי - זה נשאר החלטה של המשתמשת).

שימוש:
    python patch_add_delta_help.py                 # dry-run
    python patch_add_delta_help.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR = (
    '            scr_delta = st.number_input(\n'
    '                "דלתא יעד לפוט", min_value=0.05, max_value=0.50, value=0.20, step=0.05,\n'
    '                key=f"{key_prefix}_scr_delta",\n'
    '                help="דלתא אחידה לכל הטיקרים - סטרייק שונה לכל מניה, אבל אותו \'עומק\' יחסי.",\n'
    '            )\n'
)

NEW = (
    '            scr_delta = st.number_input(\n'
    '                "דלתא יעד לפוט", min_value=0.05, max_value=0.50, value=0.20, step=0.05,\n'
    '                key=f"{key_prefix}_scr_delta",\n'
    '                help=(\n'
    '                    "|דלתא| ≈ ההסתברות (הניטרלית-סיכון) שהאופציה תיגמר בתוך הכסף. "\n'
    '                    "0.30-0.40: קרוב לכסף - פרמיה גבוהה יותר, וסיכוי גבוה יותר שהסטרייק ייפגע. "\n'
    '                    "0.15-0.20: טווח מקובל למכירת פרמיה מתונה. "\n'
    '                    "0.05-0.10: רחוק מהכסף - פרמיה קטנה, סיכוי גבוה לפקיעה חסרת ערך. "\n'
    '                    "הבחירה תלויה במטרה (הכנסה מול הגנה) ובסובלנות לסיכון - "\n'
    '                    "אין כאן ערך אחד שהוא \'נכון\'."\n'
    '                ),\n'
    '            )\n'
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

    anchor_normalized = ANCHOR.replace("\r\n", "\n")
    count = text.count(anchor_normalized)
    if count == 0:
        print("האנקור לא נמצא. ייתכן שהקובץ השתנה - יש לעדכן ידנית.", file=sys.stderr)
        return 1
    if count > 1:
        print(f"האנקור נמצא {count} פעמים - לא ייחודי, עוצר.", file=sys.stderr)
        return 1

    new_text = text.replace(anchor_normalized, NEW.replace("\r\n", "\n"), 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת תחביר בקוד החדש: {e}", file=sys.stderr)
        return 1

    print("--- לפני ---")
    print(ANCHOR)
    print("--- אחרי ---")
    print(NEW)

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
