#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fix_portfolio_table_rtl.py

מטרה: מתקן את הטבלה "ניתוח תיק קיים" ב-render_position_module (alpha_paper_trading.py),
שהייתה עד כה st.dataframe(...).style.map(...) - טבלה שמתרנדרת על canvas ולא מכבדת RTL,
ולכן הייתה לא קריאה (כפי שתועד ב-backlog).

הפתרון: המרה לטבלת HTML, באותה תבנית שכבר קיימת ועובדת באפליקציה עבור טבלת ה"תיק"
בטאב ה-Holdings (שורה ~6960 בקובץ המקורי): אותה פלטת צבעים (#161b22/#0d1117 שורות
לסירוגין, #21262d מפרידים, #3fb950/#f85149 לצבע תשואה), אותו מבנה <table dir=rtl>.

שימוש:
    python patch_fix_portfolio_table_rtl.py                 # dry-run (ברירת מחדל) - מציג diff בלבד
    python patch_fix_portfolio_table_rtl.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: alpha_paper_trading.py (באותה תיקייה שמריצים ממנה את הסקריפט, או נתיב מלא ב---file)
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    '        if rows:\r\n'
    '            df_pf = pd.DataFrame(rows)\r\n'
    '            def color_ret(v):\r\n'
    '                try:\r\n'
    '                    n = float(str(v).replace("%","").replace("+",""))\r\n'
    '                    return "color:#3fb950;font-weight:600" if n > 0 else ("color:#f85149;font-weight:600" if n < 0 else "")\r\n'
    '                except: return ""\r\n'
    '            disp = [c for c in ["\u05de\u05e0\u05d9\u05d4","\u05de\u05d7\u05d9\u05e8 \u05e7\u05e0\u05d9\u05d9\u05d4","\u05de\u05d7\u05d9\u05e8 \u05e0\u05d5\u05db\u05d7\u05d9","\u05db\u05de\u05d5\u05ea","\u05e2\u05e8\u05da \u05db\u05d5\u05dc\u05dc","\u05ea\u05e9\u05d5\u05d0\u05d4 %"] if c in df_pf.columns]\r\n'
    '            st.dataframe(\r\n'
    '                df_pf[disp].style.map(color_ret, subset=["\u05ea\u05e9\u05d5\u05d0\u05d4 %"]),\r\n'
    '                use_container_width=True, hide_index=True\r\n'
    '            )\r\n'
)

NEW_BLOCK = (
    '        if rows:\r\n'
    '            th_pf = \'style="background:#0d1117;color:#8b949e;font-size:.64rem;'
    'text-transform:uppercase;padding:7px 10px;text-align:right;border-bottom:2px solid #21262d;"\'\r\n'
    '            headers_pf = ["\u05de\u05e0\u05d9\u05d4","\u05de\u05d7\u05d9\u05e8 \u05e7\u05e0\u05d9\u05d9\u05d4",'
    '"\u05de\u05d7\u05d9\u05e8 \u05e0\u05d5\u05db\u05d7\u05d9","\u05db\u05de\u05d5\u05ea","\u05e2\u05e8\u05da \u05db\u05d5\u05dc\u05dc","\u05ea\u05e9\u05d5\u05d0\u05d4 %"]\r\n'
    '            h_html_pf = "<tr>" + "".join(f"<th {th_pf}>{h}</th>" for h in headers_pf) + "</tr>"\r\n'
    '            rows_html_pf = ""\r\n'
    '            for i_pf, r_pf in enumerate(rows):\r\n'
    '                bg_pf = "#161b22" if i_pf % 2 == 0 else "#0d1117"\r\n'
    '                rc_pf = "#3fb950" if r_pf["_ret"] >= 0 else "#f85149"\r\n'
    '                cells_pf = (\r\n'
    '                    f\'<td style="padding:7px 10px;color:#e6edf3;font-weight:700;font-size:.78rem;'
    'border-bottom:1px solid #21262d;">{r_pf["\u05de\u05e0\u05d9\u05d4"]}</td>\'\r\n'
    '                    f\'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;'
    'color:#8b949e;border-bottom:1px solid #21262d;">{r_pf["\u05de\u05d7\u05d9\u05e8 \u05e7\u05e0\u05d9\u05d9\u05d4"]}</td>\'\r\n'
    '                    f\'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;'
    'color:#e6edf3;border-bottom:1px solid #21262d;">{r_pf["\u05de\u05d7\u05d9\u05e8 \u05e0\u05d5\u05db\u05d7\u05d9"]}</td>\'\r\n'
    '                    f\'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;'
    'color:#e6edf3;border-bottom:1px solid #21262d;">{r_pf["\u05db\u05de\u05d5\u05ea"]}</td>\'\r\n'
    '                    f\'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;'
    'color:#e6edf3;border-bottom:1px solid #21262d;">{r_pf["\u05e2\u05e8\u05da \u05db\u05d5\u05dc\u05dc"]}</td>\'\r\n'
    '                    f\'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.78rem;'
    'color:{rc_pf};font-weight:600;border-bottom:1px solid #21262d;">{r_pf["\u05ea\u05e9\u05d5\u05d0\u05d4 %"]}</td>\'\r\n'
    '                )\r\n'
    '                rows_html_pf += f\'<tr style="background:{bg_pf};">{cells_pf}</tr>\'\r\n'
    '            st.markdown(\r\n'
    '                \'<div style="overflow-x:auto;">\'\r\n'
    '                \'<table style="width:100%;border-collapse:collapse;direction:rtl;">\'\r\n'
    '                f\'<thead>{h_html_pf}</thead><tbody>{rows_html_pf}</tbody>\'\r\n'
    '                \'</table></div>\', unsafe_allow_html=True\r\n'
    '            )\r\n'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="לבצע בפועל (ברירת מחדל: dry-run בלבד)")
    ap.add_argument("--file", default="alpha_paper_trading.py", help="נתיב לקובץ (ברירת מחדל: alpha_paper_trading.py בתיקייה הנוכחית)")
    args = ap.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"❌ הקובץ לא נמצא: {target.resolve()}")
        sys.exit(1)

    raw = target.read_bytes()
    text = raw.decode("utf-8")

    count = text.count(OLD_BLOCK)
    if count == 0:
        print("❌ לא נמצא ה-anchor הצפוי בקובץ. ייתכן שהקוד כבר שונה מאז שהוצג לי, "
              "או שהתבנית לא תואמת בדיוק (למשל רווחים/CRLF). לא בוצע שינוי.")
        sys.exit(1)
    if count > 1:
        print(f"❌ ה-anchor מופיע {count} פעמים בקובץ (צריך בדיוק פעם אחת). "
              "לא בוצע שינוי, כדי למנוע פאץ' לא מדויק.")
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
