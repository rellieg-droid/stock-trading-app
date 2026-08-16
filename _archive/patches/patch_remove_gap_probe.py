#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
patch_remove_gap_probe.py
=========================
מסיר את כלי הדיבאג "אבחון מרווח" מ-strategy_tab.py.

נמחקים שלושה דברים:
  1. הצ'קבוקס "אבחון מרווח" בממשק
  2. הפונקציה _render_gap_probe
  3. הבלוק GAP_PROBE_JS (סקריפט ה-JS שסורק את ה-DOM)

הקוד לא נמחק לצמיתות — הוא נשאר בגיבוי ובהיסטוריית git, אז אפשר לשחזר
אותו אם בעיית המרווח ב-CSS תחזור.

הרצה:
    py patch_remove_gap_probe.py               # דמה בלבד
    py patch_remove_gap_probe.py --apply       # ביצוע, אחרי גיבוי עם חותמת זמן
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = "strategy_tab.py"

# מחיקת הצ'קבוקס: מחרוזת מדויקת
CHECKBOX_BLOCK = (
    '    if st.checkbox("אבחון מרווח", key="strat_gap_probe",\n'
    '                   help="סורק את העמוד ומדפיס אילו אלמנטים תופסים גובה ריק"):\n'
    '        _render_gap_probe()\n'
    '\n'
)

# מחיקת הבלוק הארוך: לפי עוגן פתיחה ועוגן סגירה, בלי להטמיע את ה-JS עצמו
SPAN_START = '\n\nGAP_PROBE_JS = """'
SPAN_END = 'components.html(GAP_PROBE_JS, height=320, scrolling=True)\n'


def fail(msg: str) -> None:
    print(f"\n[עצירה] {msg}")
    print("לא בוצע שום שינוי בקובץ.")
    sys.exit(1)


def cut_span(text: str) -> tuple[str, bool]:
    """מוחק את הקטע שבין שני העוגנים, כולל שניהם. מחזיר גם האם בוצע."""
    if SPAN_START not in text and "GAP_PROBE_JS" not in text:
        return text, False
    if text.count(SPAN_START) != 1:
        fail(f"עוגן הפתיחה של GAP_PROBE_JS מופיע {text.count(SPAN_START)} פעמים.")
    if text.count(SPAN_END) != 1:
        fail(f"עוגן הסגירה מופיע {text.count(SPAN_END)} פעמים.")
    i = text.index(SPAN_START)
    j = text.index(SPAN_END) + len(SPAN_END)
    if j <= i:
        fail("עוגן הסגירה מופיע לפני עוגן הפתיחה. הקובץ נערך ידנית.")
    return text[:i] + text[j:], True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="בצע בפועל")
    ap.add_argument("--path", default=TARGET, help="נתיב ל-strategy_tab.py")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        fail(f"הקובץ לא נמצא: {path.resolve()}")

    original = path.read_text(encoding="utf-8")
    text = original
    applied = []

    # 1. הצ'קבוקס
    count = text.count(CHECKBOX_BLOCK)
    if count == 1:
        text = text.replace(CHECKBOX_BLOCK, "", 1)
        applied.append("הצ'קבוקס \"אבחון מרווח\"")
    elif count > 1:
        fail(f"בלוק הצ'קבוקס מופיע {count} פעמים. החלפה לא חד-משמעית.")
    elif "strat_gap_probe" in text:
        fail("הצ'קבוקס קיים בקובץ אבל בנוסח שונה מהצפוי.\n"
             "ייתכן שנערך ידנית. שלחי לי את הקובץ ואתאים את הסקריפט.")
    else:
        print("[דילוג] הצ'קבוקס כבר לא קיים.")

    # 2 + 3. GAP_PROBE_JS ו-_render_gap_probe
    text, cut = cut_span(text)
    if cut:
        applied.append("GAP_PROBE_JS ו-_render_gap_probe")
    else:
        print("[דילוג] בלוק ה-JS כבר לא קיים.")

    # ודא שלא נשארה הפניה יתומה
    leftovers = [n for n in ("GAP_PROBE_JS", "_render_gap_probe", "strat_gap_probe")
                 if n in text]
    if leftovers:
        fail("נשארו הפניות יתומות בקובץ: " + ", ".join(leftovers) +
             "\nהמחיקה לא שלמה, ולכן בוטלה.")

    if text == original:
        print("\nאין מה לשנות. הכלי כבר הוסר.")
        return

    diff = difflib.unified_diff(
        original.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=f"a/{path.name}", tofile=f"b/{path.name}", n=2,
    )
    print("\n" + "".join(diff))
    print(f"שינויים מתוכננים: {len(applied)}")
    for name in applied:
        print(f"  · {name}")
    removed_lines = len(original.splitlines()) - len(text.splitlines())
    print(f"סה\"כ {removed_lines} שורות יימחקו.")

    if not args.apply:
        print("\nזו הרצת דמה. להחלה בפועל:  py patch_remove_gap_probe.py --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.{stamp}.bak")
    shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8")
    print(f"\nבוצע. גיבוי נשמר ב: {backup.name}")
    print(f"שחזור:  copy /Y \"{backup.name}\" \"{path.name}\"")


if __name__ == "__main__":
    main()
