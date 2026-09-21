"""
patch_fix_table_header_contrast.py
=====================================
משנה את צבע כותרות הטבלה (.rs-table th) מאפור עמום (--c-text-2) ללבן
בהיר (--c-text-1) ומגביר את העובי - קריאות טובה יותר על רקע כהה.
משפיע על כל טבלאות ה-rs-table בקובץ (גם טבלת ההשוואה הקיימת וגם
טבלת הסורק החדשה) - שיפור כללי, לא ספציפי לטאב אחד.

שימוש:
    python patch_fix_table_header_contrast.py                 # dry-run
    python patch_fix_table_header_contrast.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR = '.rs-table th { color: var(--c-text-2, #8B93A7); font-weight:600; font-size:.82rem; }\n'
NEW = '.rs-table th { color: var(--c-text-1, #E7EAF0); font-weight:700; font-size:.82rem; }\n'


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
