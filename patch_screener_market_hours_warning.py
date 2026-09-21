"""
פאץ': הוספת הודעת אזהרה בטאב הסורק (riskshield_tab.py) כאשר לא נמצא IV חי
לאף טיקר שנסרק - התרחיש הכי סביר: השוק האמריקאי סגור כרגע.

שימוש:
    python patch_screener_market_hours_warning.py            # dry-run - מציג תצוגה מקדימה בלבד
    python patch_screener_market_hours_warning.py --apply    # מבצע בפועל

מה זה עושה:
    - קורא את riskshield_tab.py כ-bytes גולמיים, שומר על סגנון שבירת השורות המקורי
      (זוהה LF-only בבדיקה האחרונה - לא CRLF כמו alpha_paper_trading.py, אבל
      הסקריפט מזהה זאת בעצמו ולא מניח)
    - מוצא עוגן ייחודי (חייב להופיע פעם אחת בדיוק, אחרת נכשל בקול)
    - מוסיף בדיקה: אם "iv" קיים בעמודות ה-DataFrame וכל הערכים בו הם NaN,
      מציג st.warning עם הסבר על שעות המסחר האמריקאיות
    - שומר גיבוי עם timestamp לפני כל שינוי
    - מריץ ast.parse על הקובץ המלא לפני הכתיבה, לוודא שה-syntax תקין
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "riskshield_tab.py"

ANCHOR = '            if scr_df.empty:\n                st.info("לא הוזנו טיקרים תקינים.")\n            else:\n                filt_cols = st.columns(2)\n'

INSERTION = '            if scr_df.empty:\n                st.info("לא הוזנו טיקרים תקינים.")\n            else:\n                _scr_all_iv_missing = "iv" in scr_df.columns and scr_df["iv"].isna().all()\n                if _scr_all_iv_missing:\n                    st.warning(\n                        "⚠️ לא נמצא IV חי (מחיר אופציות מהשוק) לאף אחד מהטיקרים שנסרקו - "\n                        "לכן שדות כמו סטרייק, פרמיה והסתברויות OTM לא חושבו, וטיקרים אלה "\n                        "מוסתרים כברירת מחדל. יתכן שהשוק האמריקאי סגור כרגע - שעות המסחר "\n                        "הן כ-15:30–22:00 שעון ישראל (עשוי לזוז שעה לפי שעון קיץ/חורף בארה\\"ב). "\n                        "אפשר גם להוריד את הסימון מ-\\"הסתר טיקרים שנכשלו\\" למטה כדי לראות "\n                        "את השורות הגולמיות."\n                    )\n\n                filt_cols = st.columns(2)\n'


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

    # לזהות את סגנון שבירת השורות בפועל - בודקים באמת ולא מניחים,
    # כדי לא לשבור קבצים CRLF בטעות
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

    patched_normalized = normalized.replace(ANCHOR, INSERTION, 1)

    # בדיקת syntax לפני כתיבה
    try:
        ast.parse(patched_normalized)
    except SyntaxError as e:
        print(f"[ERROR] Syntax check failed after patch: {e}", file=sys.stderr)
        sys.exit(1)

    print("[OK] Anchor found exactly once, syntax check passed.")
    print("--- Preview of inserted block ---")
    for line in INSERTION.splitlines():
        print(line)
    print("--- End preview ---")

    if not args.apply:
        print("\nDry-run only. הרצה עם --apply כדי לבצע בפועל.")
        return

    backup_path = target.with_suffix(target.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(target, backup_path)
    print(f"[OK] Backup saved: {backup_path}")

    final_text = patched_normalized.replace("\n", "\r\n") if is_crlf else patched_normalized
    target.write_bytes(final_text.encode("utf-8"))
    print(f"[OK] Patch applied to {target.resolve()}")


if __name__ == "__main__":
    main()
