#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
patch_strategy_rr.py
====================
משלב את מודול הסיכון-סיכוי בתוך טאב האסטרטגיה הקיים.

שני שינויים בלבד ב-strategy_tab.py:
  1. ייבוא render_rr_section
  2. קריאה לו מיד אחרי _render_position, בתוך הענף if report.position

הרצה:
    py patch_strategy_rr.py                 # דמה בלבד, מדפיס diff, לא נוגע בקובץ
    py patch_strategy_rr.py --apply         # מבצע, אחרי גיבוי עם חותמת זמן
    py patch_strategy_rr.py --apply --path C:\\...\\strategy_tab.py

הסקריפט עוצר אם עוגן חסר או מופיע יותר מפעם אחת.
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = "strategy_tab.py"

EDITS = [
    {
        "name": "ייבוא render_rr_section",
        "old": (
            "import strategy_data as sd\n"
            "import strategy_engine as se\n"
            "from strategy_guide import render_strategy_guide\n"
        ),
        "new": (
            "import strategy_data as sd\n"
            "import strategy_engine as se\n"
            "from strategy_guide import render_strategy_guide\n"
            "from rr_tab import render_rr_section\n"
        ),
        "skip_if": "from rr_tab import render_rr_section",
    },
    {
        "name": "קריאה ל-render_rr_section אחרי תוכנית הפוזיציה",
        "old": (
            "    if report.position:\n"
            "        _render_position(report.position)\n"
            "    elif report.verdict in (\"WAIT\", \"AVOID\"):\n"
        ),
        "new": (
            "    if report.position:\n"
            "        _render_position(report.position)\n"
            "        render_rr_section(\n"
            "            ticker=report.ticker,\n"
            "            entry=report.position.entry_price,\n"
            "            stop=report.position.stop_price,\n"
            "            shares=report.position.final_shares,\n"
            "            portfolio_value=portfolio,\n"
            "            key_prefix=\"strat_rr\",\n"
            "            interactive=False,   # אפס ווידג'טים = אפס rerun שמוחק את הסקאן\n"
            "        )\n"
            "    elif report.verdict in (\"WAIT\", \"AVOID\"):\n"
        ),
        "skip_if": "render_rr_section(",
    },
]


def fail(msg: str) -> None:
    print(f"\n[עצירה] {msg}")
    print("לא בוצע שום שינוי בקובץ.")
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="בצע בפועל")
    ap.add_argument("--path", default=TARGET, help="נתיב ל-strategy_tab.py")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        fail(f"הקובץ לא נמצא: {path.resolve()}")

    # בדיקת תלות: הקבצים החדשים חייבים לשבת ליד היעד
    for dep in ("rr_engine.py", "rr_tab.py"):
        if not (path.parent / dep).exists():
            fail(f"חסר {dep} בתיקייה {path.parent.resolve()}")

    original = path.read_text(encoding="utf-8")
    text = original
    applied, skipped = [], []

    for edit in EDITS:
        if edit["skip_if"] in text:
            skipped.append(edit["name"])
            continue
        count = text.count(edit["old"])
        if count == 0:
            fail(f"עוגן לא נמצא עבור: {edit['name']}\n"
                 f"ייתכן שהקובץ השתנה. אל תערוך ידנית — שלחי לי את הקובץ המעודכן.")
        if count > 1:
            fail(f"עוגן מופיע {count} פעמים עבור: {edit['name']}. "
                 f"החלפה לא חד-משמעית.")
        text = text.replace(edit["old"], edit["new"], 1)
        applied.append(edit["name"])

    for name in skipped:
        print(f"[דילוג] כבר קיים: {name}")

    if text == original:
        print("\nאין מה לשנות. הקובץ כבר משולב.")
        return

    diff = difflib.unified_diff(
        original.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=f"a/{path.name}", tofile=f"b/{path.name}", n=3,
    )
    print("\n" + "".join(diff))
    print(f"שינויים מתוכננים: {len(applied)}")
    for name in applied:
        print(f"  · {name}")

    if not args.apply:
        print("\nזו הרצת דמה. להחלה בפועל:  py patch_strategy_rr.py --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.{stamp}.bak")
    shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8")
    print(f"\nבוצע. גיבוי נשמר ב: {backup.name}")
    print("שחזור במקרה הצורך:")
    print(f"  copy /Y \"{backup.name}\" \"{path.name}\"")


if __name__ == "__main__":
    main()
