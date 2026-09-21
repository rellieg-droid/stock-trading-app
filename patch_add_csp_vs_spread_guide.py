"""
פאץ': מדריך מוצג (expander) שמסביר את ההבדל בין CSP ל-Bull Put Spread -
למה הביטחונות כל כך שונים, מה המחיר של ההגנה, ואיך לקרוא את יחס
קרדיט/רוחב. באותה תבנית בדיוק כמו שני מדריכי ה-expander הקיימים
בקובץ (📖 מדריך: ...). מיד אחרי כרטיס "השוואת הון וביטחונות".

שימוש:
    python patch_add_csp_vs_spread_guide.py            # dry-run
    python patch_add_csp_vs_spread_guide.py --apply    # מבצע בפועל

דורש ש-patch_capital_comparison_table.py כבר הוחל.
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "riskshield_tab.py"

ANCHOR = '            _card(\n                "השוואת הון וביטחונות - CSP מול Bull Put Spread",\n                f"{_cmp_table_html}{_cmp_explain}",\n            )\n\n            # --- בדיקות מול ספים נפוצים: DTE, יחס קרדיט/רוחב, נזילות -------\n'
INSERTION = '            _card(\n                "השוואת הון וביטחונות - CSP מול Bull Put Spread",\n                f"{_cmp_table_html}{_cmp_explain}",\n            )\n\n            with st.expander("📖 מדריך: מה ההבדל בין CSP ל-Bull Put Spread, ולמה הביטחונות כל כך שונים"):\n                st.markdown(\n                    \'<div class="rs-explain"><b>מה זה בכלל CSP?</b><br>כשמוכרים פוט "מוגן במזומן" (Cash-Secured Put), הברוקר דורש שתחזיקי בחשבון את כל הסכום שיידרש אם תצטרכי לקנות את המניה במחיר הסטרייק - זו הסיבה שבטבלה אפשר לראות ביטחונות שמגיעים ל-100% ומעלה מהתיק - זה לא באג, זה בדיוק מה שקורה במציאות: אם המניה תיפול, הברוקר ידרוש ממך לקנות את כל המניות במחיר הסטרייק, ולכן הוא נועל את כל הסכום מראש - גם אם ההפסד המרבי בפועל קטן יותר (סטרייק פחות פרמיה, לא הסטרייק המלא).<br><br><b>מה שונה ב-Bull Put Spread?</b><br>עם אותה כתיבה בדיוק, קונים גם פוט הגנה בסטרייק נמוך יותר. ההגנה "עוצרת" את ההפסד המרבי ברוחב שבין שני הסטרייקים פחות הקרדיט שקיבלת - מספר ידוע מראש, במקום חושף של כל הסטרייק כמו ב-CSP. לכן הברוקר דורש הרבה פחות ביטחונות - בדוגמה שלמעלה, 1% בלבד מהתיק, לעומת 120%-360% ב-CSP.<br><br><b>המחיר של ה"הנחה" הזו</b><br>זה לא "ארוחת חינם" - שני דברים משתנים בתמורה: הפרמיה שמקבלים קטנה יותר (חלק ממנה הולך לקניית ההגנה), והרווח המקסימלי מוגבל לקרדיט הנטו שקיבלת - בעוד שב-CSP הרווח המקסימלי הוא כל הפרמיה שקיבלת, בלי תקרה.<br><br><b>איך לקרוא את יחס קרדיט/רוחב לאור ההסבר הזה</b><br>היחס מודד כמה מהרוחב המקסימלי בפועל מגיע בחזרה כקרדיט. יחס נמוך מדי מעיד שההגנה "אוכלת" חלק גדול מדי מהפרמיה - זו הסיבה שהכרטיס של מעלה מציג עובדתית (סף נפוץ: 20%-30%) - לא קביעה שמתאימה לכל מצב.</div>\',\n                    unsafe_allow_html=True,\n                )\n\n            # --- בדיקות מול ספים נפוצים: DTE, יחס קרדיט/רוחב, נזילות -------\n'


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
    print("--- Preview ---")
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
