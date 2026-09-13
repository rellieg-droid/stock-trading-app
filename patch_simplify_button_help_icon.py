"""
patch_simplify_button_help_icon.py
=====================================
מסיר את הטקסט "מה הכפתור עושה" שליד סימן ה-❓ מעל כל כפתור - נשאר רק ה-❓
עצמו (עם ההסבר בריחוף, ב-title), באותו סגנון בדיוק כמו ליד שדות הקלט.

דורש: patch_add_button_help_icon.py כבר רץ (מוסיף את השורות עם ❓ שהפאץ'
הזה מקצר).

שימוש:
    python patch_simplify_button_help_icon.py            # dry-run
    python patch_simplify_button_help_icon.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

OLD_SUFFIX = "❓ מה הכפתור עושה</span>"
NEW_SUFFIX = "❓</span>"
EXPECTED_COUNT = 5


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    count = text.count(OLD_SUFFIX)
    if count != EXPECTED_COUNT:
        print(f"נמצאו {count} מופעים (צריך בדיוק {EXPECTED_COUNT}). לא בוצע שום שינוי.")
        return 1

    new_text = text.replace(OLD_SUFFIX, NEW_SUFFIX)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print(f"נמצאו {count} מופעים, כולם הוחלפו. ast.parse עבר בהצלחה.")

    if not args.apply:
        print("Dry-run בלבד. הרץ עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(f".py.{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נוצר: {backup}")

    out_bytes = new_text.replace("\n", line_style).encode("utf-8")
    TARGET.write_bytes(out_bytes)
    print(f"נכתב בהצלחה: {TARGET.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
