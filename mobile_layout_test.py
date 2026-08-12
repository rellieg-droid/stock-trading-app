"""
Alpha Charts Pro — MOBILE LAYOUT TEST PAGE
Standalone test of the mobile mockup design, isolated from the main app.
Bottom nav = 5 top-level groups (real navigation, switches page content).
Top pill row = sub-tabs within the selected group.
Run separately to validate before porting into alpha_paper_trading.py.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_option_menu import option_menu

# ──────────────────────────────────────────────────────────────────────────
# PAGE CONFIG — fixed mobile width
# ──────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Alpha Charts Pro — Mobile Test",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────────
# NAV STRUCTURE — bottom nav groups → top pill sub-tabs
# ──────────────────────────────────────────────────────────────────────────

NAV_GROUPS = {
    "בית":    {"icon": "house",          "subs": ["בית"]},
    "גרף":    {"icon": "graph-up",       "subs": ["גרף"]},
    "ניתוח":  {"icon": "cpu",            "subs": ["ניתוח", "השוואה"]},
    "מסחר":   {"icon": "cart",           "subs": ["מסחר", "תיק"]},
    "עוד":    {"icon": "three-dots",     "subs": ["Backtest", "התראות", "דוחות", "Watchlist", "מדריך"]},
}
GROUP_ORDER = ["בית", "גרף", "ניתוח", "מסחר", "עוד"]
GROUP_BOTTOM_ICONS = {"בית": "🏠", "גרף": "📈", "ניתוח": "🎯", "מסחר": "🛒", "עוד": "⋯"}

# ──────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ──────────────────────────────────────────────────────────────────────────

C = {
    "bg": "#0B0F17",
    "bg_top": "#10151F",
    "card": "rgba(255, 255, 255, 0.035)",
    "card_border": "rgba(255, 255, 255, 0.07)",
    "text": "#F2F4F8",
    "text_dim": "#8A93A6",
    "text_faint": "#5B6377",
    "green": "#2BD46B",
    "green_soft": "rgba(43, 212, 107, 0.12)",
    "green_border": "rgba(43, 212, 107, 0.30)",
    "red": "#F5454F",
    "blue": "#3D7CFF",
    "blue_soft": "rgba(61, 124, 255, 0.16)",
    "gold": "#E8B84B",
    "divider": "rgba(255,255,255,0.06)",
}

RADIUS = "18px"
RADIUS_SM = "14px"
RADIUS_PILL = "999px"


def inject_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Hebrew:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{ font-family: 'Inter', 'Noto Sans Hebrew', sans-serif; }}

        .stApp {{
            background: linear-gradient(180deg, {C['bg_top']} 0%, {C['bg']} 220px);
            color: {C['text']};
        }}

        #MainMenu, footer, header {{ visibility: hidden; }}
        div[data-testid="stToolbar"] {{ visibility: hidden; }}
        div[data-testid="stDecoration"] {{ display: none; }}

        /* Fixed mobile-width frame, centered on any screen */
        .block-container {{
            padding-top: 0.6rem;
            padding-bottom: 5.5rem;
            max-width: 1100px;
            width: 100%;
            margin: 0 auto;
            min-height: 100vh;
        }}

        .mono {{ font-family: 'JetBrains Mono', monospace; font-feature-settings: "tnum"; }}
        .rtl {{ direction: rtl; text-align: right; unicode-bidi: embed; }}

        /* ===== TOP BAR ===== */
        .topbar {{ display: flex; align-items: center; justify-content: space-between; padding: 0.3rem 0.1rem 0.7rem 0.1rem; }}
        .topbar-left {{ display: flex; align-items: center; gap: 0.6rem; }}
        .topbar-title {{ font-size: 1.0rem; font-weight: 700; color: {C['text']}; display: flex; align-items: center; gap: 0.3rem; }}
        .topbar-icons {{ display: flex; align-items: center; gap: 0.85rem; color: {C['text_dim']}; font-size: 1.0rem; }}
        .hamburger {{ font-size: 1.15rem; color: {C['text']}; }}

        /* ===== GLASS CARD ===== */
        .gcard {{
            background: {C['card']};
            border: 1px solid {C['card_border']};
            border-radius: {RADIUS};
            backdrop-filter: blur(18px) saturate(140%);
            -webkit-backdrop-filter: blur(18px) saturate(140%);
            box-shadow: 0 6px 24px rgba(0,0,0,0.4);
            box-shadow: 0 6px 24px rgba(0,0,0,0.4);
            padding: 1rem 1.05rem;
        }}

        /* ===== TICKER HEADER ===== */
        .ticker-card {{ padding: 1.05rem 1.1rem 1.2rem 1.1rem; }}
        .ticker-top-row {{ display: flex; align-items: flex-start; justify-content: space-between; }}
        .ticker-id-block {{ display: flex; align-items: center; gap: 0.55rem; }}
        .ticker-logo {{
            width: 38px; height: 38px; border-radius: 50%;
            background: {C['blue_soft']}; color: {C['blue']};
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 0.8rem;
            border: 1px solid rgba(61,124,255,0.35); flex-shrink: 0;
        }}
        .ticker-name-main {{ font-size: 0.92rem; font-weight: 700; color: {C['text']}; line-height: 1.25; }}
        .ticker-name-sub {{ font-size: 0.72rem; color: {C['text_faint']}; margin-top: 0.1rem; }}
        .ticker-actions {{ display: flex; gap: 0.6rem; color: {C['text_dim']}; font-size: 0.95rem; }}
        .price-hero {{ font-size: 2.7rem; font-weight: 800; letter-spacing: -0.02em; margin: 0.55rem 0 0.15rem 0; line-height: 1; }}
        .price-change-pill {{ display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.92rem; font-weight: 700; }}
        .price-change-pill.down {{ color: {C['red']}; }}
        .price-change-pill.up {{ color: {C['green']}; }}
        .price-timestamp {{ color: {C['text_faint']}; font-size: 0.74rem; margin-top: 0.45rem; }}
        .day-range-row {{ display: flex; justify-content: space-between; margin-top: 0.85rem; padding-top: 0.85rem; border-top: 1px solid {C['divider']}; }}
        .day-range-block {{ text-align: right; }}
        .day-range-label {{ font-size: 0.68rem; color: {C['text_faint']}; margin-bottom: 0.15rem; }}
        .day-range-value {{ font-size: 0.84rem; font-weight: 600; color: {C['text']}; }}

        /* ===== AI CARD ===== */
        .ai-card {{
            background: linear-gradient(160deg, rgba(43,212,107,0.16) 0%, rgba(43,212,107,0.04) 55%, rgba(255,255,255,0.02) 100%);
            border: 1px solid {C['green_border']};
            border-radius: {RADIUS};
            padding: 1.0rem 1.05rem 1.1rem 1.05rem;
            backdrop-filter: blur(18px);
        }}
        .ai-card-header {{ display: flex; align-items: center; justify-content: space-between; }}
        .ai-card-label {{ font-size: 0.7rem; font-weight: 700; color: {C['text_dim']}; letter-spacing: 0.04em; }}
        .ai-icon-circle {{
            width: 46px; height: 46px; border-radius: 50%; background: {C['green']};
            display: flex; align-items: center; justify-content: center; font-size: 1.3rem;
            color: #06210F; box-shadow: 0 0 0 6px rgba(43,212,107,0.10); margin: 0.3rem auto 0.5rem auto;
        }}
        .ai-verdict {{ text-align: center; font-size: 1.15rem; font-weight: 800; color: {C['green']}; margin-bottom: 0.55rem; }}
        .ai-confidence-label {{ text-align: center; font-size: 0.74rem; color: {C['text_dim']}; font-weight: 600; margin-bottom: 0.3rem; }}
        .ai-confidence-track {{ width: 100%; height: 6px; border-radius: 4px; background: rgba(255,255,255,0.08); overflow: hidden; margin-bottom: 0.85rem; }}
        .ai-confidence-fill {{ height: 100%; background: linear-gradient(90deg, #1FAE54, {C['green']}); border-radius: 4px; }}
        .ai-reasons-label {{ font-size: 0.72rem; font-weight: 700; color: {C['text_dim']}; margin-bottom: 0.45rem; }}
        .ai-reason-item {{ display: flex; align-items: flex-start; justify-content: flex-end; gap: 0.4rem; font-size: 0.73rem; color: {C['text']}; line-height: 1.4; margin-bottom: 0.4rem; }}
        .ai-reason-check {{ color: {C['green']}; font-size: 0.78rem; margin-top: 0.05rem; flex-shrink: 0; }}
        .ai-full-link {{ text-align: center; font-size: 0.74rem; font-weight: 700; color: {C['green']}; margin-top: 0.3rem; }}

        /* ===== MINI CHART ===== */
        .chart-card {{ padding: 0.95rem 0.95rem 0.6rem 0.95rem; }}
        /* ===== FULL CHART PAGE ===== */
        .chart-page-card {{
            background: {C['card']};
            border: 1px solid {C['card_border']};
            border-radius: {RADIUS};
            backdrop-filter: blur(18px) saturate(140%);
            box-shadow: 0 6px 24px rgba(0,0,0,0.4);
            padding: 1rem 1.1rem 0.8rem 1.1rem;
        }}

        .tf-btn-row {{
            display: flex;
            gap: 0.3rem;
            margin-bottom: 0.8rem;
            flex-wrap: nowrap;
        }}

        .tf-btn {{
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.3rem 0.65rem;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            color: {C['text_dim']};
            background: rgba(255,255,255,0.05);
            transition: all 0.15s ease;
            white-space: nowrap;
        }}
        .tf-btn.active {{
            background: {C['blue']};
            color: #fff;
        }}

        .chart-ticker-row {{
            display: flex;
            align-items: baseline;
            gap: 0.7rem;
            margin-bottom: 0.5rem;
        }}
        .chart-ticker-sym {{
            font-size: 0.82rem;
            font-weight: 700;
            color: {C['text_dim']};
        }}
        .chart-ticker-price {{
            font-size: 1.4rem;
            font-weight: 800;
            color: {C['text']};
            font-family: 'JetBrains Mono', monospace;
        }}
        .chart-ticker-change {{
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .chart-ticker-change.down {{ color: {C['red']}; }}
        .chart-ticker-change.up {{ color: {C['green']}; }}

        /* ===== SECTION LABEL ===== */
        .sec-label {{ font-size: 0.74rem; font-weight: 700; color: {C['text_dim']}; margin-bottom: 0.7rem; }}
        .sec-link {{ font-size: 0.7rem; font-weight: 600; color: {C['text_faint']}; text-align: center; margin-top: 0.55rem; }}

        /* ===== STAT LIST ===== */
        .stat-row {{ display: flex; align-items: center; justify-content: space-between; padding: 0.42rem 0; }}
        .stat-name {{ font-size: 0.74rem; color: {C['text_dim']}; font-weight: 500; }}
        .stat-value {{ font-size: 0.78rem; font-weight: 700; color: {C['text']}; }}
        .stat-value.green {{ color: {C['green']}; }}
        .stat-value.red {{ color: {C['red']}; }}
        .stat-value.gold {{ color: {C['gold']}; }}

        /* ===== ALPHA GAUGE CARD ===== */
        .alpha-card {{ text-align: center; padding: 1rem 0.7rem 0.8rem 0.7rem; }}
        .alpha-title {{ font-size: 0.78rem; font-weight: 700; color: {C['text']}; display: flex; align-items: center; justify-content: center; gap: 0.3rem; margin-bottom: 0.3rem; }}
        .alpha-score-sub {{ font-size: 0.68rem; color: {C['text_faint']}; margin-top: -0.6rem; margin-bottom: 0.4rem; }}
        .sub-bar-row {{ display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.32rem; }}
        .sub-bar-label {{ font-size: 0.66rem; color: {C['text_dim']}; width: 30px; text-align: right; flex-shrink: 0; }}
        .sub-bar-track {{ flex: 1; height: 5px; border-radius: 3px; background: rgba(255,255,255,0.08); overflow: hidden; }}
        .sub-bar-fill {{ height: 100%; border-radius: 3px; background: {C['green']}; }}
        .sub-bar-value {{ font-size: 0.66rem; color: {C['text_dim']}; width: 20px; flex-shrink: 0; }}

        /* ===== NEWS CARD ===== */
        .news-card {{ display: flex; align-items: center; gap: 0.75rem; padding: 0.85rem 0.95rem; }}
        .news-text {{ flex: 1; }}
        .news-headline {{ font-size: 0.78rem; font-weight: 600; color: {C['text']}; line-height: 1.3; }}
        .news-meta {{ font-size: 0.66rem; color: {C['text_faint']}; margin-top: 0.3rem; }}

        /* ===== PORTFOLIO CARD ===== */
        .portfolio-total-label {{ font-size: 0.7rem; color: {C['text_dim']}; }}
        .portfolio-total-value {{ font-size: 1.15rem; font-weight: 800; color: {C['text']}; margin: 0.15rem 0; }}
        .portfolio-total-delta {{ font-size: 0.72rem; color: {C['green']}; font-weight: 700; }}

        /* ===== TOP PILL NAV (sub-tabs within group) ===== */
        .top-pill-wrap nav[role="tablist"] {{ background: transparent !important; }}

        /* ===== BOTTOM NAV — real navigation via button form ===== */
        .bottom-nav-spacer {{ height: 4.6rem; }}

        div[data-testid="stHorizontalBlock"]:has(.bottom-nav-marker) {{
            position: fixed;
            bottom: 0; left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 1100px;
            background: rgba(13, 17, 26, 0.94);
            backdrop-filter: blur(20px);
            border-top: 1px solid {C['card_border']};
            padding: 0.5rem 0.6rem calc(0.5rem + env(safe-area-inset-bottom, 0px));
            z-index: 999;
            margin: 0 !important;
        }}

        .bottom-nav-btn button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 1.3rem !important;
            color: {C['text_faint']} !important;
            height: 42px !important;
            width: 100% !important;
            padding: 0 !important;
        }}
        .bottom-nav-btn-active button {{
            background: {C['blue_soft']} !important;
            border-radius: 50% !important;
            color: {C['blue']} !important;
            width: 42px !important;
            margin: 0 auto !important;
        }}

        .stTextInput input {{
            background: {C['card']} !important;
            border: 1px solid {C['card_border']} !important;
            border-radius: {RADIUS_SM} !important;
            color: {C['text']} !important;
            font-size: 0.85rem !important;
        }}

        div[data-testid="stHorizontalBlock"] {{ gap: 0.7rem; }}

        @media (max-width: 768px) {{
            .price-hero {{ font-size: 2.3rem; }}
            .block-container {{ padding-left: 0.7rem; padding-right: 0.7rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# DEMO DATA
# ──────────────────────────────────────────────────────────────────────────

def get_snapshot():
    return {
        "symbol": "NVDA", "name": "NVIDIA Corp", "exchange": "NASDAQ",
        "price": 241.30, "change": 7.42, "change_pct": 3.2, "is_up": True,
        "timestamp": "15:42 EDT", "day_low": 235.40, "day_high": 242.80,
        "day_open": 236.10, "prev_close": 233.88, "volume": 42_100_000,
        "ai": {
            "verdict": "קנייה חזקה", "confidence": 82,
            "reasons": [
                "מגמת תשואה ברורה בטווח הקצר ארוך",
                "עלייה בהיקפי המסחר בימים האחרונים",
                "מדדי סיכון בטווח הקצר ארוך נשארים נמוכים",
            ],
        },
        "financials": [
            {"label": "P/E", "value": "19.45"}, {"label": "EPS (TTM)", "value": "10.66"},
            {"label": "Market Cap", "value": "$5.93T"},
            {"label": "Revenue Growth", "value": "12.35%", "sign": "green"},
            {"label": "ROE", "value": "18.72%", "sign": "green"},
            {"label": "Dividend Yield", "value": "1.34%"},
        ],
        "ai_analysis": [
            {"label": "מגמה", "value": "חיובית", "sign": "green"},
            {"label": "סיגנל", "value": "קנייה", "sign": "green"},
            {"label": "עוצמה (RSI)", "value": "58.3"},
            {"label": "התנגדות עליונה", "value": "$198.20"},
            {"label": "התנגדות תחתונה", "value": "$216.80"},
        ],
        "alpha_score": 87,
        "alpha_subscores": [
            {"label": "צמיחה", "value": 92}, {"label": "ערך", "value": 74},
            {"label": "תנופה", "value": 79}, {"label": "סיכון", "value": 91},
        ],
        "portfolio_total": "$12,458.75", "portfolio_delta": "+2.35%",
    }


def generate_price_series(days=3650, start_price=190.0, end_price=207.41, seed=7):
    """Daily series spanning up to MAX (10y) for the 1M/6M/1Y/5Y/MAX views."""
    rng = np.random.default_rng(seed)
    walk = rng.normal(0, 1.3, days).cumsum()
    # Brownian BRIDGE: subtract the straight line between the walk's own
    # start and end values, so the wandering component starts AND ends at
    # exactly 0 on its own. An earlier version anchored only walk[0] and
    # then force-overwrote prices[-1] = end_price afterward — over 3650
    # days the random walk drifts far from the trend line by the end, so
    # that override created a single-bar jump of 40+ (vs a typical daily
    # move of ~0.4), producing one giant candle at the tail of every
    # timeframe that includes today (1M, 6M, YTD, 1Y, 5Y, All all share
    # this same last bar). The bridge makes prices[0]==start_price and
    # prices[-1]==end_price naturally, with no discontinuity anywhere.
    bridge = walk - np.linspace(walk[0], walk[-1], days)
    trend = np.linspace(0, end_price - start_price, days)
    prices = start_price + trend + bridge * 0.4
    # Business days only, normalized to midnight — mirrors real yfinance
    # daily data (no weekend rows, no time-of-day component). Using
    # datetime.today() directly would bake the current clock time (e.g.
    # 10:00 AM) into every candle, which throws off tick-label rendering.
    dates = pd.date_range(end=datetime.today().date(), periods=days, freq="B")
    df = pd.DataFrame({"date": dates, "price": prices})

    # Synthetic OHLC around the close, for candle mode.
    # NOTE: this is mock-only. The production app should use real OHLC from yfinance.
    rng2   = np.random.default_rng(seed + 1000)
    spread = np.abs(rng2.normal(0.35, 0.25, days)) + 0.05
    df["open"] = df["price"].shift(1).fillna(df["price"].iloc[0]) + rng2.normal(0, 0.15, days)
    df["high"] = df[["open", "price"]].max(axis=1) + spread
    df["low"]  = df[["open", "price"]].min(axis=1) - spread
    return df


def generate_multiday_intraday_series(num_days=5, bars_per_day=78, end_price=207.41, seed=21):
    """
    Multi-day intraday series for 5D-style views. Professional platforms
    (Yahoo, TradingView) render "5D" as several trading SESSIONS of
    intraday bars stitched together, not 5 single daily candles — that's
    what makes the chart read proportionally instead of a handful of
    stretched-out candles. Mirrors generate_intraday_series() but repeats
    the pattern across the last `num_days` business days.

    Uses ONE continuous random walk across every bar in every day (not a
    separate walk per day anchored to its own drift value). An earlier
    version anchored each day independently, which only guaranteed
    continuity at each day's OWN close — the first bar of the next day
    could start anywhere, producing a large artificial jump at every
    day boundary instead of a small realistic overnight gap.
    """
    total_bars = num_days * bars_per_day
    rng = np.random.default_rng(seed)
    walk = rng.normal(0, 0.12, total_bars).cumsum()
    walk = walk - walk[-1]  # anchor the whole walk so the very last bar = end_price
    prices = end_price + walk

    session_dates = pd.bdate_range(end=datetime.today().date(), periods=num_days)
    times = []
    for day in session_dates:
        day_open = pd.Timestamp(day).replace(hour=9, minute=30)
        times.extend(pd.date_range(start=day_open, periods=bars_per_day, freq="5min"))

    df = pd.DataFrame({"date": pd.DatetimeIndex(times), "price": prices})

    rng2 = np.random.default_rng(seed + 1000)
    n = total_bars
    spread = np.abs(rng2.normal(0.05, 0.04, n)) + 0.01
    df["open"] = df["price"].shift(1).fillna(df["price"].iloc[0]) + rng2.normal(0, 0.02, n)
    df["high"] = df[["open", "price"]].max(axis=1) + spread
    df["low"]  = df[["open", "price"]].min(axis=1) - spread
    return df


def generate_intraday_series(end_price=207.41, day_open=None, day_low=None, day_high=None, seed=11):
    """
    Minute-resolution single-day series for the 1D view. Walks from
    day_open to end_price and stays within [day_low, day_high] when those
    are supplied — matching the day's stats shown elsewhere in the app
    (stats row, prev-close reference line). Without this, the walk just
    hovered tightly around end_price regardless of the day's real range,
    so the prev_close line (often several dollars away) sat far outside
    the actual candle cluster and squashed every candle into a sliver by
    comparison.
    """
    n = 78  # ~6.5h trading day at 5-minute bars
    if day_open is None:
        day_open = end_price
    day_range = (day_high - day_low) if (day_low is not None and day_high is not None) \
        else (abs(end_price - day_open) or 1.0)

    rng = np.random.default_rng(seed)
    raw_walk = rng.normal(0, 1.0, n).cumsum()
    raw_walk = raw_walk - raw_walk[0]  # anchor the walk so it STARTS at day_open
    raw_span = raw_walk.max() - raw_walk.min()
    # Scale the walk's wander so it uses roughly 60% of the day's declared
    # range, leaving room for the linear trend toward end_price.
    scale = (day_range * 0.6) / raw_span if raw_span > 0 else 1.0

    trend = np.linspace(0, end_price - day_open, n)
    prices = day_open + trend + raw_walk * scale

    if day_low is not None and day_high is not None:
        prices = np.clip(prices, day_low, day_high)
    prices[-1] = end_price  # last bar always matches the current quoted price

    today = datetime.today().replace(hour=9, minute=30, second=0, microsecond=0)
    times = pd.date_range(start=today, periods=n, freq="5min")
    df = pd.DataFrame({"date": times, "price": prices})

    # Synthetic OHLC around the close, for candle mode (mock-only, see note above).
    rng2   = np.random.default_rng(seed + 1000)
    spread = np.abs(rng2.normal(0.05, 0.04, n)) + 0.01
    df["open"] = df["price"].shift(1).fillna(df["price"].iloc[0]) + rng2.normal(0, 0.02, n)
    df["high"] = df[["open", "price"]].max(axis=1) + spread
    df["low"]  = df[["open", "price"]].min(axis=1) - spread
    if day_low is not None and day_high is not None:
        df["high"] = df["high"].clip(upper=day_high + spread.mean())
        df["low"]  = df["low"].clip(lower=day_low - spread.mean())
    return df


# ──────────────────────────────────────────────────────────────────────────
# COMPONENT RENDERERS
# ──────────────────────────────────────────────────────────────────────────

def render_topbar():
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-left">
            <span class="hamburger">☰</span>
            <span class="topbar-title">Alpha Charts Pro 👑</span>
        </div>
        <div class="topbar-icons"><span>🔍</span><span>🔔</span><span>☆</span></div>
    </div>
    """, unsafe_allow_html=True)


