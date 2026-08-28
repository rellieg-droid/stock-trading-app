"""
riskshield_tab.py
==================
טאב RiskShield: שכבת הבסיס בלבד (Black-Scholes, IV, RV).
מודול עצמאי לחלוטין מבחינת לוגיקה - כל החישוב ב-options_engine.py.

שימוש:
    from riskshield_tab import render_riskshield_tab
    render_riskshield_tab()

אין תלות ב-fetcher חיצוני. yfinance משמש רק למילוי ראשוני נוח
(ספוט + סדרת סגירות להיסטוריה), עם נפילה חזרה שקטה אם אין רשת/סימבול.

כל שדה קלט כולל טקסט הסבר (help=) שמופיע ברחיפה על סימן ה-❓,
וכל תוצאה כוללת הסבר קבוע מתחתיה - כדי שההסבר יהיה בממשק עצמו,
לא רק בתיעוד חיצוני.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

from options_engine import bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks

# ---------------------------------------------------------------------------
# עיצוב - אותה מוסכמת CSS כמו rr_tab.py, עם משתני CSS גלובליים ו-fallback
# ---------------------------------------------------------------------------
_CSS = """
<style>
.rs-wrap { direction: rtl; text-align: right; }
.rs-wrap * { direction: rtl; }
.rs-card {
  background: var(--c-surface-1, rgba(255,255,255,0.035));
  border: 1px solid var(--c-border, rgba(255,255,255,0.08));
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.rs-title {
  font-size: 0.82rem; font-weight: 700; letter-spacing: .02em;
  color: var(--c-text-2, #8B93A7); margin-bottom: 10px;
}
.rs-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
}
.rs-metric {
  background: var(--c-surface-2, rgba(255,255,255,0.02));
  border-radius: 8px; padding: 10px 12px;
}
.rs-metric-label { font-size: 0.72rem; color: var(--c-text-2, #8B93A7); margin-bottom: 4px; }
.rs-metric-value { font-size: 1.05rem; font-weight: 700; color: var(--c-text-1, #E7EAF0); }
.rs-explain {
  font-size: 0.8rem; color: var(--c-text-1, #C7CCDA);
  border-right: 3px solid var(--c-border, rgba(255,255,255,0.15));
  padding-right: 10px; margin-top: 4px; line-height: 1.65;
}
.rs-badge {
  display: inline-block; padding: 4px 12px; border-radius: 999px;
  font-size: 0.78rem; font-weight: 700; margin-left: 6px;
}
.rs-badge.green  { background: rgba(34,197,94,.14);  color: var(--c-green,  #22c55e); }
.rs-badge.yellow { background: rgba(234,179,8,.14);  color: var(--c-yellow, #eab308); }
.rs-badge.red    { background: rgba(239,68,68,.14);  color: var(--c-red,    #ef4444); }
.rs-badge.gray   { background: rgba(139,147,161,.14);color: var(--c-text-2, #8B93A7); }

/* תיקון נראות אייקון ה-tooltip (❓) של Streamlit - ה-CSS הגלובלי הכהה של
   האפליקציה כנראה דורס את הצבע המקורי שלו לצבע קרוב מדי לרקע. */
[data-testid="stTooltipIcon"] { opacity: 1 !important; }
[data-testid="stTooltipIcon"] svg { fill: var(--c-text-2, #8B93A7) !important; }
div[data-baseweb="tooltip"], div[data-baseweb="popover"] {
  color: var(--c-text-1, #E7EAF0) !important;
  background: var(--c-surface-1, #1a1d29) !important;
}
</style>
"""

# ---------------------------------------------------------------------------
# טקסטי עזרה - מוצגים גם כ-help ליד שדות הקלט וגם כהסבר קבוע ליד תוצאות
# ---------------------------------------------------------------------------
_HELP = {
    "kind": "call = אופציית רכישה (רווח כשהמניה עולה מעל הסטרייק). "
            "put = אופציית מכירה (רווח כשהמניה יורדת מתחת לסטרייק).",
    "S": "מחיר הנכס הבסיס (המניה) כרגע בשוק.",
    "K": "מחיר המימוש. ההפרש בין מחיר הנכס לסטרייק קובע אם האופציה בכסף (ITM) או מחוצה לו (OTM).",
    "days": "מספר הימים עד לפקיעת האופציה. המודל ממיר את זה לשברי שנה (30 יום = 30/365).",
    "sigma": "התנודתיות הגלומה (IV) - כמה תנועה השוק מצפה מהמניה, לפי המחיר שהוא מוכן לשלם על האופציה עצמה.",
    "r": "ריבית חסרת סיכון (כמו תשואת אג\"ח ממשלתי קצר). משפיעה קלות על תמחור האופציה.",
    "q": "תשואת דיבידנד שנתית של המניה. דיבידנד מוריד את מחיר ה-call (כי בעל המניה מקבל אותו, לא בעל האופציה).",
    "iv_price": "מחיר השוק בפועל של האופציה (למשל, אמצע ה-bid/ask). מכאן המודל פותר אחורה איזו IV מסבירה את המחיר הזה.",
    "rv_window": "כמה ימי מסחר אחורה לכלול בחישוב. 252 ימי מסחר ≈ שנה קלנדרית.",
    "rv_iv_compare": "ה-IV שאיתו משווים את ה-RV שחושב. אפשר להזין ידנית, או להשתמש בערך שיצא בטאב 'תנודתיות גלומה'.",
}

_GREEKS_EXPLAIN = (
    '<div class="rs-explain">'
    '<b>מחיר</b>: שווי האופציה למניה אחת (למחיר החוזה המלא מכפילים ב-100).<br>'
    '<b>Delta</b>: שינוי במחיר האופציה על כל $1 שהמניה זזה (call: 0 עד 1, put: ‎-1‎ עד 0).<br>'
    '<b>Gamma</b>: קצב השינוי של ה-Delta עצמה על כל $1 בנכס - "התאוצה" של הדלתא.<br>'
    '<b>Vega</b>: שינוי במחיר האופציה על כל 1% שינוי ב-IV.<br>'
    '<b>Theta</b>: שחיקת ערך יומית בדולרים, מעבר הזמן בלבד (בלי שינוי מחיר/IV).<br>'
    '<b>הסתברות OTM</b>: הסתברות ניטרלית-סיכון (לפי המודל) שהאופציה תפקע חסרת ערך - לא תחזית.'
    '</div>'
)

_IV_EXPLAIN = (
    '<div class="rs-explain">'
    'זו התנודתיות שאם מזינים אותה בטאב "מחיר וגריקס", מקבלים בחזרה בדיוק '
    'את מחיר השוק שהוזן. משמשת לדעת כמה תנודתיות השוק בעצם מתמחר באופציה '
    'הספציפית הזו, בלי לנחש.'
    '</div>'
)

_RV_EXPLAIN = (
    '<div class="rs-explain">'
    'RV נמדד מהתנודות היומיות בפועל של המניה בעבר - לא ממה שהשוק מצפה. '
    'זה ההפך מ-IV: RV מתאר מה קרה, IV מתאר מה מתומחר שיקרה.'
    '</div>'
)


def _metric(label: str, value: str) -> str:
    return f'<div class="rs-metric"><div class="rs-metric-label">{label}</div><div class="rs-metric-value">{value}</div></div>'


def _card(title: str, inner_html: str) -> None:
    st.markdown(
        f'<div class="rs-wrap rs-card"><div class="rs-title">{title}</div>{inner_html}</div>',
        unsafe_allow_html=True,
    )


def _try_fetch_spot(ticker: str) -> Optional[float]:
    """שולף מחיר אחרון דרך yfinance. נכשל בשקט - בלי badge, בלי crash."""
    if not ticker:
        return None
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def _try_fetch_closes(ticker: str, period: str = "1y") -> Optional[list]:
    """שולף סדרת סגירות יומית להיסטוריה. נכשל בשקט."""
    if not ticker:
        return None
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty or len(hist) < 3:
            return None
        return hist["Close"].tolist()
    except Exception:
        return None


def _ratio_badge(ratio: float) -> str:
    """IV/RV מעל 1 = השוק מתמחר תנודתיות גבוהה מהמומשת. אין כאן קביעה של 'טוב'/'רע' -
    רק תיאור עובדתי של היחס, בהתאם לפילוסופיית ה-non-recommendation של RiskShield."""
    if ratio >= 1.3:
        cls, txt = "yellow", "IV גבוה משמעותית מ-RV"
    elif ratio >= 1.0:
        cls, txt = "green", "IV מעל RV"
    elif ratio >= 0.8:
        cls, txt = "gray", "IV קרוב ל-RV"
    else:
        cls, txt = "red", "IV מתחת ל-RV"
    return f'<span class="rs-badge {cls}">{txt} ({ratio:.2f})</span>'


def render_riskshield_tab(key_prefix: str = "riskshield", default_ticker: str = "NVDA") -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown('<div class="rs-wrap">', unsafe_allow_html=True)

    st.markdown("### 🛡️ RiskShield — מחשבון Black-Scholes ותנודתיות")
    st.markdown(
        '<div class="rs-explain" style="margin-bottom:12px;">'
        'מודול חישוב טהור: מחיר וגריקס לאופציה בודדת, תנודתיות גלומה מהשוק, '
        'ותנודתיות ממומשת מההיסטוריה. אין כאן איתות קנייה/מכירה — רק המספרים '
        'והמשמעות העובדתית שלהם. לכל שדה יש הסבר בריחוף על סימן ה-❓ שלידו.'
        '</div>',
        unsafe_allow_html=True,
    )

    ticker = st.text_input("טיקר (לצורך מילוי ראשוני בלבד)", value=default_ticker, key=f"{key_prefix}_ticker")

    tab_bs, tab_iv, tab_rv = st.tabs(["מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)"])

    # -------------------------------------------------------------------
    # טאב 1: Black-Scholes price + Greeks
    # -------------------------------------------------------------------
    with tab_bs:
        spot_default = _try_fetch_spot(ticker) or 100.0
        cols = st.columns(5)
        with cols[0]:
            kind = st.selectbox("סוג", ["call", "put"], key=f"{key_prefix}_bs_kind", help=_HELP["kind"])
        with cols[1]:
            S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),
                                 key=f"{key_prefix}_bs_S", help=_HELP["S"])
        with cols[2]:
            K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),
                                 key=f"{key_prefix}_bs_K", help=_HELP["K"])
        with cols[3]:
            days = st.number_input("ימים לפקיעה", min_value=1, value=30,
                                    key=f"{key_prefix}_bs_days", help=_HELP["days"])
        with cols[4]:
            sigma_pct = st.number_input("IV (%)", min_value=0.1, value=30.0,
                                         key=f"{key_prefix}_bs_sigma", help=_HELP["sigma"])

        cols2 = st.columns(2)
        with cols2[0]:
            r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,
                                     key=f"{key_prefix}_bs_r", help=_HELP["r"])
        with cols2[1]:
            q_pct = st.number_input("תשואת דיבידנד (%)", value=0.0,
                                     key=f"{key_prefix}_bs_q", help=_HELP["q"])

        if st.button("חשב", key=f"{key_prefix}_bs_calc"):
            try:
                g: Greeks = bs_greeks(
                    kind=kind, S=S, K=K, T=days / 365.0,
                    sigma=sigma_pct / 100.0, r=r_pct / 100.0, q=q_pct / 100.0,
                )
                grid = "".join([
                    _metric("מחיר", f"${g.price:,.2f}"),
                    _metric("Delta", f"{g.delta:.3f}"),
                    _metric("Gamma", f"{g.gamma:.4f}"),
                    _metric("Vega", f"{g.vega:.3f}"),
                    _metric("Theta (יומי)", f"${g.theta:,.3f}"),
                    _metric("הסתברות OTM", f"{g.prob_otm:.1%}"),
                ])
                _card("תוצאה", f'<div class="rs-grid">{grid}</div>{_GREEKS_EXPLAIN}')
            except ValueError as e:
                st.error(f"קלט לא תקין: {e}")

    # -------------------------------------------------------------------
    # טאב 2: Implied Volatility solver
    # -------------------------------------------------------------------
    with tab_iv:
        spot_default = _try_fetch_spot(ticker) or 100.0
        cols = st.columns(5)
        with cols[0]:
            iv_kind = st.selectbox("סוג", ["call", "put"], key=f"{key_prefix}_iv_kind", help=_HELP["kind"])
        with cols[1]:
            iv_price = st.number_input("מחיר שוק לאופציה", min_value=0.01, value=2.0,
                                        key=f"{key_prefix}_iv_price", help=_HELP["iv_price"])
        with cols[2]:
            iv_S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),
                                    key=f"{key_prefix}_iv_S", help=_HELP["S"])
        with cols[3]:
            iv_K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),
                                    key=f"{key_prefix}_iv_K", help=_HELP["K"])
        with cols[4]:
            iv_days = st.number_input("ימים לפקיעה", min_value=1, value=30,
                                       key=f"{key_prefix}_iv_days", help=_HELP["days"])

        iv_r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,
                                    key=f"{key_prefix}_iv_r", help=_HELP["r"])

        if st.button("חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc"):
            try:
                iv_result = implied_vol(
                    kind=iv_kind, market_price=iv_price, S=iv_S, K=iv_K,
                    T=iv_days / 365.0, r=iv_r_pct / 100.0,
                )
                _card("תוצאה", _metric("IV גלום מהשוק", f"{iv_result:.1%}") + _IV_EXPLAIN)
            except ValueError as e:
                st.error(f"לא ניתן לפתור: {e}")

    # -------------------------------------------------------------------
    # טאב 3: Realized Volatility + IV/RV ratio
    # -------------------------------------------------------------------
    with tab_rv:
        closes = _try_fetch_closes(ticker)
        if closes is None:
            st.info(f"לא נמצאה היסטוריית מחירים עבור \"{ticker}\" (בדקי טיקר / זמינות רשת).")
        else:
            window = st.number_input("חלון (ימי מסחר)", min_value=5, value=min(252, len(closes)),
                                      key=f"{key_prefix}_rv_window", help=_HELP["rv_window"])
            if st.button("חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc"):
                rv = realized_vol(closes, window=int(window))
                grid = _metric("RV (שנתי)", f"{rv:.1%}")
                _card(f"תוצאה עבור {ticker}", f'<div class="rs-grid">{grid}</div>{_RV_EXPLAIN}')

                st.markdown("---")
                st.markdown("**השוואה ל-IV** (הזיני ידנית, או השתמשי בערך שיצא בטאב הקודם):")
                manual_iv_pct = st.number_input("IV להשוואה (%)", min_value=0.1, value=30.0,
                                                 key=f"{key_prefix}_rv_iv_compare", help=_HELP["rv_iv_compare"])
                if rv > 0:
                    ratio = iv_rv_ratio(manual_iv_pct / 100.0, rv)
                    st.markdown(_ratio_badge(ratio), unsafe_allow_html=True)
                    st.markdown(
                        '<div class="rs-explain" style="margin-top:8px;">'
                        'יחס מעל 1 = השוק מתמחר תנודתיות עתידית גבוהה ממה שהמניה הראתה '
                        'בעבר בפועל. זה תיאור עובדתי של היחס בין שני מספרים - לא המלצת '
                        'קנייה/מכירה או תחזית לכיוון המניה.'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="rs-explain">RV יצא 0 - אין מספיק תנועה בסדרה כדי לחשב יחס.</div>',
                        unsafe_allow_html=True,
                    )

    st.markdown('</div>', unsafe_allow_html=True)
