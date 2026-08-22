#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fix_trade_log_table_rtl.py

מטרה: מתקן את טבלת "יומן עסקאות" בטאב ביצועים (tr_sub2, alpha_paper_trading.py),
שהייתה עד כה dt.style.map(...) + st.dataframe(...) - אותה בעיה שכבר תוקנה בטבלת
"ניתוח תיק קיים": st.dataframe מתרנדר על canvas ולא מכבד RTL.

הפתרון: אותה תבנית HTML שכבר קיימת באפליקציה (פלטת #161b22/#0d1117 לשורות
לסירוגין, #3fb950/#f85149 לצבעי BUY/SELL ורווח/הפסד).

שימוש:
    python patch_fix_trade_log_table_rtl.py                 # dry-run (ברירת מחדל)
    python patch_fix_trade_log_table_rtl.py --apply          # מבצע בפועל + גיבוי אוטומטי
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

OLD_BLOCK = (
    '                def ca(v):\r\n'
    '                    return "color:#3fb950;font-weight:600" if v == "BUY" else "color:#f85149;font-weight:600"\r\n'
    '                def cp2(v):\r\n'
    '                    try: return "color:#3fb950" if float(v) >= 0 else "color:#f85149"\r\n'
    '                    except: return ""\r\n'
    "                st_ = dt.style.map(ca, subset=['action'])\r\n"
    "                if 'pnl' in dt.columns:\r\n"
    "                    st_ = st_.map(cp2, subset=['pnl'])\r\n"
    '                st.dataframe(st_, use_container_width=True)\r\n'
)

NEW_BLOCK = (
    '                def _esc_tr(v):\r\n'
    '                    s = "" if v is None else str(v)\r\n'
    '                    return (s.replace("&", "&amp;").replace("<", "&lt;")\r\n'
    '                             .replace(">", "&gt;").replace(\'"\', "&quot;"))\r\n'
    '                def _fmt_trade_val(col, v):\r\n'
    '                    if col in ("price", "total"):\r\n'
    '                        try: return f"${float(v):,.2f}"\r\n'
    '                        except Exception: return _esc_tr(v)\r\n'
    '                    if col == "pnl":\r\n'
    '                        try:\r\n'
    '                            if v is None or (isinstance(v, float) and pd.isna(v)):\r\n'
    '                                return "\u2014"\r\n'
    '                            return f"${float(v):+,.2f}"\r\n'
    '                        except Exception:\r\n'
    '                            return "\u2014"\r\n'
    '                    if col == "shares":\r\n'
    '                        try: return f"{int(v)}"\r\n'
    '                        except Exception: return _esc_tr(v)\r\n'
    '                    if v is None or (isinstance(v, float) and pd.isna(v)):\r\n'
    '                        return ""\r\n'
    '                    return _esc_tr(v)\r\n'
    '\r\n'
    '                _trade_cols = [c for c in ["date","symbol","action","shares","price","total","pnl","note"] if c in dt.columns]\r\n'
    '                _trade_headers = {"date":"\u05ea\u05d0\u05e8\u05d9\u05da","symbol":"\u05e1\u05d9\u05de\u05d5\u05dc","action":"\u05e4\u05e2\u05d5\u05dc\u05d4",\r\n'
    '                                  "shares":"\u05db\u05de\u05d5\u05ea","price":"\u05de\u05d7\u05d9\u05e8","total":"\u05e1\u05d4\u05f4\u05db",\r\n'
    '                                  "pnl":"\u05e8\u05d5\u05d5\u05d7/\u05d4\u05e4\u05e1\u05d3","note":"\u05d4\u05e2\u05e8\u05d4"}\r\n'
    '                th_tr = (\'style="background:#0d1117;color:#8b949e;font-size:.64rem;\'\r\n'
    '                         \'text-transform:uppercase;padding:7px 10px;text-align:right;\'\r\n'
    '                         \'border-bottom:2px solid #21262d;"\')\r\n'
    '                h_html_tr = "<tr>" + "".join(f"<th {th_tr}>{_trade_headers.get(c, c)}</th>" for c in _trade_cols) + "</tr>"\r\n'
    '                rows_html_tr = ""\r\n'
    '                for i_tr, row_tr in dt.reset_index(drop=True).iterrows():\r\n'
    '                    bg_tr = "#161b22" if i_tr % 2 == 0 else "#0d1117"\r\n'
    '                    act_clr = "#3fb950" if row_tr.get("action") == "BUY" else "#f85149"\r\n'
    '                    pnl_val = row_tr.get("pnl") if "pnl" in dt.columns else None\r\n'
    '                    pnl_ok = pnl_val is not None and not (isinstance(pnl_val, float) and pd.isna(pnl_val))\r\n'
    '                    pnl_clr = ("#3fb950" if pnl_ok and float(pnl_val) >= 0 else "#f85149") if pnl_ok else "#8b949e"\r\n'
    '                    cells_tr = ""\r\n'
    '                    for c in _trade_cols:\r\n'
    '                        txt = _fmt_trade_val(c, row_tr.get(c))\r\n'
    '                        if c == "action":\r\n'
    '                            clr, wt = act_clr, "700"\r\n'
    '                        elif c == "pnl":\r\n'
    '                            clr, wt = pnl_clr, "600"\r\n'
    '                        else:\r\n'
    '                            clr, wt = "#e6edf3", "400"\r\n'
    '                        mono = "font-family:JetBrains Mono,monospace;" if c in ("shares", "price", "total", "pnl") else ""\r\n'
    '                        cells_tr += (f\'<td style="padding:7px 10px;{mono}color:{clr};font-weight:{wt};\'\r\n'
    '                                     f\'font-size:.75rem;border-bottom:1px solid #21262d;">{txt}</td>\')\r\n'
    '                    rows_html_tr += f\'<tr style="background:{bg_tr};">{cells_tr}</tr>\'\r\n'
    '                st.markdown(\r\n'
    '                    \'<div style="overflow-x:auto;">\'\r\n'
    '                    \'<table style="width:100%;border-collapse:collapse;direction:rtl;">\'\r\n'
    '                    f\'<thead>{h_html_tr}</thead><tbody>{rows_html_tr}</tbody>\'\r\n'
    '                    \'</table></div>\', unsafe_allow_html=True\r\n'
    '                )\r\n'
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
        print("❌ לא נמצא ה-anchor הצפוי בקובץ. ייתכן שהקוד כבר שונה מאז שהוצג לי. לא בוצע שינוי.")
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
