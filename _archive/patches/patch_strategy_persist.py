#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
patch_strategy_persist.py
=========================
מתקן את בעיית ה-rerun בטאב האסטרטגיה.

הבעיה כיום: `if not st.button(...): return` — כל נגיעה בסליידר, בצ'קבוקס או
בכל ווידג'ט אחר גורמת ל-rerun, הכפתור מחזיר False, והדוח נמחק מהמסך.

הפתרון: התוצאה נשמרת ב-st.session_state["strat_result"] ומצוירת מחדש בכל rerun.
הכפתור אחראי רק על החישוב, לא על התצוגה.

שלושה שינויים ב-strategy_tab.py:
  1. ייבוא datetime (לחותמת זמן ההרצה)
  2. החלפת בלוק הכפתור בבלוק שמור-והצג, כולל אזהרת "תוצאה מיושנת"
  3. הפעלת interactive=True ב-render_rr_section (אופציונלי — מדלג אם לא משולב)

הרצה:
    py patch_strategy_persist.py               # דמה בלבד
    py patch_strategy_persist.py --apply       # ביצוע, אחרי גיבוי עם חותמת זמן
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = "strategy_tab.py"

OLD_RUN_BLOCK = '''    if not st.button("הרץ ניתוח", type="primary", key="strat_run"):
        st.caption("הנתונים נשמרים בקאש ל-15 דקות. הרצה חוזרת על אותה מניה מיידית.")
        return

    if not ticker:
        st.warning("הזיני סימול מניה.")
        return

    with st.spinner(f"מושך נתונים עבור {ticker}..."):
        try:
            report, diag = sd.build_report(
                ticker, portfolio_value=portfolio, position_pct=position_pct,
                risk_profile=profile, macro_event=macro or None, config=cfg)
        except Exception as exc:
            st.error(f"שגיאה במשיכת הנתונים: {exc}")
            return

    if report is None:
        st.error(f"לא ניתן להפיק ניתוח עבור {ticker}.")
        st.dataframe(diag.to_table(), hide_index=True, use_container_width=True)
        return
'''

NEW_RUN_BLOCK = '''    run_clicked = st.button("הרץ ניתוח", type="primary", key="strat_run")

    # חתימת הפרמטרים הנוכחיים בטופס. משמשת לזיהוי תוצאה מיושנת.
    params = (ticker, portfolio, position_pct, profile,
              rel_max, hv_max, vix_max, atr_mult, blackout, macro)

    if run_clicked:
        if not ticker:
            st.warning("הזיני סימול מניה.")
            return
        with st.spinner(f"מושך נתונים עבור {ticker}..."):
            try:
                report, diag = sd.build_report(
                    ticker, portfolio_value=portfolio, position_pct=position_pct,
                    risk_profile=profile, macro_event=macro or None, config=cfg)
            except Exception as exc:
                st.error(f"שגיאה במשיכת הנתונים: {exc}")
                return
        st.session_state["strat_result"] = {
            "report": report, "diag": diag, "params": params,
            "ticker": ticker, "portfolio": portfolio,
            "ran_at": datetime.now(),
        }

    # מכאן והלאה מציירים תמיד מה-session_state, גם ב-rerun שלא נגרם מהכפתור.
    result = st.session_state.get("strat_result")
    if not result:
        st.caption("הנתונים נשמרים בקאש ל-15 דקות. הרצה חוזרת על אותה מניה מיידית.")
        return

    report, diag = result["report"], result["diag"]
    portfolio = result["portfolio"]

    if result["params"] != params:
        st.warning(
            f"מוצגת תוצאה של {result['ticker']} מהרצת {result['ran_at']:%H:%M}. "
            f"הפרמטרים בטופס השתנו מאז — לחצי \\"הרץ ניתוח\\" לרענון.")
    else:
        st.caption(f"הורץ ב-{result['ran_at']:%H:%M:%S}")

    if report is None:
        st.error(f"לא ניתן להפיק ניתוח עבור {result['ticker']}.")
        st.dataframe(diag.to_table(), hide_index=True, use_container_width=True)
        return
'''

EDITS = [
    {
        "name": "ייבוא datetime",
        "old": "import html\nfrom typing import Optional\n",
        "new": "import html\nfrom datetime import datetime\nfrom typing import Optional\n",
        "skip_if": "from datetime import datetime",
        "optional": False,
    },
    {
        "name": "שמירת תוצאת הסקאן ב-session_state",
        "old": OLD_RUN_BLOCK,
        "new": NEW_RUN_BLOCK,
        "skip_if": 'st.session_state["strat_result"]',
        "optional": False,
    },
    {
        "name": "הפעלת ווידג'טים אינטראקטיביים בסקשן הסיכון-סיכוי",
        "old": "            interactive=False,   # אפס ווידג'טים = אפס rerun שמוחק את הסקאן\n",
        "new": "            interactive=True,    # מותר כעת: הדוח שמור ב-session_state\n",
        "skip_if": "interactive=True",
        "optional": True,
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

    original = path.read_text(encoding="utf-8")
    text = original
    applied, skipped, missing = [], [], []

    for edit in EDITS:
        if edit["skip_if"] in text:
            skipped.append(edit["name"])
            continue
        count = text.count(edit["old"])
        if count == 0:
            if edit["optional"]:
                missing.append(edit["name"])
                continue
            fail(f"עוגן לא נמצא עבור: {edit['name']}\n"
                 f"ייתכן שהקובץ נערך ידנית. שלחי לי אותו ואתאים את הסקריפט.")
        if count > 1:
            fail(f"עוגן מופיע {count} פעמים עבור: {edit['name']}. החלפה לא חד-משמעית.")
        text = text.replace(edit["old"], edit["new"], 1)
        applied.append(edit["name"])

    for name in skipped:
        print(f"[דילוג] כבר קיים: {name}")
    for name in missing:
        print(f"[אזהרה] עוגן אופציונלי לא נמצא, מדולג: {name}")
        print("        אם עדיין לא הרצת את patch_strategy_rr.py — זה צפוי.")

    if text == original:
        print("\nאין מה לשנות.")
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
        print("\nזו הרצת דמה. להחלה בפועל:  py patch_strategy_persist.py --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.{stamp}.bak")
    shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8")
    print(f"\nבוצע. גיבוי נשמר ב: {backup.name}")
    print(f"שחזור:  copy /Y \"{backup.name}\" \"{path.name}\"")


if __name__ == "__main__":
    main()
