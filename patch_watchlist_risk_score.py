#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_watchlist_risk_score.py

מטרה: משימה 4 מהיוזמה הגדולה. מחליף את באדג' ה-RSI בכרטיסי Watchlist
בציון Risk אמיתי (מבוסס ATR% - יחס ATR14 למחיר), ומציג את שלושת
הציונים (Fundamental / Technical / Risk) כ-3 פסים אופקיים זעירים
במקום 3 תיבות מספר + פס משוקלל אחד בתחתית (שהיה חוזר על אותו מידע
כמו באדג' ההחלטה הצבעוני).

חישוב ה-Risk score (0-100, גבוה יותר = בטוח יותר, עקבי עם F/T):
    atr_pct   = ATR14 / מחיר * 100
    risk_score = 100 - (atr_pct / 8 * 100), מוגבל ל-[0, 100]
    (8% ATR נחשב "תנודתיות קיצונית" -> ציון קרוב ל-0;
     1% ATR נחשב "רגוע" -> ציון קרוב ל-87)

שימוש:
    python patch_watchlist_risk_score.py                 # dry-run (ברירת מחדל)
    python patch_watchlist_risk_score.py --apply          # מבצע בפועל + גיבוי אוטומטי

קובץ יעד: alpha_paper_trading.py (CRLF)
"""

import argparse
import datetime
import difflib
import sys
from pathlib import Path

# ── חלק 1: חישוב Risk score במקום RSI, בלולאת בניית הנתונים ──
OLD_DATA = (
    "                    # rsi\r\n"
    "                    rsi_wl = float(df_wl['RSI'].iloc[-1]) if 'RSI' in df_wl.columns else 50\r\n"
    "\r\n"
    "                    wl_rows.append({\r\n"
    '                        "sym":      sym_wl,\r\n'
    '                        "name":     (inf_wl.get("shortName","") or "")[:18],\r\n'
    '                        "price":    price_wl,\r\n'
    '                        "chg":      chg_wl,\r\n'
    '                        "rsi":      rsi_wl,\r\n'
    '                        "trend":    trend_wl,\r\n'
    '                        "f_score":  f_wl.get("score"),\r\n'
    '                        "t_score":  t_wl.get("score"),\r\n'
    '                        "decision": dec_wl.get("decision","\u2014"),\r\n'
    '                        "dec_clr":  dec_wl.get("color","#8b949e"),\r\n'
    '                        "dec_icon": dec_wl.get("icon","\u26aa"),\r\n'
    '                        "weighted": dec_wl.get("weighted",0) or 0,\r\n'
    "                    })\r\n"
    "                except: pass\r\n"
)

NEW_DATA = (
    "                    # risk score - \u05de\u05d1\u05d5\u05e1\u05e1 ATR% (\u05d0\u05d5\u05ea\u05d5 \u05d4\u05d7\u05d9\u05e9\u05d5\u05d1 \u05e9\u05de\u05e9\u05de\u05e9 \u05dc\u05e1\u05d8\u05d5\u05e4 \u05d1\u05e2\u05e1\u05e7\u05d5\u05ea \u05d0\u05de\u05d9\u05ea\u05d9\u05d5\u05ea).\r\n"
    "                    # \u05d2\u05d1\u05d5\u05d4 = \u05d1\u05d8\u05d5\u05d7 \u05d9\u05d5\u05ea\u05e8 (\u05e2\u05e7\u05d1\u05d9 \u05dc-F/T), \u05e0\u05de\u05d5\u05da = \u05ea\u05e0\u05d5\u05d3\u05ea\u05d9\u05d5\u05ea \u05d2\u05d1\u05d5\u05d4\u05d4 \u05d9\u05d5\u05ea\u05e8.\r\n"
    "                    try:\r\n"
    "                        _atr_wl = true_atr(df_wl)\r\n"
    "                        _atr_pct_wl = (_atr_wl / price_wl * 100) if _atr_wl and price_wl else None\r\n"
    "                    except Exception:\r\n"
    "                        _atr_pct_wl = None\r\n"
    "                    if _atr_pct_wl is not None:\r\n"
    "                        risk_score_wl = max(0, min(100, round(100 - (_atr_pct_wl / 8 * 100))))\r\n"
    "                    else:\r\n"
    "                        risk_score_wl = None\r\n"
    "\r\n"
    "                    wl_rows.append({\r\n"
    '                        "sym":      sym_wl,\r\n'
    '                        "name":     (inf_wl.get("shortName","") or "")[:18],\r\n'
    '                        "price":    price_wl,\r\n'
    '                        "chg":      chg_wl,\r\n'
    '                        "risk_score": risk_score_wl,\r\n'
    '                        "trend":    trend_wl,\r\n'
    '                        "f_score":  f_wl.get("score"),\r\n'
    '                        "t_score":  t_wl.get("score"),\r\n'
    '                        "decision": dec_wl.get("decision","\u2014"),\r\n'
    '                        "dec_clr":  dec_wl.get("color","#8b949e"),\r\n'
    '                        "dec_icon": dec_wl.get("icon","\u26aa"),\r\n'
    '                        "weighted": dec_wl.get("weighted",0) or 0,\r\n'
    "                    })\r\n"
    "                except: pass\r\n"
)

# ── חלק 2: עיצוב הכרטיס — 3 פסים אופקיים במקום תיבות מספר + פס משוקלל ──
OLD_CARD = (
    '                    chg_c = "#3fb950" if r["chg"] >= 0 else "#f85149"\r\n'
    '                    rsi_c = "#f85149" if r["rsi"] >= 70 else ("#3fb950" if r["rsi"] <= 30 else "#8b949e")\r\n'
    '                    bar_w = r["weighted"]\r\n'
    '                    dec_c = r["dec_clr"]\r\n'
    "\r\n"
    "                    wcols[j].markdown(\r\n"
    '                        f\'<div style="background:#161b22;border:1px solid #21262d;\'\r\n'
    '                        f\'border-top:2px solid {dec_c};border-radius:12px;padding:14px 16px;">\'\r\n'
    "\r\n"
    "                        # header\r\n"
    '                        f\'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">\'\r\n'
    "                        f'<div>'\r\n"
    '                        f\'<div style="font-size:.92rem;font-weight:700;color:#e6edf3;">{r["sym"]}</div>\'\r\n'
    '                        f\'<div style="color:#8b949e;font-size:.68rem;">{r["name"]}</div>\'\r\n'
    "                        f'</div>'\r\n"
    '                        f\'<div style="text-align:left;">\'\r\n'
    '                        f\'<div style="font-family:JetBrains Mono,monospace;font-size:.92rem;font-weight:700;color:#e6edf3;">${r["price"]:.2f}</div>\'\r\n'
    '                        f\'<div style="color:{chg_c};font-size:.72rem;font-weight:600;">{r["chg"]:+.2f}%</div>\'\r\n'
    "                        f'</div></div>'\r\n"
    "\r\n"
    "                        # scores row\r\n"
    '                        f\'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;margin-bottom:8px;">\'\r\n'
    '                        f\'<div style="background:#0d1117;border-radius:6px;padding:5px;text-align:center;">\'\r\n'
    '                        f\'<div style="color:#8b949e;font-size:.55rem;text-transform:uppercase;">\u05e4\u05d5\u05e0\u05d3\u05f3</div>\'\r\n'
    '                        f\'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#388bfd;">{r["f_score"] or "\u2014"}</div>\'\r\n'
    "                        f'</div>'\r\n"
    '                        f\'<div style="background:#0d1117;border-radius:6px;padding:5px;text-align:center;">\'\r\n'
    '                        f\'<div style="color:#8b949e;font-size:.55rem;text-transform:uppercase;">\u05d8\u05db\u05e0\u05d9</div>\'\r\n'
    '                        f\'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#3fb950;">{r["t_score"] or "\u2014"}</div>\'\r\n'
    "                        f'</div>'\r\n"
    '                        f\'<div style="background:#0d1117;border-radius:6px;padding:5px;text-align:center;">\'\r\n'
    '                        f\'<div style="color:#8b949e;font-size:.55rem;text-transform:uppercase;">RSI</div>\'\r\n'
    '                        f\'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:{rsi_c};">{r["rsi"]:.0f}</div>\'\r\n'
    "                        f'</div></div>'\r\n"
    "\r\n"
    "                        # trend + decision\r\n"
    '                        f\'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">\'\r\n'
    '                        f\'<span style="font-size:.72rem;">{r["trend"]}</span>\'\r\n'
    "                        f'<span style=\"background:{dec_c}22;color:{dec_c};border:1px solid {dec_c}55;'\r\n"
    '                        f\'border-radius:20px;padding:2px 8px;font-size:.68rem;font-weight:700;">\'\r\n'
    '                        f\'{r["dec_icon"]} {r["decision"]}</span>\'\r\n'
    "                        f'</div>'\r\n"
    "\r\n"
    "                        # score bar\r\n"
    '                        f\'<div style="height:4px;background:#21262d;border-radius:2px;overflow:hidden;">\'\r\n'
    '                        f\'<div style="height:100%;width:{bar_w}%;background:{dec_c};border-radius:2px;"></div>\'\r\n'
    "                        f'</div>'\r\n"
    '                        f\'<div style="color:#8b949e;font-size:.6rem;text-align:center;margin-top:3px;">{bar_w}/100</div>\'\r\n'
    "                        f'</div>',\r\n"
    "                        unsafe_allow_html=True\r\n"
    "                    )\r\n"
)

NEW_CARD = (
    '                    chg_c = "#3fb950" if r["chg"] >= 0 else "#f85149"\r\n'
    '                    dec_c = r["dec_clr"]\r\n'
    '                    _f_val   = r["f_score"] if r["f_score"] is not None else 0\r\n'
    '                    _t_val   = r["t_score"] if r["t_score"] is not None else 0\r\n'
    '                    _rk_val  = r["risk_score"] if r["risk_score"] is not None else 0\r\n'
    '                    _f_lbl   = r["f_score"] if r["f_score"] is not None else "\u2014"\r\n'
    '                    _t_lbl   = r["t_score"] if r["t_score"] is not None else "\u2014"\r\n'
    '                    _rk_lbl  = r["risk_score"] if r["risk_score"] is not None else "\u2014"\r\n'
    "\r\n"
    "                    wcols[j].markdown(\r\n"
    '                        f\'<div style="background:#161b22;border:1px solid #21262d;\'\r\n'
    '                        f\'border-top:2px solid {dec_c};border-radius:12px;padding:14px 16px;">\'\r\n'
    "\r\n"
    "                        # header\r\n"
    '                        f\'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">\'\r\n'
    "                        f'<div>'\r\n"
    '                        f\'<div style="font-size:.92rem;font-weight:700;color:#e6edf3;">{r["sym"]}</div>\'\r\n'
    '                        f\'<div style="color:#8b949e;font-size:.68rem;">{r["name"]}</div>\'\r\n'
    "                        f'</div>'\r\n"
    '                        f\'<div style="text-align:left;">\'\r\n'
    '                        f\'<div style="font-family:JetBrains Mono,monospace;font-size:.92rem;font-weight:700;color:#e6edf3;">${r["price"]:.2f}</div>\'\r\n'
    '                        f\'<div style="color:{chg_c};font-size:.72rem;font-weight:600;">{r["chg"]:+.2f}%</div>\'\r\n'
    "                        f'</div></div>'\r\n"
    "\r\n"
    "                        # 3 \u05e4\u05e1\u05d9\u05dd \u05d0\u05d5\u05e4\u05e7\u05d9\u05d9\u05dd \u05d6\u05e2\u05d9\u05e8\u05d9\u05dd: Fundamental / Technical / Risk\r\n"
    '                        f\'<div style="margin-bottom:4px;">\'\r\n'
    '                        f\'<div style="display:flex;justify-content:space-between;font-size:.58rem;color:#8b949e;margin-bottom:2px;">\'\r\n'
    '                        f\'<span>\u05e4\u05d5\u05e0\u05d3\u05de\u05e0\u05d8\u05dc\u05d9 (F)</span><span style="font-family:JetBrains Mono,monospace;color:#388bfd;">{_f_lbl}</span></div>\'\r\n'
    '                        f\'<div style="height:4px;background:#21262d;border-radius:2px;overflow:hidden;">\'\r\n'
    '                        f\'<div style="height:100%;width:{_f_val}%;background:#388bfd;border-radius:2px;"></div></div></div>\'\r\n'
    '                        f\'<div style="margin-bottom:4px;">\'\r\n'
    '                        f\'<div style="display:flex;justify-content:space-between;font-size:.58rem;color:#8b949e;margin-bottom:2px;">\'\r\n'
    '                        f\'<span>\u05d8\u05db\u05e0\u05d9 (T)</span><span style="font-family:JetBrains Mono,monospace;color:#3fb950;">{_t_lbl}</span></div>\'\r\n'
    '                        f\'<div style="height:4px;background:#21262d;border-radius:2px;overflow:hidden;">\'\r\n'
    '                        f\'<div style="height:100%;width:{_t_val}%;background:#3fb950;border-radius:2px;"></div></div></div>\'\r\n'
    '                        f\'<div style="margin-bottom:8px;">\'\r\n'
    '                        f\'<div style="display:flex;justify-content:space-between;font-size:.58rem;color:#8b949e;margin-bottom:2px;">\'\r\n'
    '                        f\'<span>\u05e1\u05d9\u05db\u05d5\u05df (R)</span><span style="font-family:JetBrains Mono,monospace;color:#f0883e;">{_rk_lbl}</span></div>\'\r\n'
    '                        f\'<div style="height:4px;background:#21262d;border-radius:2px;overflow:hidden;">\'\r\n'
    '                        f\'<div style="height:100%;width:{_rk_val}%;background:#f0883e;border-radius:2px;"></div></div></div>\'\r\n'
    "\r\n"
    "                        # trend + decision\r\n"
    '                        f\'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">\'\r\n'
    '                        f\'<span style="font-size:.72rem;">{r["trend"]}</span>\'\r\n'
    "                        f'<span style=\"background:{dec_c}22;color:{dec_c};border:1px solid {dec_c}55;'\r\n"
    '                        f\'border-radius:20px;padding:2px 8px;font-size:.68rem;font-weight:700;">\'\r\n'
    '                        f\'{r["dec_icon"]} {r["decision"]}</span>\'\r\n'
    "                        f'</div>'\r\n"
    "                        f'</div>',\r\n"
    "                        unsafe_allow_html=True\r\n"
    "                    )\r\n"
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
        (OLD_DATA, NEW_DATA, "חישוב Risk score"),
        (OLD_CARD, NEW_CARD, "עיצוב הכרטיס"),
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
