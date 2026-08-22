#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_watchlist_smart_search.py (v2 - CRLF/LF-robust)

מטרה: מחליף את שדה הוספת המניה ב-Watchlist (הגרסה עם בדיקת הבטיחות
שכבר רצה - patch_validate_watchlist_add.py) באותה קומפוננטת Smart
Search (st_searchbox + _header_search) שכבר משמשת בכותרת העליונה.
dropdown חי עם הצעות אמיתיות תוך כדי הקלדה, כך שאי אפשר להזין שם
חברה שגוי (כמו "apple" במקום "AAPL"), כי הבחירה עצמה מחזירה כבר
את הסימול הנכון. נשמרת גם בדיקת load_ohlcv כרשת ביטחון נוספת.

עמיד ל-CRLF/LF: הבלוקים מוגדרים ב-\n, וההשוואה בפועל מנרמלת את שני
הצדדים (טקסט הקובץ וה-anchor) לאותו סגנון לפני ההשוואה, כדי שזה יעבוד
בלי קשר לאיך בדיוק ה-editor/git שמרו את שורות הקובץ.

שימוש:
    python patch_watchlist_smart_search.py                 # dry-run (ברירת מחדל)
    python patch_watchlist_smart_search.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: alpha_paper_trading.py
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = '    wl1, wl2 = st.columns([4, 1])\n    with wl1:\n        wl_new = st.text_input("הוסיפי מניה לרשימה", placeholder="לדוג: GOOGL", key="wl_new").upper().strip()\n    with wl2:\n        st.markdown(\'<div style="height:28px;"></div>\', unsafe_allow_html=True)\n        if st.button("➕ הוסף", key="wl_add", type="primary"):\n            if wl_new and wl_new not in st.session_state.watchlist:\n                with st.spinner(f"בודקת ש-{wl_new} סימול תקין..."):\n                    _wl_check = load_ohlcv(wl_new, "5d", "1d")\n                if _wl_check is None or len(_wl_check) == 0:\n                    st.error(\n                        f"❌ לא נמצאו נתונים עבור {wl_new}. "\n                        "וודאי שזה סימול מניה כמו AAPL, לא שם חברה "\n                        "כמו apple. עבור מניות ישראליות הוסיפו .TA כמו TEVA.TA"\n                    )\n                else:\n                    st.session_state.watchlist.append(wl_new)\n                    save_user_data()\n                    st.rerun()\n'

NEW_BLOCK = '    # Smart Search: אותה קומפוננטת st_searchbox + _header_search שכבר\n    # משמשת בכותרת העליונה. dropdown חי עם הצעות אמיתיות (סימול או שם\n    # חברה, כולל עברית וטיקרים ישראליים), במקום טקסט חופשי שיכול לקבל\n    # שם חברה שגוי כמו "apple" בטעות במקום "AAPL".\n    wl_picked = st_searchbox(\n        _header_search,\n        placeholder="🔍 סימול או שם חברה — AAPL, Tesla, טבע...",\n        key="wl_search_sb",\n        debounce=250,\n        clear_on_submit=True,\n    )\n    if wl_picked and wl_picked not in st.session_state.watchlist:\n        # בדיקת בטיחות נוספת: גם תוצאה שהוחזרה מהחיפוש עלולה להיכשל\n        # בפועל (סימול לא פעיל וכו), אז עדיין מוודאים לפני הוספה.\n        with st.spinner(f"בודקת ש-{wl_picked} סימול תקין..."):\n            _wl_check = load_ohlcv(wl_picked, "5d", "1d")\n        if _wl_check is None or len(_wl_check) == 0:\n            st.error(f"❌ לא נמצאו נתונים עבור {wl_picked} כרגע. נסי שוב עוד רגע.")\n        else:\n            st.session_state.watchlist.append(wl_picked)\n            save_user_data()\n            st.rerun()\n'


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
    uses_crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    # מנרמלים הכל ל-\n לצורך ההשוואה וההחלפה, ומחזירים CRLF בסוף אם היה קיים בקובץ.
    text_lf = text.replace("\r\n", "\n")
    old_lf = OLD_BLOCK.replace("\r\n", "\n")
    new_lf = NEW_BLOCK.replace("\r\n", "\n")

    count = text_lf.count(old_lf)
    if count == 0:
        print("❌ לא נמצא ה-anchor הצפוי בקובץ. ייתכן שהקוד שונה מאז שהוצג לי. לא בוצע שינוי.")
        sys.exit(1)
    if count > 1:
        print(f"❌ ה-anchor מופיע {count} פעמים (צריך בדיוק פעם אחת). לא בוצע שינוי.")
        sys.exit(1)

    new_text_lf = text_lf.replace(old_lf, new_lf)
    new_text = new_text_lf.replace("\n", "\r\n") if uses_crlf else new_text_lf

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
