#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
patch_trade_tab_rr.py
=====================
משלב את מנהל הפוזיציות (סיכון-סיכוי) בתוך TAB 4 — מסחר, בקובץ
alpha_paper_trading.py.

שלושה שינויים:
  1. ייבוא render_position_manager
  2. פונקציית עזר _rr_earnings_date — ממירה את הפלט של next_earnings
     (מחרוזת dd/mm/yyyy) לאובייקט date שהמודול מצפה לו
  3. קריאה ל-render_position_manager בסוף תת-הטאב "מסחר"

הסקריפט שומר על סיומות שורה מקוריות (CRLF) כדי שה-diff ב-git יישאר נקי.

הרצה:
    py patch_trade_tab_rr.py                # דמה בלבד
    py patch_trade_tab_rr.py --apply        # ביצוע, אחרי גיבוי עם חותמת זמן
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = "alpha_paper_trading.py"

# --- 1 + 2. ייבוא ופונקציית עזר, מוזרקים לפני שכבת הנתונים ---

OLD_HELPERS = '''def pf_val(p: dict) -> float:
    total = p['cash']
    for sym, pos in p['positions'].items():
        pr = get_live_price(sym)
        if pr: total += pos['shares'] * pr
    return total

# ── DATA LAYER ──
'''

NEW_HELPERS = '''def pf_val(p: dict) -> float:
    total = p['cash']
    for sym, pos in p['positions'].items():
        pr = get_live_price(sym)
        if pr: total += pos['shares'] * pr
    return total


# ── Risk / Reward ──
from rr_tab import render_position_manager


def _rr_earnings_date(symbol: str):
    """next_earnings מחזיר (dd/mm/yyyy, ימים). המודול צריך date בלבד."""
    try:
        res = next_earnings(symbol)
        if not res:
            return None
        return datetime.strptime(res[0], "%d/%m/%Y").date()
    except Exception:
        return None


def _rr_atr(symbol: str):
    """ATR יומי לסימול. משתמש ב-true_atr הקיים, שכבר מטפל ב-None."""
    try:
        return true_atr(load_ohlcv(symbol, "3mo", "1d"))
    except Exception:
        return None


# ── DATA LAYER ──
'''

# --- 3. הקריאה בסוף תת-הטאב "מסחר" ---

OLD_TRADE_END = '''            else:
                st.error(f"לא ניתן לטעון מחיר עבור {ticker}.")
'''

NEW_TRADE_END = '''            else:
                st.error(f"לא ניתן לטעון מחיר עבור {ticker}.")

            # ── ניהול יעדים לפוזיציות פתוחות ──
            st.markdown('<hr style="margin:16px 0 10px;"/>', unsafe_allow_html=True)
            st.markdown("#### ניהול יעדים לפוזיציות פתוחות")
            render_position_manager(
                positions=st.session_state.pf.get("positions", {}),
                price_fetcher=get_live_price,
                atr_fetcher=_rr_atr,
                earnings_fetcher=_rr_earnings_date,
                portfolio_value=pf_val(st.session_state.pf),
                key_prefix="pm_trade",
            )
'''

EDITS = [
    {"name": "ייבוא ופונקציות עזר של מודול הסיכון-סיכוי",
     "old": OLD_HELPERS, "new": NEW_HELPERS,
     "skip_if": "from rr_tab import render_position_manager"},
    {"name": "מנהל הפוזיציות בסוף תת-הטאב מסחר",
     "old": OLD_TRADE_END, "new": NEW_TRADE_END,
     "skip_if": "render_position_manager("},
]

DEPS = ("rr_engine.py", "rr_tab.py", "rr_guide.py")


def fail(msg: str) -> None:
    print(f"\n[עצירה] {msg}")
    print("לא בוצע שום שינוי בקובץ.")
    sys.exit(1)


def read_keep_eol(path: Path) -> tuple[str, str]:
    """קורא את הקובץ ומחזיר (טקסט עם \\n, סיומת השורה המקורית)."""
    with open(path, encoding="utf-8", newline="") as f:
        raw = f.read()
    eol = "\r\n" if raw.count("\r\n") > raw.count("\n") - raw.count("\r\n") else "\n"
    return raw.replace("\r\n", "\n"), eol


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="בצע בפועל")
    ap.add_argument("--path", default=TARGET, help="נתיב ל-alpha_paper_trading.py")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        fail(f"הקובץ לא נמצא: {path.resolve()}")

    for dep in DEPS:
        if not (path.parent / dep).exists():
            fail(f"חסר {dep} בתיקייה {path.parent.resolve()}")

    original, eol = read_keep_eol(path)
    print(f"סיומת שורה שזוהתה: {'CRLF' if eol == chr(13) + chr(10) else 'LF'}")

    text = original
    applied, skipped = [], []

    for edit in EDITS:
        if edit["skip_if"] in text:
            skipped.append(edit["name"])
            continue
        count = text.count(edit["old"])
        if count == 0:
            fail(f"עוגן לא נמצא עבור: {edit['name']}\n"
                 f"הקובץ כנראה נערך מאז. שלחי לי אותו ואתאים את הסקריפט.")
        if count > 1:
            fail(f"עוגן מופיע {count} פעמים עבור: {edit['name']}. "
                 f"החלפה לא חד-משמעית, ולכן בוטלה.")
        text = text.replace(edit["old"], edit["new"], 1)
        applied.append(edit["name"])

    for name in skipped:
        print(f"[דילוג] כבר קיים: {name}")

    if text == original:
        print("\nאין מה לשנות. השילוב כבר קיים.")
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
        print("\nזו הרצת דמה. להחלה בפועל:  py patch_trade_tab_rr.py --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.{stamp}.bak")
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", eol))
    print(f"\nבוצע. גיבוי נשמר ב: {backup.name}")
    print(f"שחזור:  copy /Y \"{backup.name}\" \"{path.name}\"")


if __name__ == "__main__":
    main()
