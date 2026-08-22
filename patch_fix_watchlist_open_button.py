#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fix_watchlist_open_button.py

מטרה: מתקן את כפתור "📈 פתח <סימול>" בכרטיסי Watchlist. הוא כבר החליף
את הטיקר הפעיל (st.session_state.ticker), אבל לא החליף את קבוצת
הניווט העליונה הפעילה (st.session_state.active_group), ולכן המשתמשת
נשארה ויזואלית בטאב Watchlist גם אחרי הלחיצה — הטיקר התחלף "מתחת"
לטאב הלא-נכון.

מבנה הניווט: "📈 גרף" שייך לקבוצה "גרף" (NAV_GROUPS), שיש לה תת-טאב
יחיד — ולכן מספיק להגדיר את הקבוצה, בלי צורך במפתח sub_<group> נפרד.

שימוש:
    python patch_fix_watchlist_open_button.py                 # dry-run (ברירת מחדל)
    python patch_fix_watchlist_open_button.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: alpha_paper_trading.py (CRLF)
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    "                    # click to navigate\r\n"
    "                    if wcols[j].button(f\"\U0001f4c8 \u05e4\u05ea\u05d7 {r['sym']}\", key=f\"wl_open_{i}_{j}\"):\r\n"
    '                        st.session_state.ticker = r["sym"]\r\n'
    "                        st.session_state.ai_res = None\r\n"
    "                        st.rerun()\r\n"
)

NEW_BLOCK = (
    "                    # click to navigate\r\n"
    "                    if wcols[j].button(f\"\U0001f4c8 \u05e4\u05ea\u05d7 {r['sym']}\", key=f\"wl_open_{i}_{j}\"):\r\n"
    '                        st.session_state.ticker = r["sym"]\r\n'
    "                        st.session_state.ai_res = None\r\n"
    "                        # \u05de\u05e2\u05d1\u05d9\u05e8 \u05d2\u05dd \u05d0\u05ea \u05e7\u05d1\u05d5\u05e6\u05ea \u05d4\u05e0\u05d9\u05d5\u05d5\u05d8 \u05d4\u05e2\u05dc\u05d9\u05d5\u05e0\u05d4 (\u05dc\u05d0 \u05e8\u05e7 \u05d0\u05ea \u05d4\u05d8\u05d9\u05e7\u05e8),\r\n"
    "                        # \u05d0\u05d7\u05e8\u05ea \u05d4\u05d8\u05d9\u05e7\u05e8 \u05d4\u05d9\u05d4 \u05de\u05ea\u05d7\u05dc\u05e3 \u05de\u05ea\u05d7\u05ea \u05d8\u05d0\u05d1 \u05d4-Watchlist \u05d1\u05dc\u05d9 \u05de\u05e2\u05d1\u05e8 \u05d0\u05dc\u05d9\u05d5.\r\n"
    '                        st.session_state.active_group = "\u05d2\u05e8\u05e3"\r\n'
    "                        st.rerun()\r\n"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="לבצע בפועל (ברירת מחדל: dry-run בלבד)")
    ap.add_argument("--file", default="alpha_paper_trading.py", help="נתיב לקובץ")
    args = ap.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"❌ הקובץ לא נמצא: {target.resolve()}")
        sys.exit(1)

    raw = target.read_bytes()
    text = raw.decode("utf-8")

    count = text.count(OLD_BLOCK)
    if count == 0:
        print("❌ לא נמצא ה-anchor הצפוי בקובץ. ייתכן שהקוד כבר שונה. לא בוצע שינוי.")
        sys.exit(1)
    if count > 1:
        print(f"❌ ה-anchor מופיע {count} פעמים (צריך בדיוק פעם אחת). לא בוצע שינוי.")
        sys.exit(1)

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK)

    diff = difflib.unified_diff(
        text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=str(target),
        tofile=str(target) + " (after patch)",
    )
    print("".join(diff))

    if not args.apply:
        print("\n🔎 זהו dry-run. שום דבר לא נכתב. הריצי עם --apply כדי לבצע בפועל.")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = target.with_suffix(target.suffix + f".bak_{ts}")
    backup.write_bytes(raw)
    print(f"\n💾 גיבוי נשמר: {backup}")

    target.write_bytes(new_text.encode("utf-8"))
    print(f"✅ הקובץ עודכן: {target}")


if __name__ == "__main__":
    main()
