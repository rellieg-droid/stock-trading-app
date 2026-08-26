# -*- coding: utf-8 -*-
"""
strategy_tab.py
===============
טאב "אסטרטגיה" — שכבת התצוגה בלבד. אפס לוגיקה פיננסית כאן.

שילוב באפליקציה הראשית, בתוך בלוק הקונטיינר של הטאב:

    from strategy_tab import render_strategy_tab
    ...
    with st.container():
        render_strategy_tab(default_ticker=st.session_state.ticker)

בדיקה עצמאית בלי לגעת באפליקציה:

    streamlit run strategy_tab.py

כל מפתחות ה-session_state מתחילים ב-strat_ כדי למנוע התנגשות
עם 11 הטאבים הקיימים.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Optional

import streamlit as st

import strategy_data as sd
import strategy_engine as se
from strategy_guide import render_strategy_guide

VERDICT_STYLE = {
    "INVEST":         ("var(--c-green, #16c784)", "▲"),
    "INVEST_REDUCED": ("var(--c-blue-lt, #4d9fff)", "◆"),
    "WAIT":           ("var(--c-amber, #f0b90b)", "■"),
    "AVOID":          ("var(--c-red, #ea3943)", "▼"),
}

RISK_PROFILES = {"נמוכה": "low", "בינונית": "medium", "גבוהה": "high"}


def _esc(x) -> str:
    return html.escape(str(x))


def _verdict_card(report: se.StrategyReport) -> str:
    color, glyph = VERDICT_STYLE.get(report.verdict, ("#888", "•"))
    vetoes = ""
    if report.vetoes:
        items = " · ".join(_esc(v) for v in report.vetoes)
        vetoes = (f'<div style="margin-top:.5rem;font-size:.82rem;opacity:.85;">'
                  f'וטו: {items}</div>')
    return f'''
<div dir="rtl" style="
     border:1px solid {color}44;border-right:4px solid {color};
     background:linear-gradient(90deg,{color}12,transparent);
     border-radius:12px;padding:1rem 1.2rem;margin:.4rem 0 1rem;">
  <div style="display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap;">
    <span style="font-size:1.55rem;font-weight:800;color:{color};">
      {glyph} {_esc(report.verdict_label)}</span>
    <span style="font-family:JetBrains Mono,monospace;font-size:1.1rem;
                 color:var(--c-text-1,#c9d1d9);">{_esc(report.score_text)}</span>
    <span style="font-size:.9rem;opacity:.75;">{_esc(report.ticker)}</span>
  </div>
  <div style="margin-top:.45rem;font-size:.95rem;color:var(--c-text-1,#c9d1d9);">
    {_esc(report.flavor)}</div>
  {vetoes}
</div>'''


def _criteria_table(report: se.StrategyReport) -> str:
    """טבלת HTML ולא st.dataframe, כי RTL ועברית ארוכה לא נראים טוב שם."""
    green = "var(--c-green, #16c784)"
    red = "var(--c-red, #ea3943)"
    rows = []
    for c in report.criteria:
        if c.passed is None:
            mark, mc = "?", "#8b949e"
        elif c.passed:
            mark, mc = "V", green
        else:
            mark, mc = "X", red
        proxy = ('<span style="font-size:.68rem;opacity:.6;"> פרוקסי</span>'
                 if c.is_proxy else "")
        rows.append(f'''
    <tr style="border-top:1px solid #ffffff14;">
      <td style="padding:.6rem .7rem;font-weight:600;white-space:nowrap;">
        {_esc(c.label)}{proxy}</td>
      <td style="padding:.6rem .7rem;opacity:.72;font-size:.85rem;">{_esc(c.optimal)}</td>
      <td style="padding:.6rem .7rem;font-family:JetBrains Mono,monospace;
                 font-size:.84rem;">{_esc(c.current)}</td>
      <td style="padding:.6rem .7rem;text-align:center;font-weight:800;
                 font-size:1.05rem;color:{mc};">{mark}</td>
      <td style="padding:.6rem .7rem;font-size:.85rem;line-height:1.5;">{_esc(c.meaning)}</td>
    </tr>''')

    return f'''
<div dir="rtl" style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-size:.9rem;
              color:var(--c-text-1,#c9d1d9);">
  <thead><tr style="background:#ffffff0a;">
    <th style="padding:.55rem .7rem;text-align:right;">אינדיקטור</th>
    <th style="padding:.55rem .7rem;text-align:right;">מצב אופטימלי (לונג)</th>
    <th style="padding:.55rem .7rem;text-align:right;">המצב הנוכחי</th>
    <th style="padding:.55rem .7rem;text-align:center;">עמידה</th>
    <th style="padding:.55rem .7rem;text-align:right;">מה זה מלמד אותך</th>
  </tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table></div>'''


def _render_position(plan: se.PositionPlan) -> None:
    st.markdown('<div dir="rtl" style="font-weight:700;margin:.9rem 0 .3rem;">'
                'תוכנית פוזיציה</div>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric("כניסה", f"${plan.entry_price:,.2f}")
    b.metric("Stop Loss", f"${plan.stop_price:,.2f}", f"-{plan.stop_pct:.1f}%")
    c.metric("Take Profit", f"${plan.take_profit_price:,.2f}",
             f"+{(plan.take_profit_price / plan.entry_price - 1) * 100:.1f}%")
    d.metric("מניות", f"{plan.final_shares:,}")

    rr = ((plan.take_profit_price - plan.entry_price) / plan.stop_distance
          if plan.stop_distance else 0.0)
    st.markdown(
        f'<div dir="rtl" style="font-size:.85rem;opacity:.8;margin-top:.2rem;">'
        f'הון מושקע ${plan.capital_used:,.0f} · '
        f'הון בסיכון ${plan.capital_at_risk:,.0f} '
        f'({plan.capital_at_risk_pct:.2f}% מהתיק) · '
        f'יחס סיכוי-סיכון {rr:.1f}:1 · '
        f'תקרת כלל ה-1% מאפשרת {plan.max_shares_by_risk:,} מניות</div>',
        unsafe_allow_html=True)

    if plan.final_shares == plan.max_shares_by_risk and plan.intended_shares > plan.final_shares:
        st.info("גודל הפוזיציה נחתך על ידי כלל ה-1%, לא על ידי אחוז התיק שביקשת.")



def render_strategy_tab(default_ticker: str = "NVDA",
                        default_portfolio: float = 100_000.0) -> None:
    st.markdown('<div dir="rtl"><h3 style="margin:.2rem 0;">אסטרטגיה — הציון המשולב</h3>'
                '<div style="opacity:.7;font-size:.88rem;">'
                'ארבעה קריטריונים: תנודתיות יחסית, אחוזון תנודתיות, מאקרו ולוח אירועים.'
                '</div></div>', unsafe_allow_html=True)

    # תיבות מתקפלות שקופות עם טקסט קריא, ותוויות ווידג'טים בהירות
    st.markdown("""<style>
      div[data-testid="stExpander"], div[data-testid="stExpander"] details,
      div[data-testid="stExpander"] > details > summary {
        background:transparent !important; background-color:transparent !important;
        border-color:#ffffff2e !important; border-radius:10px !important;
        box-shadow:none !important;
      }
      div[data-testid="stExpander"] summary,
      div[data-testid="stExpander"] summary p,
      div[data-testid="stExpander"] summary span {
        color:#e6edf3 !important; font-weight:700 !important;
        font-size:.92rem !important; opacity:1 !important;
      }
      div[data-testid="stExpander"] summary svg { fill:#e6edf3 !important; }
      div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
        background:transparent !important;
      }
      label[data-testid="stWidgetLabel"] p,
      div[data-testid="stCheckbox"] label p,
      div[data-testid="stCheckbox"] label span {
        color:#e6edf3 !important; opacity:1 !important; font-weight:600 !important;
      }
      div[data-testid="stCaptionContainer"] p { color:#9fb0c3 !important; }
    </style>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1.2])
    ticker = c1.text_input("מניה", value=default_ticker, key="strat_ticker").strip().upper()
    portfolio = c2.number_input("שווי תיק ($)", min_value=1_000.0, step=1_000.0,
                                value=float(default_portfolio), key="strat_portfolio")
    position_pct = c3.slider("% מהתיק", 1, 50, 5, key="strat_pos_pct") / 100.0
    profile_he = c4.selectbox("פרופיל סיכון", list(RISK_PROFILES),
                              index=1, key="strat_profile")
    profile = RISK_PROFILES[profile_he]

    cfg = se.StrategyConfig.for_profile(profile)

    with st.expander("כוונון ספים", expanded=True):
        st.caption("הספים אינם קבועי טבע. במשטר פיזור גבוה כמעט כל המניות "
                   "יושבות באחוזון עליון, ואז שווה להעלות את הסף ל-70 ולראות מה עובר.")
        # כל הסליידרים ברוחב מלא, בלי st.columns() -- תבנית מוכחת (rr_tab.py)
        rel_max = st.slider("סף אחוזון תנודתיות יחסית", 10, 95,
                            int(cfg.rel_vol_rank_pass_max), key="strat_rel_max")
        hv_max = st.slider("סף אחוזון HV", 10, 95,
                           int(cfg.hv_rank_pass_max), key="strat_hv_max")
        vix_max = st.slider("סף VIX", 10, 40, int(cfg.vix_max), key="strat_vix_max")
        atr_mult = st.slider("מכפיל ATR ל-Stop", 1.0, 4.0,
                             float(cfg.atr_stop_multiplier), 0.5, key="strat_atr_mult")
        blackout = st.slider("חלון חסימה לפני דוח (ימים)", 0, 21,
                             int(cfg.earnings_blackout_days), key="strat_blackout")
        e6 = st
        from macro_events import macro_event_within, get_macro_events
        from datetime import date as _mdate, timedelta as _mtd
        _macro_computed = macro_event_within(blackout)
        if "strat_macro" not in st.session_state:
            st.session_state["strat_macro"] = _macro_computed
            st.session_state["_strat_macro_auto_val"] = _macro_computed
        elif st.session_state.get("_strat_macro_auto_val") == st.session_state.get("strat_macro"):
            st.session_state["strat_macro"] = _macro_computed
            st.session_state["_strat_macro_auto_val"] = _macro_computed
        macro = e6.text_input("אירוע מאקרו ידוע", key="strat_macro",
                              placeholder="למשל: החלטת ריבית בשבוע הבא")
        _upcoming_macro = get_macro_events(start=_mdate.today(), end=_mdate.today() + _mtd(days=30))
        if _upcoming_macro:
            _macro_lines = "  \n".join(f"{d.strftime('%d/%m')} - {lbl}" for d, lbl in _upcoming_macro[:5])
            e6.caption(f"אירועים קרובים (30 יום):  \n{_macro_lines}")

    cfg = se.StrategyConfig(
        risk_profile=profile,
        rel_vol_rank_pass_max=float(rel_max),
        hv_rank_pass_max=float(hv_max),
        vix_max=float(vix_max),
        atr_stop_multiplier=float(atr_mult),
        earnings_blackout_days=int(blackout),
        max_relative_std=cfg.max_relative_std,
        high_risk_relative_std=cfg.high_risk_relative_std,
    )

    with st.expander("מה כל פרמטר אומר", expanded=False):
        render_strategy_guide(compact=True)

    run_clicked = st.button("הרץ ניתוח", type="primary", key="strat_run")

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
            f"הפרמטרים בטופס השתנו מאז — לחצי \"הרץ ניתוח\" לרענון.")
    else:
        st.caption(f"הורץ ב-{result['ran_at']:%H:%M:%S}")

    if report is None:
        st.error(f"לא ניתן להפיק ניתוח עבור {result['ticker']}.")
        st.dataframe(diag.to_table(), hide_index=True, use_container_width=True)
        return

    st.markdown(_verdict_card(report), unsafe_allow_html=True)
    st.markdown(_criteria_table(report), unsafe_allow_html=True)

    if report.position:
        _render_position(report.position)
    elif report.verdict in ("WAIT", "AVOID"):
        st.markdown('<div dir="rtl" style="opacity:.75;font-size:.88rem;margin-top:.8rem;">'
                    'לא מוצגת תוכנית פוזיציה. פסק הדין אינו כניסה.</div>',
                    unsafe_allow_html=True)

    with st.expander("מקורות נתונים ואזהרות", expanded=False):
        st.dataframe(diag.to_table(), hide_index=True, use_container_width=True)
        for n in report.notes:
            st.caption(f"• {n}")
        st.caption(f"מנוע {se.__version__} · מתאם {sd.__version__}")


# ---------------------------------------------------------------------------
# הרצה עצמאית: streamlit run strategy_tab.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    st.set_page_config(page_title="אסטרטגיה", layout="wide")
    st.markdown("""<style>
      .block-container{direction:rtl;}
      :root{--c-green:#16c784;--c-red:#ea3943;--c-amber:#f0b90b;
            --c-blue-lt:#4d9fff;--c-text-1:#c9d1d9;}
    </style>""", unsafe_allow_html=True)
    render_strategy_tab()
