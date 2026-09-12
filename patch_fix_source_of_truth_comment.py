"""
patch_fix_source_of_truth_comment.py
=====================================
מתקן את שורת ה-docstring שהייתה מיושנת: הקבצים הועברו מ-options_sim לתוך
Stock_tracking, וזה הפך למקור האמת בפועל. שינוי אחד, נפרד, לפי הכלל של
"בעיה אחת בכל פעם".

שימוש:
    python patch_fix_source_of_truth_comment.py            # dry-run
    python patch_fix_source_of_truth_comment.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("options_engine.py")

OLD = (
    "תלויות: ספריית התקן של פייתון בלבד.\n"
    "מקור אמת (source of truth): rellieg-droid/options-analysis.\n"
    "שינויים בלוגיקה שייכים לשם קודם, ומסונכרנים לכאן ידנית.\n"
)

NEW = (
    "תלויות: ספריית התקן של פייתון בלבד.\n"
    "מקור אמת (source of truth): rellieg-droid/stock-trading-app - קובץ זה.\n"
    "הקבצים הועברו מ-options_sim/options-analysis לכאן; אין יותר סנכרון ידני "
    "בין שני מיקומים.\n"
)


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

    count = text.count(OLD)
    if count != 1:
        print(f"עוגן נמצא {count} פעמים (צריך בדיוק 1). ייתכן שכבר עודכן בעבר. לא בוצע שינוי.")
        return 1

    new_text = text.replace(OLD, NEW, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("עוגן נמצא פעם אחת. ast.parse עבר בהצלחה.")

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
