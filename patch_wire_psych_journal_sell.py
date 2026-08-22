#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_wire_psych_journal_sell.py

מטרה: מחבר את המודול הפסיכולוגי (psych_journal.py) לזרימת סגירת עסקה
(SELL) בטאב 🛒 מסחר. מוסיף שני שדות UI שמופיעים רק כשבוחרים "מכירה":
"עקבת אחרי תוכנית ה-ATR שלך במדויק?" (כן/לא) ו"רגש עיקרי בעסקה"
(רוגע/FOMO/מסחר נקמה/פחד/חמדנות). בסגירת עסקה מוצלחת, רושם שורה
ל-trading_journal.db דרך log_trade_psychology().

שימוש:
    python patch_wire_psych_journal_sell.py                 # dry-run (ברירת מחדל)
    python patch_wire_psych_journal_sell.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: alpha_paper_trading.py (CRLF)
דורש: psych_journal.py קיים באותה תיקייה.
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

# ── חלק 1: ייבוא + אתחול ה-DB ──
OLD_IMPORT = (
    '# \u2500\u2500 Risk / Reward \u2500\u2500\r\n'
    'from rr_tab import render_position_manager\r\n'
)

NEW_IMPORT = (
    '# \u2500\u2500 Risk / Reward \u2500\u2500\r\n'
    'from rr_tab import render_position_manager\r\n'
    '\r\n'
    '# \u2014\u2014 \u05d9\u05d5\u05de\u05df \u05e4\u05e1\u05d9\u05db\u05d5\u05dc\u05d5\u05d2\u05d9 (SQLite \u05e0\u05e4\u05e8\u05d3 - \u05dc\u05d0 \u05e0\u05d5\u05d2\u05e2 \u05d1-paper_portfolio.json) \u2014\u2014\r\n'
    'import psych_journal as pj\r\n'
    'pj.initialize_application_database()\r\n'
    'PSYCH_EMOTION_HE = {\r\n'
    '    "\u05e8\u05d5\u05d2\u05e2": "Calm", "FOMO": "FOMO",\r\n'
    '    "\u05de\u05e1\u05d7\u05e8 \u05e0\u05e7\u05de\u05d4": "Revenge Trading",\r\n'
    '    "\u05e4\u05d7\u05d3": "Fear", "\u05d7\u05de\u05d3\u05e0\u05d5\u05ea": "Greed",\r\n'
    '}\r\n'
)

# ── חלק 2: שדות UI (מופיעים רק במכירה) ──
OLD_UI = (
    '                    act = st.radio("\u05e4\u05e2\u05d5\u05dc\u05d4:", ["\U0001f7e2 \u05e7\u05e0\u05d9\u05d9\u05d4", "\U0001f534 \u05de\u05db\u05d9\u05e8\u05d4"], horizontal=True)\r\n'
    '                    si_ = st.number_input("\u05db\u05de\u05d5\u05ea:", min_value=1, max_value=1000, value=1)\r\n'
    '                    tv_ = si_ * cp_\r\n'
    '                    st.markdown(f"**\u05e2\u05dc\u05d5\u05ea: {sym}{tv_:,.2f}**")\r\n'
    '                    nt_ = st.text_input("\u05d4\u05e2\u05e8\u05d4:", placeholder="\u05e1\u05d9\u05d1\u05d4 \u05dc\u05e2\u05e1\u05e7\u05d4")\r\n'
)

