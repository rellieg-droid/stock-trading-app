import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json
import os
from streamlit_autorefresh import st_autorefresh

# ============================================================
# הגדרות
# ============================================================
st.set_page_config(page_title="Alpha Trading Pro", layout="wide", page_icon="📈")
st_autorefresh(interval=60000, key="autorefresh")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff !important; color: #111111 !important; }
    section[data-testid="stSidebar"] { background-color: #f5f5f5 !important; min-width: 280px !important; }
    .stMetric { background-color: #f0f4ff !important; padding: 15px; border-radius: 12px; border: 1px solid #c0c8e8; min-width: 150px !important; }
    .block-container { direction: rtl; text-align: right; }
    div[data-testid="stSidebarContent"] { direction: rtl; text-align: right; }
    p, h1, h2, h3, h4, label, span { color: #111111 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #eeeeee; border-radius: 10px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { background-color: #ffffff; color: #111111 !important; border-radius: 8px; border: 1px solid #cccccc; }
    .stTabs [aria-selected="true"] { background-color: #0f3460 !important; color: white !important; }
    .stButton > button { background-color: #0f3460; color: white; border-radius: 8px; width: 100%; }
    .stTextInput input, .stNumberInput input { background-color: #ffffff !important; color: #111111 !important; border: 1px solid #cccccc; border-radius: 8px; }
    hr { border-color: #dddddd; }
    button[data-testid="collapsedControl"] { background-color: #0f3460 !important; color: white !important; border: 2px solid #ef5350 !important; border-radius: 8px !important; }
    button[data-testid="collapsedControl"] svg { fill: white !important; }
    </style>
""", unsafe_allow_html=True)

PORTFOLIO_FILE = "paper_portfolio.json"
STARTING_CASH = 10_000.0


# ============================================================
# ניהול תיק
# ============================================================
def load_portfolio() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"cash": STARTING_CASH, "positions": {}, "trades": []}


def save_portfolio(portfolio: dict):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2, default=str)


def get_current_price(symbol: str) -> float | None:
    try:
        hist = yf.Ticker(symbol).history(period="1d")
        return float(hist['Close'].iloc[-1]) if not hist.empty else None
    except:
        return None


def portfolio_value(portfolio: dict) -> float:
    total = portfolio['cash']
    for sym, pos in portfolio['positions'].items():
        price = get_current_price(sym)
        if price:
            total += pos['shares'] * price
    return total


# ============================================================
# אינדיקטורים טכניים
# ============================================================
def calc_rsi_wilder(series: pd.Series, period: int) -> pd.Series:
    """RSI לפי שיטת Wilder - הסטנדרט התעשייתי"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_bollinger(series: pd.Series, period: int = 20, std: float = 2.0):
    """רצועות בולינגר"""
    mid = series.rolling(period).mean()
    std_dev = series.rolling(period).std()
    return mid + std * std_dev, mid, mid - std * std_dev


def calc_max_drawdown(equity_curve: pd.Series) -> float:
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return float(drawdown.min() * 100)


# ============================================================
# זיהוי תבניות נרות יפניים
# ============================================================
def detect_candle_patterns(df: pd.DataFrame) -> list[dict]:
    """מזהה תבניות נרות יפניות על הנר האחרון"""
    patterns = []
    if len(df) < 3:
        return patterns

    o = df['Open'].squeeze()
    h = df['High'].squeeze()
    l = df['Low'].squeeze()
    c = df['Close'].squeeze()

    o1, h1, l1, c1 = float(o.iloc[-1]), float(h.iloc[-1]), float(l.iloc[-1]), float(c.iloc[-1])
    o2, h2, l2, c2 = float(o.iloc[-2]), float(h.iloc[-2]), float(l.iloc[-2]), float(c.iloc[-2])
    o3, c3 = float(o.iloc[-3]), float(c.iloc[-3])

    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)
    upper_wick1 = h1 - max(o1, c1)
    lower_wick1 = min(o1, c1) - l1
    candle_range1 = h1 - l1

    # פטיש
    if candle_range1 > 0 and lower_wick1 > 2 * body1 and upper_wick1 < body1 * 0.5:
        patterns.append({"תבנית": "🔨 Hammer", "משמעות": "היפוך שורי פוטנציאלי", "כיוון": "🟢 קנייה"})

    # Shooting Star
    if candle_range1 > 0 and upper_wick1 > 2 * body1 and lower_wick1 < body1 * 0.5:
        patterns.append({"תבנית": "⭐ Shooting Star", "משמעות": "היפוך דובי פוטנציאלי", "כיוון": "🔴 מכירה"})

    # Doji
    if candle_range1 > 0 and body1 < candle_range1 * 0.1:
        patterns.append({"תבנית": "✝️ Doji", "משמעות": "חוסר החלטיות בשוק", "כיוון": "⚪ המתן"})

    # Bullish Engulfing
    if c2 < o2 and c1 > o1 and o1 < c2 and c1 > o2:
        patterns.append({"תבנית": "📈 Bullish Engulfing", "משמעות": "בליעה שורית חזקה", "כיוון": "🟢 קנייה"})

    # Bearish Engulfing
    if c2 > o2 and c1 < o1 and o1 > c2 and c1 < o2:
        patterns.append({"תבנית": "📉 Bearish Engulfing", "משמעות": "בליעה דובית חזקה", "כיוון": "🔴 מכירה"})

    # Morning Star
    if c3 < o3 and body2 < abs(c3 - o3) * 0.3 and c1 > o1 and c1 > (o3 + c3) / 2:
        patterns.append({"תבנית": "🌅 Morning Star", "משמעות": "היפוך שורי חזק (3 נרות)", "כיוון": "🟢 קנייה"})

    # Evening Star
    if c3 > o3 and body2 < abs(c3 - o3) * 0.3 and c1 < o1 and c1 < (o3 + c3) / 2:
        patterns.append({"תבנית": "🌆 Evening Star", "משמעות": "היפוך דובי חזק (3 נרות)", "כיוון": "🔴 מכירה"})

    # Marubozu
    if candle_range1 > 0 and body1 > candle_range1 * 0.9:
        direction = "🟢 קנייה" if c1 > o1 else "🔴 מכירה"
        patterns.append({"תבנית": "💪 Marubozu", "משמעות": "מומנטום חזק", "כיוון": direction})

    if not patterns:
        patterns.append({"תבנית": "⚪ אין תבנית", "משמעות": "נר רגיל", "כיוון": "⚪ המתן"})

    return patterns


# ============================================================
# ניתוח סיגנלים
# ============================================================
def detect_signals(df: pd.DataFrame, ma_fast: int, ma_slow: int) -> list[str]:
    signals = []
    close = df['Close'].squeeze()
    rsi = calc_rsi_wilder(close, 14)
    ma_f = close.rolling(ma_fast).mean()
    ma_s = close.rolling(ma_slow).mean()
    upper_bb, mid_bb, lower_bb = calc_bollinger(close)

    if (ma_f.iloc[-1] > ma_s.iloc[-1]) and (ma_f.iloc[-2] <= ma_s.iloc[-2]):
        signals.append("🟡 Golden Cross - חצייה שורית!")
    if (ma_f.iloc[-1] < ma_s.iloc[-1]) and (ma_f.iloc[-2] >= ma_s.iloc[-2]):
        signals.append("💀 Death Cross - חצייה דובית!")

    rsi_val = float(rsi.iloc[-1])
    if rsi_val < 30:
        signals.append(f"🟢 RSI={rsi_val:.1f} - Oversold, הזדמנות כניסה")
    elif rsi_val > 70:
        signals.append(f"🔴 RSI={rsi_val:.1f} - Overbought, שקלי מכירה")

    last_close = float(close.iloc[-1])
    if not pd.isna(lower_bb.iloc[-1]) and last_close <= float(lower_bb.iloc[-1]):
        signals.append("📉 מחיר נגע ברצועה התחתונה של בולינגר - היפוך שורי אפשרי")
    if not pd.isna(upper_bb.iloc[-1]) and last_close >= float(upper_bb.iloc[-1]):
        signals.append("📈 מחיר נגע ברצועה העליונה של בולינגר - היפוך דובי אפשרי")

    if 'Volume' in df.columns:
        vol = df['Volume'].squeeze()
        avg_vol = float(vol.rolling(20).mean().iloc[-1])
        last_vol = float(vol.iloc[-1])
        if avg_vol > 0 and last_vol > avg_vol * 1.5:
            signals.append(f"💰 נפח חריג: פי {last_vol/avg_vol:.1f} מהממוצע - כסף חכם נכנס")

    if not signals:
        signals.append("⚪ אין סיגנל חזק כרגע - המתן")
    return signals


# ============================================================
# טעינת נתונים
# ============================================================
@st.cache_data(ttl=300)
def fetch_data(symbol: str, period: str, maf: int, mas: int) -> pd.DataFrame | None:
    try:
        if period in ["1d", "5d"]:
            df = yf.download(symbol, period=period, interval="5m", progress=False, auto_adjust=True)
        else:
            df = yf.download(symbol, period=period, progress=False, auto_adjust=True)

        if df.empty or len(df) < 5:
            return None

        close = df['Close'].squeeze()
        if not hasattr(close, 'rolling'):
            return None

        n = len(df)
        df['MA_Fast'] = close.rolling(min(maf, n)).mean()
        df['MA_Slow'] = close.rolling(min(mas, n)).mean()
        df['RSI'] = calc_rsi_wilder(close, min(14, n - 1))
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calc_bollinger(close)
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת נתונים: {e}")
        return None


# ============================================================
# אתחול state
# ============================================================
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()
portfolio = st.session_state.portfolio

# ============================================================
# Sidebar
# ============================================================
st.sidebar.header("🛠️ הגדרות")
ticker = st.sidebar.text_input("סימול מניה:", "NVDA").upper()
timeframe = st.sidebar.selectbox("טווח זמן:", ["1d", "5d", "1mo", "6mo", "ytd", "1y", "2y", "5y", "max"])
ma_fast_val = st.sidebar.number_input("ממוצע מהיר:", value=50, min_value=1)
ma_slow_val = st.sidebar.number_input("ממוצע איטי:", value=200, min_value=2)
show_bb = st.sidebar.checkbox("הצג רצועות בולינגר", value=True)

st.sidebar.divider()
st.sidebar.subheader("💰 תיק וירטואלי")
total_val = portfolio_value(portfolio)
gain = total_val - STARTING_CASH
gain_pct = (gain / STARTING_CASH) * 100
st.sidebar.metric("שווי תיק", f"${total_val:,.2f}", f"{gain_pct:+.1f}%")
st.sidebar.metric("מזומן פנוי", f"${portfolio['cash']:,.2f}")

if st.sidebar.button("🔄 איפוס תיק"):
    st.session_state.portfolio = {"cash": STARTING_CASH, "positions": {}, "trades": []}
    save_portfolio(st.session_state.portfolio)
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("👁️ מעקב מניות")
watchlist_input = st.sidebar.text_input("מניות למעקב (בפסיק):", "NVDA, AAPL, TSLA, MSFT")
watchlist = [s.strip().upper() for s in watchlist_input.split(",") if s.strip()]

if watchlist:
    watch_data = []
    for sym in watchlist:
        try:
            hist = yf.Ticker(sym).history(period="2d")
            if len(hist) >= 2:
                last = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                chg = ((last - prev) / prev) * 100
                watch_data.append({"מניה": sym, "מחיר": f"${last:.2f}", "שינוי": f"{chg:+.2f}%", "": "🟢" if chg > 0 else "🔴"})
        except:
            pass
    if watch_data:
        st.sidebar.dataframe(pd.DataFrame(watch_data), use_container_width=True, hide_index=True)

# ============================================================
# טאבים
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 גרף וניתוח",
    "🕯️ תבניות נרות",
    "⚠️ ניהול סיכונים",
    "⏳ Backtest",
    "🛒 מסחר וירטואלי",
    "📊 ביצועים"
])

data = fetch_data(ticker, timeframe, ma_fast_val, ma_slow_val)

# ============================================================
# TAB 1: גרף וניתוח
# ============================================================
with tab1:
    st.title(f"📈 {ticker} - ניתוח טכני")

    if data is not None:
        close = data['Close'].squeeze()
        last_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        last_rsi = float(data['RSI'].iloc[-1])
        day_change = ((last_close - prev_close) / prev_close) * 100

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("מחיר", f"${last_close:.2f}", f"{day_change:+.2f}%")
        c2.metric("RSI", f"{last_rsi:.1f}", "Overbought ⚠️" if last_rsi > 70 else ("Oversold 🟢" if last_rsi < 30 else "Neutral"))
        c3.metric("מגמה", "📈 BULLISH" if last_close > float(data['MA_Slow'].squeeze().iloc[-1]) else "📉 BEARISH")
        macd_val = float(data['MACD'].iloc[-1])
        c4.metric("MACD", f"{macd_val:.3f}", "Bullish" if macd_val > 0 else "Bearish")
        if not pd.isna(data['BB_Upper'].iloc[-1]):
            bb_width = float((data['BB_Upper'].iloc[-1] - data['BB_Lower'].iloc[-1]) / data['BB_Mid'].iloc[-1] * 100)
            c5.metric("רוחב בולינגר", f"{bb_width:.1f}%")

        st.subheader("🚦 סיגנלים אוטומטיים")
        signals = detect_signals(data, ma_fast_val, ma_slow_val)
        for sig in signals:
            if "🟢" in sig or "🟡" in sig:
                st.success(sig)
            elif "🔴" in sig or "💀" in sig:
                st.error(sig)
            elif "💰" in sig:
                st.warning(sig)
            else:
                st.info(sig)

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            vertical_spacing=0.04, row_heights=[0.6, 0.2, 0.2],
                            subplot_titles=("Price Action", "RSI", "MACD"))

        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'].squeeze(), high=data['High'].squeeze(),
            low=data['Low'].squeeze(), close=close,
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350', name="Price"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=data.index, y=data['MA_Fast'].squeeze(),
                                 name=f"MA{ma_fast_val}", line=dict(color='orange', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA_Slow'].squeeze(),
                                 name=f"MA{ma_slow_val}", line=dict(color='blue', width=2)), row=1, col=1)

        if show_bb and not data['BB_Upper'].isna().all():
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'].squeeze(),
                                     name="BB Upper", line=dict(color='purple', width=1, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'].squeeze(),
                                     name="BB Lower", line=dict(color='purple', width=1, dash='dash'),
                                     fill='tonexty', fillcolor='rgba(128,0,128,0.05)'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_Mid'].squeeze(),
                                     name="BB Mid", line=dict(color='purple', width=1, dash='dot')), row=1, col=1)

        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'].squeeze(),
                                 name="RSI", line=dict(color='#e91e63', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)

        colors_hist = ['#26a69a' if v >= 0 else '#ef5350' for v in data['MACD_Hist'].squeeze()]
        fig.add_trace(go.Bar(x=data.index, y=data['MACD_Hist'].squeeze(),
                             marker_color=colors_hist, name="Hist", opacity=0.7), row=3, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'].squeeze(),
                                 line=dict(color='blue', width=1), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD_Signal'].squeeze(),
                                 line=dict(color='orange', width=1), name="Signal"), row=3, col=1)

        fig.update_layout(template='plotly_white', height=850,
                          xaxis_rangeslider_visible=False,
                          legend=dict(orientation="h", y=1.02))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("לא ניתן לטעון נתונים. בדקי את הסימול.")


# ============================================================
# TAB 2: תבניות נרות
# ============================================================
with tab2:
    st.header("🕯️ ניתוח תבניות נרות יפניים")

    if data is not None:
        patterns = detect_candle_patterns(data)

        st.subheader("תבניות שזוהו בנר האחרון:")
        for p in patterns:
            if "🟢" in p["כיוון"]:
                st.success(f"**{p['תבנית']}** | {p['משמעות']} | {p['כיוון']}")
            elif "🔴" in p["כיוון"]:
                st.error(f"**{p['תבנית']}** | {p['משמעות']} | {p['כיוון']}")
            else:
                st.info(f"**{p['תבנית']}** | {p['משמעות']} | {p['כיוון']}")

        st.divider()
        st.subheader("📊 ניתוח יחסי גוף-פתיל (5 נרות אחרונים)")

        o = data['Open'].squeeze()
        h = data['High'].squeeze()
        l = data['Low'].squeeze()
        c = data['Close'].squeeze()

        candle_analysis = []
        for i in range(-5, 0):
            body = abs(float(c.iloc[i]) - float(o.iloc[i]))
            candle_range = float(h.iloc[i]) - float(l.iloc[i])
            upper_wick = float(h.iloc[i]) - max(float(o.iloc[i]), float(c.iloc[i]))
            lower_wick = min(float(o.iloc[i]), float(c.iloc[i])) - float(l.iloc[i])
            body_pct = body / candle_range * 100 if candle_range > 0 else 0
            candle_analysis.append({
                "תאריך": str(data.index[i])[:10],
                "כיוון": "🟢 שורי" if float(c.iloc[i]) > float(o.iloc[i]) else "🔴 דובי",
                "גוף %": f"{body_pct:.0f}%",
                "פתיל עליון": f"{upper_wick:.2f}",
                "פתיל תחתון": f"{lower_wick:.2f}",
                "טווח כולל": f"{candle_range:.2f}"
            })
        st.dataframe(pd.DataFrame(candle_analysis), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📦 ניתוח נפח מסחר")
        if 'Volume' in data.columns:
            vol = data['Volume'].squeeze()
            avg_vol_20 = float(vol.rolling(20).mean().iloc[-1])
            last_vol = float(vol.iloc[-1])
            vol_ratio = last_vol / avg_vol_20 if avg_vol_20 > 0 else 0

            v1, v2, v3 = st.columns(3)
            v1.metric("נפח היום", f"{last_vol:,.0f}")
            v2.metric("ממוצע 20 יום", f"{avg_vol_20:,.0f}")
            v3.metric("יחס נפח", f"{vol_ratio:.2f}x", "חריג! 💰" if vol_ratio > 1.5 else "רגיל")

            o_col = data['Open'].squeeze()
            c_col = data['Close'].squeeze()
            colors_vol = ['#26a69a' if float(c_col.iloc[i]) >= float(o_col.iloc[i]) else '#ef5350'
                          for i in range(len(data))]
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(x=data.index, y=vol, marker_color=colors_vol, name="נפח"))
            fig_vol.add_trace(go.Scatter(x=data.index, y=vol.rolling(20).mean(),
                                         name="ממוצע 20", line=dict(color='orange', width=2)))
            fig_vol.update_layout(template='plotly_white', height=300, title="נפח מסחר")
            st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.error("לא ניתן לטעון נתונים.")


# ============================================================
# TAB 3: ניהול סיכונים
# ============================================================
with tab3:
    st.header("⚠️ ניהול סיכונים - Position Sizing")
    st.write("מחשב כמה מניות לקנות לפי רמת הסיכון שלך")

    current_price = get_current_price(ticker)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("🔢 פרמטרי סיכון")
        account_size = st.number_input("גודל חשבון ($):", value=10000, min_value=100, step=500)
        risk_pct = st.slider("סיכון לעסקה (% מהחשבון):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
        entry_price = st.number_input("מחיר כניסה ($):", value=float(current_price) if current_price else 100.0, min_value=0.01)
        stop_loss = st.number_input("Stop Loss ($):", value=float(entry_price * 0.95), min_value=0.01)
        target_price = st.number_input("מחיר יעד ($):", value=float(entry_price * 1.1), min_value=0.01)

    with col_right:
        st.subheader("📊 תוצאות החישוב")
        if entry_price > stop_loss:
            risk_per_share = entry_price - stop_loss
            risk_amount = account_size * (risk_pct / 100)
            shares_to_buy = int(risk_amount / risk_per_share)
            position_size = shares_to_buy * entry_price
            position_pct = position_size / account_size * 100
            reward = target_price - entry_price
            risk = entry_price - stop_loss
            rr_ratio = reward / risk if risk > 0 else 0
            potential_profit = shares_to_buy * (target_price - entry_price)
            potential_loss = shares_to_buy * risk_per_share

            st.metric("כמות מניות לקנות", f"{shares_to_buy} מניות")
            st.metric("גודל פוזיציה", f"${position_size:,.2f}", f"{position_pct:.1f}% מהחשבון")
            st.metric("סיכון מקסימלי", f"${potential_loss:,.2f}", f"-{risk_pct}%")
            st.metric("רווח פוטנציאלי", f"${potential_profit:,.2f}")
            st.metric("יחס סיכוי/סיכון", f"1:{rr_ratio:.2f}", "✅ טוב" if rr_ratio >= 2 else "⚠️ נמוך")

            if rr_ratio < 2:
                st.warning("יחס סיכוי/סיכון מתחת ל-1:2. כדאי לשקול מחדש.")
            else:
                st.success("יחס סיכוי/סיכון טוב!")
        else:
            st.error("Stop Loss חייב להיות נמוך ממחיר הכניסה!")

    st.divider()
    st.subheader("📏 רצועות בולינגר כרמות תמיכה/התנגדות")
    if data is not None and not data['BB_Upper'].isna().all():
        bb_u = float(data['BB_Upper'].iloc[-1])
        bb_m = float(data['BB_Mid'].iloc[-1])
        bb_l = float(data['BB_Lower'].iloc[-1])
        last_c = float(data['Close'].squeeze().iloc[-1])

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("רצועה עליונה", f"${bb_u:.2f}", "התנגדות")
        b2.metric("ממוצע אמצעי", f"${bb_m:.2f}", "ציר")
        b3.metric("רצועה תחתונה", f"${bb_l:.2f}", "תמיכה")
        b4.metric("מחיר נוכחי", f"${last_c:.2f}",
                  "ליד עליונה ⚠️" if last_c > bb_u * 0.99 else ("ליד תחתונה 🟢" if last_c < bb_l * 1.01 else "באמצע"))


# ============================================================
# TAB 4: Backtest
# ============================================================
with tab4:
    st.header("⏳ Backtest - בדיקה לאחור")

    if data is not None and len(data) > max(ma_fast_val, ma_slow_val) + 10:
        bt = data[['Close', 'MA_Fast', 'MA_Slow']].copy()
        bt['Close'] = bt['Close'].squeeze()
        bt['MA_Fast'] = bt['MA_Fast'].squeeze()
        bt['MA_Slow'] = bt['MA_Slow'].squeeze()
        bt['Signal'] = np.where(bt['MA_Fast'] > bt['MA_Slow'], 1.0, 0.0)
        bt['Daily_Return'] = bt['Close'].pct_change()
        bt['Strategy_Return'] = bt['Daily_Return'] * bt['Signal'].shift(2)
        bt = bt.dropna()

        cum_strategy = (1 + bt['Strategy_Return']).cumprod()
        cum_market = (1 + bt['Daily_Return']).cumprod()

        total_return = (cum_strategy.iloc[-1] - 1) * 100
        market_return = (cum_market.iloc[-1] - 1) * 100
        avg_ret = bt['Strategy_Return'].mean()
        std_ret = bt['Strategy_Return'].std()
        sharpe = (avg_ret / std_ret) * np.sqrt(252) if std_ret != 0 else 0.0
        max_dd = calc_max_drawdown(cum_strategy)
        trades_count = int(bt['Signal'].diff().abs().sum() / 2)
        win_days = (bt['Strategy_Return'] > 0).sum()
        total_days = (bt['Strategy_Return'] != 0).sum()
        win_rate = (win_days / total_days * 100) if total_days > 0 else 0
        alpha = total_return - market_return

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("תשואת אסטרטגיה", f"{total_return:.1f}%", f"vs שוק {market_return:.1f}%")
        m2.metric("Sharpe Ratio", f"{sharpe:.2f}", "✅ טוב" if sharpe > 1 else "⚠️ חלש")
        m3.metric("Max Drawdown", f"{max_dd:.1f}%")
        m4.metric("Win Rate", f"{win_rate:.1f}%", f"{trades_count} עסקאות")
        m5.metric("Alpha vs שוק", f"{alpha:+.1f}%", "✅ מכה שוק" if alpha > 0 else "❌ מפסיד לשוק")

        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=cum_strategy.index, y=cum_strategy,
                                    name="אסטרטגיה", line=dict(color='#0f3460', width=2.5)))
        fig_bt.add_trace(go.Scatter(x=cum_market.index, y=cum_market,
                                    name="Buy & Hold", line=dict(color='#ef5350', width=2, dash='dash')))
        fig_bt.add_hline(y=1.0, line_dash="dot", line_color="gray")
        fig_bt.update_layout(template='plotly_white', height=400,
                              title="אסטרטגיה vs Buy & Hold", yaxis_title="צמיחה ($1 = התחלה)")
        st.plotly_chart(fig_bt, use_container_width=True)

        rolling_max = cum_strategy.cummax()
        drawdown_series = (cum_strategy - rolling_max) / rolling_max * 100
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=drawdown_series.index, y=drawdown_series,
                                    fill='tozeroy', fillcolor='rgba(239,83,80,0.3)',
                                    line=dict(color='#ef5350'), name="Drawdown"))
        fig_dd.update_layout(template='plotly_white', height=250,
                              title="Drawdown לאורך זמן", yaxis_title="%")
        st.plotly_chart(fig_dd, use_container_width=True)
        st.info("הערה: סיגנלים מבוצעים יומיים אחרי היווצרותם. אין עמלות בחישוב.")
    else:
        st.warning("אין מספיק נתונים לבדיקה. בחרי טווח זמן ארוך יותר.")


