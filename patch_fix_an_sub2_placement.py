"""
patch_fix_an_sub2_placement.py

מטרה: לתקן באג מבני שבו בלוק "an_sub2" (טאב המשנה "AI ניתוח מתקדם")
נוצר בתוך container "tabbody_analysis" (שורה ~5089, יחד עם an_sub1/
an_sub3/an_sub4), אבל התוכן שלו בפועל (with an_sub2:) ממוקם בטעות
בתוך container אחר לגמרי - "tabbody_guide" (מדריך למשתמש) - ולא
לצד שאר טאבי המשנה שלו.

הפאץ' מעביר את כל הבלוק (מ-"with an_sub2:" ועד ממש לפני
container הבא, tabbody_compare) למיקום הנכון: מיד אחרי סיום
an_sub1, לפני an_sub3 -- כך שסדר הקוד יתאים לסדר ההגדרה
(an_sub1, an_sub2, an_sub3, an_sub4).

רמת ההזחה זהה בשני המקומות (4 רווחים), כך שאין צורך בהתאמת הזחה,
רק בהעברת הטקסט כמות שהוא.

שימוש:
    python patch_fix_an_sub2_placement.py                 # dry-run (ברירת מחדל)
    python patch_fix_an_sub2_placement.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

INSERT_ANCHOR = "    with an_sub3:"          # לפני זה נכניס את הבלוק המועבר
BLOCK_START_ANCHOR = "    with an_sub2:"      # תחילת הבלוק שצריך להעביר
BLOCK_END_ANCHOR = 'with st.container(key="tabbody_compare"):'  # קצה הבלוק (לא כולל)


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

    # אימות שכל העוגנים קיימים בדיוק פעם אחת, ובסדר הנכון
    for name, anchor in [("INSERT_ANCHOR", INSERT_ANCHOR),
                          ("BLOCK_START_ANCHOR", BLOCK_START_ANCHOR),
                          ("BLOCK_END_ANCHOR", BLOCK_END_ANCHOR)]:
        c = text.count(anchor)
        if c != 1:
            print(f"שגיאה: {name} ({anchor!r}) נמצא {c} פעמים (צריך פעם אחת בדיוק). לא בוצע שינוי.")
            sys.exit(1)

    insert_idx = text.index(INSERT_ANCHOR)
    block_start_idx = text.index(BLOCK_START_ANCHOR)
    block_end_idx = text.index(BLOCK_END_ANCHOR)

    if not (insert_idx < block_start_idx < block_end_idx):
        print("שגיאה: סדר העוגנים בקובץ לא כמו שציפינו (ייתכן שהבאג כבר תוקן, או שהקוד השתנה).")
        print(f"  insert_idx={insert_idx}, block_start_idx={block_start_idx}, block_end_idx={block_end_idx}")
        sys.exit(1)

    block_text = text[block_start_idx:block_end_idx]

    new_text = (
        text[:insert_idx]
        + block_text
        + text[insert_idx:block_start_idx]
        + text[block_end_idx:]
    )

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        print(f"הבלוק שיוזז: {block_text.count(chr(10))} שורות")
        print(f"מ: תוך tabbody_guide (אחרי המדריך למשתמש)")
        print(f"אל: תוך tabbody_analysis, מיד לפני an_sub3\n")
        old_lines = text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="לפני", tofile="אחרי", lineterm="", n=2))
        # מדפיסים רק את תחילת וסוף כל hunk כדי לא להציף - הדיף כאן ענק כי כל הבלוק "זז"
        print(f"סה\"כ {len(diff)} שורות diff (הבלוק כולו מוצג כמחיקה+הוספה בשני מקומות שונים).")
        print("להצגת הדיף המלא, אפשר להריץ עם --apply ואז 'git diff' על הקובץ.")
        print("\nלביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"גיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן.")
    print("קריטי לבדוק ידנית:")
    print("  1. טאב 'ניתוח' -> תת-טאב 'AI ניתוח מתקדם' -- אמור להופיע שם עכשיו, לא בטאב 'מדריך'")
    print("  2. טאב 'מדריך' -- אמור עדיין להציג את תוכן המדריך הרגיל, בלי AI ניתוח מתקדם")
    print("  3. הרצת git diff לפני commit, לוודא שההזזה נראית נקייה")


if __name__ == "__main__":
    main()