NEW_UI = (
    '                    act = st.radio("\u05e4\u05e2\u05d5\u05dc\u05d4:", ["\U0001f7e2 \u05e7\u05e0\u05d9\u05d9\u05d4", "\U0001f534 \u05de\u05db\u05d9\u05e8\u05d4"], horizontal=True)\r\n'
    '                    si_ = st.number_input("\u05db\u05de\u05d5\u05ea:", min_value=1, max_value=1000, value=1)\r\n'
    '                    tv_ = si_ * cp_\r\n'
    '                    st.markdown(f"**\u05e2\u05dc\u05d5\u05ea: {sym}{tv_:,.2f}**")\r\n'
    '                    nt_ = st.text_input("\u05d4\u05e2\u05e8\u05d4:", placeholder="\u05e1\u05d9\u05d1\u05d4 \u05dc\u05e2\u05e1\u05e7\u05d4")\r\n'
    '                    if "\u05de\u05db\u05d9\u05e8\u05d4" in act:\r\n'
    '                        # \u05e9\u05d3\u05d5\u05ea \u05d4\u05de\u05d5\u05d3\u05d5\u05dc \u05d4\u05e4\u05e1\u05d9\u05db\u05d5\u05dc\u05d5\u05d2\u05d9 \u2014 \u05de\u05d5\u05e4\u05d9\u05e2\u05d9\u05dd \u05e8\u05e7 \u05d1\u05e1\u05d2\u05d9\u05e8\u05ea \u05e2\u05e1\u05e7\u05d4, \u05dc\u05d0 \u05d1\u05e7\u05e0\u05d9\u05d9\u05d4.\r\n'
    '                        followed_plan_ui = st.radio(\r\n'
    '                            "\u05e2\u05e7\u05d1\u05ea \u05d0\u05d7\u05e8\u05d9 \u05ea\u05d5\u05db\u05e0\u05d9\u05ea \u05d4-ATR \u05e9\u05dc\u05da \u05d1\u05de\u05d3\u05d5\u05d9\u05e7?",\r\n'
    '                            ["\u05db\u05df", "\u05dc\u05d0"], horizontal=True, key="tr_followed_plan")\r\n'
    '                        emotion_ui = st.selectbox(\r\n'
    '                            "\u05e8\u05d2\u05e9 \u05e2\u05d9\u05e7\u05e8\u05d9 \u05d1\u05e2\u05e1\u05e7\u05d4:",\r\n'
    '                            list(PSYCH_EMOTION_HE.keys()), key="tr_emotion")\r\n'
)

# ── חלק 3: רישום ל-DB בסגירת עסקה מוצלחת ──
OLD_SAVE = (
    '                                p[\'trades\'].append({\r\n'
    '                                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),\r\n'
    '                                    "symbol": ticker, "action": "SELL",\r\n'
    '                                    "shares": si_, "price": cp_,\r\n'
    '                                    "total": tv_, "pnl": round(pnl, 2), "note": nt_,\r\n'
    '                                })\r\n'
    '                                save_pf(p)\r\n'
    '                                st.success(f"{\'\u2705\' if pnl >= 0 else \'\u274c\'} P&L: {sym}{pnl:+.2f}")\r\n'
)

NEW_SAVE = (
    '                                _sell_date = datetime.now().strftime("%Y-%m-%d %H:%M")\r\n'
    '                                p[\'trades\'].append({\r\n'
    '                                    "date": _sell_date,\r\n'
    '                                    "symbol": ticker, "action": "SELL",\r\n'
    '                                    "shares": si_, "price": cp_,\r\n'
    '                                    "total": tv_, "pnl": round(pnl, 2), "note": nt_,\r\n'
    '                                })\r\n'
    '                                save_pf(p)\r\n'
    '                                try:\r\n'
    '                                    pj.log_trade_psychology(\r\n'
    '                                        trade_date=_sell_date, symbol=ticker, pnl=round(pnl, 2),\r\n'
    '                                        followed_plan=(followed_plan_ui == "\u05db\u05df"),\r\n'
    '                                        emotion=PSYCH_EMOTION_HE[emotion_ui],\r\n'
    '                                    )\r\n'
    '                                except Exception:\r\n'
    '                                    pass  # \u05d0\u05d9 \u05e8\u05d9\u05e9\u05d5\u05dd \u05dc\u05d9\u05d5\u05de\u05df \u05d4\u05e4\u05e1\u05d9\u05db\u05d5\u05dc\u05d5\u05d2\u05d9 \u05dc\u05d0 \u05d0\u05de\u05d5\u05e8 \u05dc\u05d7\u05e1\u05d5\u05dd \u05e1\u05d2\u05d9\u05e8\u05ea \u05d4\u05e2\u05e1\u05e7\u05d4 \u05e2\u05e6\u05de\u05d4\r\n'
    '                                st.success(f"{\'\u2705\' if pnl >= 0 else \'\u274c\'} P&L: {sym}{pnl:+.2f}")\r\n'
)


def _apply_one(text, old, new, label):
    count = text.count(old)
    if count == 0:
        print(f"❌ [{label}] לא נמצא ה-anchor הצפוי. ייתכן שהקוד כבר שונה. לא בוצע שינוי.")
        return None
    if count > 1:
        print(f"❌ [{label}] ה-anchor מופיע {count} פעמים (צריך בדיוק פעם אחת). לא בוצע שינוי.")
        return None
    return text.replace(old, new)


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

    new_text = text
    for old, new, label in (
        (OLD_IMPORT, NEW_IMPORT, "ייבוא + אתחול DB"),
        (OLD_UI, NEW_UI, "שדות UI"),
        (OLD_SAVE, NEW_SAVE, "רישום בסגירת עסקה"),
    ):
        result = _apply_one(new_text, old, new, label)
        if result is None:
            sys.exit(1)
        new_text = result

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
