"""
rr_tab.py
=========
ממשק המשתמש של מודול אסטרטגיית סיכון-סיכוי + ניהול דוחות.

נקודת כניסה יחידה:
    from rr_tab import render_rr_tab
    render_rr_tab()

המודול אינו יודע דבר על שאר האפליקציה. כל תלות חיצונית מוזרקת כפרמטר
אופציונלי, ואם לא הוזרקה — יש נפילה חיננית ל-yfinance או לקלט ידני:

    render_rr_tab(
        key_prefix="rr",
        price_fetcher=my_price_func,        # (ticker) -> float
        atr_fetcher=my_atr_func,            # (ticker) -> float
        earnings_fetcher=my_earnings_func,  # (ticker) -> datetime.date | None
        default_account_value=100_000,
    )
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Optional

import pandas as pd
import streamlit as st

import rr_engine as rr

# ---------------------------------------------------------------------------
# עיצוב — משתמש במשתני ה-CSS המרכזיים של האפליקציה, עם ערכי גיבוי
# ---------------------------------------------------------------------------

_CSS = """
<style>
.rr-wrap { direction: rtl; text-align: right; }
.rr-wrap * { direction: rtl; }

.rr-card {
  background: var(--c-surface-1, rgba(255,255,255,0.035));
  border: 1px solid var(--c-border, rgba(255,255,255,0.08));
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.rr-title {
  font-size: 0.82rem; font-weight: 700; letter-spacing: .02em;
  color: var(--c-text-2, #8B93A7); margin-bottom: 10px;
}
.rr-badge {
  display: inline-block; padding: 4px 12px; border-radius: 999px;
  font-size: 0.78rem; font-weight: 700; margin-left: 6px;
}
.rr-badge.green  { background: rgba(34,197,94,.14);  color: var(--c-green,  #22c55e); }
.rr-badge.yellow { background: rgba(234,179,8,.14);  color: var(--c-yellow, #eab308); }
.rr-badge.orange { background: rgba(249,115,22,.14); color: var(--c-orange, #f97316); }
.rr-badge.red    { background: rgba(239,68,68,.14);  color: var(--c-red,    #ef4444); }
.rr-badge.gray   { background: rgba(139,147,161,.14);color: var(--c-text-2, #8B93A7); }

.rr-tbl { width: 100%; border-collapse: collapse; direction: rtl;
          font-size: 0.88rem; table-layout: fixed; }
.rr-tbl tr { border-bottom: 1px solid var(--c-border, rgba(255,255,255,0.08)); }
.rr-tbl tr:last-child { border-bottom: none; }
.rr-tbl td { padding: 7px 0; vertical-align: top; line-height: 1.5; }
.rr-k { text-align: right; width: 55%; color: var(--c-text-2, #8B93A7);
        padding-left: 10px !important; word-break: break-word; }
.rr-v { text-align: left; width: 45%; font-weight: 700;
        font-variant-numeric: tabular-nums; color: var(--c-text-1, #F4F6FB); }

.rr-alert { border-radius: 10px; padding: 12px 14px; font-size: 0.87rem;
            line-height: 1.6; margin-bottom: 12px; border-right: 3px solid;
            color: var(--c-text-1, #F4F6FB); }
.rr-alert.red    { background: rgba(239,68,68,.10);  border-color: var(--c-red,   #ef4444); }
.rr-alert.orange { background: rgba(249,115,22,.10); border-color: var(--c-orange,#f97316); }
.rr-alert.green  { background: rgba(34,197,94,.10);  border-color: var(--c-green, #22c55e); }

/* RTL_HEADINGS — הכלל הגלובלי באפליקציה מכסה div, p, span ו-label בלבד.
   כותרות h1-h6 נשארות LTR ולכן מופיעות צמודות לשמאל. */
.rr-wrap h1, .rr-wrap h2, .rr-wrap h3, .rr-wrap h4, .rr-wrap h5,
.rr-head, .rr-head h1, .rr-head h2, .rr-head h3, .rr-head h4 {
  direction: rtl !important; text-align: right !important;
}

/* המדריך המתקפל. ממוקד לפי מפתח הקונטיינר כדי לא לגעת בשאר הטאבים. */
[class*="st-key-rrguide_"] details,
[class*="st-key-rrguide_"] summary {
  direction: rtl !important; text-align: right !important;
  background: transparent !important; border-color: rgba(255,255,255,.18) !important;
}
[class*="st-key-rrguide_"] summary p,
[class*="st-key-rrguide_"] summary span {
  text-align: right !important; color: var(--c-text-1, #F4F6FB) !important;
  font-weight: 700 !important; opacity: 1 !important;
}
[class*="st-key-rrguide_"] summary svg { fill: var(--c-text-1, #F4F6FB) !important; }
</style>
"""

_POS = "color: var(--c-green, #22c55e); font-weight: 700;"
_NEG = "color: var(--c-red, #ef4444); font-weight: 700;"


# ---------------------------------------------------------------------------
# מקורות נתונים — ברירת מחדל עם yfinance, ניתנים להחלפה
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _yf_snapshot(ticker: str) -> dict:
    """מחיר אחרון, ATR(14) ותאריך דוח קרוב. נכשל בשקט ומחזיר ערכים ריקים."""
    out = {"price": None, "atr": None, "earnings": None}
    try:
        import yfinance as yf

        tk = yf.Ticker(ticker)
        hist = tk.history(period="3mo", interval="1d", auto_adjust=True)
        if hist is not None and not hist.empty:
            out["price"] = float(hist["Close"].iloc[-1])
            out["atr"] = _atr_wilder(hist, 14)
        try:
            cal = tk.calendar
            if isinstance(cal, dict):
                dates = cal.get("Earnings Date") or []
                if dates:
                    d = dates[0]
                    out["earnings"] = d if isinstance(d, date) else pd.to_datetime(d).date()
            elif cal is not None and not cal.empty:
                out["earnings"] = pd.to_datetime(cal.iloc[0, 0]).date()
        except Exception:
            pass
    except Exception:
        pass
    return out


def _atr_wilder(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    """ATR אמיתי עם החלקה אקספוננציאלית של Wilder."""
    if df is None or len(df) < period + 1:
        return None
    high, low, close = df["High"], df["Low"], df["Close"]
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    val = float(atr.iloc[-1])
    return val if val > 0 else None


# ---------------------------------------------------------------------------
# עזרי תצוגה
# ---------------------------------------------------------------------------

def _metric(label: str, value: str) -> str:
    """שורת מדד. טבלה ולא flex: flex עם space-between נראה נכון על המסך,
    אבל בהעתקה הטקסט נדבק, והתווית מתנגשת בערך כשהיא ארוכה."""
    return (f'<tr><td class="rr-k">{label}</td>'
            f'<td class="rr-v">{value}</td></tr>')


def _money(x: float) -> str:
    return f"{x:,.0f}$" if abs(x) >= 1000 else f"{x:,.2f}$"


def _card(title: str, rows_html: str, lead_html: str = "") -> None:
    st.markdown(
        f'<div class="rr-wrap"><div class="rr-card">'
        f'<div class="rr-title">{title}</div>{lead_html}'
        f'<table class="rr-tbl">{rows_html}</table></div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# הרכיב הראשי
# ---------------------------------------------------------------------------

def render_rr_tab(
    key_prefix: str = "rr",
    price_fetcher: Optional[Callable[[str], Optional[float]]] = None,
    atr_fetcher: Optional[Callable[[str], Optional[float]]] = None,
    earnings_fetcher: Optional[Callable[[str], Optional[date]]] = None,
    default_ticker: str = "NVDA",
    default_account_value: float = 100_000.0,
) -> Optional[rr.TradePlan]:
    """
    מצייר את המודול המלא ומחזיר את תוכנית העסקה (או None אם הקלט לא תקין).
    בטוח לקריאה ללא תנאי — אינו מגדיר פונקציות בתוך ענפי if.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    k = lambda name: f"{key_prefix}_{name}"  # noqa: E731

    st.markdown('<div class="rr-wrap">', unsafe_allow_html=True)

    # ---------------- קלט ----------------
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        ticker = st.text_input("סימול", value=default_ticker, key=k("ticker")).upper().strip()
    with c2:
        direction = "long" if st.radio(
            "כיוון", ["לונג", "שורט"], horizontal=True, key=k("dir")) == "לונג" else "short"
    with c3:
        account_value = st.number_input(
            "שווי תיק ($)", min_value=100.0, value=float(default_account_value),
            step=1000.0, key=k("acct"))

    snap = _yf_snapshot(ticker) if ticker else {"price": None, "atr": None, "earnings": None}
    live_price = (price_fetcher(ticker) if price_fetcher else None) or snap["price"]
    live_atr = (atr_fetcher(ticker) if atr_fetcher else None) or snap["atr"]
    earn_date = (earnings_fetcher(ticker) if earnings_fetcher else None) or snap["earnings"]

    c4, c5, c6 = st.columns(3)
    with c4:
        entry = st.number_input(
            "מחיר כניסה", min_value=0.01,
            value=float(live_price) if live_price else 100.0,
            step=0.01, format="%.2f", key=k("entry"))
    with c5:
        stop_mode = st.selectbox("שיטת סטופ", ["לפי ATR", "ידני", "לפי אחוז"], key=k("smode"))
    with c6:
        risk_pct = st.number_input(
            "סיכון לעסקה (%)", min_value=0.1, max_value=10.0,
            value=1.0, step=0.1, key=k("riskpct")) / 100.0

    # חישוב הסטופ לפי השיטה הנבחרת
    sign = rr.direction_sign(direction)
    if stop_mode == "לפי ATR":
        a1, a2 = st.columns(2)
        with a1:
            atr_val = st.number_input(
                "ATR(14)", min_value=0.01,
                value=float(live_atr) if live_atr else round(entry * 0.02, 2),
                step=0.01, format="%.2f", key=k("atr"))
        with a2:
            atr_mult = st.slider("מכפיל ATR", 0.5, 4.0, 2.0, 0.25, key=k("atrmult"))
        stop = rr.stop_from_atr(entry, atr_val, atr_mult, direction)
    elif stop_mode == "לפי אחוז":
        pct = st.slider("מרחק סטופ (%)", 0.5, 20.0, 5.0, 0.5, key=k("spct")) / 100.0
        stop = entry * (1 - sign * pct)
    else:
        default_stop = round(entry * (1 - sign * 0.05), 2)
        stop = st.number_input("מחיר סטופ", min_value=0.01, value=default_stop,
                               step=0.01, format="%.2f", key=k("stop"))

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- בניית התוכנית ----------------
    try:
        plan = rr.build_plan(
            ticker=ticker or "—", entry=entry, stop=stop, direction=direction,
            account_value=account_value, risk_pct=risk_pct, earnings_date=earn_date,
        )
    except ValueError as exc:
        st.error(str(exc))
        return None

    if plan.shares == 0:
        st.warning("הסיכון למניה גדול מדי ביחס לתקציב הסיכון — לא ניתן לפתוח פוזיציה בגודל תקין.")

    days = rr.days_to_earnings(plan.earnings_date)
    assessment = rr.earnings_action(days)

    # ---------------- סיזינג לפי תקציב פער ----------------
    # זה החלק היחיד שקיים כאן ולא ב-render_rr_section, כי הוא שאלה של
    # תכנון לפני כניסה ולא של ניהול פוזיציה קיימת.
    g1, g2 = st.columns(2)
    with g1:
        gap_budget = st.number_input("תקציב הפסד בפער (% מהתיק)", 0.1, 10.0, 1.0, 0.1,
                                     key=k("gapbudget")) / 100.0
    with g2:
        assumed_gap = st.number_input("פער צפוי בדוח (%)", 1.0, 50.0, 12.0, 1.0,
                                      key=k("assumedgap")) / 100.0

    gap_size = rr.size_for_gap_budget(account_value, gap_budget, entry,
                                      assumed_gap, direction)
    _card("גודל פוזיציה מותאם לדוח", "".join([
        _metric("לפי הסטופ", f"{plan.shares:,} מניות"),
        _metric("לפי תקציב הפער", f"{gap_size['shares']:,} מניות"),
        _metric("הפרש", f"{plan.shares - gap_size['shares']:,} מניות לצמצום"),
        _metric("הפסד בתרחיש הפער", _money(gap_size["gap_loss"])),
    ]))

    # ---------------- כל השאר מגיע מהסקשן המשותף ----------------
    # טבלאות HTML ולא st.dataframe: הדאטהפריים של סטרימליט מצייר קנבס,
    # לא DOM, ולכן הוא לא יודע לקרוא משתני CSS ולא מכבד direction:rtl.
    render_rr_section(
        ticker=plan.ticker, entry=entry, stop=stop, shares=plan.shares,
        portfolio_value=account_value, direction=direction,
        earnings_date=plan.earnings_date, key_prefix=f"{key_prefix}_sec",
        interactive=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return plan


# ---------------------------------------------------------------------------
# תרשים התרחישים
# ---------------------------------------------------------------------------

def _render_gap_chart(plan: rr.TradePlan, outcomes: list) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    green = "#22c55e"
    red = "#ef4444"
    fig = go.Figure(go.Bar(
        x=[f"{o.gap_pct:+.0%}" for o in outcomes],
        y=[o.pnl for o in outcomes],
        marker_color=[green if o.pnl >= 0 else red for o in outcomes],
        hovertemplate="פער %{x}<br>תוצאה %{y:,.0f}$<extra></extra>",
    ))
    fig.add_hline(y=-plan.risk_amount, line_dash="dash", line_color="#f97316",
                  annotation_text="הסיכון המתוכנן (1R-)", annotation_position="bottom left")
    fig.add_hline(y=0, line_color="#8b93a1", line_width=1)
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8b93a1"), showlegend=False,
        title=dict(text="רווח/הפסד לפי גודל הפער", x=0.98, xanchor="right",
                   font=dict(size=13)),
        yaxis=dict(gridcolor="rgba(139,147,161,.15)", tickformat=",.0f"),
    )
    st.plotly_chart(fig, use_container_width=True,
                    key=f"rr_gap_chart_{plan.ticker}")


# ---------------------------------------------------------------------------
# גרסת "סקשן" — לשילוב בתוך טאב האסטרטגיה הקיים
# ---------------------------------------------------------------------------
#
# ההבדל מ-render_rr_tab: אין כאן שדות קלט לסימול / תיק / סטופ. הכל מגיע
# מ-report.position שכבר חושב במנוע האסטרטגיה. במצב ברירת המחדל
# (interactive=False) אין אף ווידג'ט, ולכן אין rerun שמוחק את תוצאות הסקאן.
#
# הטבלאות כאן הן HTML ולא st.dataframe, כדי להתאים לסגנון RTL של טאב 14.

_C = {
    "green": "var(--c-green, #16c784)",
    "red":   "var(--c-red, #ea3943)",
    "amber": "var(--c-amber, #f0b90b)",
    "blue":  "var(--c-blue-lt, #4d9fff)",
    "text":  "var(--c-text-1, #c9d1d9)",
    "gray":  "#8b949e",
}

_TIER_COLOR = {"green": _C["green"], "yellow": _C["amber"], "orange": _C["amber"],
               "red": _C["red"], "gray": _C["gray"]}


def _num(v: float, fmt: str, color: bool = True) -> str:
    txt = format(v, fmt)
    if not color:
        return f'<span style="font-family:JetBrains Mono,monospace;">{txt}</span>'
    c = _C["green"] if v > 0 else (_C["red"] if v < 0 else _C["text"])
    return (f'<span style="font-family:JetBrains Mono,monospace;'
            f'font-weight:700;color:{c};">{txt}</span>')


def _targets_table_html(plan: rr.TradePlan) -> str:
    entry_label = "מחיר קנייה (כניסה)" if plan.direction == "long" else "מחיר מכירה (כניסה)"
    rows = [
        (entry_label, "—", plan.entry, 0.0, plan.shares, 0.0, 0.0, _C["text"]),
        ("פקודת הגנה (Stop Loss)", "—", plan.stop, -plan.stop_distance_pct,
         plan.shares, -plan.risk_amount, -1.0, _C["red"]),
    ]
    for t in plan.targets:
        dist = rr.direction_sign(plan.direction) * (t.price - plan.entry) / plan.entry
        rows.append((t.label, t.rr_text, t.price, dist, t.shares, t.profit,
                     t.r_multiple, _C["green"]))

    body = ""
    for label, ratio, price, dist, sh, pnl, r_mult, accent in rows:
        body += f'''
    <tr style="border-top:1px solid #ffffff14;">
      <td style="padding:.55rem .7rem;font-weight:600;white-space:nowrap;
                 border-right:3px solid {accent};">{_esc_rr(label)}</td>
      <td style="padding:.55rem .7rem;opacity:.7;">{_esc_rr(ratio)}</td>
      <td style="padding:.55rem .7rem;">{_num(price, ",.2f", color=False)}</td>
      <td style="padding:.55rem .7rem;">{_num(dist, "+.2%")}</td>
      <td style="padding:.55rem .7rem;">{_num(sh, ",d", color=False)}</td>
      <td style="padding:.55rem .7rem;">{_num(pnl, "+,.0f")}</td>
      <td style="padding:.55rem .7rem;">{_num(r_mult, "+.1f")}</td>
    </tr>'''

    return f'''
<div dir="rtl" style="overflow-x:auto;margin:.3rem 0 .9rem;">
<table style="width:100%;border-collapse:collapse;font-size:.9rem;color:{_C["text"]};">
  <thead><tr style="background:#ffffff0a;">
    <th style="padding:.5rem .7rem;text-align:right;">שלב</th>
    <th style="padding:.5rem .7rem;text-align:right;">יחס</th>
    <th style="padding:.5rem .7rem;text-align:right;">מחיר</th>
    <th style="padding:.5rem .7rem;text-align:right;">מרחק</th>
    <th style="padding:.5rem .7rem;text-align:right;">מניות</th>
    <th style="padding:.5rem .7rem;text-align:right;">רווח/הפסד</th>
    <th style="padding:.5rem .7rem;text-align:right;">R</th>
  </tr></thead>
  <tbody>{body}</tbody>
</table></div>'''


def _gap_table_html(plan: rr.TradePlan, outcomes: list) -> str:
    body = ""
    for o in outcomes:
        if o.outcome == "stop_breached":
            accent = _C["red"]
        elif o.outcome.startswith("target"):
            accent = _C["green"]
        else:
            accent = _C["gray"]
        slip = (f'{_num(-o.slippage_r, "+.2f")}R' if o.slippage_r
                else '<span style="opacity:.4;">—</span>')
        body += f'''
    <tr style="border-top:1px solid #ffffff14;">
      <td style="padding:.5rem .7rem;border-right:3px solid {accent};">
        {_num(o.gap_pct, "+.0%")}</td>
      <td style="padding:.5rem .7rem;">{_num(o.open_price, ",.2f", color=False)}</td>
      <td style="padding:.5rem .7rem;font-size:.84rem;">{_esc_rr(o.label)}</td>
      <td style="padding:.5rem .7rem;">{_num(o.realized_r, "+.2f")}</td>
      <td style="padding:.5rem .7rem;">{_num(o.pnl, "+,.0f")}</td>
      <td style="padding:.5rem .7rem;">{slip}</td>
    </tr>'''

    return f'''
<div dir="rtl" style="overflow-x:auto;margin:.3rem 0 .6rem;">
<table style="width:100%;border-collapse:collapse;font-size:.9rem;color:{_C["text"]};">
  <thead><tr style="background:#ffffff0a;">
    <th style="padding:.5rem .7rem;text-align:right;">פער בפתיחה</th>
    <th style="padding:.5rem .7rem;text-align:right;">מחיר פתיחה</th>
    <th style="padding:.5rem .7rem;text-align:right;">מה קורה</th>
    <th style="padding:.5rem .7rem;text-align:right;">R בפועל</th>
    <th style="padding:.5rem .7rem;text-align:right;">רווח/הפסד</th>
    <th style="padding:.5rem .7rem;text-align:right;">חריגה מהתכנון</th>
  </tr></thead>
  <tbody>{body}</tbody>
</table></div>'''


def _esc_rr(x) -> str:
    import html as _html
    return _html.escape(str(x))


def _earnings_card_html(plan: rr.TradePlan, assessment, trim: dict) -> str:
    color = _TIER_COLOR.get(assessment.color, _C["gray"])
    d = assessment.days
    when = ("היום" if d == 0 else f"בעוד {d} ימים" if d and d > 0
            else f"לפני {abs(d)} ימים" if d is not None else "תאריך לא ידוע")
    detail = ""
    if assessment.days is not None and assessment.recommended_size_pct < 1.0:
        detail = (f'<div style="margin-top:.5rem;font-size:.86rem;opacity:.9;">'
                  f'להשאיר {trim["keep_shares"]:,} מניות · '
                  f'לצמצם {trim["trim_shares"]:,} מניות · '
                  f'סיכון שנותר ${trim["residual_risk"]:,.0f}</div>')
    return f'''
<div dir="rtl" style="border:1px solid {color}44;border-right:4px solid {color};
     background:linear-gradient(90deg,{color}12,transparent);
     border-radius:12px;padding:.85rem 1.1rem;margin:.4rem 0 .9rem;">
  <div style="display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap;">
    <span style="font-size:1.05rem;font-weight:800;color:{color};">
      {_esc_rr(assessment.label)}</span>
    <span style="font-family:JetBrains Mono,monospace;font-size:.95rem;color:{_C["text"]};">
      דוח {_esc_rr(when)}</span>
    <span style="font-size:.85rem;opacity:.75;">
      חשיפה מומלצת {assessment.recommended_size_pct:.0%}</span>
  </div>
  <div style="margin-top:.4rem;font-size:.9rem;color:{_C["text"]};">
    {_esc_rr(assessment.action)}</div>
  {detail}
</div>'''


def _bullet(color: str, text: str) -> str:
    return (f'<li style="margin-bottom:.35rem;line-height:1.65;">'
            f'<span style="color:{color};font-weight:800;">●</span> {text}</li>')


def _summary_html(plan: rr.TradePlan, assessment, outcomes: list) -> str:
    """
    סיכום דינמי שקורא את המספרים של העסקה הזו ואומר מה הם אומרים.
    לא טקסט קבוע — כל שורה נגזרת מהנתונים בפועל.
    """
    g, r_, a, t = _C["green"], _C["red"], _C["amber"], _C["text"]
    sp = plan.stop_distance_pct
    bullets = []

    # 1. הקריאה המרכזית: מה הסטופ דורש מהיעדים
    bullets.append(_bullet(t,
        f'סטופ של <b>{sp:.1%}</b> קובע את הכל. יעד 1:2 דורש תנועה של '
        f'<b>{2 * sp:.1%}</b>, ויעד 1:3 דורש <b>{3 * sp:.1%}</b>. '
        f'מזיזה את הסטופ — כל השורות בטבלה זזות איתו.'))

    # 2. האם הסטופ במרחק שפוי
    if sp < 0.02:
        bullets.append(_bullet(a,
            'הסטופ צר מאוד. הפוזיציה יוצאת גדולה, אבל רעש יומיומי רגיל '
            'יתפוס אותו עוד לפני שהתזה נבדקה.'))
    elif sp > 0.10:
        bullets.append(_bullet(a,
            f'הסטופ רחב מאוד. יעד 1:3 דורש תנועה של {3 * sp:.0%}, '
            f'וזה תרחיש שקורה לעיתים נדירות. שקלי לקצר את הסטופ או '
            f'להסתפק ביעד 1:2.'))
    elif sp > 0.08:
        bullets.append(_bullet(a,
            'הסטופ רחב. הפוזיציה קטנה יחסית, וזה תקין — '
            'הסיכון הכספי נשמר קבוע גם כשהמרחק גדל.'))
    else:
        bullets.append(_bullet(g, 'מרחק הסטופ בטווח סביר ביחס למחיר המניה.'))

    # 3. חשיפה מול התיק
    if plan.account_value:
        risk_share = plan.risk_amount / plan.account_value
        notional_share = plan.notional / plan.account_value
        color = r_ if notional_share > 0.30 else (a if notional_share > 0.20 else g)
        extra = (' זו ריכוזיות גבוהה למניה בודדת.' if notional_share > 0.30 else '')
        bullets.append(_bullet(color,
            f'הפוזיציה תופסת <b>{notional_share:.0%}</b> מהתיק '
            f'(${plan.notional:,.0f}), אבל מסכנת רק <b>{risk_share:.2%}</b> '
            f'(${plan.risk_amount:,.0f}).{extra}'))

    # 4. מה נדרש כדי להרוויח לאורך זמן
    be_blend = rr.breakeven_win_rate(plan.blended_r)
    bullets.append(_bullet(t,
        f'ביציאה מדורגת 50/30/20 היחס האפקטיבי הוא <b>{plan.blended_r:.2f}R</b>, '
        f'ולכן דרושות <b>{be_blend:.0%}</b> הצלחות רק כדי לא להפסיד. '
        f'הכותרת "1:3" מטעה — אל תתכנני לפיה.'))

    # 5. דוח
    if assessment.days is None:
        bullets.append(_bullet(a,
            'אין תאריך דוח מאומת. אל תגדילי חשיפה לפני בדיקה ידנית בלוח הדוחות.'))
    else:
        col = _TIER_COLOR.get(assessment.color, _C["gray"])
        when = ('היום' if assessment.days == 0
                else f'בעוד {assessment.days} ימים' if assessment.days > 0
                else f'לפני {abs(assessment.days)} ימים')
        bullets.append(_bullet(col,
            f'הדוח {when}. {_esc_rr(assessment.action)}'))

    # 6. מה הפער עושה בפועל
    losers = [o for o in outcomes if o.pnl < 0]
    worst = min(outcomes, key=lambda o: o.pnl)
    breached = [o for o in outcomes if o.outcome == "stop_breached"]
    if breached:
        deep = [o for o in breached if o.slippage_r > 0]
        if deep:
            bullets.append(_bullet(r_,
                f'מתוך {len(outcomes)} תרחישי פער, <b>{len(losers)}</b> מסתיימים בהפסד, '
                f'ו-<b>{len(deep)}</b> מהם פורצים את הסטופ ומפסידים יותר מ-1R. '
                f'הגרוע: ${abs(worst.pnl):,.0f} במקום ${plan.risk_amount:,.0f} שתוכננו.'))
        else:
            bullets.append(_bullet(a,
                f'{len(losers)} מתוך {len(outcomes)} תרחישי פער מסתיימים בהפסד, '
                f'אבל אף אחד מהם לא חורג מהסיכון המתוכנן בטווח שנבדק.'))

    return f'''
<div dir="rtl" style="border:1px solid #ffffff1f;border-radius:12px;
     background:#ffffff06;padding:.85rem 1.1rem;margin:.2rem 0 1rem;color:{t};">
  <div style="font-weight:800;margin-bottom:.5rem;font-size:.95rem;">
    מה הטבלאות אומרות על העסקה הזו</div>
  <ul style="font-size:.88rem;padding-right:1.1rem;padding-left:0;margin:0;text-align:right;direction:rtl;list-style:none;">{"".join(bullets)}</ul>
</div>'''


def render_rr_section(
    ticker: str,
    entry: float,
    stop: float,
    shares: int = 0,
    portfolio_value: Optional[float] = None,
    direction: str = "long",
    earnings_date: Optional[date] = None,
    earnings_fetcher: Optional[Callable[[str], Optional[date]]] = None,
    key_prefix: str = "rr_sec",
    interactive: bool = False,
    show_chart: bool = True,
    show_summary: bool = True,
    show_guide: bool = True,
) -> Optional[rr.TradePlan]:
    """
    מציג את מפת יעדי הרווח, פאנל הדוחות וסימולציית הפערים עבור פוזיציה קיימת.

    interactive=False (ברירת מחדל) — אפס ווידג'טים, ולכן אפס rerun. זהו המצב
    הבטוח לשילוב בתוך טאב שנשען על כפתור "הרץ ניתוח".
    """
    try:
        plan = rr.build_plan(
            ticker=ticker, entry=float(entry), stop=float(stop),
            shares=int(shares), direction=direction,
            account_value=portfolio_value,
        )
    except ValueError as exc:
        st.warning(f"לא ניתן לבנות מפת יעדים: {exc}")
        return None

    if earnings_date is None:
        if earnings_fetcher:
            earnings_date = earnings_fetcher(ticker)
        else:
            earnings_date = _yf_snapshot(ticker).get("earnings")
    plan.earnings_date = earnings_date

    # ---- 1. מפת יעדי הרווח ----
    st.markdown('<div dir="rtl" style="text-align:right;font-weight:700;margin:1.1rem 0 .2rem;">'
                'מפת יעדי רווח לפי יחס סיכון-סיכוי</div>', unsafe_allow_html=True)
    st.markdown(_targets_table_html(plan), unsafe_allow_html=True)

    be2 = rr.breakeven_win_rate(2.0)
    st.markdown(
        f'<div dir="rtl" style="font-size:.85rem;opacity:.8;margin:-.4rem 0 .9rem;">'
        f'סיכון ליחידה ${plan.r_unit:,.2f} · '
        f'מרחק סטופ {plan.stop_distance_pct:.2%} · '
        f'R משוקלל ביציאה מדורגת 50/30/20 — {plan.blended_r:.2f}R · '
        f'אחוז הצלחה נדרש ביחס 1:2 — {be2:.0%} · '
        f'תוחלת ב-40% הצלחה {rr.expectancy_r(0.40, 2.0):+.2f}R לעסקה</div>',
        unsafe_allow_html=True)

    # ---- 2. ניהול ציפיות לקראת דוח ----
    days = rr.days_to_earnings(plan.earnings_date)
    assessment = rr.earnings_action(days)
    trim = rr.trim_plan(plan, assessment.recommended_size_pct)
    st.markdown('<div dir="rtl" style="text-align:right;font-weight:700;margin:.6rem 0 .2rem;">'
                'ניהול חשיפה לקראת הדוח</div>', unsafe_allow_html=True)
    st.markdown(_earnings_card_html(plan, assessment, trim), unsafe_allow_html=True)

    # ---- 3. סימולציית פערים ----
    ref_price = plan.entry
    gaps = rr.DEFAULT_GAP_GRID
    if interactive:
        i1, i2 = st.columns(2)
        ref_price = i1.number_input(
            "מחיר סגירה לפני הדוח", min_value=0.01, value=float(plan.entry),
            step=0.01, format="%.2f", key=f"{key_prefix}_ref",
            help="שני אם הפוזיציה כבר ברווח — הפער נמדד מהסגירה, לא מהכניסה.")
        span = i2.slider("טווח פערים לבדיקה (%)", 5, 40, 20, 5,
                         key=f"{key_prefix}_span")
        gaps = tuple(round(x / 100, 4) for x in range(-span, span + 1, 5))

    outcomes = rr.gap_scenario_table(plan, gaps=gaps, ref_price=ref_price)
    wc = rr.worst_case_gap_loss(plan, gap_pct=0.15, ref_price=ref_price)

    st.markdown('<div dir="rtl" style="text-align:right;font-weight:700;margin:.6rem 0 .2rem;">'
                'סימולציית פער בפתיחה שאחרי הדוח</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div dir="rtl" style="border-right:3px solid {_C["red"]};'
        f'background:{_C["red"]}12;border-radius:10px;padding:.7rem .95rem;'
        f'margin:.2rem 0 .7rem;font-size:.87rem;line-height:1.65;color:{_C["text"]};">'
        f'<b>הסטופ אינו מגן מעבר לדוח.</b> בפער נגדי של 15% הפוזיציה נסגרת ב-'
        f'${wc["open_price"]:,.2f} ולא בסטופ. ההפסד בפועל '
        f'${abs(wc["actual_loss"]):,.0f} במקום ${abs(wc["planned_loss"]):,.0f} '
        f'שתוכננו — פי {wc["multiple_of_plan"]:.1f}.</div>',
        unsafe_allow_html=True)
    st.markdown(_gap_table_html(plan, outcomes), unsafe_allow_html=True)

    if show_chart:
        _render_gap_chart(plan, outcomes)

    # ---- 4. סיכום דינמי של שלוש הטבלאות ----
    if show_summary:
        st.markdown(_summary_html(plan, assessment, outcomes), unsafe_allow_html=True)

    # ---- 5. מדריך הפרמטרים ----
    if show_guide:
        with st.container(key=f"rrguide_{key_prefix}"):
            with st.expander("מה כל פרמטר בטבלאות אומר", expanded=False):
                try:
                    from rr_guide import render_rr_guide
                    render_rr_guide(compact=True)
                except ImportError:
                    st.caption("קובץ rr_guide.py לא נמצא בתיקיית הפרויקט.")

    return plan


# ---------------------------------------------------------------------------
# הרצה עצמאית לבדיקה ויזואלית:  streamlit run rr_tab.py
# מציג את הסקשן עם נתוני דמה, בלי תלות במנוע האסטרטגיה ובלי פסק דין.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    st.set_page_config(page_title="סיכון-סיכוי", layout="wide")
    st.markdown("""<style>
      .block-container{direction:rtl;}
      :root{--c-green:#16c784;--c-red:#ea3943;--c-amber:#f0b90b;
            --c-blue-lt:#4d9fff;--c-text-1:#c9d1d9;}
    </style>""", unsafe_allow_html=True)

    st.markdown('<div dir="rtl" class="rr-head"><h3 style="text-align:right;direction:rtl;">בדיקה עצמאית — סקשן סיכון-סיכוי</h3>'
                '<div style="opacity:.7;font-size:.88rem;">נתוני דמה. '
                'זה בדיוק מה שייראה בטאב האסטרטגיה מתחת לתוכנית הפוזיציה.'
                '</div></div>', unsafe_allow_html=True)

    d1, d2, d3, d4 = st.columns(4)
    _tkr = d1.text_input("סימול", "NVDA", key="demo_tkr")
    _entry = d2.number_input("כניסה", value=180.00, step=0.5, format="%.2f", key="demo_entry")
    _stop = d3.number_input("סטופ", value=172.50, step=0.5, format="%.2f", key="demo_stop")
    _shares = d4.number_input("מניות", value=133, step=1, key="demo_shares")

    st.divider()
    render_rr_section(
        ticker=_tkr, entry=_entry, stop=_stop, shares=int(_shares),
        portfolio_value=100_000.0, key_prefix="demo_rr", interactive=True,
    )


# ---------------------------------------------------------------------------
# מנהל פוזיציות — לשילוב בטאב המסחר הווירטואלי
# ---------------------------------------------------------------------------
#
# ההבדל מ-render_rr_section: כאן הפוזיציה כבר פתוחה. יש מחיר נוכחי, יש
# רווח לא ממומש, ויש שאלה אחרת לגמרי — לא "איפה אכנס" אלא "מה לעשות עכשיו".

_POS_KEYS = {
    "ticker": ("ticker", "symbol", "סימול", "מניה", "stock"),
    "entry":  ("entry", "entry_price", "avg_price", "avg_cost", "buy_price",
               "price", "מחיר_כניסה"),
    "shares": ("shares", "qty", "quantity", "units", "amount", "מניות"),
    "stop":   ("stop", "stop_price", "stop_loss", "sl", "סטופ"),
    "direction": ("direction", "side", "כיוון"),
}


def normalize_positions(positions) -> list[dict]:
    """
    ממיר רשימת פוזיציות מכל מבנה סביר למבנה אחיד.

    קולט: list[dict], DataFrame, או list של אובייקטים עם תכונות.
    מזהה שמות שדות נפוצים (ticker/symbol, entry_price/avg_price, qty/shares...).
    פוזיציה בלי סימול או בלי מחיר כניסה מדולגת בשקט.
    """
    if positions is None:
        return []
    if hasattr(positions, "to_dict") and hasattr(positions, "columns"):
        positions = positions.to_dict("records")
    # מבנה {סימול: {shares, avg_price}} — כמו pf["positions"] באפליקציה
    if isinstance(positions, dict):
        positions = [
            ({"ticker": k, **v} if isinstance(v, dict) else {"ticker": k, "entry": v})
            for k, v in positions.items()
        ]

    out = []
    for raw in positions:
        if not isinstance(raw, dict):
            raw = {k: getattr(raw, k) for k in dir(raw) if not k.startswith("_")}
        lower = {str(k).lower(): v for k, v in raw.items()}

        def pick(field):
            for name in _POS_KEYS[field]:
                if name in lower and lower[name] not in (None, ""):
                    return lower[name]
            return None

        ticker, entry = pick("ticker"), pick("entry")
        if not ticker or entry in (None, ""):
            continue
        side = str(pick("direction") or "long").lower()
        side = "short" if side in ("short", "sell", "שורט") else "long"
        try:
            shares = int(float(pick("shares") or 0))
            if shares <= 0:
                continue
            out.append({
                "ticker": str(ticker).upper().strip(),
                "entry": float(entry),
                "shares": shares,
                "stop": float(pick("stop")) if pick("stop") else None,
                "direction": side,
            })
        except (TypeError, ValueError):
            continue
    return out


def _status_card_html(plan: rr.TradePlan, status) -> str:
    color = _TIER_COLOR.get(status.color, _C["gray"])
    nxt = ""
    if status.next_target:
        nxt = (f'<span style="font-size:.85rem;opacity:.8;">'
               f'היעד הבא: {_esc_rr(status.next_target.label)} ב-'
               f'${status.next_target.price:,.2f} '
               f'({status.distance_to_next_pct:+.1%} מכאן)</span>')
    pnl_c = _C["green"] if status.unrealized_pnl >= 0 else _C["red"]
    return f'''
<div dir="rtl" style="border:1px solid {color}44;border-right:4px solid {color};
     background:linear-gradient(90deg,{color}12,transparent);
     border-radius:12px;padding:.85rem 1.1rem;margin:.4rem 0 .9rem;">
  <div style="display:flex;align-items:baseline;gap:.8rem;flex-wrap:wrap;">
    <span style="font-size:1.05rem;font-weight:800;color:{color};">
      {_esc_rr(status.label)}</span>
    <span style="font-family:JetBrains Mono,monospace;font-size:1.05rem;
                 font-weight:700;color:{pnl_c};">
      {status.current_r:+.2f}R · {status.unrealized_pnl:+,.0f}$</span>
    <span style="font-size:.85rem;opacity:.75;">
      מרחק מהסטופ {status.distance_to_stop_pct:+.1%}</span>
  </div>
  <div style="margin-top:.35rem;">{nxt}</div>
</div>'''


def render_position_manager(
    positions=None,
    price_fetcher: Optional[Callable[[str], Optional[float]]] = None,
    atr_fetcher: Optional[Callable[[str], Optional[float]]] = None,
    earnings_fetcher: Optional[Callable[[str], Optional[date]]] = None,
    portfolio_value: float = 100_000.0,
    default_atr_mult: float = 2.0,
    key_prefix: str = "pm",
) -> Optional[rr.TradePlan]:
    """
    בוחר פוזיציה פתוחה ומציג עליה את מפת היעדים, מצב נוכחי וניהול דוח.

    positions – רשימת הפוזיציות מטאב המסחר הווירטואלי, בכל מבנה סביר.
                אם ריק, נפתח מצב הזנה ידנית.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    pos = normalize_positions(positions)

    if not pos:
        st.markdown('<div dir="rtl" style="opacity:.75;font-size:.88rem;">'
                    'אין פוזיציות פתוחות. אפשר לתכנן עסקה ידנית.</div>',
                    unsafe_allow_html=True)
        return render_rr_tab(key_prefix=f"{key_prefix}_manual",
                             price_fetcher=price_fetcher,
                             atr_fetcher=atr_fetcher,
                             earnings_fetcher=earnings_fetcher,
                             default_account_value=portfolio_value)

    labels = [f"{p['ticker']} · {p['shares']:,} מניות · כניסה ${p['entry']:,.2f}"
              for p in pos]
    idx = st.selectbox("פוזיציה", range(len(pos)), format_func=lambda i: labels[i],
                       key=f"{key_prefix}_sel")
    p = pos[idx]

    snap = _yf_snapshot(p["ticker"])
    live = (price_fetcher(p["ticker"]) if price_fetcher else None) or snap["price"]
    atr = (atr_fetcher(p["ticker"]) if atr_fetcher else None) or snap["atr"]

    c1, c2 = st.columns(2)
    current_price = c1.number_input(
        "מחיר נוכחי", min_value=0.01,
        value=float(live) if live else float(p["entry"]),
        step=0.01, format="%.2f", key=f"{key_prefix}_px")

    # אם לא נשמר סטופ בפוזיציה, גוזרים אותו מ-ATR
    if p["stop"]:
        stop = c2.number_input("סטופ", min_value=0.01, value=float(p["stop"]),
                               step=0.01, format="%.2f", key=f"{key_prefix}_stop")
    else:
        fallback = atr if atr else p["entry"] * 0.02
        stop = rr.stop_from_atr(p["entry"], fallback, default_atr_mult, p["direction"])
        c2.number_input("סטופ (נגזר מ-ATR)", min_value=0.01, value=float(stop),
                        step=0.01, format="%.2f", key=f"{key_prefix}_stop",
                        disabled=True,
                        help="לא נמצא סטופ שמור לפוזיציה. הערך נגזר מ-ATR כברירת מחדל.")

    try:
        plan = rr.build_plan(p["ticker"], entry=p["entry"], stop=stop,
                             shares=p["shares"], direction=p["direction"],
                             account_value=portfolio_value)
        status = rr.position_status(plan, current_price)
    except ValueError as exc:
        st.warning(f"לא ניתן לנתח את הפוזיציה: {exc}")
        return None

    st.markdown(_status_card_html(plan, status), unsafe_allow_html=True)

    if status.targets_hit and not status.stop_breached:
        be = rr.breakeven_stop_after_target(plan)
        st.markdown(
            f'<div dir="rtl" style="border-right:3px solid {_C["green"]};'
            f'background:{_C["green"]}12;border-radius:10px;padding:.65rem .95rem;'
            f'margin:-.4rem 0 .9rem;font-size:.87rem;color:{_C["text"]};">'
            f'יעד ראשון כבר נפגע. העברת הסטופ ל-${be:,.2f} מבטלת את הסיכון '
            f'על היתרה ומשאירה את הפוזיציה פתוחה ליעדים הבאים.</div>',
            unsafe_allow_html=True)

    return render_rr_section(
        ticker=p["ticker"], entry=p["entry"], stop=stop, shares=p["shares"],
        portfolio_value=portfolio_value, direction=p["direction"],
        earnings_fetcher=earnings_fetcher, key_prefix=f"{key_prefix}_rr",
        interactive=True,
    )
