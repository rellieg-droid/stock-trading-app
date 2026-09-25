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

from math import log as _log

import sqlite3
import json
from datetime import date as _date, timedelta as _timedelta

from options_engine import (
    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,
    historical_put_otm_probability, fat_tail_otm_probability,
    rv_rank, rv_percentile,
    expected_move, strike_distance_in_expected_moves,
    stress_test_table, historical_short_put_pnl_distribution, expected_shortfall,
    protection_table, insurance_cost,
    short_put_breakeven,
    size_position, Position, Leg,
    bull_put_spread, CONTRACT_MULTIPLIER,
    quote_summary, nearest_strike,
)

from put_tracker_tab import render_put_tracker_tab

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
.rs-btn-help {
  display: inline-block; cursor: help; font-size: 0.78rem;
  color: var(--c-text-2, #8B93A7); margin-bottom: 6px;
}
.rs-table { width:100%; border-collapse:collapse; direction:rtl; margin-top:8px; }
.rs-table th, .rs-table td { padding:8px 10px; text-align:center; border-bottom:1px solid rgba(255,255,255,.08); white-space:nowrap; }
.rs-table th { color: var(--c-text-1, #E7EAF0); font-weight:700; font-size:.82rem; }
.rs-table td { font-weight:600; font-size:.9rem; }
.rs-table tr:hover td { background: rgba(255,255,255,.03); }

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
    "days": "תאריך פקיעת האופציה. כשיש שרשרת אופציות לטיקר, מוצגים רק תאריכי פקיעה אמיתיים. המודל ממיר את הזמן עד הפקיעה לשברי שנה.",
    "sigma": "התנודתיות הגלומה (IV) - כמה תנועה השוק מצפה מהמניה, לפי המחיר שהוא מוכן לשלם על האופציה עצמה.",
    "r": "ריבית חסרת סיכון (כמו תשואת אג\"ח ממשלתי קצר). משפיעה קלות על תמחור האופציה.",
    "q": "תשואת דיבידנד שנתית של המניה. דיבידנד מוריד את מחיר ה-call (כי בעל המניה מקבל אותו, לא בעל האופציה).",
    "iv_price": "מחיר השוק בפועל של האופציה (למשל, אמצע ה-bid/ask). מכאן המודל פותר אחורה איזו IV מסבירה את המחיר הזה.",
    "rv_window": "כמה ימי מסחר אחורה לכלול בחישוב. 252 ימי מסחר ≈ שנה קלנדרית.",
    "rv_iv_compare": "ה-IV שאיתו משווים את ה-RV שחושב. אפשר להזין ידנית, או להשתמש בערך שיצא בטאב 'תנודתיות גלומה'.",
    "contracts": "כמה חוזי אופציה. כל חוזה מייצג 100 מניות - זה מה שהופך פרמיה קטנה למספרים גדולים.",
    "capital": "ההון שהוקצה לעסקה הזו. משמש רק כדי להציג את הסיכון כאחוז מההון שלך - לא משפיע על שום חישוב אחר.",
    "prot_shares": "כמה מניות בפועל מוחזקות ורוצים להגן עליהן.",
    "prot_entry": "המחיר שבו נקנתה המניה (עלות הבסיס) - קובע את הרווח/הפסד היחסי בכל תרחיש סטרס.",
    "prot_strike": "מחיר המימוש של הפוט המגן. מתחתיו הוא מתחיל לקזז הפסדים דולר-לדולר.",
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


def _metric(label: str, value: str, tooltip: Optional[str] = None) -> str:
    help_html = f' <span class="rs-btn-help" title="{tooltip}">❓</span>' if tooltip else ""
    return (
        f'<div class="rs-metric"><div class="rs-metric-label">{label}{help_html}</div>'
        f'<div class="rs-metric-value">{value}</div></div>'
    )


def _card(title: str, inner_html: str) -> None:
    st.markdown(
        f'<div class="rs-wrap rs-card"><div class="rs-title">{title}</div>{inner_html}</div>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300, show_spinner=False)  # RS_CACHE_V1
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


@st.cache_data(ttl=900, show_spinner=False)  # RS_CACHE_V1
def _try_fetch_atm_iv(ticker: str) -> Optional[float]:
    """
    IV אמיתי מהשוק (ATM, תפוגה 20-60 יום) - אותה fetch_atm_iv() מ-strategy_data.py
    שכבר מייצרת את באדג' ה-IV בכותרת הראשית. מחזיר אחוזים (32.3, לא 0.323).
    נכשל בשקט (None) אם strategy_data לא נגיש או שאין אופציות לטיקר.
    """
    if not ticker:
        return None
    try:
        from strategy_data import fetch_atm_iv
        iv = fetch_atm_iv(ticker)
        if iv is None:
            return None
        return float(iv) * 100.0
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)  # RS_CACHE_V1
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


@st.cache_data(ttl=3600, show_spinner=False)  # RS_CACHE_V1
def _try_fetch_expirations(ticker: str) -> list:
    """תאריכי פקיעה אמיתיים מהשרשרת (yfinance), רק עתידיים. רשימה ריקה אם אין."""
    if not ticker:
        return []
    try:
        import yfinance as yf
        today = _date.today()
        return [e for e in (yf.Ticker(ticker).options or ())
                if (_date.fromisoformat(e) - today).days >= 1]
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)  # RS_CACHE_V1
def _try_fetch_put_chain(ticker: str, expiry: str) -> list:
    """שרשרת PUT לפקיעה אחת (ISO) כרשימת dict. NaN -> None. ריקה אם אין."""
    if not ticker or not expiry:
        return []
    try:
        import yfinance as yf
        import pandas as pd
        puts = yf.Ticker(ticker).option_chain(expiry).puts
        if puts is None or puts.empty:
            return []
        cols = ["strike", "bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"]
        return [
            {k: (None if pd.isna(v) else float(v)) for k, v in row.items()}
            for row in puts.reindex(columns=cols).to_dict("records")
        ]
    except Exception:
        return []


def _fmt_exp(e: str) -> str:
    return _date.fromisoformat(e).strftime("%d/%m/%Y")


def _expiry_input(label: str, key: str, ticker: str, default_days: int = 30,
                  help: Optional[str] = None):
    """
    בחירת תאריך פקיעה במקום "ימים לפקיעה". יש שרשרת לטיקר -> selectbox
    מתאריכי הפקיעה האמיתיים (ברירת מחדל: הקרוב ל-default_days). אין שרשרת
    (או סורק רב-מניות, ticker="") -> בחירת תאריך חופשית.
    מחזירה (ימים, תאריך) - החישובים ממשיכים לעבוד בימים.
    """
    today = _date.today()
    exps = _try_fetch_expirations(ticker)
    if exps:
        target = today + _timedelta(days=default_days)
        default_idx = min(range(len(exps)),
                          key=lambda i: abs((_date.fromisoformat(exps[i]) - target).days))
        chosen = st.selectbox(label, exps, index=default_idx, key=f"{key}_{ticker}",
                              format_func=_fmt_exp, help=help)
        exp_date = _date.fromisoformat(chosen)
    else:
        exp_date = st.date_input(label, value=today + _timedelta(days=default_days),
                                 min_value=today + _timedelta(days=1),
                                 key=f"{key}_free_{ticker}", format="DD/MM/YYYY", help=help)
    return max(1, (exp_date - today).days), exp_date


@st.cache_data(ttl=600, show_spinner=False)  # RS_CACHE_V1
def _try_fetch_otm_put_quote(
    ticker: str, below_strike: float, dte_days: int = 30, target_delta: float = 0.15,
) -> Optional[tuple[float, float]]:
    """
    שולפת מ-yfinance סטרייק ופרמיה אמיתיים (Ask) לפוט הגנה מחוץ לכסף,
    מתחת ל-below_strike - הסטרייק שהדלתא שלו (מחושבת מה-IV הגלום בציטוט
    עצמו, לא IV חיצוני) הכי קרובה ל-target_delta. משתמשת ב-bs_greeks הקיים -
    לא נוסחת דלתא נפרדת. נכשלת בשקט (None) אם אין רשת, אין תפוגות
    זמינות, או אין ציטוטי bid/ask תקינים מתחת לסטרייק המבוקש.
    """
    if not ticker or not below_strike or below_strike <= 0:
        return None
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        expirations = tk.options
        if not expirations:
            return None

        target_date = _date.today() + _timedelta(days=dte_days)
        best_exp = min(expirations, key=lambda e: abs((_date.fromisoformat(e) - target_date).days))
        actual_dte = (_date.fromisoformat(best_exp) - _date.today()).days
        if actual_dte <= 0:
            return None

        puts = tk.option_chain(best_exp).puts
        if puts is None or puts.empty:
            return None

        spot = _try_fetch_spot(ticker)
        if spot is None:
            return None

        candidates = puts[
            (puts["strike"] < below_strike) & (puts["bid"] > 0) & (puts["ask"] > 0)
        ].copy()
        if candidates.empty:
            return None

        T = actual_dte / 365.0

        def _row_delta(row):
            iv = row.get("impliedVolatility")
            if iv is None or iv <= 0:
                return None
            try:
                return abs(bs_greeks("put", spot, float(row["strike"]), T, float(iv)).delta)
            except Exception:
                return None

        candidates["_delta"] = candidates.apply(_row_delta, axis=1)
        candidates = candidates.dropna(subset=["_delta"])
        if candidates.empty:
            return None

        best_idx = (candidates["_delta"] - target_delta).abs().idxmin()
        best_row = candidates.loc[best_idx]
        return float(best_row["strike"]), float(best_row["ask"])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# רשימת מעקב אישית לסורק - קובץ JSON נפרד מ-Watchlist הראשי של האפליקציה
# בכוונה: זו רשימת "מניות שכדאי לבדוק" לצורך הסורק, לא רשימת ההחזקות/
# מעקב הכללית. שילוב עם ה-Watchlist הראשי (אם רוצים גם את זה) דורש
# לראות איפה הוא ממומש - זה קובץ אחר.
# ---------------------------------------------------------------------------
_SCREENER_WATCHLIST_FILE = "riskshield_watchlist.json"


def _load_screener_watchlist() -> list[str]:
    """טוענת את רשימת המעקב האישית של הסורק. נכשלת בשקט לרשימה ריקה."""
    try:
        with open(_SCREENER_WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [t for t in data if isinstance(t, str)]
    except Exception:
        return []


def _save_screener_watchlist(tickers: list[str]) -> None:
    """שומרת את רשימת המעקב. נכשלת בשקט (דיסק/הרשאות) - לא שוברת את הטאב."""
    try:
        with open(_SCREENER_WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(set(tickers)), f, ensure_ascii=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# סורק רב-מניות - שכבת ריכוז בלבד. שואבת עם אותם _try_fetch_* שכבר בקובץ,
# מחשבת עם build_screener_row (options_engine.py) - אין כאן נוסחה חדשה.
# ---------------------------------------------------------------------------

def _run_screener(
    tickers,
    target_put_delta: float = 0.20,
    dte_days: int = 30,
    closes_period: str = "10y",
):
    """
    מריצה build_screener_row על כל טיקר ברשימה, טיקר אחרי טיקר (לא
    במקביל - yfinance לא אוהב הצפה של בקשות). טיקר שנכשל בשליפת מחיר
    (סימבול שגוי / בעיית רשת) לא מפיל את כל הסריקה - הוא מקבל שורה עם
    note בלבד, שאר העמודות NaN, בדיוק כמו שאר ה-_try_fetch_* בקובץ
    שנכשלים בשקט. מחזירה pandas.DataFrame, שורה אחת לטיקר.
    """
    import pandas as pd
    from dataclasses import asdict
    from options_engine import build_screener_row

    rows = []
    for raw_ticker in tickers:
        ticker = raw_ticker.strip().upper()
        if not ticker:
            continue

        spot = _try_fetch_spot(ticker)
        if spot is None:
            rows.append({"ticker": ticker, "spot": None,
                        "note": "לא נמצא מחיר - טיקר שגוי או בעיית רשת"})
            continue

        closes = _try_fetch_closes(ticker, period=closes_period)
        iv_pct = _try_fetch_atm_iv(ticker)
        iv = (iv_pct / 100.0) if iv_pct is not None else None

        row = build_screener_row(
            ticker=ticker, S=spot, closes=closes, iv=iv,
            target_put_delta=target_put_delta, dte_days=dte_days,
        )
        rows.append(asdict(row))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# איסוף היסטוריית IV - תשתית ל-IV Rank אמיתי בעתיד. options_engine.py
# נשאר טהור בכוונה; כל ה-I/O כאן, ליד ה-yfinance שכבר בקובץ הזה.
# ---------------------------------------------------------------------------
_IV_HISTORY_DB = "iv_history.db"


def _iv_history_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_IV_HISTORY_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS iv_observations ("
        "ticker TEXT NOT NULL, observed_at TEXT NOT NULL, "
        "dte INTEGER NOT NULL, iv REAL NOT NULL)"
    )
    return conn


def _record_iv_observation(ticker: str, dte: int, iv: float) -> None:
    """שומרת תצפית IV יומית. נכשלת בשקט אם אי אפשר לכתוב (דיסק/הרשאות) -
    זו תשתית עזר, לא אמורה לשבור את הטאב אם היא נכשלת."""
    if not ticker:
        return
    try:
        with _iv_history_conn() as conn:
            conn.execute(
                "INSERT INTO iv_observations (ticker, observed_at, dte, iv) VALUES (?, ?, ?, ?)",
                (ticker.upper(), _date.today().isoformat(), int(dte), float(iv)),
            )
    except Exception:
        pass


def _iv_observation_count(ticker: str) -> int:
    """כמה תצפיות IV נאספו עד כה לטיקר הזה. 0 אם אין/נכשל - לא קורס."""
    if not ticker:
        return 0
    try:
        with _iv_history_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM iv_observations WHERE ticker = ?", (ticker.upper(),)
            ).fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0


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
        'סריקת מניות, בדיקה לעומק של מכירת פוט, יומן פרמיות, וכלי בסיס '
        'למחיר, גריקס ותנודתיות. אין כאן איתות קנייה/מכירה — רק המספרים '
        'והמשמעות העובדתית שלהם. לכל שדה יש הסבר בריחוף על סימן ה-❓ שלידו.'
        '</div>',
        unsafe_allow_html=True,
    )

    ticker = st.text_input("טיקר (לצורך מילוי ראשוני בלבד)", value=default_ticker, key=f"{key_prefix}_ticker")

    with st.expander("📖 מדריך: מה ההבדל בין הטאבים, ומה זה אומר"):
        st.markdown(
            '<div class="rs-explain">'
            '<b>סורק רב-מניות</b>: נקודת ההתחלה - משווה כמה מניות בבת אחת לפי '
            'אותה דלתא יעד ואותו תאריך פקיעה, כך שההשוואה הוגנת. לכל מניה: '
            'פרמיה, הסתברות OTM לפי שלושה מודלים, RV Rank, תזוזה צפויה ו-CVaR. '
            'הפרמיה כאן תיאורטית (Black-Scholes), לא ציטוט שוק. מניה שנראית '
            'מעניינת בודקים לעומק בטאב הבא.<br><br>'
            '<b>הסתברות OTM (Put)</b>: הטאב המרכזי - בדיקה לעומק של מכירת פוט '
            'אחת: "מה הסיכוי שהמניה תישאר מעל סטרייק מסוים עד הפקיעה?" לפי שלוש '
            'שיטות נפרדות, פלוס ציטוט שוק חי מהשרשרת, תזוזה צפויה, סטרס טסט, '
            'CVaR, השוואה ל-Bull Put Spread, וטבלת הגנה (לצד קניית פוט).<br><br>'
            '<b>📒 מעקב פרמיות</b>: לא חישוב תיאורטי בכלל - יומן בפועל של פוזיציות PUT שמכרת. רושמים כל מכירה (סימבול, סטרייק, פרמיה), ומסמנים איך היא נסגרה (פקעה חסרת ערך / נקנתה בחזרה / הוקצתה) - והטאב מחשב לבד כמה פרמיה נגבתה בסך הכול, כמה כבר מומש כרווח, וכמה עדיין "תלוי באוויר" בפוזיציות פתוחות. אפשר גם למשוך נתונים ישירות מטאב הסתברות OTM במקום להקליד הכול ידנית.<br><br>'
            '<b>מחיר וגריקס</b>: כלי בסיס, תיאורטי לגמרי - מזינים IV משוערת, מקבלים מחיר '
            'תיאורטי לאופציה ואת הרגישויות שלה (גריקס). שאלה שהוא עונה עליה: '
            '"אם התנודתיות היא X, כמה האופציה אמורה לעלות?"<br><br>'
            '<b>תנודתיות גלומה (IV)</b>: ההפך - מזינים את המחיר האמיתי בשוק, '
            'והמערכת פותרת אחורה איזו תנודתיות "מוסתרת" בתוכו. שאלה: '
            '"השוק מתמחר את זה ב-$X - כלומר כמה תנועה הוא בעצם מצפה?"<br><br>'
            '<b>תנודתיות ממומשת (RV)</b>: לא תיאורטי בכלל - מודד כמה המניה '
            'באמת זזה בעבר, מהיסטוריית המחירים. משווים ל-IV כדי לראות אם '
            'האופציה "יקרה" או "זולה" ביחס למה שקרה בפועל.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="rs-explain" style="margin-top:10px;">'
            '<b>מילון מונחים קצר:</b><br>'
            '<b>Strike (סטרייק)</b>: המחיר שנקבע מראש באופציה.<br>'
            '<b>OTM</b>: "מחוץ לכסף" - האופציה פוקעת חסרת ערך (טוב למוכר פוט, רע לקונה).<br>'
            '<b>IV</b>: מה השוק מצפה שהמניה תזוז (מהמחיר של האופציה עצמה).<br>'
            '<b>RV</b>: מה המניה באמת זזה בעבר (מהמחיר ההיסטורי).<br>'
            '<b>Expected Move</b>: טווח מחירים סביר עד הפקיעה, לפי ה-IV (בהנחת התפלגות נורמלית).<br>'
            '<b>Fat-tail</b>: הסתברות OTM לפי התפלגות t-Student במקום נורמלית - '
            '"זנבות שמנים" יותר, בדיוק התיקון להנחה של Expected Move שלא תמיד מחזיקה.<br>'
            '<b>CVaR</b>: ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר בפועל - '
            'לא מניח שום התפלגות בכלל, פשוט לוקח מה שקרה.<br>'
            '<b>סטרס טסט</b>: תרחישי ירידה קבועים (עד 50%-) - גם הם לא תלויים בשום הנחת התפלגות.'
            '</div>',
            unsafe_allow_html=True,
        )

    tab_screener, tab_prob, tab_tracker, tab_bs, tab_iv, tab_rv = st.tabs(
        ["סורק רב-מניות", "הסתברות OTM (Put)", "📒 מעקב פרמיות", "מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)"]
    )

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
                                 key=f"{key_prefix}_bs_S_{ticker}", help=_HELP["S"])
        with cols[2]:
            K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),
                                 key=f"{key_prefix}_bs_K_{ticker}", help=_HELP["K"])
        with cols[3]:
            days, _bs_exp = _expiry_input("תאריך פקיעה", f"{key_prefix}_bs_exp", ticker,
                                          help=_HELP["days"])
        with cols[4]:
            _bs_iv_live = _try_fetch_atm_iv(ticker)
            sigma_pct = st.number_input(
                "IV (%)", min_value=0.1,
                value=float(round(_bs_iv_live, 1)) if _bs_iv_live else 30.0,
                key=f"{key_prefix}_bs_sigma_{ticker}", help=_HELP["sigma"],
            )
            if _bs_iv_live:
                st.caption(f"נמשך אוטומטית משוק אמיתי: {_bs_iv_live:.1f}%")

        cols2 = st.columns(2)
        with cols2[0]:
            r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,
                                     key=f"{key_prefix}_bs_r", help=_HELP["r"])
        with cols2[1]:
            q_pct = st.number_input("תשואת דיבידנד (%)", value=0.0,
                                     key=f"{key_prefix}_bs_q", help=_HELP["q"])

        _bs_flag = f"{key_prefix}_bs_show"
        st.markdown(
            '<span class="rs-btn-help" title="מחשב מחיר ואת כל הגריקס (Delta/Gamma/Vega/Theta) והסתברות OTM לפי המודל, מהערכים שהוזנו למעלה.">❓</span>',
            unsafe_allow_html=True,
        )
        if st.button(
            "חשב", key=f"{key_prefix}_bs_calc",
            help="מחשב מחיר ואת כל הגריקס (Delta/Gamma/Vega/Theta) והסתברות OTM לפי המודל, "
                 "מהערכים שהוזנו למעלה.",
        ) or st.session_state.get(_bs_flag):
            st.session_state[_bs_flag] = True
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
                                    key=f"{key_prefix}_iv_S_{ticker}", help=_HELP["S"])
        with cols[3]:
            iv_K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),
                                    key=f"{key_prefix}_iv_K_{ticker}", help=_HELP["K"])
        with cols[4]:
            iv_days, _iv_exp = _expiry_input("תאריך פקיעה", f"{key_prefix}_iv_exp", ticker,
                                             help=_HELP["days"])

        iv_r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,
                                    key=f"{key_prefix}_iv_r", help=_HELP["r"])

        _iv_flag = f"{key_prefix}_iv_show"
        st.markdown(
            '<span class="rs-btn-help" title="פותר אחורה איזו IV מסבירה את מחיר השוק שהוזן, ושומר את התצפית לאיסוף היסטוריית IV (לצורך IV Rank אמיתי בעתיד).">❓</span>',
            unsafe_allow_html=True,
        )
        if st.button(
            "חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc",
            help="פותר אחורה איזו IV מסבירה את מחיר השוק שהוזן, ושומר את התצפית "
                 "לאיסוף היסטוריית IV (לצורך IV Rank אמיתי בעתיד).",
        ) or st.session_state.get(_iv_flag):
            st.session_state[_iv_flag] = True
            try:
                iv_result = implied_vol(
                    kind=iv_kind, market_price=iv_price, S=iv_S, K=iv_K,
                    T=iv_days / 365.0, r=iv_r_pct / 100.0,
                )
                _card("תוצאה", _metric("IV גלום מהשוק", f"{iv_result:.1%}") + _IV_EXPLAIN)
                _record_iv_observation(ticker, int(iv_days), iv_result)
                n_obs = _iv_observation_count(ticker)
                st.caption(
                    f"נשמר לאיסוף היסטוריית IV. {n_obs} תצפיות עד כה עבור {ticker or 'טיקר לא צוין'} "
                    "(IV Rank אמיתי דורש היסטוריה - עד אז, טאב 'הסתברות OTM' מציג RV Rank כתחליף)."
                )
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
            _rv_flag = f"{key_prefix}_rv_show"
            st.markdown(
                '<span class="rs-btn-help" title="מחשב RV מהיסטוריית המחירים בפועל (לא ממה שהשוק מצפה), ומשווה אותו ל-IV שתזיני.">❓</span>',
                unsafe_allow_html=True,
            )
            if st.button(
                "חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc",
                help="מחשב RV מהיסטוריית המחירים בפועל (לא ממה שהשוק מצפה), "
                     "ומשווה אותו ל-IV שתזיני.",
            ) or st.session_state.get(_rv_flag):
                st.session_state[_rv_flag] = True
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


    # -------------------------------------------------------------------
    # טאב 4: הסתברות OTM - שלושה מודלים נפרדים, בלי מיזוג ובלי המלצה
    # -------------------------------------------------------------------
    with tab_prob:
        st.markdown(
            '<div class="rs-explain" style="margin-bottom:12px;">'
            'שלושה מודלים נפרדים להערכת הסתברות OTM לפוט: מודל (Black-Scholes), '
            'היסטורי (לפי מה שקרה בפועל בעבר), ו-Fat-tail (מתחשב בזנבות שמנים '
            'מעבר להתפלגות נורמלית). המודלים מוצגים כל אחד בנפרד - אין כאן ציון '
            'מאוחד, דירוג, או "המלצה". אם המודלים חלוקים ביניהם באופן משמעותי, '
            'זה מוצג במפורש, לא מוסתר.'
            '</div>',
            unsafe_allow_html=True,
        )

        spot_default = _try_fetch_spot(ticker) or 100.0
        # --- הצמדת סטרייק לשרשרת: הערך נקבע בריצה הקודמת (למטה), ומוחל כאן
        # לפני יצירת ה-widget - Streamlit לא מרשה לשנות widget אחרי שנוצר.
        # ברירות מחדל דרך session_state ולא value= - אחרת Streamlit מזהיר
        # על widget שקיבל גם value= וגם ערך מ-Session State.
        _k_key = f"{key_prefix}_prob_K_{ticker}"
        _k_snap = st.session_state.pop(f"{key_prefix}_prob_K_snap", None)
        if _k_snap is not None:
            st.session_state[_k_key] = _k_snap
        st.session_state.setdefault(_k_key, float(round(spot_default * 0.9, 2)))
        st.session_state.setdefault(f"{key_prefix}_prob_premium", 2.0)
        st.session_state.setdefault(f"{key_prefix}_prob_volume", 0)
        st.session_state.setdefault(f"{key_prefix}_prob_oi", 0)

        cols = st.columns(4)
        with cols[0]:
            prob_S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),
                                      key=f"{key_prefix}_prob_S_{ticker}", help=_HELP["S"])
        with cols[1]:
            prob_K = st.number_input("סטרייק (K)", min_value=0.01,
                                      key=f"{key_prefix}_prob_K_{ticker}", help=_HELP["K"])
        with cols[2]:
            prob_days, prob_exp = _expiry_input("תאריך פקיעה", f"{key_prefix}_prob_exp", ticker,
                                                help=_HELP["days"])
        with cols[3]:
            _prob_iv_live = _try_fetch_atm_iv(ticker)
            prob_sigma_pct = st.number_input(
                "IV למודל (%)", min_value=0.1,
                value=float(round(_prob_iv_live, 1)) if _prob_iv_live else 30.0,
                key=f"{key_prefix}_prob_sigma_{ticker}", help=_HELP["sigma"],
            )
            if _prob_iv_live:
                st.caption(f"נמשך אוטומטית משוק אמיתי: {_prob_iv_live:.1f}%")

        # --- ציטוט שוק לסטרייק/פקיעה שנבחרו ------------------------------
        _chain = _try_fetch_put_chain(ticker, prob_exp.isoformat())
        _chain_K = nearest_strike([r["strike"] for r in _chain], float(prob_K)) if _chain else None
        if _chain_K is not None and abs(_chain_K - float(prob_K)) > 1e-6:
            st.session_state[f"{key_prefix}_prob_K_snap"] = _chain_K
            st.rerun()

        _qrow = next((r for r in _chain if r["strike"] == _chain_K), None) if _chain_K is not None else None
        _q = quote_summary(_qrow["bid"], _qrow["ask"]) if _qrow else None

        # מילוי בכוח רק כשהטיקר/הפקיעה/הסטרייק השתנו - כמו רגל ההגנה למטה
        _q_sig_key = f"{key_prefix}_prob_quote_sig"
        _q_sig = (ticker, prob_exp.isoformat(), _chain_K)
        if _qrow and st.session_state.get(_q_sig_key) != _q_sig:
            if _q.is_live:
                st.session_state[f"{key_prefix}_prob_premium"] = float(round(max(_q.mid, 0.01), 2))
            if _qrow["volume"] is not None:
                st.session_state[f"{key_prefix}_prob_volume"] = int(_qrow["volume"])
            if _qrow["openInterest"] is not None:
                st.session_state[f"{key_prefix}_prob_oi"] = int(_qrow["openInterest"])
            st.session_state[_q_sig_key] = _q_sig

        if not _chain:
            st.caption("אין שרשרת אופציות לטיקר/תאריך הזה - פרמיה, נפח ו-OI בהזנה ידנית.")
        else:
            def _usd(v):
                return f"${v:,.2f}" if v is not None else "—"

            def _int(v):
                return f"{int(v):,}" if v is not None else "—"

            if _q.is_live:
                _q_grid = "".join([
                    _metric("Bid", _usd(_qrow["bid"])),
                    _metric("Ask", _usd(_qrow["ask"])),
                    _metric("Mid", _usd(_q.mid)),
                    _metric("מרווח", f"{_usd(_q.spread)} ({_q.spread_pct:.1%})"),
                ])
                _q_note = "הפרמיה מולאה מה-Mid (מחיר עם הוראת לימיט). במרווח רחב, מכירה מיידית תהיה קרובה יותר ל-Bid."
            else:
                _q_grid = _metric("Bid / Ask", "אין ציטוט חי")
                _q_note = "אין ציטוט חי (bid=0 - כנראה מחוץ לשעות המסחר ב-US). הפרמיה לא מולאה, אין fallback ל-Last."
            _q_grid += "".join([
                _metric("Last", _usd(_qrow["lastPrice"])),
                _metric("נפח", _int(_qrow["volume"])),
                _metric("OI", _int(_qrow["openInterest"])),
                _metric("IV (Yahoo)", f"{_qrow['impliedVolatility']:.1%}" if _qrow["impliedVolatility"] else "—"),
            ])
            _card(
                f"ציטוט שוק: PUT {_chain_K:g} | {prob_exp.strftime('%d/%m/%Y')}",
                f'<div class="rs-grid">{_q_grid}</div><div class="rs-explain">{_q_note}</div>',
            )

        prob_r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,
                                      key=f"{key_prefix}_prob_r", help=_HELP["r"])

        stress_cols = st.columns(3)
        with stress_cols[0]:
            prob_premium = st.number_input("פרמיה שהתקבלה ($)", min_value=0.01,
                                            key=f"{key_prefix}_prob_premium", help=_HELP["iv_price"])
        with stress_cols[1]:
            prob_contracts = st.number_input("מספר חוזים", min_value=1, value=1,
                                              key=f"{key_prefix}_prob_contracts", help=_HELP["contracts"])
        with stress_cols[2]:
            prob_capital = st.number_input("הון זמין ($, אופציונלי - להצגת % מההון)", min_value=0.0, value=0.0,
                                            key=f"{key_prefix}_prob_capital", help=_HELP["capital"])
        liq_cols = st.columns(2)
        with liq_cols[0]:
            prob_volume = st.number_input("נפח (מ-Yahoo/הברוקר, אופציונלי)", min_value=0,
                                           key=f"{key_prefix}_prob_volume")
        with liq_cols[1]:
            prob_oi = st.number_input("עניין פתוח (מ-Yahoo/הברוקר, אופציונלי)", min_value=0,
                                       key=f"{key_prefix}_prob_oi")

        # --- רגל הגנה ל-Bull Put Spread - לצורך השוואת הון/ביטחונות למטה --------
        _protect_live = _try_fetch_otm_put_quote(ticker, below_strike=prob_K, dte_days=int(prob_days))
        # Streamlit מתעלם מ-value= ברגע שלשדה כבר יש ערך שמור ב-session_state -
        # לכן מעדכנים בכוח רק כשהטיקר/הסטרייק/ה-DTE השתנו מאז השליפה
        # האחרונה - כדי לא לדרוס עריכה ידנית שעוד רלוונטית.
        _protect_sig_key = f"{key_prefix}_prob_protect_sig"
        _protect_sig = (ticker, round(float(prob_K), 2), int(prob_days))
        if st.session_state.get(_protect_sig_key) != _protect_sig:
            if _protect_live:
                st.session_state[f"{key_prefix}_prob_protect_K"] = float(round(_protect_live[0], 2))
                st.session_state[f"{key_prefix}_prob_protect_premium"] = float(round(_protect_live[1], 2))
            else:
                # בלי ציטוט חי: איפוס לברירת מחדל יחסית לסטרייק הנוכחי - לא להשאיר
                # ערך ישן (טיקר קודם / סטרייק קודם) שעלול להיות מעל סטרייק הכתיבה
                st.session_state[f"{key_prefix}_prob_protect_K"] = float(round(prob_K * 0.95, 2))
                st.session_state[f"{key_prefix}_prob_protect_premium"] = float(round(max(prob_premium * 0.4, 0.01), 2))
            st.session_state[_protect_sig_key] = _protect_sig
        spread_cols = st.columns(2)
        with spread_cols[0]:
            prob_protect_K = st.number_input(
                "סטרייק הגנה ל-Bull Put Spread", min_value=0.01,
                key=f"{key_prefix}_prob_protect_K",
                help="הסטרייק שבו קונים פוט הגנה, מתחת לסטרייק הכתיבה - קובע את רוחב המרווח. נמשך אוטומטית משוק אמיתי כשזמין (דלתא ~0.15), אחרת 95% מסטרייק הכתיבה.",
            )
        with spread_cols[1]:
            prob_protect_premium = st.number_input(
                "פרמיית ההגנה ($)", min_value=0.01,
                key=f"{key_prefix}_prob_protect_premium",
                help="הפרמיה ששולמת עבור פוט ההגנה. נמשך אוטומטית (Ask אמיתי) כשזמין.",
            )
        if _protect_live:
            st.caption(
                f"נמשך אוטומטית משוק אמיתי (דלתא יעד ~0.15): "
                f"סטרייק ${_protect_live[0]:,.2f}, Ask ${_protect_live[1]:,.2f}"
            )
        else:
            st.caption(
                "לא נמצא ציטוט הגנה חי - הוזנו ערכי ברירת מחדל משוערים בלבד. "
                "לפני החלטה אמיתית, כדאי לבדוק בשרשרת האופציות אצל הברוקר."
            )

        _prob_flag = f"{key_prefix}_prob_show"
        st.markdown(
            '<span class="rs-btn-help" title="מריץ בבת אחת: הסתברות לפי שלושה מודלים נפרדים, תזוזה צפויה, סטרס טסט ו-CVaR. חלק מהתוצאות דורשות היסטוריית מחירים (yfinance).">❓</span>',
            unsafe_allow_html=True,
        )
        if st.button(
            "חשב הסתברות OTM", key=f"{key_prefix}_prob_calc",
            help="מריץ בבת אחת: הסתברות לפי שלושה מודלים נפרדים, תזוזה צפויה, "
                 "סטרס טסט ו-CVaR. חלק מהתוצאות דורשות היסטוריית מחירים (yfinance).",
        ) or st.session_state.get(_prob_flag):
            st.session_state[_prob_flag] = True
            # --- מודל 1: Normal (Black-Scholes) - קיים כבר, רק נחשף כאן ---
            try:
                normal_prob = bs_greeks(
                    kind="put", S=prob_S, K=prob_K, T=prob_days / 365.0,
                    sigma=prob_sigma_pct / 100.0, r=prob_r_pct / 100.0,
                ).prob_otm
            except ValueError as e:
                st.error(f"קלט לא תקין למודל: {e}")
                normal_prob = None

            available_for_diff = {}
            if normal_prob is not None:
                available_for_diff["מודל"] = normal_prob

            breakeven = short_put_breakeven(strike=prob_K, premium=prob_premium)
            grid_normal = "".join([
                _metric("הסתברות OTM - מודל", f"{normal_prob:.1%}" if normal_prob is not None else "—"),
                _metric(
                    "Breakeven", f"${breakeven:,.2f}",
                    tooltip="הסטרייק פחות הפרמיה שקיבלת. זה המחיר שמתחתיו העסקה מתחילה "
                            "להפסיד בפועל - מעליו, הפרמיה מכסה את ההפסד המהותי במלואו.",
                ),
            ])
            model_extra = ""
            LIQUIDITY_THRESHOLD = 50
            if 0 < prob_volume < LIQUIDITY_THRESHOLD or 0 < prob_oi < LIQUIDITY_THRESHOLD:
                model_extra = (
                    '<span class="rs-badge red" style="margin-top:8px; display:inline-block;">'
                    f'נפח/עניין פתוח נמוכים ({int(prob_volume)}/{int(prob_oi)}) - המחיר עלול '
                    'לא לשקף מסחר אמיתי</span>'
                )
            _card("מודל (Black-Scholes)", f'<div class="rs-grid">{grid_normal}</div>{model_extra}')

            # --- תזוזה צפויה - לא תלוי בהיסטוריה, זמין תמיד ------------------
            em = expected_move(S=prob_S, sigma=prob_sigma_pct / 100.0, T_days=prob_days)
            em_distance = strike_distance_in_expected_moves(S=prob_S, K=prob_K, move=em.move)
            grid_em = "".join([
                _metric("תזוזה צפויה", f"±${em.move:,.2f}"),
                _metric("טווח צפוי", f"${em.low:,.2f} - ${em.high:,.2f}"),
                _metric("מרחק הסטרייק", f"{em_distance:.2f}x תזוזה צפויה" if em_distance is not None else "—"),
            ])
            em_explain = (
                '<div class="rs-explain">קירוב מהנוסחה S×IV×√T (סטיית תקן אחת, לא טווח '
                'מובטח - בהנחת התפלגות נורמלית, שראינו שלא תמיד מחזיקה). מרחק הסטרייק '
                'חיובי אומר שהוא מתחת למחיר הנוכחי; ככל שהמספר גבוה יותר, הסטרייק רחוק '
                'יותר ביחס לתזוזה הצפויה.'
                '</div>'
            )
            _card("תזוזה צפויה (Expected Move)", f'<div class="rs-grid">{grid_em}</div>{em_explain}')

            # --- טבלת השוואה - HTML מותאם אישית, בטוח ל-RTL -----------------
            _compare_key = f"{key_prefix}_compare_rows"
            if _compare_key not in st.session_state:
                st.session_state[_compare_key] = []

            _fat_for_row = None
            _rv_rank_for_row = None
            add_col, export_col = st.columns([1, 1])
            with add_col:
                if st.button("➕ הוסף שורה", key=f"{key_prefix}_compare_add"):
                    st.session_state[f"{key_prefix}_compare_pending"] = True

            # --- סטרס טסט - תרחישי % קבועים, לא תלוי בהיסטוריה --------------
            capital_arg = prob_capital if prob_capital > 0 else None
            stress_rows = stress_test_table(
                S=prob_S, strike=prob_K, premium=prob_premium, contracts=int(prob_contracts),
                available_capital=capital_arg,
            )
            grid_stress = []
            for row in stress_rows:
                label = f"{row.pct_move:+.0%} (${row.stressed_price:,.0f})"
                value = f"${row.pnl:,.2f}"
                if capital_arg:
                    value += f" ({row.pct_of_capital:+.1%})"
                grid_stress.append(_metric(label, value))
            stress_explain = (
                '<div class="rs-explain">P/L של שורט-פוט יחיד בתרחישי % קבועים ביחס למחיר הנוכחי - '
                'משתמש באותו מנוע payoff כמו שאר האסטרטגיות בקובץ, לא נוסחה נפרדת. '
                'בסוגריים: % מההון הזמין, אם הוזן.</div>'
            )
            _card("סטרס טסט", f'<div class="rs-grid">{"".join(grid_stress)}</div>{stress_explain}')

            # --- גודל פוזיציה לפי חוק הסיכון (1%-3% מהתיק) --------------
            if capital_arg:
                _size_template = Position(legs=[Leg("put", -1, 1, prob_premium, prob_K, label="שורט פוט")])
                prob_max_risk_pct = st.number_input(
                    "מגבלת סיכון לעסקה (% מהתיק)", min_value=0.5, max_value=10.0, value=1.0, step=0.5,
                    key=f"{key_prefix}_prob_max_risk_pct",
                    help="ההפסד המרבי המותר בעסקה בודדת, כאחוז מהתיק. מקובל למסחר ספקולטיבי: 1%-3%.",
                )
                verdict = size_position(
                    template=_size_template, portfolio_usd=capital_arg,
                    max_risk_pct=prob_max_risk_pct / 100.0, template_contracts=1,
                )
                grid_size = "".join([
                    _metric("חוזים מאושרים", str(verdict.contracts)),
                    _metric("סיכון לחוזה", f"${verdict.unit_risk_usd:,.2f}"),
                    _metric("סיכון כולל מאושר", f"${verdict.risk_usd:,.2f} ({verdict.risk_pct:.2%})"),
                ])
                size_extra = f'<div class="rs-explain">{verdict.reason}</div>'
                if verdict.risk_pct > 0.05:
                    size_extra += (
                        '<span class="rs-badge red" style="margin-top:8px; display:inline-block;">'
                        '⚠️ ריכוז יתר - הפוזיציה מסכנת מעל 5% מהתיק (מעל טווח 1%-3% המקובל)'
                        '</span>'
                    )
                _card("גודל פוזיציה לפי חוק הסיכון", f'<div class="rs-grid">{grid_size}</div>{size_extra}')
            else:
                st.caption(
                    "💡 הזיני \"הון זמין\" למעלה (בשורת הפרמיה/חוזים) כדי לראות כמה חוזים "
                    "מותרים לפי חוק הסיכון (1%-3% מהתיק), וקבלת התראה על ריכוז יתר."
                )

            # --- השוואת הון/ביטחונות ו-ROC: CSP מול Bull Put Spread -----------
            _csp1_collateral = prob_K * CONTRACT_MULTIPLIER * 1
            _csp1_credit = prob_premium * CONTRACT_MULTIPLIER * 1
            _csp1_max_loss = Position(legs=[Leg("put", -1, 1, prob_premium, prob_K)]).max_loss()
            _csp1_roc = (_csp1_credit / _csp1_collateral) if _csp1_collateral else None

            _csp3_collateral = _csp1_collateral * 3
            _csp3_credit = _csp1_credit * 3
            _csp3_max_loss = _csp1_max_loss * 3
            _csp3_roc = _csp1_roc

            try:
                _bps = bull_put_spread(
                    1, short_put=prob_K, short_put_prem=prob_premium,
                    long_put=prob_protect_K, long_put_prem=prob_protect_premium,
                )
            except ValueError:
                _bps = None
                st.warning(
                    f"סטרייק ההגנה (${prob_protect_K:,.2f}) חייב להיות מתחת לסטרייק הכתיבה "
                    f"(${prob_K:,.2f}) - עמודת Bull Put Spread לא חושבה."
                )
            _bps_credit = _bps.net_cash if _bps else None
            _bps_max_loss = _bps.max_loss() if _bps else None
            _bps_collateral = _bps_max_loss  # Reg-T: ביטחונות = הפסד מרבי בסיכון מוגדר
            _bps_roc = (_bps_credit / _bps_collateral) if _bps_collateral else None

            def _usd0(v):
                return f"${v:,.0f}" if v is not None else "—"

            def _roc_str(r):
                return f"{r:.1%}" if r is not None else "—"

            _cmp_headers = ["", "CSP (חוזה 1)", "CSP (3 חוזים)", "Bull Put Spread (חוזה 1)"]
            _cmp_rows = [
                ("ביטחונות נדרשים", f"${_csp1_collateral:,.0f}", f"${_csp3_collateral:,.0f}", _usd0(_bps_collateral)),
                ("קרדיט נטו", f"${_csp1_credit:,.0f}", f"${_csp3_credit:,.0f}", _usd0(_bps_credit)),
                ("הפסד מרבי", f"${_csp1_max_loss:,.0f}", f"${_csp3_max_loss:,.0f}", _usd0(_bps_max_loss)),
                ("ROC (קרדיט/ביטחונות)", _roc_str(_csp1_roc), _roc_str(_csp3_roc), _roc_str(_bps_roc)),
            ]
            _cmp_thead = "".join(f"<th>{h}</th>" for h in _cmp_headers)
            _cmp_trs = "".join(
                "<tr>" + f"<td>{row[0]}</td>" + "".join(f"<td>{v}</td>" for v in row[1:]) + "</tr>"
                for row in _cmp_rows
            )
            _cmp_table_html = (
                f'<div style="overflow-x:auto;"><table class="rs-table">'
                f'<thead><tr>{_cmp_thead}</tr></thead><tbody>{_cmp_trs}</tbody></table></div>'
            )
            _cmp_explain = (
                '<div class="rs-explain">'
                'ביטחונות ב-CSP הם הסטרייק המלא × 100 (הסכום שנועל הברוקר בחשבון קאש), '
                'לא ההפסד המרבי התיאורטי - שני מספרים שונים בכוונה. ב-Bull Put Spread, '
                'הביטחונות (לפי כלל Reg-T הרגיל) שווים בדיוק להפסד המרבי, כי ההגנה כבר '
                'מגבילה את הסיכון. ROC כאן הוא קרדיט חלקי ביטחונות, לא קרדיט חלקי הפסד מרבי - '
                'ל-CSP השניים שונים.'
                '</div>'
            )
            _card(
                "השוואת הון וביטחונות - CSP מול Bull Put Spread",
                f"{_cmp_table_html}{_cmp_explain}",
            )

            with st.expander("📖 מדריך: מה ההבדל בין CSP ל-Bull Put Spread, ולמה הביטחונות כל כך שונים"):
                st.markdown(
                    '<div class="rs-explain"><b>מה זה בכלל CSP?</b><br>כשמוכרים פוט "מוגן במזומן" (Cash-Secured Put), הברוקר דורש שתחזיקי בחשבון את כל הסכום שיידרש אם תצטרכי לקנות את המניה במחיר הסטרייק - זו הסיבה שבטבלה אפשר לראות ביטחונות שמגיעים ל-100% ומעלה מהתיק - זה לא באג, זה בדיוק מה שקורה במציאות: אם המניה תיפול, הברוקר ידרוש ממך לקנות את כל המניות במחיר הסטרייק, ולכן הוא נועל את כל הסכום מראש - גם אם ההפסד המרבי בפועל קטן יותר (סטרייק פחות פרמיה, לא הסטרייק המלא).<br><br><b>מה שונה ב-Bull Put Spread?</b><br>עם אותה כתיבה בדיוק, קונים גם פוט הגנה בסטרייק נמוך יותר. ההגנה "עוצרת" את ההפסד המרבי ברוחב שבין שני הסטרייקים פחות הקרדיט שקיבלת - מספר ידוע מראש, במקום חושף של כל הסטרייק כמו ב-CSP. לכן הברוקר דורש הרבה פחות ביטחונות - בדוגמה שלמעלה, 1% בלבד מהתיק, לעומת 120%-360% ב-CSP.<br><br><b>המחיר של ה"הנחה" הזו</b><br>זה לא "ארוחת חינם" - שני דברים משתנים בתמורה: הפרמיה שמקבלים קטנה יותר (חלק ממנה הולך לקניית ההגנה), והרווח המקסימלי מוגבל לקרדיט הנטו שקיבלת - בעוד שב-CSP הרווח המקסימלי הוא כל הפרמיה שקיבלת, בלי תקרה.<br><br><b>איך לקרוא את יחס קרדיט/רוחב לאור ההסבר הזה</b><br>היחס מודד כמה מהרוחב המקסימלי בפועל מגיע בחזרה כקרדיט. יחס נמוך מדי מעיד שההגנה "אוכלת" חלק גדול מדי מהפרמיה - זו הסיבה שהכרטיס של מעלה מציג עובדתית (סף נפוץ: 20%-30%) - לא קביעה שמתאימה לכל מצב.</div>',
                    unsafe_allow_html=True,
                )

            # --- בדיקות מול ספים נפוצים: DTE, יחס קרדיט/רוחב, נזילות -------
            _dte_badge_cls = "green" if 30 <= int(prob_days) <= 45 else "gray"
            _dte_badge = (
                f'<span class="rs-badge {_dte_badge_cls}">פקיעה: {prob_exp.strftime("%d/%m/%Y")} '
                f'(טווח 30-45 יום נפוץ לשחיקת תטא)</span>'
            )

            _width = prob_K - prob_protect_K
            if _width > 0:
                _cw_ratio = _bps_credit / (_width * CONTRACT_MULTIPLIER)
                _cw_cls = "green" if _cw_ratio >= 0.20 else "yellow" if _cw_ratio >= 0.10 else "red"
                _cw_badge = (
                    f'<span class="rs-badge {_cw_cls}">יחס קרדיט/רוחב (Bull Put Spread): '
                    f'{_cw_ratio:.0%} (סף נפוץ: 20%-30%)</span>'
                )
            else:
                _cw_badge = (
                    '<span class="rs-badge gray">יחס קרדיט/רוחב: לא ניתן לחשב - '
                    'רוחב מרווח 0 או שלילי</span>'
                )

            _threshold_badges = [_dte_badge, _cw_badge]
            if prob_capital:
                for _label, _coll in [
                    ("CSP (חוזה 1)", _csp1_collateral),
                    ("CSP (3 חוזים)", _csp3_collateral),
                    ("Bull Put Spread (חוזה 1)", _bps_collateral),
                ]:
                    if _coll is None:
                        continue
                    _pct_locked = _coll / prob_capital
                    _liq_cls = "green" if _pct_locked <= 0.5 else "yellow" if _pct_locked <= 0.75 else "red"
                    _threshold_badges.append(
                        f'<span class="rs-badge {_liq_cls}">{_label}: {_pct_locked:.0%} מהתיק נעול '
                        f'(סף נזילות נפוץ: עד 50%)</span>'
                    )

            _thresholds_html = (
                '<div style="display:flex; flex-direction:column; gap:8px; align-items:flex-start;">'
                + "".join(_threshold_badges) + "</div>"
            )
            if not prob_capital:
                _thresholds_html += (
                    '<div class="rs-explain" style="margin-top:8px;">'
                    'הזיני "הון זמין" למעלה כדי לראות איזה אחוז מהתיק כל אסטרטגיה '
                    'נועלת כביטחונות.'
                    '</div>'
                )
            _card("בדיקות מול ספים נפוצים", _thresholds_html)

            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------
            closes = _try_fetch_closes(ticker, period="10y")
            if closes is None:
                st.info(
                    f"לא נמצאה היסטוריית מחירים עבור \"{ticker}\" - מוצג רק מודל "
                    "ה-Black-Scholes. היסטורי ו-Fat-tail דורשים סדרת מחירים."
                )
            else:
                hist = historical_put_otm_probability(closes, strike=prob_K, dte_days=int(prob_days))
                period_metrics = "".join(
                    _metric(f"{years} שנים", f"{p:.1%}" if p is not None else "אין מספיק היסטוריה")
                    for years, p in sorted(hist.by_period.items())
                )
                weighted_html = (
                    _metric("ממוצע משוקלל", f"{hist.weighted_otm:.1%}")
                    if hist.weighted_otm is not None else ""
                )
                hist_explain = (
                    '<div class="rs-explain">כל תקופה (1/3/5/10 שנים) מחושבת בנפרד לפי '
                    'כמה פעמים בעבר המחיר, בהינתן אותו מרחק זמן לפקיעה, נשאר מעל הסטרייק. '
                    'הממוצע המשוקלל (40/30/20/10) מוצג לצד הפירוט המלא, לא במקומו.'
                    + (f'<br><b>{hist.note}</b>' if hist.note else '')
                    + '</div>'
                )
                _card("היסטורי", f'<div class="rs-grid">{period_metrics}{weighted_html}</div>{hist_explain}')
                if hist.weighted_otm is not None:
                    available_for_diff["היסטורי"] = hist.weighted_otm

                log_returns = [_log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
                fat = fat_tail_otm_probability(log_returns, S=prob_S, K=prob_K, dte_days=int(prob_days))
                if fat.otm_probability is not None:
                    grid_fat = "".join([
                        _metric("הסתברות OTM - Fat-tail", f"{fat.otm_probability:.1%}"),
                        _metric("דרגות חופש (df)", f"{fat.degrees_of_freedom:.1f}"),
                        _metric("קורטוזיס עודף", f"{fat.excess_kurtosis:.2f}"),
                    ])
                    fat_explain = (
                        '<div class="rs-explain">קירוב מוצהר: מעריך דרגות חופש של התפלגות '
                        't-Student מהקורטוזיס העודף בתשואות ההיסטוריות, ומתאים לאופק הזמן '
                        'לפי שורש-זמן. df נמוך = זנבות שמנים משמעותיים ביחס להתפלגות נורמלית.'
                        '</div>'
                    )
                    _card("Fat-tail", f'<div class="rs-grid">{grid_fat}</div>{fat_explain}')
                    available_for_diff["Fat-tail"] = fat.otm_probability
                    _fat_for_row = fat.otm_probability
                else:
                    st.info(f"Fat-tail: {fat.note}")

                rank = rv_rank(closes)
                pct = rv_percentile(closes)
                n_obs = _iv_observation_count(ticker)
                grid_rv = "".join([
                    _metric("RV Rank", f"{rank:.0f}" if rank is not None else "אין מספיק היסטוריה"),
                    _metric("RV Percentile", f"{pct:.0f}%" if pct is not None else "אין מספיק היסטוריה"),
                ])
                rv_explain = (
                    '<div class="rs-explain">תחליף זמני ל-IV Rank: yfinance/Yahoo לא שומרים '
                    'ארכיון היסטוריית IV (רק שרשרת אופציות נוכחית), אז מוצג כאן דירוג של '
                    'התנודתיות הממומשת (RV) - מה שקרה בפועל, לא מה שהשוק מתמחר. '
                    f'נאספו {n_obs} תצפיות IV אמיתיות לטיקר הזה בטאב "תנודתיות גלומה" - '
                    'ברגע שיצטבר מספיק, ניתן יהיה לחשב IV Rank אמיתי.'
                    '</div>'
                )
                _card("RV Rank (תחליף זמני ל-IV Rank)", f'<div class="rs-grid">{grid_rv}</div>{rv_explain}')
                _rv_rank_for_row = rank

                pnl_dist = historical_short_put_pnl_distribution(
                    closes, strike=prob_K, dte_days=int(prob_days),
                    premium=prob_premium, contracts=int(prob_contracts),
                )
                es = expected_shortfall(pnl_dist, tail_fraction=0.05)
                if es is not None:
                    grid_cvar = [_metric("CVaR (5% הגרועים ביותר)", f"${es:,.2f}")]
                    if capital_arg:
                        grid_cvar.append(_metric("CVaR כ-% מההון", f"{es / capital_arg:+.1%}"))
                    cvar_explain = (
                        '<div class="rs-explain">ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר '
                        f'(מתוך {len(pnl_dist)} תקופות היסטוריות בפועל) - לא תרחיש קיצון בודד ושרירותי, '
                        'אלא ממוצע על פני כל הפעמים שבאמת היה גרוע.</div>'
                    )
                    _card("CVaR (Expected Shortfall)", f'<div class="rs-grid">{"".join(grid_cvar)}</div>{cvar_explain}')

            if st.session_state.get(f"{key_prefix}_compare_pending"):
                new_row = {
                    "טיקר": ticker, "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,
                    "נפח": prob_volume, "עניין פתוח": prob_oi,
                    "Breakeven": round(breakeven, 2),
                    "הסתברות מודל (%)": round(normal_prob * 100, 1) if normal_prob is not None else None,
                    "Fat-tail (%)": round(_fat_for_row * 100, 1) if _fat_for_row is not None else None,
                    "RV Rank": round(_rv_rank_for_row, 0) if _rv_rank_for_row is not None else None,
                    "מרחק (xEM)": round(em_distance, 2) if em_distance is not None else None,
                    "נזילות": "⚠️ נמוכה" if (0 < prob_volume < 50 or 0 < prob_oi < 50) else "תקינה",
                }
                existing = next(
                    (r for r in st.session_state[_compare_key]
                     if r["טיקר"] == ticker and r["סטרייק"] == prob_K),
                    None,
                )
                if existing is not None:
                    existing.update(new_row)
                else:
                    st.session_state[_compare_key].append(new_row)
                st.session_state[f"{key_prefix}_compare_pending"] = False

            _rows_for_ticker = sorted(
                [r for r in st.session_state[_compare_key] if r["טיקר"] == ticker],
                key=lambda r: r["סטרייק"],
            )
            if _rows_for_ticker:
                import pandas as pd
                _df = pd.DataFrame(_rows_for_ticker)
                with export_col:
                    st.download_button(
                        "⬇️ CSV", data=_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"riskshield_{ticker}.csv", mime="text/csv",
                        key=f"{key_prefix}_compare_export",
                    )
                st.markdown(
                    f'<div class="rs-explain" style="margin-top:8px;">'
                    f'טבלת השוואה - {ticker} (לפי סטרייק, לא לפי "כדאיות").</div>',
                    unsafe_allow_html=True,
                )

                _metric_rows = [
                    ("פרמיה", lambda r: f"${r['פרמיה']:.2f}"),
                    ("IV (%)", lambda r: f"{r['IV (%)']:.1f}%"),
                    ("הסתברות מודל OTM", lambda r: (
                        f"{r['הסתברות מודל (%)']:.1f}%" if r["הסתברות מודל (%)"] is not None else "—"
                    )),
                    ("הסתברות Fat-tail OTM", lambda r: (
                        f"{r.get('Fat-tail (%)'):.1f}%" if r.get("Fat-tail (%)") is not None else "—"
                    )),
                    ("RV Rank", lambda r: (
                        f"{r.get('RV Rank'):.0f}" if r.get("RV Rank") is not None else "—"
                    )),
                    ("Breakeven", lambda r: f"${r['Breakeven']:.2f}"),
                    ("מרחק (xEM)", lambda r: (
                        f"{r['מרחק (xEM)']:.2f}x" if r["מרחק (xEM)"] is not None else "—"
                    )),
                    ("עניין פתוח / נפח", lambda r: (
                        f"{'✅' if r['נזילות'] == 'תקינה' else '⚠️'} "
                        f"{int(r['עניין פתוח'])} / {int(r['נפח'])}"
                    )),
                ]
                _thead = "<th></th>" + "".join(
                    f"<th>סטרייק {r['סטרייק']:g}</th>" for r in _rows_for_ticker
                )
                _trs = ""
                for _label, _fmt in _metric_rows:
                    _tds = "".join(f"<td>{_fmt(r)}</td>" for r in _rows_for_ticker)
                    _trs += f"<tr><td>{_label}</td>{_tds}</tr>"
                st.markdown(
                    f'<table class="rs-table"><thead><tr>{_thead}</tr></thead>'
                    f'<tbody>{_trs}</tbody></table>',
                    unsafe_allow_html=True,
                )

                del_col1, del_col2 = st.columns([3, 1])
                with del_col1:
                    _strike_to_delete = st.selectbox(
                        "מחיקת שורה - בחרי סטרייק",
                        options=[r["סטרייק"] for r in _rows_for_ticker],
                        key=f"{key_prefix}_compare_del_select",
                    )
                with del_col2:
                    st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
                    if st.button("🗑️ מחק", key=f"{key_prefix}_compare_del_btn"):
                        st.session_state[_compare_key] = [
                            r for r in st.session_state[_compare_key]
                            if not (r["טיקר"] == ticker and r["סטרייק"] == _strike_to_delete)
                        ]
                        st.rerun()

            # --- פערי מודלים - עובדה, לא ציון ------------------------------
            if len(available_for_diff) >= 2:
                spread = max(available_for_diff.values()) - min(available_for_diff.values())
                cls = "red" if spread > 0.15 else ("yellow" if spread > 0.05 else "gray")
                txt = f"פער בין המודלים: {spread:.1%}"
                st.markdown(f'<span class="rs-badge {cls}">{txt}</span>', unsafe_allow_html=True)
                if spread > 0.15:
                    st.markdown(
                        '<div class="rs-explain" style="margin-top:8px;">'
                        'המודלים חלוקים ביותר מ-15 נקודות אחוז - זה סימן לאי-ודאות '
                        'גבוהה, לא לכך שאחד מהם "נכון" והשאר טועים.'
                        '</div>',
                        unsafe_allow_html=True,
                    )


        st.markdown('<hr style="border-color: rgba(255,255,255,.08); margin: 24px 0;">', unsafe_allow_html=True)
        st.markdown(
            '<div class="rs-explain" style="margin-bottom:12px;">'
            '🛡️ <b>צד ההגנה (קניית פוט)</b>: כמה הגנה בדולרים נותן פוט מגן על מניות             שכבר מחזיקים, בכל תרחיש ירידה. לא תלוי בחישוב ההסתברות למעלה - קלט נפרד.'
            '</div>',
            unsafe_allow_html=True,
        )
        prot_cols = st.columns(4)
        with prot_cols[0]:
            prot_shares = st.number_input("מניות מוחזקות", min_value=1, value=100,
                                           key=f"{key_prefix}_prot_shares", help=_HELP["prot_shares"])
        with prot_cols[1]:
            prot_entry = st.number_input("מחיר עלות המניה", min_value=0.01, value=float(round(spot_default, 2)),
                                          key=f"{key_prefix}_prot_entry_{ticker}", help=_HELP["prot_entry"])
        with prot_cols[2]:
            prot_strike = st.number_input("סטרייק הפוט המגן", min_value=0.01, value=float(round(spot_default * 0.9, 2)),
                                           key=f"{key_prefix}_prot_strike_{ticker}", help=_HELP["prot_strike"])
        with prot_cols[3]:
            prot_premium = st.number_input("פרמיית הפוט ($)", min_value=0.01, value=5.0,
                                            key=f"{key_prefix}_prot_premium", help=_HELP["iv_price"])
        prot_contracts = st.number_input("מספר חוזי פוט", min_value=1, value=1,
                                          key=f"{key_prefix}_prot_contracts", help=_HELP["contracts"])

        _prot_flag = f"{key_prefix}_prot_show"
        st.markdown(
            '<span class="rs-btn-help" title="משווה מניה בלבד מול מניה+פוט מגן בכל תרחיש ירידה, ומראה כמה דולרים ואיזה אחוז מההפסד הלא-מוגן ההגנה קיזזה.">❓</span>',
            unsafe_allow_html=True,
        )
        if st.button(
            "חשב הגנה", key=f"{key_prefix}_prot_calc",
            help="משווה מניה בלבד מול מניה+פוט מגן בכל תרחיש ירידה, "
                 "ומראה כמה דולרים ואיזה אחוז מההפסד הלא-מוגן ההגנה קיזזה.",
        ) or st.session_state.get(_prot_flag):
            st.session_state[_prot_flag] = True
            cost = insurance_cost(prot_premium, prot_contracts)
            rows = protection_table(
                shares=int(prot_shares), stock_entry=prot_entry, strike=prot_strike,
                premium=prot_premium, contracts=int(prot_contracts),
            )
            grid_prot = [_metric("עלות הביטוח", f"${cost:,.2f}")]
            for row in rows:
                label = f"{row.pct_move:+.0%} (${row.stressed_price:,.0f})"
                if row.protection_pct is not None:
                    value = f"${row.protection_amount:,.2f} ({row.protection_pct:+.0%})"
                else:
                    value = f"${row.protection_amount:,.2f} (אין הפסד ללא הגנה)"
                grid_prot.append(_metric(label, value))
            prot_explain = (
                '<div class="rs-explain">כל תא: כמה הפוט המגן שיפר את התוצאה לעומת '
                'מניה בלבד, באותו תרחיש (בסוגריים: % מההפסד הלא-מוגן שקוזז). ליד/מעל '
                'הסטרייק זה יכול להיות שלילי - שילמת פרמיה לפני שההגנה נכנסה לתוקף, '
                'זה תקין ולא שגיאה.</div>'
            )
            _card("טבלת הגנה", f'<div class="rs-grid">{"".join(grid_prot)}</div>{prot_explain}')

    with tab_screener:
        st.markdown(
            '<div class="rs-explain" style="margin-bottom:12px;">'
            'מריץ את המודל, ההסתברויות, ה-CVaR וה-RV Rank על רשימת טיקרים בבת אחת, '
            'בדלתא יעד אחידה לכולם (כך ההשוואה בין מניות שונות הוגנת - אותו "עומק" '
            'יחסי, לא סטרייק דולרי קבוע). פרמיית הפוט בטבלה תיאורטית (Black-Scholes), '
            'לא מחיר שוק בפועל.'
            '</div>',
            unsafe_allow_html=True,
        )

        with st.expander("📖 מדריך: מה המטרה של הטבלה, ומאיפה המספרים מגיעים"):
            st.markdown(
                '<div class="rs-explain">'
                '<b>מה זה בכלל עושה?</b><br>'
                'לוקח רשימת מניות שאת נותנת, ומריץ על כל אחת את אותה שאלה בדיוק: '
                '"אם הייתי כותבת (מוכרת) Put על המניה הזו, בסטרייק שנמצא באותו '
                '\'מרחק יחסי\' מהמחיר הנוכחי (נקבע לפי הדלתא שבחרת), מה היו '
                'המספרים?" המטרה היא להשוות הרבה מניות זו לזו במבט אחד - לא לומר '
                'איזו לבחור.<br><br>'
                '<b>מאיפה מגיעה "פרמיה תיאורטית"?</b><br>'
                'מנוסחה מתמטית ידועה (Black-Scholes) - אותה נוסחה שגם עושי-שוק '
                'משתמשים בה כנקודת פתיחה לתמחור אופציות. היא מקבלת 5 מספרים: מחיר '
                'המניה כרגע, הסטרייק, כמה ימים נשארו לפקיעה, כמה תנועה השוק מצפה '
                'מהמניה (IV, נשלף מהשוק האמיתי), וריבית חסרת סיכון - ומחשבת מהם '
                '"מחיר הוגן" תיאורטי.<br><br>'
                '<b>למה זה "עקבי להשוואה" אם זה לא המחיר האמיתי?</b><br>'
                'כמו למדוד כמה חדרים באותו סרגל בדיוק - ההשוואה ביניהם אמינה, גם '
                'אם הסרגל עצמו סוטה קצת מהמטר האמיתי. אותה נוסחה, באותה לוגיקה, '
                'מופעלת על כל מניה בטבלה בלי יוצא מן הכלל - אז השוואה יחסית '
                'ביניהן הגיונית, גם אם המספר המוחלט של כל אחת עלול להיות שונה '
                'ממה שהברוקר יציע בפועל. מחיר שוק אמיתי מושפע גם מדברים שהמודל '
                'לא רואה - כמה קונים/מוכרים יש כרגע על החוזה הספציפי, וכמה '
                '"עמלת תיווך" (bid-ask spread) השוק גובה.<br><br>'
                '<b>המסקנה המעשית:</b> אפשר לסמוך על הטבלה כדי לצמצם רשימה ארוכה '
                'למועמדות שכדאי לבדוק לעומק - אבל לפני שסוגרים עסקה בפועל, תמיד '
                'פותחים את שרשרת האופציות האמיתית אצל הברוקר ובודקים את המחיר '
                'בפועל.'
                '</div>',
                unsafe_allow_html=True,
            )

        _scr_pending_key = f"{key_prefix}_scr_tickers_pending"
        if _scr_pending_key in st.session_state:
            # מותר לכתוב ל-session_state של ה-widget רק *לפני* שהוא נוצר -
            # זו בדיוק הנקודה הזו, עוד לפני קריאת st.text_area שמתחת.
            st.session_state[f"{key_prefix}_scr_tickers"] = st.session_state.pop(_scr_pending_key)

        scr_tickers_raw = st.text_area(
            "טיקרים (מופרדים בפסיק או בשורות נפרדות)",
            value="AAPL, MSFT, NVDA",
            key=f"{key_prefix}_scr_tickers",
        )

        wl_cols = st.columns(4)
        with wl_cols[0]:
            if st.button("💾 שמרי לרשימת המעקב שלי", key=f"{key_prefix}_scr_wl_save"):
                current = [
                    t.strip().upper()
                    for chunk in scr_tickers_raw.split("\n")
                    for t in chunk.split(",") if t.strip()
                ]
                merged = sorted(set(_load_screener_watchlist()) | set(current))
                _save_screener_watchlist(merged)
                st.success(f"נשמרו. סה\"כ ברשימת המעקב: {len(merged)} טיקרים.")
        with wl_cols[1]:
            if st.button("📋 טעני מרשימת המעקב שלי", key=f"{key_prefix}_scr_wl_load"):
                saved = _load_screener_watchlist()
                if saved:
                    st.session_state[_scr_pending_key] = ", ".join(saved)
                    st.rerun()
                else:
                    st.info("רשימת המעקב ריקה עדיין.")
        with wl_cols[2]:
            if st.button("🗑️ נקי את רשימת המעקב", key=f"{key_prefix}_scr_wl_clear"):
                _save_screener_watchlist([])
                st.success("רשימת המעקב נוקתה.")
        with wl_cols[3]:
            if st.button("📥 טעני מה-Watchlist הראשי", key=f"{key_prefix}_scr_wl_main"):
                main_wl = st.session_state.get("watchlist", [])
                if main_wl:
                    st.session_state[_scr_pending_key] = ", ".join(main_wl)
                    st.rerun()
                else:
                    st.info("ה-Watchlist הראשי ריק.")

        _current_wl = _load_screener_watchlist()
        if _current_wl:
            st.caption(f"ברשימת המעקב שלך כרגע: {', '.join(_current_wl)}")

        scr_cols = st.columns(3)
        with scr_cols[0]:
            scr_delta = st.number_input(
                "דלתא יעד לפוט", min_value=0.05, max_value=0.50, value=0.20, step=0.05,
                key=f"{key_prefix}_scr_delta",
                help=(
                    "|דלתא| ≈ ההסתברות (הניטרלית-סיכון) שהאופציה תיגמר בתוך הכסף. "
                    "0.30-0.40: קרוב לכסף - פרמיה גבוהה יותר, וסיכוי גבוה יותר שהסטרייק ייפגע. "
                    "0.15-0.20: טווח מקובל למכירת פרמיה מתונה. "
                    "0.05-0.10: רחוק מהכסף - פרמיה קטנה, סיכוי גבוה לפקיעה חסרת ערך. "
                    "הבחירה תלויה במטרה (הכנסה מול הגנה) ובסובלנות לסיכון - "
                    "אין כאן ערך אחד שהוא 'נכון'."
                ),
            )
        with scr_cols[1]:
            scr_dte, _scr_exp = _expiry_input(
                "תאריך פקיעה", f"{key_prefix}_scr_exp", "", help=_HELP["days"],
            )
        with scr_cols[2]:
            scr_period = st.selectbox(
                "עומק היסטוריה (RV/CVaR)", ["5y", "10y", "max"], index=1,
                key=f"{key_prefix}_scr_period",
            )

        _scr_key = f"{key_prefix}_scr_results"
        if st.button("🔍 סרוק", key=f"{key_prefix}_scr_run"):
            raw_list = [t for chunk in scr_tickers_raw.split("\n") for t in chunk.split(",")]
            with st.spinner("סורקת..."):
                st.session_state[_scr_key] = _run_screener(
                    raw_list, target_put_delta=scr_delta,
                    dte_days=int(scr_dte), closes_period=scr_period,
                )

        if _scr_key in st.session_state:
            import pandas as pd
            scr_df = st.session_state[_scr_key]
            if scr_df.empty:
                st.info("לא הוזנו טיקרים תקינים.")
            else:
                _scr_all_iv_missing = "iv" in scr_df.columns and scr_df["iv"].isna().all()
                if _scr_all_iv_missing:
                    st.warning(
                        "⚠️ לא נמצא IV חי (מחיר אופציות מהשוק) לאף אחד מהטיקרים שנסרקו - "
                        "לכן שדות כמו סטרייק, פרמיה והסתברויות OTM לא חושבו, וטיקרים אלה "
                        "מוסתרים כברירת מחדל. יתכן שהשוק האמריקאי סגור כרגע - שעות המסחר "
                        "הן כ-15:30–22:00 שעון ישראל (עשוי לזוז שעה לפי שעון קיץ/חורף בארה\"ב). "
                        "אפשר גם להוריד את הסימון מ-\"הסתר טיקרים שנכשלו\" למטה כדי לראות "
                        "את השורות הגולמיות."
                    )

                filt_cols = st.columns(2)
                with filt_cols[0]:
                    hide_failed = st.checkbox(
                        "הסתר טיקרים שנכשלו", value=True, key=f"{key_prefix}_scr_hide_failed",
                    )
                with filt_cols[1]:
                    rv_range = st.slider(
                        "RV Rank (טווח)", 0, 100, (0, 100), key=f"{key_prefix}_scr_rv_range",
                        help="מסנן לפי rv_rank. טיקרים ללא ערך (למשל נכשלו) לא מודרים בגלל הטווח.",
                    )

                scr_view = scr_df.copy()
                if hide_failed and "strike" in scr_view.columns:
                    scr_view = scr_view[scr_view["strike"].notna()]
                if "rv_rank" in scr_view.columns:
                    scr_view = scr_view[
                        scr_view["rv_rank"].isna()
                        | scr_view["rv_rank"].between(rv_range[0], rv_range[1])
                    ]

                _sortable = [c for c in [
                    "ticker", "spot", "strike", "iv", "rv_rank", "rv_percentile",
                    "iv_rv_spread", "expected_move_pct", "put_premium", "put_delta",
                    "breakeven", "prob_otm_model", "prob_otm_fat_tail",
                    "prob_otm_historical", "xem_distance", "cvar_5pct", "max_loss",
                ] if c in scr_view.columns]

                _scr_metric_labels = {
                    "ticker": "טיקר", "spot": "מחיר", "strike": "סטרייק", "iv": "IV",
                    "rv_rank": "RV Rank", "rv_percentile": "RV Percentile",
                    "iv_rv_spread": "IV-RV (הפרש)", "expected_move_pct": "תזוזה צפויה (%)",
                    "put_premium": "פרמיית הפוט", "put_delta": "דלתא בפועל",
                    "breakeven": "Breakeven", "prob_otm_model": "הסתברות OTM - מודל",
                    "prob_otm_fat_tail": "הסתברות OTM - Fat-tail",
                    "prob_otm_historical": "הסתברות OTM - היסטורי", "xem_distance": "מרחק (xEM)",
                    "cvar_5pct": "CVaR (5% הגרועים)", "max_loss": "הפסד מקסימלי",
                }
                _scr_metric_explain = {
                    "ticker": "סימול המניה.",
                    "spot": "מחיר המניה הנוכחי בשוק.",
                    "strike": "מחיר המימוש שנבחר לפי הדלתא היעד שהוגדרה למעלה.",
                    "iv": "תנודתיות גלומה - כמה תנועה השוק מצפה, לפי מחיר האופציה בפועל.",
                    "rv_rank": "דירוג התנודתיות שהמניה הראתה בפועל (0-100) ביחס לטווח שלה. תחליף זמני ל-IV Rank.",
                    "rv_percentile": "אחוז הימים בהיסטוריה שבהם ה-RV היה נמוך מהערך הנוכחי.",
                    "iv_rv_spread": "ההפרש בין IV ל-RV. חיובי = השוק מתמחר יותר תנודתיות ממה שקרה בפועל.",
                    "expected_move_pct": "התזוזה הצפויה עד הפקיעה, כאחוז מהמחיר הנוכחי (סטיית תקן אחת).",
                    "put_premium": "פרמיית הפוט התיאורטית (Black-Scholes) - לא מחיר שוק בפועל.",
                    "put_delta": "הדלתא בפועל של הסטרייק שנבחר - אמורה להיות קרובה לדלתא היעד שהוגדרה.",
                    "breakeven": "המחיר שמתחתיו מוכר הפוט מתחיל להפסיד בפועל (סטרייק פחות פרמיה).",
                    "prob_otm_model": "הסתברות (Black-Scholes) שהאופציה תפקע מחוץ לכסף.",
                    "prob_otm_fat_tail": "אותה הסתברות OTM, לפי מודל עם \'זנבות שמנים\' (t-Student) במקום נורמלית.",
                    "prob_otm_historical": "הסתברות OTM לפי מה שקרה בפועל בהיסטוריה, לא לפי מודל תיאורטי.",
                    "xem_distance": "כמה \'תזוזות צפויות\' רחוק הסטרייק מהמחיר הנוכחי.",
                    "cvar_5pct": "ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר, לתקופה עד תאריך הפקיעה שנבחר.",
                    "max_loss": "ההפסד המקסימלי התיאורטי בפוזיציה (סטרייק פחות פרמיה, כפול 100 כפול חוזים).",
                }

                with st.expander("📖 הסבר לכל המדדים ברשימה"):
                    _legend_html = "".join(
                        f'<div class="rs-explain" style="margin-bottom:6px;">'
                        f'<b>{_scr_metric_labels.get(c, c)}</b>: {_scr_metric_explain.get(c, "")}'
                        f'</div>'
                        for c in _sortable
                    )
                    st.markdown(_legend_html, unsafe_allow_html=True)

                sort_ui = st.columns([2, 1])
                with sort_ui[0]:
                    sort_by = st.selectbox(
                        "מיין לפי", _sortable, index=0, key=f"{key_prefix}_scr_sort_by",
                        format_func=lambda c: _scr_metric_labels.get(c, c),
                    )
                with sort_ui[1]:
                    sort_desc = st.checkbox("יורד", value=False, key=f"{key_prefix}_scr_sort_desc")
                st.caption(_scr_metric_explain.get(sort_by, ""))
                scr_view = scr_view.sort_values(sort_by, ascending=not sort_desc, na_position="last")

                st.download_button(
                    "⬇️ CSV", data=scr_view.to_csv(index=False).encode("utf-8-sig"),
                    file_name="riskshield_screener.csv", mime="text/csv",
                    key=f"{key_prefix}_scr_export",
                )

                _scr_headers = {
                    "ticker": "טיקר", "spot": "מחיר", "strike": "סטרייק", "iv": "IV",
                    "rv_rank": "RV Rank", "rv_percentile": "RV %", "iv_rv_spread": "IV-RV",
                    "expected_move_pct": "EM %", "put_premium": "פרמיה", "put_delta": "דלתא",
                    "breakeven": "Breakeven", "prob_otm_model": "OTM מודל",
                    "prob_otm_fat_tail": "OTM Fat-tail", "prob_otm_historical": "OTM היסטורי",
                    "xem_distance": "xEM", "cvar_5pct": "CVaR", "max_loss": "Max Loss",
                    "note": "הערה",
                }
                _shown = [c for c in _scr_headers if c in scr_view.columns]
                _thead = "".join(
                    f'<th title="{_scr_metric_explain.get(c, "")}">{_scr_headers[c]}</th>'
                    for c in _shown
                )

                def _scr_fmt(col, val):
                    if val is None or (isinstance(val, float) and pd.isna(val)):
                        return "—"
                    if col in ("spot", "strike", "put_premium", "breakeven", "cvar_5pct", "max_loss"):
                        return f"${val:,.2f}"
                    if col in ("iv", "expected_move_pct", "prob_otm_model",
                               "prob_otm_fat_tail", "prob_otm_historical"):
                        return f"{val:.1%}"
                    if col in ("rv_rank", "rv_percentile"):
                        return f"{val:.0f}"
                    if col == "iv_rv_spread":
                        return f"{val:+.1%}"
                    if col in ("put_delta", "xem_distance"):
                        return f"{val:.2f}"
                    return str(val)

                _trs = ""
                for _, _r in scr_view.iterrows():
                    _tds = "".join(f"<td>{_scr_fmt(c, _r.get(c))}</td>" for c in _shown)
                    _trs += f"<tr>{_tds}</tr>"

                st.markdown(
                    f'<div style="overflow-x:auto;"><table class="rs-table">'
                    f'<thead><tr>{_thead}</tr></thead><tbody>{_trs}</tbody></table></div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"{len(scr_view)} מתוך {len(scr_df)} טיקרים מוצגים.")

    with tab_tracker:
        render_put_tracker_tab()

    st.markdown('</div>', unsafe_allow_html=True)
