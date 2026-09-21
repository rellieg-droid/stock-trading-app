"""
patch_add_breakeven.py
========================
מוסיף ל-options_engine.py: short_put_breakeven() - נקודת האיזון של שורט-פוט
(הסטרייק פחות הפרמיה). פונקציה טהורה, טריוויאלית, אבל ממורכזת במקום אחד
כדי שלא תיכתב שוב בכל מקום שצריך אותה.

שימוש:
    python patch_add_breakeven.py            # dry-run
    python patch_add_breakeven.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("options_engine.py")

ANCHOR = (
    "def insurance_cost(premium: float, contracts: float) -> float:\n"
    "    \"\"\"עלות הביטוח בדולרים: פרמיה × 100 × חוזים. לא כולל עמלות (מתווספות בשכבת ה-UI אם רלוונטי).\"\"\"\n"
    "    return premium * CONTRACT_MULTIPLIER * contracts\n"
)

NEW_CODE = '''

def short_put_breakeven(strike: float, premium: float) -> float:
    """
    נקודת האיזון של שורט-פוט: המחיר שמתחתיו העסקה מתחילה להפסיד בפועל
    (אחרי שהפרמיה כבר כוסתה במלואה). strike - premium, לא יותר מזה -
    אבל ממורכז כאן כדי שלא ייכתב שוב בכל מקום.
    """
    return strike - premium
'''


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

    count = text.count(ANCHOR)
    if count != 1:
        print(f"עוגן נמצא {count} פעמים (צריך בדיוק 1). לא בוצע שינוי.")
        return 1

    new_text = text.replace(ANCHOR, ANCHOR + NEW_CODE, 1)

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
