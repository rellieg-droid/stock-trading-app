"""
patch_fix_ta_tickers.py

מטרה: לתקן טיקרים שגויים של מניות ת"א בקוד, שגילינו כגורם ל"possibly
delisted" (לא בעיית period, אלא סימולים שגויים/מתים):

    CHKP.TA  -> CHKP      (Check Point נסחרת בנאסד"ק בלבד ב-Yahoo, לא כ-.TA)
    SANO.TA  -> SANO1.TA  (טעות בסימול)
    HAPO.TA  -> POLI.TA   (בנק הפועלים, טעות בסימול)
    MIZR.TA  -> MZTF.TA   (מזרחי טפחות, טעות בסימול)
    SPNS.TA  -> EVGN.TA   (Sapiens נמחקה מהמסחר ב-2025 לאחר רכישה;
                           הוחלפה ב-Evogene, חברת ביוטק ישראלית פעילה,
                           נשארת בקטגוריית "ביומד")

EMCO.TA נשאר ללא שינוי -- הטיקר מאומת כנכון, אך yfinance מחזיר נתונים
ריקים; כנראה מניה לא נזילה. נשאר לניטור בבאקלוג בנפרד.

שימוש:
    python patch_fix_ta_tickers.py                 # dry-run (ברירת מחדל)
    python patch_fix_ta_tickers.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

REPLACEMENTS = [
    ('"CHKP.TA"', '"CHKP"'),
    ('"SANO.TA"', '"SANO1.TA"'),
    ('"HAPO.TA"', '"POLI.TA"'),
    ('"MIZR.TA"', '"MZTF.TA"'),
    ('"SPNS.TA"', '"EVGN.TA"'),
]


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

    total_found = sum(text.count(old) for old, _ in REPLACEMENTS)
    if total_found == 0:
        print("לא נמצאו מופעים של אף אחד מהטיקרים השגויים בקובץ. אין מה לתקן.")
        sys.exit(0)

    print("נמצאו המופעים הבאים:")
    for old, new in REPLACEMENTS:
        c = text.count(old)
        if c:
            print(f"  {old}  ->  {new}   ({c} מופעים)")
        else:
            print(f"  {old}  ->  {new}   (0 מופעים -- לא נמצא, מדלגים)")

    new_text = text
    for old, new in REPLACEMENTS:
        new_text = new_text.replace(old, new)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("\n=== DRY RUN (לא בוצע שינוי) ===\n")
        old_lines = text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="לפני", tofile="אחרי", lineterm="")
        for line in diff:
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                print(line)
        print(f"\nסה\"כ {total_found} מופעים ישונו. לביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"\nגיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן ({total_found} מופעים הוחלפו).")
    print("מומלץ להריץ את האפליקציה ולבדוק את הטאבים עם מניות ת\"א (Watchlist/שוק ישראלי) שהשגיאות נעלמו.")


if __name__ == "__main__":
    main()
