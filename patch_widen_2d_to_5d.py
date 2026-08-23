"""
patch_widen_2d_to_5d.py

מטרה: בשלוש הפונקציות (load_market_group, load_market_movers, וקבוצת המניות
הישראליות) יש קריאה ל-yf.Ticker(...).history(period="2d") שמצפה לפחות ל-2
שורות נתונים (h["Close"].iloc[-1] ו-iloc[-2]).

period="2d" הוא טווח קלנדרי, לא טווח של ימי מסחר - סביב סופ"ש/חגים בבורסה
(במיוחד ת"א, שסגורה בשישי-שבת) הטווח הזה עלול לא לתפוס אף יום מסחר,
מה שגורם לשגיאת "possibly delisted / no price data found".

הפתרון: להרחיב ל-period="5d". הלוגיקה הקיימת (iloc[-1], iloc[-2]) ממילא
מביאה תמיד את שני ימי המסחר האחרונים בפועל, בלי קשר לכמה ימים קלנדריים
חלפו - כך שההרחבה בטוחה ולא משנה התנהגות, רק מוסיפה מרווח ביטחון.

שימוש:
    python patch_widen_2d_to_5d.py                 # dry-run (ברירת מחדל)
    python patch_widen_2d_to_5d.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

OLD = 'period="2d"'
NEW = 'period="5d"'


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

    count = text.count(OLD)
    if count == 0:
        print(f"לא נמצאו מופעים של {OLD} בקובץ. אין מה לתקן (ייתכן שכבר תוקן).")
        sys.exit(0)

    expected = 3
    if count != expected:
        print(f"שימי לב: נמצאו {count} מופעים, ציפיתי ל-{expected} לפי הסריקה הקודמת.")
        print("ממשיכים בכל זאת, אבל כדאי לבדוק את ה-diff בזהירות.")

    print(f"נמצאו {count} מופעים של {OLD} -> יוחלפו ב-{NEW}")

    new_text = text.replace(OLD, NEW)

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
        print(f"\nלביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"\nגיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן ({count} מופעים הוחלפו).")
    print("מומלץ להריץ את האפליקציה ולבדוק את הטאבים עם מניות ת\"א (Watchlist/שוק ישראלי) שהשגיאות נעלמו.")


if __name__ == "__main__":
    main()