# ============================================================
# TAB 5: מסחר וירטואלי
# ============================================================
with tab5:
    st.header("🛒 מסחר וירטואלי - Paper Trading")
    current_price = get_current_price(ticker)

    if current_price:
        col_info, col_trade = st.columns([1, 1])
        with col_info:
            st.subheader(f"📌 {ticker}")
            st.metric("מחיר עכשווי", f"${current_price:.2f}")
            st.metric("מזומן פנוי", f"${portfolio['cash']:,.2f}")
            if ticker in portfolio['positions']:
                pos = portfolio['positions'][ticker]
                pos_val = pos['shares'] * current_price
                pos_gain = (current_price - pos['avg_price']) / pos['avg_price'] * 100
                st.metric(f"אחזקה ב-{ticker}", f"{pos['shares']} מניות (${pos_val:,.2f})",
                          f"{pos_gain:+.1f}% מהכניסה")

        with col_trade:
            st.subheader("ביצוע עסקה")
            action = st.radio("פעולה:", ["🟢 קנייה", "🔴 מכירה"], horizontal=True)
            shares_input = st.number_input("כמות מניות:", min_value=1, max_value=1000, value=1)
            trade_value = shares_input * current_price
            st.write(f"**עלות עסקה: ${trade_value:,.2f}**")
            note = st.text_input("הערה:", placeholder="למה ביצעתי את העסקה?")

            if st.button("✅ בצע עסקה", type="primary"):
                p = st.session_state.portfolio
                if "קנייה" in action:
                    if p['cash'] >= trade_value:
                        p['cash'] -= trade_value
                        if ticker not in p['positions']:
                            p['positions'][ticker] = {"shares": 0, "avg_price": 0.0}
                        pos = p['positions'][ticker]
                        total_shares = pos['shares'] + shares_input
                        pos['avg_price'] = (pos['shares'] * pos['avg_price'] + shares_input * current_price) / total_shares
                        pos['shares'] = total_shares
                        p['trades'].append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                            "symbol": ticker, "action": "BUY", "shares": shares_input,
                                            "price": current_price, "total": trade_value, "note": note})
                        save_portfolio(p)
                        st.success(f"✅ קנית {shares_input} מניות של {ticker} ב-${current_price:.2f}")
                        st.rerun()
                    else:
                        st.error(f"אין מספיק מזומן! צריך ${trade_value:,.2f}, יש ${p['cash']:,.2f}")
                elif "מכירה" in action:
                    if ticker in p['positions'] and p['positions'][ticker]['shares'] >= shares_input:
                        p['cash'] += trade_value
                        avg_p = p['positions'][ticker]['avg_price']
                        pnl = (current_price - avg_p) * shares_input
                        p['positions'][ticker]['shares'] -= shares_input
                        if p['positions'][ticker]['shares'] == 0:
                            del p['positions'][ticker]
                        p['trades'].append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                            "symbol": ticker, "action": "SELL", "shares": shares_input,
                                            "price": current_price, "total": trade_value,
                                            "pnl": round(pnl, 2), "note": note})
                        save_portfolio(p)
                        st.success(f"{'✅' if pnl >= 0 else '❌'} מכרת {shares_input} מניות | רווח/הפסד: ${pnl:+.2f}")
                        st.rerun()
                    else:
                        st.error("אין מספיק מניות למכירה.")
    else:
        st.error("לא ניתן לטעון מחיר.")