def render_ticker_card(s):
    sign_class = "up" if s["is_up"] else "down"
    arrow = "▲" if s["is_up"] else "▼"
    sign_prefix = "+" if s["is_up"] else ""
    st.markdown(f"""
    <div class="gcard ticker-card">
        <div class="ticker-top-row rtl">
            <div class="ticker-actions">☆&nbsp;&nbsp;⤴</div>
            <div class="ticker-id-block">
                <div>
                    <div class="ticker-name-main">{s['symbol']} · {s['name']}</div>
                    <div class="ticker-name-sub">{s['exchange']} 🇺🇸</div>
                </div>
                <div class="ticker-logo">{s['symbol'][:3]}</div>
            </div>
        </div>
        <div class="price-hero mono">${s['price']:.2f}</div>
        <span class="price-change-pill {sign_class} mono">
            {sign_prefix}${abs(s['change']):.2f} ({sign_prefix}{s['change_pct']:.2f}%) {arrow}
        </span>
        <div class="price-timestamp rtl">{s['timestamp']}</div>
        <div class="day-range-row rtl">
            <div class="day-range-block">
                <div class="day-range-label">סגירה קודמת</div>
                <div class="day-range-value mono">${s['prev_close']:.2f}</div>
            </div>
            <div class="day-range-block">
                <div class="day-range-label">טווח יומי</div>
                <div class="day-range-value mono">${s['day_low']:.2f} – ${s['day_high']:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_ai_card(ai):
    reasons_html = "".join([
        f'<div class="ai-reason-item"><span>{r}</span><span class="ai-reason-check">✓</span></div>'
        for r in ai["reasons"]
    ])
    st.markdown(f"""
    <div class="ai-card">
        <div class="ai-card-header rtl"><span>📈</span><span class="ai-card-label">AI · המלצה</span></div>
        <div class="ai-icon-circle">📈</div>
        <div class="ai-verdict">{ai['verdict']}</div>
        <div class="ai-confidence-label">ביטחון {ai['confidence']}%</div>
        <div class="ai-confidence-track"><div class="ai-confidence-fill" style="width:{ai['confidence']}%;"></div></div>
        <div class="ai-reasons-label rtl">סימוכות עיקריות</div>
        <div class="rtl">{reasons_html}</div>
        <div class="ai-full-link">לניתוח מלא ›</div>
    </div>
    """, unsafe_allow_html=True)


TIMEFRAMES     = ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y", "All"]
TIMEFRAME_DAYS = {"1D": 1, "5D": 5, "1W": 5, "1M": 21, "6M": 126, "YTD": None, "1Y": 252, "5Y": 1260, "All": 3650}
TIMEFRAMES_V2  = ["1D", "1W", "1M", "1Y"]  # simplified set for the terminal-style chart layout


def get_tf_slice(df_full, tf, s=None):
    if tf == "1D":
        s = s or {}
        return generate_intraday_series(
            end_price=float(df_full["price"].iloc[-1]),
            day_open=s.get("day_open"), day_low=s.get("day_low"), day_high=s.get("day_high"),
        )
    if tf == "5D":
        return generate_multiday_intraday_series(end_price=float(df_full["price"].iloc[-1]))
    if tf == "1M":
        # Load ~8 months of real daily history so zooming/panning out from
        # the initial 1-month view reveals actual candles instead of dead
        # space. The initial VIEW still only focuses on the most recent
        # ~21 trading days — see the recent_window handling in
        # build_chart_module_fig, which computes the padded initial range
        # from just that recent slice, not this whole 8-month load.
        return df_full.tail(min(168, len(df_full))).copy()
    if tf == "YTD":
        start = pd.Timestamp(datetime.today().year, 1, 1)
        sliced = df_full[df_full["date"] >= start].copy()
        return sliced if len(sliced) > 1 else df_full.tail(30).copy()
    days = TIMEFRAME_DAYS[tf]
    return df_full.tail(min(days, len(df_full))).copy()


def compute_indicators(df_full):
    """RSI(14), MACD(12,26,9), Stochastic %K(14), SMA50/200 — computed on the full daily series
    so the longer-window indicators (SMA200 especially) have enough history."""
    close = df_full["price"]

    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.rolling(14, min_periods=1).mean()
    avg_loss = loss.rolling(14, min_periods=1).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    rsi      = 100 - (100 / (1 + rs))
    rsi_val  = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else 50.0

    ema12       = close.ewm(span=12, adjust=False).mean()
    ema26       = close.ewm(span=26, adjust=False).mean()
    macd_line   = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_val    = float(macd_line.iloc[-1])
    signal_val  = float(signal_line.iloc[-1])
    macd_hist   = macd_val - signal_val

    if "low" in df_full.columns and "high" in df_full.columns:
        low14  = df_full["low"].rolling(14, min_periods=1).min()
        high14 = df_full["high"].rolling(14, min_periods=1).max()
    else:
        low14  = close.rolling(14, min_periods=1).min()
        high14 = close.rolling(14, min_periods=1).max()
    stoch_range = (high14 - low14).replace(0, np.nan)
    stoch_k     = 100 * (close - low14) / stoch_range
    stoch_val   = float(stoch_k.iloc[-1]) if pd.notna(stoch_k.iloc[-1]) else 50.0

    sma50  = float(close.rolling(50, min_periods=1).mean().iloc[-1])
    sma200 = float(close.rolling(200, min_periods=1).mean().iloc[-1])
    last_price = float(close.iloc[-1])

    return {
        "rsi": rsi_val, "macd": macd_val, "macd_signal": signal_val, "macd_hist": macd_hist,
        "stoch": stoch_val, "sma50": sma50, "sma200": sma200, "last_price": last_price,
    }


def build_full_chart(df, s, tf):
    prices = df["price"].values
    dates  = df["date"].values
    n      = len(prices)
    p_min  = float(prices.min())
    p_max  = float(prices.max())
    p_rng  = p_max - p_min or 1.0

    resistance = p_min + p_rng * 0.82
    vwap       = p_min + p_rng * 0.48

    dot_indices = [max(0, int(n * 0.05)), int(n * 0.38), min(n-1, int(n * 0.82))]

    rng      = np.random.default_rng(42)
    vol_raw  = rng.integers(800, 5000, n).astype(float)
    vol_norm = vol_raw / vol_raw.max()

    # Price delta per point, for the tooltip — formatted as strings up front,
    # since Plotly's d3-format spec on customdata isn't reliable across builds.
    price_delta = np.diff(prices, prepend=prices[0])
    price_delta_pct = np.divide(
        price_delta, np.roll(prices, 1), out=np.zeros_like(price_delta), where=prices != 0
    ) * 100
    price_delta_pct[0] = 0.0
    delta_str = np.array([f"{d:+.2f}" for d in price_delta])
    pct_str   = np.array([f"{p:+.2f}" for p in price_delta_pct])
    hover_data = np.column_stack([delta_str, pct_str])

    fig = go.Figure()

    # Price area
    fig.add_trace(go.Scatter(
        x=dates, y=prices, mode="lines",
        line=dict(color=C["green"], width=2.2, shape="spline", smoothing=0.6),
        fill="tozeroy", fillcolor="rgba(43,212,107,0.08)",
        name="Price",
        customdata=hover_data,
        hovertemplate=(
            "<b>$%{y:.2f}</b>  "
            "%{customdata[0]} (%{customdata[1]}%)"
            "<extra></extra>"
        ),
        yaxis="y",
    ))

    # Resistance line (green dashed)
    fig.add_hline(
        y=resistance, line_dash="dot",
        line_color="rgba(43,212,107,0.65)", line_width=1.4,
        annotation_text=f"Target  ${resistance:.2f}",
        annotation_font_color="rgba(43,212,107,0.9)",
        annotation_font_size=10, annotation_position="top right", yref="y",
    )

    # VWAP line (grey dashed)
    fig.add_hline(
        y=vwap, line_dash="dot",
        line_color="rgba(180,185,200,0.45)", line_width=1.2,
        annotation_text=f"VWAP  ${vwap:.2f}",
        annotation_font_color="rgba(180,185,200,0.7)",
        annotation_font_size=10, annotation_position="bottom right", yref="y",
    )

    # Purple signal dots
    fig.add_trace(go.Scatter(
        x=[dates[i] for i in dot_indices],
        y=[float(prices[i]) for i in dot_indices],
        mode="markers",
        marker=dict(color="#A78BFA", size=9, line=dict(color="#1E1B2E", width=1.8)),
        name="Signal",
        hovertemplate="<b>Signal  $%{y:.2f}</b><extra></extra>",
        yaxis="y",
    ))

    # Current price dot (blue)
    fig.add_trace(go.Scatter(
        x=[dates[-1]], y=[float(prices[-1])],
        mode="markers+text",
        marker=dict(color=C["blue"], size=10, line=dict(color="#fff", width=1.8)),
        text=[f"  ${prices[-1]:.2f}"],
        textposition="middle right",
        textfont=dict(size=10, color=C["blue"], family="JetBrains Mono"),
        name="Current",
        hovertemplate=f"<b>Current  ${prices[-1]:.2f}</b><extra></extra>",
        yaxis="y",
    ))

    # Volume bars (green/red per candle direction)
    vol_colors = [
        "rgba(43,212,107,0.45)" if i == 0 or prices[i] >= prices[i-1]
        else "rgba(245,69,79,0.35)"
        for i in range(n)
    ]
    fig.add_trace(go.Bar(
        x=dates, y=vol_norm,
        marker_color=vol_colors, marker_line_width=0,
        name="Volume", yaxis="y2",
        hovertemplate="Vol: %{customdata:,}<extra></extra>",
        customdata=vol_raw,
    ))

    fig.update_layout(
        height=430,
        margin=dict(l=8, r=72, t=14, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0E1730", font_size=12,
                        font_family="Inter", bordercolor=C["card_border"]),
        yaxis=dict(
            domain=[0.18, 1.0], showgrid=True,
            gridcolor="rgba(255,255,255,0.05)", gridwidth=1,
            color=C["text_dim"], tickfont=dict(size=10, family="JetBrains Mono"),
            tickprefix="$", side="right", zeroline=False, tickformat=".2f",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikedash="solid",
            spikethickness=1,
            spikecolor="rgba(167,139,250,0.55)",
        ),
        yaxis2=dict(
            domain=[0, 0.14], showgrid=False,
            showticklabels=False, zeroline=False,
        ),
        xaxis=dict(
            showgrid=False, color=C["text_dim"],
            tickfont=dict(size=10, family="Inter"),
            rangeslider=dict(visible=False), zeroline=False,
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikedash="solid",
            spikethickness=1,
            spikecolor="rgba(167,139,250,0.55)",
        ),
    )
    return fig


def render_full_chart(df_full, s):
    if "chart_tf" not in st.session_state:
        st.session_state.chart_tf = "1D"
    active_tf = st.session_state.chart_tf

    sign_class  = "up" if s["is_up"] else "down"
    sign_prefix = "+" if s["is_up"] else ""
    arrow       = "▲" if s["is_up"] else "▼"

    st.markdown(f"""
    <div class="chart-page-card">
        <div class="chart-ticker-row">
            <span class="chart-ticker-sym">{s['symbol']}</span>
            <span class="chart-ticker-price">${s['price']:.2f}</span>
            <span class="chart-ticker-change {sign_class}">
                {sign_prefix}{s['change']:.2f} ({sign_prefix}{s['change_pct']:.2f}%) {arrow}
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Timeframe buttons
    tf_cols = st.columns(len(TIMEFRAMES))
    for i, tf in enumerate(TIMEFRAMES):
        with tf_cols[i]:
            if st.button(
                tf, key=f"tf_{tf}",
                type="primary" if tf == active_tf else "secondary",
            ):
                st.session_state.chart_tf = tf
                st.rerun()

    df  = get_tf_slice(df_full, active_tf, s)
    fig = build_full_chart(df, s, active_tf)
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="main_chart_click",
        config={
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "resetScale2d"],
            "displaylogo": False,
        },
    )

    selected_points = event.selection.points if event and event.selection else []
    if selected_points:
        pt = selected_points[0]
        if pt.get("curve_number") == 0:  # 0 = ה-trace של המחיר
            idx = pt["point_index"]
            row = df.iloc[idx]
            row_date = pd.to_datetime(row["date"])
            row_price = float(row["price"])
            prev_price = float(df["price"].iloc[idx - 1]) if idx > 0 else row_price
            delta = row_price - prev_price
            delta_pct = (delta / prev_price * 100) if prev_price else 0.0
            sign = "+" if delta >= 0 else ""
            color = C["green"] if delta >= 0 else C["red"]

            st.markdown(f"""
            <div class="t-card" style="margin-top:10px; padding:12px 16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; font-family:'JetBrains Mono';">
                    <div>
                        <div style="color:{C['text_dim']}; font-size:11px;">{row_date.strftime('%d %b %Y  %H:%M')}</div>
                        <div style="color:{C['text']}; font-size:20px; font-weight:600;">${row_price:.2f}</div>
                    </div>
                    <div style="text-align:left; color:{color}; font-size:14px;">
                        {sign}{delta:.2f} ({sign}{delta_pct:.2f}%)
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# CHART MODULE v3 — matches Alpha_Charts_Design_Brief.docx exactly.
# Token values below are the OFFICIAL brief tokens (section 1.1), which differ
# from the C{} dict used elsewhere in this test file. Scoped locally here on
# purpose — do not widen this until the rest of the file is reconciled with
# the brief, see note at the end of this block.
# ──────────────────────────────────────────────────────────────────────────

BRIEF = {
    "bg_base": "#0D1117", "bg_surface": "#161B22", "bg_elevated": "#1C2128",
    "border": "#30363D", "border_strong": "#484F58",
    "text_primary": "#E6EDF3", "text_secondary": "#8B949E", "text_muted": "#484F58",
    "accent": "#1F6FEB", "accent_hover": "#388BFD",
    "positive": "#3FB950", "negative": "#F85149", "info": "#388BFD",
}


def render_chart_title_strip(s):
    """Zone 1 — ticker + name, price + change (largest text on screen), status badge."""
    is_open = "09:30" <= datetime.now().strftime("%H:%M") <= "16:00"
    status_text  = "שוק פתוח" if is_open else "אחרי שעות הפעילות"
    status_color = BRIEF["positive"] if is_open else BRIEF["text_muted"]
    color = BRIEF["positive"] if s["is_up"] else BRIEF["negative"]
    sign  = "+" if s["is_up"] else ""

    st.markdown(f"""
    <div style="display:flex; align-items:baseline; justify-content:space-between;
                flex-wrap:wrap; gap:0.5rem; margin-bottom:0.3rem;">
        <div style="display:flex; align-items:baseline; gap:0.6rem;">
            <span style="font-family:'JetBrains Mono',monospace; font-weight:700;
                        font-size:1rem; color:{BRIEF['text_primary']};">{s['symbol']}</span>
            <span style="font-size:0.7rem; color:{BRIEF['text_secondary']};">{s['name']}</span>
        </div>
        <div style="display:flex; align-items:center; gap:0.6rem;">
            <span style="font-size:0.6rem; color:{status_color}; border:1px solid {BRIEF['border']};
                        border-radius:6px; padding:0.1rem 0.45rem;">{status_text}</span>
            <span style="font-size:0.58rem; color:{BRIEF['text_muted']};">נכון לשעה {s['timestamp']}</span>
        </div>
    </div>
    <div style="display:flex; align-items:baseline; gap:0.7rem; margin-bottom:0.6rem;">
        <span style="font-family:'JetBrains Mono',monospace; font-weight:700;
                    font-size:1.9rem; color:{BRIEF['text_primary']};">${s['price']:.2f}</span>
        <span style="font-family:'JetBrains Mono',monospace; font-weight:600;
                    font-size:0.88rem; color:{color};">
            {sign}{s['change']:.2f} ({sign}{s['change_pct']:.2f}%)
        </span>
    </div>
    """, unsafe_allow_html=True)


def render_chart_range_control():
    """Zone 2 — single-row pill timeframe buttons, one active state.
    Active = solid dark pill. Inactive = plain text, no border/fill.
    Column widths are explicit and small (1) with one large trailing spacer (10) —
    st.columns(N) alone makes every column equal width, which stretches buttons
    apart instead of packing them; this is what actually keeps them compact."""
    if "chart_tf_v3" not in st.session_state:
        st.session_state.chart_tf_v3 = "1D"

    st.markdown(f"""
    <style>
    .st-key-range_control_row button {{
        white-space: nowrap !important;
    }}
    .st-key-range_control_row button[kind="secondary"] {{
        background: transparent !important; border: none !important;
        color: {BRIEF['text_secondary']} !important; font-weight: 500 !important;
        font-size: 0.68rem !important; box-shadow: none !important; padding: 0.2rem 0.4rem !important;
    }}
    .st-key-range_control_row button[kind="primary"] {{
        background: {BRIEF['text_primary']} !important; border: none !important;
        color: {BRIEF['bg_base']} !important; font-weight: 700 !important;
        font-size: 0.68rem !important; border-radius: 999px !important; box-shadow: none !important;
        padding: 0.2rem 0.55rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    tfs = ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y", "Max"]
    tf_map = {"Max": "All"}  # display label vs internal key
    with st.container(key="range_control_row"):
        cols = st.columns([1] * len(tfs) + [10])  # last column absorbs leftover width
        for i, tf_label in enumerate(tfs):
            tf_val = tf_map.get(tf_label, tf_label)
            with cols[i]:
                active = tf_val == st.session_state.chart_tf_v3
                if st.button(tf_label, key=f"tfv3_{tf_val}", type="primary" if active else "secondary"):
                    st.session_state.chart_tf_v3 = tf_val
                    st.rerun()
    return st.session_state.chart_tf_v3


def render_chart_controls_row():
    """Zone 5 (+ chart type) — one real row: line/candle toggle, a thin divider,
    then the opt-in overlay pills. Everything lives in ONE set of weighted columns
    so nothing gets nested inside an already-narrow column and squeezed further."""
    if "chart_type_v3" not in st.session_state:
        st.session_state.chart_type_v3 = "line"
    for key in ("ov_vwap", "ov_ma", "ov_compare"):
        if key not in st.session_state:
            st.session_state[key] = False

    st.markdown(f"""
    <style>
    .st-key-chart_controls_row button {{
        background: transparent !important; border: 1px solid {BRIEF['border']} !important;
        border-radius: 999px !important; color: {BRIEF['text_secondary']} !important;
        font-weight: 400 !important; font-size: 0.7rem !important; box-shadow: none !important;
        padding: 0.15rem 0.6rem !important; white-space: nowrap !important;
    }}
    /* columns 1-2 = line/candle toggle: elevated neutral style when active */
    .st-key-chart_controls_row [data-testid="stColumn"]:nth-of-type(-n+2) button[kind="primary"] {{
        border-color: {BRIEF['border_strong']} !important; color: {BRIEF['text_primary']} !important;
        background: {BRIEF['bg_elevated']} !important; font-weight: 600 !important;
    }}
    /* columns 3-5 = overlay pills: accent-blue style when active */
    .st-key-chart_controls_row [data-testid="stColumn"]:nth-of-type(n+3) button[kind="primary"] {{
        border-color: {BRIEF['accent']} !important; color: {BRIEF['accent_hover']} !important;
        background: rgba(31,111,235,0.08) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    type_opts    = [("line", "קווי"), ("candle", "נרות")]
    overlay_opts = [("ov_vwap", "+ VWAP"), ("ov_ma", "+ MA 50/200"), ("ov_compare", "+ השוואה")]

    with st.container(key="chart_controls_row"):
        # widths: 2 type buttons, 3 overlay buttons, one big trailing spacer
        cols = st.columns([1.1, 1.1, 1.4, 1.6, 1.9, 8])
        for i, (val, label) in enumerate(type_opts):
            with cols[i]:
                active = st.session_state.chart_type_v3 == val
                if st.button(label, key=f"ct_{val}", type="primary" if active else "secondary"):
                    st.session_state.chart_type_v3 = val
                    st.rerun()
        for j, (key, label) in enumerate(overlay_opts):
            with cols[2 + j]:
                active = st.session_state[key]
                if st.button(label, key=f"btn_{key}", type="primary" if active else "secondary"):
                    st.session_state[key] = not active
                    st.rerun()

    overlays = {k: st.session_state[k] for k, _ in overlay_opts}
    return st.session_state.chart_type_v3, overlays


def get_explicit_ticks(dates, active_tf, desired_ticks):
    """
    Builds tickvals/ticktext from the ACTUAL candle dates only (never from
    the padded axis range). Letting Plotly auto-place ticks across a range
    that's mostly empty padding causes ticks to land on dates with no
    candle, which triggers Plotly's date-axis fallback to an inconsistent
    two-row auto format (time on one row, date on the other, format
    changing tick to tick). Explicit tickvals/ticktext sidesteps that
    entirely — every tick sits on a real candle with one fixed format.
    """
    tick_format_map = {
        "1D": "%I:%M %p", "5D": "%d %b '%y", "1M": "%d %b '%y",
        "6M": "%b '%y", "YTD": "%b '%y", "1Y": "%b '%y",
        "5Y": "%Y", "All": "%Y",
    }
    fmt = tick_format_map.get(active_tf, "%d %b")

    dates = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    n = len(dates)
    if n == 0:
        return [], []

    if active_tf == "5D":
        # One tick at the first bar of each trading day, rather than evenly
        # spaced indices — reads as clean per-day markers, matching how
        # professional platforms label a multi-session intraday view.
        day_starts = dates.groupby(dates.dt.date).head(1)
        tickvals = list(day_starts)
        ticktext = [d.strftime(fmt) for d in tickvals]
        return tickvals, ticktext

    k = max(1, min(desired_ticks, n))
    if k == 1:
        idx = [n - 1]
    else:
        idx = sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})

    tickvals = [dates.iloc[i] for i in idx]
    ticktext = [d.strftime(fmt) for d in tickvals]
    return tickvals, ticktext


def get_x_axis_padded_range(dates, active_tf, min_visible_slots=100):
    """
    Prevents candles from stretching to fill the whole chart width when a
    timeframe has few data points relative to the others (e.g. 1M's ~21
    daily candles vs 6M's ~126). Candlestick traces don't support a
    per-trace width or a bargap-style spacing control the way go.Bar does
    — range padding (adding empty space on both sides so the pixels-per-
    day ratio drops) is the only real lever Plotly gives us for this.
    100 keeps 1M closer to 6M's ~126 real candles, without padding so
    aggressively that most of the chart is empty space (e.g. padding to
    390 like 5D's intraday count would leave ~95% of the chart blank).
    """
    dates = pd.to_datetime(pd.Series(dates))
    n = len(dates)
    if n < 2 or n >= min_visible_slots or active_tf == "1D":
        return None

    missing = min_visible_slots - n
    pad_each_side = missing // 2
    if pad_each_side < 1:
        return None

    bday = pd.tseries.offsets.BDay(pad_each_side)
    return [dates.iloc[0] - bday, dates.iloc[-1] + bday]


def build_chart_module_fig(df, chart_type, prev_close, overlays, active_tf="1D"):
    """Zone 3+4 — price canvas (55-70%) + volume subpanel (~15%), sharing the x-axis.
    Baseline = previous close (thin neutral reference line). Crosshair on hover.
    Green/red used ONLY for price direction, volume bars, and overlay accents."""
    dates  = df["date"].values
    closes = df["price"].values
    n      = len(closes)

    # 1M loads 8 months of background data for zoom-out (see get_tf_slice),
    # but the initial view — y-axis range, ticks, and x-axis padding —
    # should still focus on just the most recent trading month. Everything
    # below that needs "what the person sees by default" uses recent_df
    # instead of the full loaded df.
    if active_tf == "1M" and n > TIMEFRAME_DAYS["1M"]:
        recent_df = df.tail(TIMEFRAME_DAYS["1M"])
    else:
        recent_df = df

    price_delta = np.diff(closes, prepend=closes[0])
    price_delta_pct = np.divide(
        price_delta, np.roll(closes, 1), out=np.zeros_like(price_delta), where=closes != 0
    ) * 100
    price_delta_pct[0] = 0.0
    # Formatted as strings up front — Plotly's d3-format spec on customdata isn't reliable.
    delta_str = np.array([f"{d:+.2f}" for d in price_delta])
    pct_str   = np.array([f"{p:+.2f}" for p in price_delta_pct])
    hover_data = np.column_stack([delta_str, pct_str])

    rng      = np.random.default_rng(42)
    vol_raw  = rng.integers(800, 5000, n).astype(float)
    vol_norm = vol_raw / vol_raw.max()
    vol_colors = [
        BRIEF["positive"] if i == 0 or closes[i] >= closes[i - 1] else BRIEF["negative"]
        for i in range(n)
    ]

    fig = go.Figure()

    if chart_type == "candle" and "open" in df.columns:
        fig.add_trace(go.Candlestick(
            x=dates, open=df["open"], high=df["high"], low=df["low"], close=df["price"],
            increasing_line_color=BRIEF["positive"], decreasing_line_color=BRIEF["negative"],
            increasing_fillcolor=BRIEF["positive"], decreasing_fillcolor=BRIEF["negative"],
            name="Price", yaxis="y",
        ))
    else:
        line_color = BRIEF["positive"] if closes[-1] >= prev_close else BRIEF["negative"]
        fig.add_trace(go.Scatter(
            x=dates, y=closes, mode="lines",
            line=dict(color=line_color, width=1.6),
            fill="tozeroy", fillcolor=(
                "rgba(63,185,80,0.06)" if closes[-1] >= prev_close else "rgba(248,81,73,0.06)"
            ),
            name="Price", yaxis="y", customdata=hover_data,
            hovertemplate="<b>$%{y:.2f}</b>  %{customdata[0]} (%{customdata[1]}%)<extra></extra>",
        ))

    # Baseline = previous close, thin neutral reference line
    fig.add_hline(
        y=prev_close, line_dash="dot", line_color=BRIEF["border_strong"], line_width=1,
        annotation_text=f"סגירה קודמת ${prev_close:.2f}", annotation_font_color=BRIEF["text_muted"],
        annotation_font_size=9, annotation_position="bottom left", yref="y",
    )

    if overlays.get("ov_vwap"):
        vwap = float(np.average(closes, weights=vol_raw))
        fig.add_hline(
            y=vwap, line_dash="dash", line_color=BRIEF["info"], line_width=1.2,
            annotation_text=f"VWAP ${vwap:.2f}", annotation_font_color=BRIEF["info"],
            annotation_font_size=9, annotation_position="top left", yref="y",
        )

    if overlays.get("ov_ma") and n >= 5:
        ma_window = min(50, max(2, n // 4))
        ma = pd.Series(closes).rolling(ma_window, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=dates, y=ma, mode="lines",
            line=dict(color=BRIEF["accent_hover"], width=1.2, dash="dot"),
            name=f"MA{ma_window}", yaxis="y", hoverinfo="skip",
        ))

    fig.add_trace(go.Bar(
        x=dates, y=vol_norm, marker_color=vol_colors, marker_line_width=0,
        name="Volume", yaxis="y2",
        hovertemplate="Vol: %{customdata:,}<extra></extra>", customdata=vol_raw,
    ))

    # Tight y-axis range around the actual price data — NOT from zero. "fill=tozeroy"
    # otherwise pulls Plotly's autorange down to 0, which is not how price charts work.
    # Uses recent_df (the initially-visible window) so 1M's 8-month background
    # load doesn't stretch the scale beyond what the last month actually needs.
    price_points = [recent_df["price"].min(), recent_df["price"].max(), prev_close]
    if chart_type == "candle" and "high" in df.columns:
        price_points += [recent_df["high"].max(), recent_df["low"].min()]
    y_min, y_max = min(price_points), max(price_points)
    y_pad = (y_max - y_min) * 0.08 or y_max * 0.01
    y_range = [y_min - y_pad, y_max + y_pad]

    # recent_df (computed above, right after dates/closes) already isolates
    # the initially-visible window for 1M — reuse it here for ticks too.
    recent_dates = recent_df["date"].values

    # X-axis ticks are placed explicitly on real candle dates only (never on
    # the padded blank space) — see get_explicit_ticks() above. Formatting
    # depends on the active range: intraday shows clock time, short ranges
    # show the date, long ranges collapse down to month/year only.
    nticks_map = {"1D": 6, "5D": 5, "1M": 6, "6M": 6, "YTD": 6, "1Y": 6, "5Y": 8, "All": 8}
    x_desired_ticks = nticks_map.get(active_tf, 8)
    x_tickvals, x_ticktext = get_explicit_ticks(recent_dates, active_tf, x_desired_ticks)

    # Skip dead time so the timeline doesn't stretch across non-trading hours —
    # this is what makes professional charts read as continuous. 1D never needs
    # this (single session, no gaps). 5D is intraday across several sessions, so
    # it needs both the overnight hours AND weekends hidden. Daily+ views only
    # need weekends hidden.
    if active_tf == "1D":
        x_rangebreaks = []
    elif active_tf == "5D":
        x_rangebreaks = [dict(bounds=[16, 9.5], pattern="hour"), dict(bounds=["sat", "mon"])]
    else:
        x_rangebreaks = [dict(bounds=["sat", "mon"])]

    # Pads short timeframes (5D etc.) so candles don't stretch to fill the
    # whole canvas — see get_x_axis_padded_range() above. Reuses the same
    # recent_dates slice computed above for ticks (1M's 8-month background
    # load shouldn't affect the initial padded view either).
    x_padded_range = get_x_axis_padded_range(recent_dates, active_tf)

    fig.update_layout(
        height=380,
        margin=dict(l=4, r=64, t=10, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BRIEF["bg_surface"],
        showlegend=False,
        hovermode="x unified",
        bargap=0.25,
        # Every Streamlit rerun rebuilds this figure from scratch (e.g.
        # clicking an overlay toggle). Without uirevision, Plotly treats
        # that as a brand-new chart and resets any manual zoom/pan the
        # person had — it looks like the chart "loses" their zoom.
        # Keying it to active_tf preserves zoom across those reruns, but
        # still resets to the default view when they actually switch
        # timeframe (1D -> 5D etc.), which is the behavior you'd want.
        uirevision=active_tf,
        hoverlabel=dict(bgcolor=BRIEF["bg_elevated"], font_size=10,
                        font_family="JetBrains Mono", bordercolor=BRIEF["border"]),
        xaxis=dict(
            showgrid=False, color=BRIEF["text_secondary"], tickfont=dict(size=9),
            tickmode="array", tickvals=x_tickvals, ticktext=x_ticktext,
            rangebreaks=x_rangebreaks, automargin=True,
            rangeslider=dict(visible=False), zeroline=False,
            range=x_padded_range, autorange=(x_padded_range is None),
            showspikes=True, spikemode="across", spikesnap="cursor",
            spikedash="dot", spikethickness=1, spikecolor=BRIEF["text_secondary"],
        ),
        yaxis=dict(
            domain=[0.18, 1.0], range=y_range, autorange=False,
            showgrid=True, gridcolor="rgba(255,255,255,0.04)", gridwidth=1,
            color=BRIEF["text_secondary"], tickfont=dict(size=9, family="JetBrains Mono"),
            tickprefix="$", side="right", zeroline=False, tickformat=".2f",
            showspikes=True, spikemode="across", spikesnap="cursor",
            spikedash="dot", spikethickness=1, spikecolor=BRIEF["text_secondary"],
        ),
        yaxis2=dict(domain=[0, 0.14], showgrid=False, showticklabels=False, zeroline=False),
    )
    return fig


def render_chart_stats_row(s, df_full):
    """Zone 6 — 2-row x 3-col grid of value/label pairs, tabular monospace figures."""
    market_cap = next((f["value"] for f in s.get("financials", []) if f["label"] == "Market Cap"), "—")
    vol_fmt = f"{s['volume']/1_000_000:.1f}M"

    row1 = [("נמוך", f"{s['day_low']:.2f}"), ("גבוה", f"{s['day_high']:.2f}"), ("פתיחה", f"{s['day_open']:.2f}")]
    row2 = [("שווי שוק", market_cap.lstrip("$")), ("נפח", vol_fmt), ("סגירה קודמת", f"{s['prev_close']:.2f}")]

    def _render_row(items):
        cols = st.columns(3)
        for col, (label, value) in zip(cols, items):
            with col:
                st.markdown(f"""
                <div style="display:flex; align-items:baseline; justify-content:space-between;
                            padding:0.25rem 0; border-top:1px solid {BRIEF['border']};">
                    <span style="font-family:'JetBrains Mono',monospace; font-size:0.76rem;
                                font-weight:700; color:{BRIEF['text_primary']};">{value}</span>
                    <span style="font-size:0.62rem; color:{BRIEF['text_muted']};">{label}</span>
                </div>
                """, unsafe_allow_html=True)

    _render_row(row1)
    _render_row(row2)


def render_chart_page_v3(df_full, s):
    """Orchestrates the full spec-correct chart module (Zones 1-6)."""
    st.markdown(
        f'<div style="background:{BRIEF["bg_surface"]}; border:1px solid {BRIEF["border"]}; '
        f'border-radius:14px; padding:1rem 1.1rem 0.9rem 1.1rem;">',
        unsafe_allow_html=True,
    )

    render_chart_title_strip(s)
    active_tf = render_chart_range_control()

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
    chart_type, overlays = render_chart_controls_row()

    df  = get_tf_slice(df_full, active_tf, s)
    fig = build_chart_module_fig(df, chart_type, s["prev_close"], overlays, active_tf)
    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "resetScale2d"],
        "displaylogo": False,
        "scrollZoom": True,
    })

    st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
    render_chart_stats_row(s, df_full)

    st.markdown("</div>", unsafe_allow_html=True)


def render_mini_chart(df_full):
    """Compact chart used on the Home page — keeps the dropdown selector."""
    st.markdown('<div class="gcard chart-card">', unsafe_allow_html=True)

    tf_options  = ["1D", "1M", "6M", "1Y", "5Y", "All"]
    default_tf  = st.session_state.get("mini_chart_tf", "1Y")
    default_idx = tf_options.index(default_tf) if default_tf in tf_options else 3

    selected_tf = st.selectbox(
        "טווח זמן", options=tf_options, index=default_idx,
        key="mini_chart_tf_select", label_visibility="collapsed",
    )
    st.session_state.mini_chart_tf = selected_tf

    df     = get_tf_slice(df_full, selected_tf)
    prices = df["price"].values
    dates  = df["date"].values

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=prices, mode="lines",
        line=dict(color=C["green"], width=2),
        fill="tozeroy", fillcolor="rgba(43,212,107,0.12)",
    ))
    fig.add_annotation(
        x=dates[-1], y=float(prices[-1]), text=f"{prices[-1]:.2f}", showarrow=False,
        font=dict(size=11, color="#06210F", family="JetBrains Mono"),
        bgcolor=C["green"], bordercolor=C["green"], borderpad=4, xanchor="left",
    )
    fig.update_layout(
        height=210, margin=dict(l=0, r=40, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
        xaxis=dict(showgrid=False, color=C["text_faint"], tickfont=dict(size=10),
                    fixedrange=True, rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color=C["text_faint"],
                    side="right", tickfont=dict(size=10), fixedrange=True),
        hovermode="x unified", hoverlabel=dict(bgcolor="#10151F", font_size=11),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def render_stat_list(rows):
    items = ""
    for r in rows:
        sign = r.get("sign", "")
        cls = f"stat-value {sign}".strip()
        items += f"""
        <div class="stat-row rtl">
            <span class="{cls} mono">{r['value']}</span>
            <span class="stat-name">{r['label']}</span>
        </div>"""
    st.markdown(items, unsafe_allow_html=True)


def render_alpha_card(score, subscores):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"size": 34, "color": C["text"], "family": "Inter"}},
        gauge={
            "axis": {"range": [0, 100], "showticklabels": False, "tickwidth": 0},
            "bar": {"color": C["green"], "thickness": 0.26},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [
                {"range": [0, 50], "color": "rgba(245,69,79,0.08)"},
                {"range": [50, 75], "color": "rgba(232,184,75,0.08)"},
                {"range": [75, 100], "color": "rgba(43,212,107,0.08)"},
            ],
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(height=140, margin=dict(l=10, r=10, t=10, b=0),
                       paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter"))

    st.markdown('<div class="gcard alpha-card">', unsafe_allow_html=True)
    st.markdown('<div class="alpha-title">⭐ Alpha ציון</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<div class="alpha-score-sub">/100</div>', unsafe_allow_html=True)

    sub_html = ""
    for sb in subscores:
        sub_html += f"""
        <div class="sub-bar-row">
            <span class="sub-bar-value mono">{sb['value']}</span>
            <div class="sub-bar-track"><div class="sub-bar-fill" style="width:{sb['value']}%;"></div></div>
            <span class="sub-bar-label">{sb['label']}</span>
        </div>"""
    st.markdown(sub_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_news_card():
    st.markdown(f"""
    <div class="gcard news-card rtl">
        <div class="news-text">
            <div class="news-headline">חדשות אחרונות: השוק ההודי ממשיך לעלות לאחר נתוני צמיחה חזקים</div>
            <div class="news-meta">לפני 12 דקות · Reuters</div>
        </div>
        <div style="font-size:1.8rem;">🏙️</div>
    </div>
    """, unsafe_allow_html=True)


def render_portfolio_card(total, delta):
    fig = go.Figure(data=[go.Pie(
        values=[42, 31, 27], hole=0.62,
        marker=dict(colors=[C["blue"], C["green"], C["gold"]], line=dict(color=C["bg"], width=2)),
        textinfo="none", sort=False,
    )])
    fig.update_layout(height=110, width=110, margin=dict(l=0, r=0, t=0, b=0),
                       paper_bgcolor="rgba(0,0,0,0)", showlegend=False)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<div class="gcard" style="text-align:right;">', unsafe_allow_html=True)
        st.markdown('<div class="portfolio-total-label rtl">סיכום תיק</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="portfolio-total-value mono">{total}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="portfolio-total-delta mono">{delta} ▲</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-link rtl">לכל תיק ›</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="gcard" style="display:flex; align-items:center; justify-content:center;">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=False, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# PAGE BODIES — one per sub-tab. Demo placeholders; swap with real tab logic
# when porting into alpha_paper_trading.py
# ──────────────────────────────────────────────────────────────────────────

def page_home(s, df):
    render_ticker_card(s)
    st.write("")
    render_ai_card(s["ai"])
    st.write("")
    render_mini_chart(df)
    st.write("")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="gcard" style="height:100%;">', unsafe_allow_html=True)
        st.markdown('<div class="sec-label rtl">נתונים פיננסים</div>', unsafe_allow_html=True)
        render_stat_list(s["financials"])
        st.markdown('<div class="sec-link rtl">לכל הנתונים ›</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        render_alpha_card(s["alpha_score"], s["alpha_subscores"])
    with col3:
        st.markdown('<div class="gcard" style="height:100%;">', unsafe_allow_html=True)
        st.markdown('<div class="sec-label rtl">AI ניתוח</div>', unsafe_allow_html=True)
        render_stat_list(s["ai_analysis"])
        st.markdown('<div class="sec-link rtl">לניתוח מפורט ›</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.write("")
    render_news_card()
    st.write("")
    render_portfolio_card(s["portfolio_total"], s["portfolio_delta"])


def page_chart(s, df):
    render_chart_page_v3(df, s)


def page_analysis(s):
    render_ai_card(s["ai"])
    st.write("")
    render_alpha_card(s["alpha_score"], s["alpha_subscores"])
    st.write("")
    st.markdown('<div class="gcard"><div class="sec-label rtl">AI ניתוח</div></div>', unsafe_allow_html=True)
    render_stat_list(s["ai_analysis"])


def page_compare(s):
    st.markdown('<div class="gcard"><div class="sec-label rtl">השוואת מניות</div><div class="stat-name rtl">בחרי שתי מניות להשוואה</div></div>', unsafe_allow_html=True)


def page_trade(s):
    st.markdown('<div class="gcard"><div class="sec-label rtl">מסחר</div></div>', unsafe_allow_html=True)


def page_portfolio(s):
    render_portfolio_card(s["portfolio_total"], s["portfolio_delta"])


def page_placeholder(name):
    st.markdown(f'<div class="gcard"><div class="sec-label rtl">{name}</div><div class="stat-name rtl">בקרוב</div></div>', unsafe_allow_html=True)


PAGE_RENDERERS = {
    "בית":        lambda s, df: page_home(s, df),
    "גרף":        lambda s, df: page_chart(s, df),
    "ניתוח":      lambda s, df: page_analysis(s),
    "השוואה":     lambda s, df: page_compare(s),
    "מסחר":       lambda s, df: page_trade(s),
    "תיק":        lambda s, df: page_portfolio(s),
    "Backtest":   lambda s, df: page_placeholder("Backtest"),
    "התראות":     lambda s, df: page_placeholder("התראות"),
    "דוחות":      lambda s, df: page_placeholder("דוחות"),
    "Watchlist":  lambda s, df: page_placeholder("Watchlist"),
    "מדריך":      lambda s, df: page_placeholder("מדריך"),
}


def render_top_pill(active_group):
    subs = NAV_GROUPS[active_group]["subs"]
    if len(subs) == 1:
        return subs[0]  # no sub-nav needed, single page in this group
    default_sub = st.session_state.get(f"sub_{active_group}", subs[0])
    default_idx = subs.index(default_sub) if default_sub in subs else 0

    st.markdown('<div class="top-pill-wrap">', unsafe_allow_html=True)
    selected = option_menu(
        menu_title=None, options=subs, default_index=default_idx,
        orientation="horizontal",
        styles={
            "container": {"padding": "4px", "background-color": "rgba(255,255,255,0.035)",
                          "border": f"1px solid {C['card_border']}", "border-radius": "999px",
                          "margin": "0 0 0.9rem 0"},
            "nav-link": {"font-size": "11px", "font-weight": "600", "color": C["text_faint"],
                        "text-align": "center", "border-radius": "999px", "padding": "8px 6px", "margin": "0px"},
            "nav-link-selected": {"background-color": C["blue"], "color": "#FFFFFF"},
        },
        key=f"pill_{active_group}",
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.session_state[f"sub_{active_group}"] = selected
    return selected


def render_bottom_nav(active_group):
    st.markdown('<div class="bottom-nav-spacer"></div>', unsafe_allow_html=True)
    cols = st.columns(len(GROUP_ORDER))
    for i, group in enumerate(GROUP_ORDER):
        with cols[i]:
            is_active = (group == active_group)
            st.markdown(
                f'<div class="bottom-nav-btn{" bottom-nav-btn-active" if is_active else ""} bottom-nav-marker">',
                unsafe_allow_html=True,
            )
            if st.button(GROUP_BOTTOM_ICONS[group], key=f"nav_{group}", use_container_width=True):
                st.session_state.active_group = group
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────

def main():
    inject_css()

    if "active_group" not in st.session_state:
        st.session_state.active_group = "בית"

    s = get_snapshot()
    df = generate_price_series(start_price=s["prev_close"], end_price=s["price"])

    render_topbar()
    st.write("")

    active_group = st.session_state.active_group
    active_sub = render_top_pill(active_group)

    renderer = PAGE_RENDERERS.get(active_sub, lambda s, df: page_placeholder(active_sub))
    renderer(s, df)

    render_bottom_nav(active_group)


if __name__ == "__main__":
    main()
