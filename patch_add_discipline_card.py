#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_add_discipline_card.py

מטרה: מוסיף כרטיס "משמעת מסחר" מעל יומן העסקאות (טאב ביצועים), שמציג
את Discipline Score (%) ואת העלות הרגשית הכוללת, מתוך
calculate_trader_discipline_metrics() ב-psych_journal.py (משימה 1).

- ציון משמעת >= 80% -> ירוק, 50-79% -> צהוב, <50% -> אדום.
- אם עדיין אין נתונים ביומן הפסיכולוגי (0 עסקאות נרשמו), מוצג כרטיס
  ניטרלי עם הסבר, לא שגיאה.

שימוש:
    python patch_add_discipline_card.py                 # dry-run (ברירת מחדל)
    python patch_add_discipline_card.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: alpha_paper_trading.py (CRLF)
דורש: psych_journal.py ו-patch_wire_psych_journal_sell.py כבר רצו.
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    '    with tr_sub2:\r\n'
    '            st.markdown("### \U0001f4ca \u05d9\u05d5\u05de\u05df \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea")\r\n'
    "            trd = pf['trades']\r\n"
)

NEW_BLOCK = (
    '    with tr_sub2:\r\n'
    '            st.markdown("### \U0001f4ca \u05d9\u05d5\u05de\u05df \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea")\r\n'
    '\r\n'
    '            # \u2014\u2014 \u05db\u05e8\u05d8\u05d9\u05e1 \u05de\u05e9\u05de\u05e2\u05ea \u2014 \u05de\u05e9\u05d9\u05de\u05d4 3 \u05e9\u05dc \u05d4\u05de\u05d5\u05d3\u05d5\u05dc \u05d4\u05e4\u05e1\u05d9\u05db\u05d5\u05dc\u05d5\u05d2\u05d9 \u2014\u2014\r\n'
    '            _dm = pj.calculate_trader_discipline_metrics()\r\n'
    '            if _dm.total_trades == 0:\r\n'
    '                st.markdown(\r\n'
    '                    \'<div style="background:#161b22;border:1px solid #21262d;\'\r\n'
    '                    \'border-radius:12px;padding:14px 18px;margin-bottom:14px;\'\r\n'
    '                    \'direction:rtl;text-align:right;color:#8b949e;font-size:.8rem;">\'\r\n'
    '                    \'\U0001f9e0 \u05e2\u05d3\u05d9\u05d9\u05df \u05d0\u05d9\u05df \u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05d1\u05d9\u05d5\u05de\u05df \u05d4\u05e4\u05e1\u05d9\u05db\u05d5\u05dc\u05d5\u05d2\u05d9 \u2014 \u05d9\u05d5\u05e4\u05d9\u05e2 \u05d0\u05d7\u05e8\u05d9 \u05e1\u05d2\u05d9\u05e8\u05d4 \u05e8\u05d0\u05e9\u05d5\u05e0\u05d4 \u05e9\u05dc \u05e2\u05e1\u05e7\u05d4.\'\r\n'
    '                    \'</div>\', unsafe_allow_html=True)\r\n'
    '            else:\r\n'
    '                _ds = _dm.discipline_score_pct\r\n'
    '                _dm_clr = "#3fb950" if _ds >= 80 else ("#d29922" if _ds >= 50 else "#f85149")\r\n'
    '                st.markdown(\r\n'
    '                    f\'<div style="background:#161b22;border:1px solid #21262d;\'\r\n'
    '                    f\'border-top:3px solid {_dm_clr};border-radius:12px;\'\r\n'
    '                    f\'padding:14px 18px;margin-bottom:14px;direction:rtl;">\'\r\n'
    '                    f\'<div style="display:flex;justify-content:space-between;\'\r\n'
    '                    f\'align-items:center;flex-wrap:wrap;gap:14px;">\'\r\n'
    '                    f\'<div style="text-align:right;">\'\r\n'
    '                    f\'<div style="color:#8b949e;font-size:.64rem;text-transform:uppercase;">\'\r\n'
    '                    f\'\u05e6\u05d9\u05d5\u05df \u05de\u05e9\u05de\u05e2\u05ea (Discipline Score)</div>\'\r\n'
    '                    f\'<div style="font-family:JetBrains Mono,monospace;font-size:1.7rem;\'\r\n'
    '                    f\'font-weight:700;color:{_dm_clr};">{_ds:.0f}%</div>\'\r\n'
    '                    f\'<div style="color:#8b949e;font-size:.68rem;">\'\r\n'
    '                    f\'\u05de\u05ea\u05d5\u05da {_dm.total_trades} \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea \u05e9\u05e0\u05e8\u05e9\u05de\u05d5 \u05d1\u05d9\u05d5\u05de\u05df</div>\'\r\n'
    '                    f\'</div>\'\r\n'
    '                    f\'<div style="text-align:right;">\'\r\n'
    '                    f\'<div style="color:#8b949e;font-size:.64rem;text-transform:uppercase;">\'\r\n'
    '                    f\'\u05e2\u05dc\u05d5\u05ea \u05e8\u05d2\u05e9\u05d9\u05ea \u05db\u05d5\u05dc\u05dc\u05ea</div>\'\r\n'
    '                    f\'<div style="font-family:JetBrains Mono,monospace;font-size:1.7rem;\'\r\n'
    '                    f\'font-weight:700;color:#f85149;">${_dm.total_emotional_loss_cost:,.0f}</div>\'\r\n'
    '                    f\'<div style="color:#8b949e;font-size:.68rem;">\'\r\n'
    '                    f\'\u05d1-{_dm.emotional_loss_trade_count} \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea \u05de\u05e4\u05e1\u05d9\u05d3\u05d5\u05ea \u05dc\u05d0 \u05dc\u05e4\u05d9 \u05d4\u05ea\u05d5\u05db\u05e0\u05d9\u05ea/\u05d1\u05e8\u05d5\u05d2\u05e2</div>\'\r\n'
    '                    f\'</div>\'\r\n'
    '                    f\'</div></div>\', unsafe_allow_html=True)\r\n'
    '\r\n'
    "            trd = pf['trades']\r\n"
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
