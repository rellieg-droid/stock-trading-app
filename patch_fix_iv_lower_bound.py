"""
patch_fix_iv_lower_bound.py
============================
מתקן: implied_vol() ב-options_engine.py בודקת גבול עליון (market_price > price(hi))
אבל לא גבול תחתון. כשמחיר השוק שהוזן נמוך מהמחיר המינימלי שהמודל יכול לייצר
(ב-sigma=lo, כמעט 0), הביסקציה מתכנסת בשקט ל-lo ומחזירה ~0.0001 (מוצג כ-"0.0%")
במקום להרים שגיאה ברורה - בדיוק כמו שכבר קורה עבור הגבול העליון.

תרחיש טיפוסי שמפעיל את זה: בטאב "תנודתיות גלומה", ה-selectbox "סוג" נשאר על
ברירת המחדל "call" בזמן שהמחיר שהוזן מתאים ל-put (או להפך) - הפונקציה לא
מזהירה, רק מחזירה 0.0%.

שימוש:
    python patch_fix_iv_lower_bound.py <path_to_options_engine.py>            # dry-run
    python patch_fix_iv_lower_bound.py <path_to_options_engine.py> --apply    # מבצע בפועל

יש להריץ פעמיים - פעם אחת על מקור האמת (options-analysis) ופעם על ההעתק
ב-Stock_tracking, לפי הנוהג הקיים.
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

ANCHOR = (
    "    price = lambda v: bs_greeks(kind, S, K, T, v, r, q).price\n"
    "    if market_price > price(hi):\n"
    "        raise ValueError(\n"
    "            f\"price ${market_price:,.4f} exceeds the model at sigma={hi:.0%}; \"\n"
    "            \"widen hi or check the quote\"\n"
    "        )\n"
)

REPLACEMENT = (
    "    price = lambda v: bs_greeks(kind, S, K, T, v, r, q).price\n"
    "    if market_price > price(hi):\n"
    "        raise ValueError(\n"
    "            f\"price ${market_price:,.4f} exceeds the model at sigma={hi:.0%}; \"\n"
    "            \"widen hi or check the quote\"\n"
    "        )\n"
    "    if market_price < price(lo):\n"
    "        raise ValueError(\n"
    "            f\"price ${market_price:,.4f} is below the model at sigma={lo:.2%} \"\n"
    "            f\"(~${price(lo):,.4f}); check the quote or the call/put selection\"\n"
    "        )\n"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="הוספת בדיקת גבול תחתון ל-implied_vol")
    parser.add_argument("path", type=Path, help="נתיב ל-options_engine.py")
    parser.add_argument("--apply", action="store_true", help="לבצע בפועל (ברירת מחדל: dry-run)")
    args = parser.parse_args()

    if not args.path.exists():
        sys.exit(f"שגיאה: הקובץ לא נמצא: {args.path}")

    raw = args.path.read_bytes()
    uses_crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")  # נרמול פנימי לצורך התאמת העוגן

    if "if market_price < price(lo):" in text:
        sys.exit("הקובץ כבר מכיל את בדיקת הגבול התחתון - לא עושים כלום (אידמפוטנטי).")

    count = text.count(ANCHOR)
    if count == 0:
        sys.exit("שגיאה: העוגן לא נמצא בקובץ. ייתכן שהקובץ כבר תוקן, או שהתוכן שונה מהצפוי.")
    if count > 1:
        sys.exit(f"שגיאה: העוגן נמצא {count} פעמים. נדרש עוגן ייחודי - לא ממשיכים.")

    new_text = text.replace(ANCHOR, REPLACEMENT)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        sys.exit(f"שגיאת syntax אחרי הפאץ' - לא נכתב שום דבר: {e}")

    if not args.apply:
        print("DRY RUN - לא בוצע שום שינוי בפועל. הריצי שוב עם --apply כדי לבצע.")
        print("\n--- הקוד שיתווסף אחרי הבדיקה הקיימת ---")
        print(REPLACEMENT[len(ANCHOR):])
        return

    backup_path = args.path.with_name(
        args.path.name + f".{datetime.now():%Y%m%d_%H%M%S}.bak"
    )
    shutil.copy2(args.path, backup_path)
    print(f"גיבוי נשמר: {backup_path}")

    out_text = new_text.replace("\n", "\r\n") if uses_crlf else new_text
    args.path.write_bytes(out_text.encode("utf-8"))
    print(f"בוצע בהצלחה. עודכן: {args.path}")


if __name__ == "__main__":
    main()
