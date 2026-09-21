# -*- coding: utf-8 -*-
"""
patch_add_tracker_to_guide.py

Adds a short explanation of the "📒 מעקב פרמיות" tab to the existing
"📖 מדריך: מה ההבדל בין הטאבים, ומה זה אומר" expander inside
render_riskshield_tab().

The anchor was verified against the actual uploaded riskshield_tab.py
(occurs exactly once).

Usage:
    python patch_add_tracker_to_guide.py            # dry run
    python patch_add_tracker_to_guide.py --apply    # applies the patch
"""

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = Path("riskshield_tab.py")

ANCHOR = (
    "            'צפויה, סטרס טסט, CVaR, וטבלת הגנה (לצד קניית פוט).'\n"
    "            '</div>',"
)

INSERT = (
    "            'צפויה, סטרס טסט, CVaR, וטבלת הגנה (לצד קניית פוט).<br><br>'\n"
    "            '<b>📒 מעקב פרמיות</b>: לא חישוב תיאורטי בכלל - יומן בפועל של "
    "פוזיציות PUT שמכרת. רושמים כל מכירה (סימבול, סטרייק, פרמיה), ומסמנים איך "
    "היא נסגרה (פקעה חסרת ערך / נקנתה בחזרה / הוקצתה) - והטאב מחשב לבד כמה "
    "פרמיה נגבתה בסך הכול, כמה כבר מומש כרווח, וכמה עדיין \"תלוי באוויר\" "
    "בפוזיציות פתוחות. אפשר גם למשוך נתונים ישירות מטאב הסתברות OTM במקום "
    "להקליד הכול ידנית.'\n"
    "            '</div>',"
)


def read_normalized(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    was_crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    if was_crlf:
        text = text.replace("\r\n", "\n")
    return text, was_crlf


def write_normalized(path: Path, text: str, restore_crlf: bool) -> None:
    if restore_crlf:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    if not TARGET_FILE.exists():
        print(f"[FAIL] {TARGET_FILE} not found in current directory")
        sys.exit(1)

    text, was_crlf = read_normalized(TARGET_FILE)

    count = text.count(ANCHOR)
    if count == 0:
        print(f"[FAIL] anchor not found: {ANCHOR!r}")
        sys.exit(1)
    if count > 1:
        print(f"[FAIL] anchor found {count} times (expected exactly 1)")
        sys.exit(1)
    print("[OK] anchor found exactly once")

    patched = text.replace(ANCHOR, INSERT, 1)

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[FAIL] Patched file would not parse: {e}")
        sys.exit(1)
    print("[OK] Patched content passes ast.parse")

    if not args.apply:
        print("\n--- DRY RUN — no changes written. Re-run with --apply to write. ---")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = TARGET_FILE.with_suffix(TARGET_FILE.suffix + f".{timestamp}.bak")
    shutil.copy2(TARGET_FILE, backup_path)
    print(f"[OK] Backup written to {backup_path}")

    write_normalized(TARGET_FILE, patched, restore_crlf=was_crlf)
    print(f"[OK] {TARGET_FILE} patched (CRLF preserved: {was_crlf})")


if __name__ == "__main__":
    main()
