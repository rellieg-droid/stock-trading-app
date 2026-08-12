"""
fix_analyst_breakdown.py — Alpha Charts Pro
צעד 1 מתוך 3.

מוסיף את פירוק המלצות האנליסטים (Strong Buy / Buy / Hold / Sell /
Strong Sell) שלא היה קיים. load_analyst_data מחזירה היום רק
numberOfAnalystOpinions, כלומר מספר כולל בלי פילוח.

המקור הוא tk.recommendations, שהוא DataFrame נפרד ולא חלק מ-.info.
yfinance שינתה את המבנה שלו בין גרסאות, ולכן הפונקציה מטפלת
בשתי הצורות:
  חדשה: עמודות strongBuy / buy / hold / sell / strongSell
  ישנה: היסטוריית שינויים עם עמודת To Grade שצריך לספור

שימוש:
    py fix_analyst_breakdown.py            <- תצוגה מקדימה
    py fix_analyst_breakdown.py --apply    <- ביצוע + גיבוי
"""

import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

# ── עוגן 1: הפונקציה נכנסת לפני render_analyst_snapshot ─────────────
ANCHOR_FUNCS = '''def render_analyst_snapshot(symbol: str, cur_price: float, ccy_s: str):'''

NEW_FUNCS = '''@st.cache_data(ttl=3600)
def analyst_breakdown(symbol: str) -> dict | None:
    """
    פירוק המלצות אנליסטים לקטגוריות.
    מחזיר {"strong_buy":int,"buy":int,"hold":int,"sell":int,
           "strong_sell":int,"total":int} או None אם אין נתון.

    yfinance החליפה את מבנה recommendations בין גרסאות, ולכן
    מטופלות שתי הצורות.
    """
    try:
        rec = yf.Ticker(symbol).recommendations
        if rec is None or len(rec) == 0:
            return None

        cols = {str(c).lower().replace(" ", "").replace("_", ""): c
                for c in rec.columns}

        # ── צורה חדשה: עמודות מונים ──
        if "strongbuy" in cols or "buy" in cols:
            row = rec.iloc[0]
            def g(key):
                c = cols.get(key)
                if c is None:
                    return 0
                try:
                    v = row[c]
                    return int(v) if pd.notna(v) else 0
                except Exception:
                    return 0
            out = {
                "strong_buy":  g("strongbuy"),
                "buy":         g("buy"),
                "hold":        g("hold"),
                "sell":        g("sell"),
                "strong_sell": g("strongsell"),
            }
            out["total"] = sum(out.values())
            return out if out["total"] > 0 else None

        # ── צורה ישנה: היסטוריית שינויים, סופרים To Grade ──
        grade_col = cols.get("tograde") or cols.get("grade")
        if grade_col is None:
            return None
        out = {"strong_buy": 0, "buy": 0, "hold": 0,
               "sell": 0, "strong_sell": 0}
        for g_ in rec[grade_col].tail(40).astype(str):
            t = g_.lower().strip()
            if "strong buy" in t:
                out["strong_buy"] += 1
            elif "strong sell" in t:
                out["strong_sell"] += 1
            elif any(k in t for k in ("buy", "outperform", "overweight")):
                out["buy"] += 1
            elif any(k in t for k in ("hold", "neutral", "equal")):
                out["hold"] += 1
            elif any(k in t for k in ("sell", "underperform", "underweight")):
                out["sell"] += 1
        out["total"] = sum(out.values())
        return out if out["total"] > 0 else None
    except Exception:
        return None


def _breakdown_html(symbol: str) -> str:
    """
    בר מקובץ + מקרא לפירוק ההמלצות.
    מחרוזת ריקה אם אין נתון, כדי לא להציג אזור ריק.
    """
    b = analyst_breakdown(symbol)
    if not b:
        return ""
    total = b["total"]
    segs = [
        ("Strong Buy",  b["strong_buy"],  "#2ea043"),
        ("Buy",         b["buy"],         "#3fb950"),
        ("Hold",        b["hold"],        "#d29922"),
        ("Sell",        b["sell"],        "#f85149"),
        ("Strong Sell", b["strong_sell"], "#da3633"),
    ]
    bar = "".join(
        f'<div title="{lb}: {v}" style="width:{v/total*100:.1f}%;'
        f'background:{c};height:100%;"></div>'
        for lb, v, c in segs if v > 0
    )
    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'margin-left:12px;font-size:.66rem;color:#8b949e;white-space:nowrap;">'
        f'<span style="width:8px;height:8px;border-radius:2px;'
        f'background:{c};display:inline-block;"></span>{lb} {v}</span>'
        for lb, v, c in segs if v > 0
    )
    return (
        f'<div style="margin-top:14px;direction:rtl;">'
        f'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;'
        f'margin-bottom:6px;">פילוח המלצות ({total} אנליסטים)</div>'
        f'<div style="display:flex;height:10px;border-radius:5px;'
        f'overflow:hidden;background:#21262d;direction:ltr;">{bar}</div>'
        f'<div style="margin-top:7px;">{legend}</div>'
        f'</div>'
    )


def render_analyst_snapshot(symbol: str, cur_price: float, ccy_s: str):'''

