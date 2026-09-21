"""
פאץ': הוספת bull_put_spread() ל-options_engine.py - תבנית ל-Bull Put Spread,
באותו דפוס בדיוק כמו protective_put()/collar()/iron_condor() הקיימים.
לא נוגע ב-riskshield_tab.py - זה פאץ' למנוע בלבד. חיבור למסך יבוא בפאץ' נפרד.

שימוש:
    python patch_add_bull_put_spread.py            # dry-run
    python patch_add_bull_put_spread.py --apply    # מבצע בפועל

מה זה עושה:
    - מוסיף פונקציה אחת: bull_put_spread(contracts, short_put, short_put_prem,
      long_put, long_put_prem) -> Position
    - משתמשת רק ב-Position/Leg הקיימים - אין נוסחה חדשה, כמו כל שאר
      התבניות בקובץ (iron_condor, collar וכו')
    - בודקת long_put < short_put ומרימה ValueError אם לא, באותו סגנון
      בדיוק כמו iron_condor
    - עוגן יחיד, גיבוי עם timestamp, בדיקת ast.parse לפני כתיבה,
      שימור סגנון שבירת שורות מקורי (LF/CRLF, מזוהה אוטומטית)
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "options_engine.py"

ANCHOR = '    return collar(shares, stock_entry, put_k, put_prem, best_k, best_prem)\n\n\ndef iron_condor(contracts: int,\n'
INSERTION = '    return collar(shares, stock_entry, put_k, put_prem, best_k, best_prem)\n\n\ndef bull_put_spread(contracts: int,\n                    short_put: float, short_put_prem: float,\n                    long_put: float, long_put_prem: float) -> Position:\n    """\n    מרווח פוטים בקרדיט: כותבים פוט בסטרייק הגבוה יותר (short_put),\n    קונים הגנה בסטרייק נמוך יותר (long_put). סיכון מוגדר מראש:\n    רוחב המרווח (short_put - long_put) פחות הקרדיט שהתקבל, כפול 100,\n    כפול חוזים - לא יותר מזה ולא פחות, עקב העובדה בסיכון מוגדר.\n    """\n    if not (long_put < short_put):\n        raise ValueError(\n            f"long_put must be below short_put, got long_put={long_put}, short_put={short_put}"\n        )\n    return Position(\n        name="Bull Put Spread",\n        legs=[\n            Leg("put", -1, contracts, short_put_prem, short_put, label="כתיבה"),\n            Leg("put", +1, contracts, long_put_prem, long_put, label="הגנה"),\n        ],\n    )\n\n\ndef iron_condor(contracts: int,\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually write the change (default: dry-run)")
    parser.add_argument("--file", default=TARGET_FILE, help=f"Path to {TARGET_FILE} (default: current directory)")
    args = parser.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"[ERROR] File not found: {target.resolve()}", file=sys.stderr)
        sys.exit(1)

    raw = target.read_bytes()
    is_crlf = raw.count(b"\r\n") > 0
    text = raw.decode("utf-8")
    normalized = text.replace("\r\n", "\n")

    count = normalized.count(ANCHOR)
    if count == 0:
        print("[ERROR] Anchor not found. הקובץ השתנה מאז שנכתב הפאץ' הזה - צריך לעדכן את העוגן.", file=sys.stderr)
        sys.exit(1)
    if count > 1:
        print(f"[ERROR] Anchor found {count} times - צריך עוגן ייחודי יותר.", file=sys.stderr)
        sys.exit(1)

    patched = normalized.replace(ANCHOR, INSERTION, 1)

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[ERROR] Syntax check failed after patch: {e}", file=sys.stderr)
        sys.exit(1)

    print("[OK] Anchor found exactly once, syntax check passed.")
    print("--- Preview of inserted function ---")
    for line in INSERTION.splitlines():
        print(line)
    print("--- End preview ---")

    if not args.apply:
        print("\nDry-run only. הרצה עם --apply כדי לבצע בפועל.")
        return

    backup_path = target.with_suffix(target.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(target, backup_path)
    print(f"[OK] Backup saved: {backup_path}")

    final_text = patched.replace("\n", "\r\n") if is_crlf else patched
    target.write_bytes(final_text.encode("utf-8"))
    print(f"[OK] Patch applied to {target.resolve()}")


if __name__ == "__main__":
    main()
