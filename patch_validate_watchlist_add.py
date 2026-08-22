#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_validate_watchlist_add.py

מטרה: לפני שהוספה ל-Watchlist, מוודאים שהסימול תקין (יש לו נתונים
ב-Yahoo Finance) לפני שמוסיפים אותו לרשימה. עד כה, הקלדת שם חברה
במקום סימול (למשל "apple" במקום "AAPL") נכשלה בשקט: הסימול נשמר
ב-session_state.watchlist, אבל הכרטיס לא הופיע בכלל בגריד (רק ב-
צ'יפ ההסרה בתחתית), בלי שום הסבר.

עכשיו: בדיקת load_ohlcv קצרה לפני ההוספה. אם נכשלת, מוצגת שגיאה
ברורה במקום הוספה שקטה, והרשימה לא מתעדכנת.

שימוש:
    python patch_validate_watchlist_add.py                 # dry-run (ברירת מחדל)
    python patch_validate_watchlist_add.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: alpha_paper_trading.py (CRLF)
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    '        if st.button("\u2795 \u05d4\u05d5\u05e1\u05e3", key="wl_add", type="primary"):\r\n'
    "            if wl_new and wl_new not in st.session_state.watchlist:\r\n"
    "                st.session_state.watchlist.append(wl_new)\r\n"
    "                save_user_data()\r\n"
    "                st.rerun()\r\n"
)

NEW_BLOCK = '        if st.button("➕ הוסף", key="wl_add", type="primary"):\r\n            if wl_new and wl_new not in st.session_state.watchlist:\r\n                with st.spinner(f"בודקת ש-{wl_new} סימול תקין..."):\r\n                    _wl_check = load_ohlcv(wl_new, "5d", "1d")\r\n                if _wl_check is None or len(_wl_check) == 0:\r\n                    st.error(\r\n                        f"❌ לא נמצאו נתונים עבור {wl_new}. "\r\n                        "וודאי שזה סימול מניה כמו AAPL, לא שם חברה "\r\n                        "כמו apple. עבור מניות ישראליות הוסיפו .TA כמו TEVA.TA"\r\n                    )\r\n                else:\r\n                    st.session_state.watchlist.append(wl_new)\r\n                    save_user_data()\r\n                    st.rerun()\r\n'


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