# ── עוגן 2: הצגת הפירוק בסוף כרטיס האנליסטים ────────────────────────
ANCHOR_RENDER = '''    rating = d["rating"]; rc = d["rc"]; ri = d["ri"]'''
NEW_RENDER = '''    _bd_html = _breakdown_html(symbol)

    rating = d["rating"]; rc = d["rc"]; ri = d["ri"]'''

# ── עוגן 3: שיבוץ הבר לפני שורת הדיסקליימר בתחתית הכרטיס ────────────
ANCHOR_HTML = '''  <div style="color:#8b949e;font-size:.63rem;margin-top:10px;padding-top:8px;border-top:1px solid #21262d;">
    ⚠️ נתוני אנליסטים הם הערכות בלבד ואינם מהווים ייעוץ השקעות.'''
NEW_HTML = '''  {_bd_html}

  <div style="color:#8b949e;font-size:.63rem;margin-top:10px;padding-top:8px;border-top:1px solid #21262d;">
    ⚠️ נתוני אנליסטים הם הערכות בלבד ואינם מהווים ייעוץ השקעות.'''


def main():
    try:
        with open(TARGET, "r", encoding="utf-8", newline="") as fh:
            src = fh.read()
    except FileNotFoundError:
        print(f"[עצירה] {TARGET} לא נמצא. מריצים מתיקיית הפרויקט.")
        return 1

    newline = "\r\n" if "\r\n" in src else "\n"

    def norm(s):
        return s.replace("\n", newline)

    if "def analyst_breakdown" in src:
        print("[עצירה] analyst_breakdown כבר קיימת. הסקריפט כבר רץ.")
        return 1

    edits = [
        ("פונקציית analyst_breakdown + בר הפילוח",
         norm(ANCHOR_FUNCS), norm(NEW_FUNCS)),
        ("חישוב הפילוח בתוך render_analyst_snapshot",
         norm(ANCHOR_RENDER), norm(NEW_RENDER)),
        ("שיבוץ הבר בכרטיס האנליסטים",
         norm(ANCHOR_HTML), norm(NEW_HTML)),
    ]

    for label, anchor, _ in edits:
        n = src.count(anchor)
        if n == 0:
            print(f"[עצירה] לא נמצא עוגן עבור: {label}")
            return 1
        if n > 1:
            print(f"[עצירה] העוגן עבור '{label}' מופיע {n} פעמים.")
            return 1

    print("=" * 62)
    print("פילוח המלצות אנליסטים"
          + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print("\nשלושה עוגנים נמצאו, כל אחד פעם אחת בדיוק.\n")
    print("  analyst_breakdown(symbol) -> dict | None   [cache 1h]")
    print("  מקור: tk.recommendations (לא .info)")
    print("  מטופלות שתי צורות DataFrame של yfinance\n")
    print("  התצוגה: בר מקובץ בחמישה צבעים + מקרא עם מספרים")
    print("  אין נתון -> לא מוצג כלום\n")
    print("  שימי לב: הסקריפט מחשב את _bd_html אבל עדיין לא")
    print("  משבץ אותו ב-HTML של הכרטיס. זה נעשה ידנית בצעד הבא,")
    print("  כי מבנה ה-HTML שם ארוך ואני לא רוצה לנחש איפה הוא נגמר.")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_analyst_breakdown.py --apply")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)

    out = src
    for label, anchor, replacement in edits:
        out = out.replace(anchor, replacement, 1)
        print(f"  [בוצע] {label}")

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print("\n" + "-" * 62)
    print(f"עודכן. גיבוי: {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