# ============================================================
# TAB 6: ביצועים
# ============================================================
with tab6:
    st.header("📊 יומן עסקאות וביצועים")
    trades = portfolio['trades']

    if trades:
        df_trades = pd.DataFrame(trades)
        sells = df_trades[df_trades['action'] == 'SELL']

        if not sells.empty and 'pnl' in sells.columns:
            total_pnl = sells['pnl'].sum()
            winners = (sells['pnl'] > 0).sum()
            losers = (sells['pnl'] < 0).sum()
            win_r = winners / (winners + losers) * 100 if (winners + losers) > 0 else 0
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("רווח/הפסד כולל", f"${total_pnl:+.2f}")
            s2.metric("עסקאות מנצחות", winners)
            s3.metric("עסקאות מפסידות", losers)
            s4.metric("Win Rate", f"{win_r:.0f}%")

        st.divider()

        def color_action(val):
            return "color: #26a69a; font-weight:bold" if val == "BUY" else "color: #ef5350; font-weight:bold"

        def color_pnl(val):
            try:
                return "color: #26a69a" if float(val) >= 0 else "color: #ef5350"
            except:
                return ""

        styled = df_trades.style.map(color_action, subset=['action'])
        if 'pnl' in df_trades.columns:
            styled = styled.map(color_pnl, subset=['pnl'])
        st.dataframe(styled, use_container_width=True)

        csv = df_trades.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ הורד יומן CSV", csv, "trades_journal.csv", "text/csv")
    else:
        st.info("עדיין אין עסקאות. עברי לטאב 'מסחר וירטואלי' כדי להתחיל.")
