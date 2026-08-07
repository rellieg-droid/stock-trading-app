import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json
import os

# ============================================================
# הגדרות
# ============================================================
st.set_page_config(page_title="Alpha Paper Trading", layout="wide")

st.markdown("""
    <style>
    .stApp { 
        background-color: #0a0a0a !important; 
        color: white !important; 
    }
    /* תיקון סיידבר - שמאל בלבד */
    section[data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #333;
        min-width: 280px !important;
    }
    /* כפתור פתיחה/סגירה */
    button[data-testid="collapsedControl"] {
        color: white !important;
        background-color: #1a1a2e !important;
    }
    /* RTL רק על תוכן - לא על מבנה */
    .stSidebar .stMarkdown,
    .stSidebar label,
    .main .block-container { 
        direction: rtl; 
        text-align: right; 
    }
    .stMetric { 
        background-color: #1a1a2e !important; 
        padding: 15px; 
        border-radius: 12px; 
        border: 1px solid #0f3460;
    }
    p, h1, h2, h3, label, span { 
        color: white !important; 
    }
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px;
        background-color: #111111;
        border-radius: 10px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a2e;
        color: white !important;
        border-radius: 8px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f3460 !important;
    }
    .stButton > button {
        background-color: #0f3460;
        color: white;
        border-radius: 8px;
        width: 100%;
    }
    .stTextInput input, .stNumberInput input {
        background-color: #1a1a2e !important;
        color: white !important;
        border: 1px solid #0f3460;
        border-radius: 8px;
    }
    hr { border-color: #333333; }
    </style>
""", unsafe_allow_html=True)

PORTFOLIO_FILE = "paper_portfolio.json"
STARTING_CASH = 10_000.0


# ============================================================
# ניהול Portfolio בקובץ JSON (פשוט, בלי DB)
# ============================================================
def load_portfolio() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {
        "cash": STARTING_CASH,
        "positions": {},   # { "NVDA": {"shares": 5, "avg_price": 120.0} }
        "trades": [],      # רשימת כל העסקאות
    }


def save_portfolio(portfolio: dict):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2, default=str)


def get_current_price(symbol: str) -> float | None:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
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
# פונקציות אינדיקטורים
# ============================================================
def calc_rsi_wilder(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def detect_signals(df: pd.DataFrame, ma_fast: int, ma_slow: int) -> list[str]:
    """מזהה סיגנלים על נתוני הסגירה האחרונים."""
    signals = []
    close = df['Close'].squeeze()
    rsi = calc_rsi_wilder(close, 14)

    ma_f = close.rolling(ma_fast).mean()
    ma_s = close.rolling(ma_slow).mean()

    # Golden Cross
    if (ma_f.iloc[-1] > ma_s.iloc[-1]) and (ma_f.iloc[-2] <= ma_s.iloc[-2]):
        signals.append("🟡 Golden Cross - חצייה שורית!")
    # Death Cross
    if (ma_f.iloc[-1] < ma_s.iloc[-1]) and (ma_f.iloc[-2] >= ma_s.iloc[-2]):
        signals.append("💀 Death Cross - חצייה דובית!")
    # RSI
    if float(rsi.iloc[-1]) < 30:
        signals.append(f"🟢 RSI={rsi.iloc[-1]:.1f} - Oversold, הזדמנות כניסה פוטנציאלית")
    if float(rsi.iloc[-1]) > 70:
        signals.append(f"🔴 RSI={rsi.iloc[-1]:.1f} - Overbought, שקלי מכירה")

    if not signals:
        signals.append("⚪ אין סיגנל חזק כרגע - המתני")
    return signals


@st.cache_data(ttl=300)
def fetch_data(symbol: str, period: str, maf: int, mas: int) -> pd.DataFrame | None:
    try:
        df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
        if df.empty:
            return None
        df['MA_Fast'] = df['Close'].squeeze().rolling(maf).mean()
        df['MA_Slow'] = df['Close'].squeeze().rolling(mas).mean()
        df['RSI'] = calc_rsi_wilder(df['Close'].squeeze(), 14)
        ema12 = df['Close'].squeeze().ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].squeeze().ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
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
timeframe = st.sidebar.selectbox("טווח זמן:", ["1y", "2y", "5y"])
ma_fast_val = st.sidebar.number_input("ממוצע מהיר:", value=50, min_value=1)
ma_slow_val = st.sidebar.number_input("ממוצע איטי:", value=200, min_value=2)

st.sidebar.divider()
st.sidebar.subheader("💰 תיק וירטואלי")
total_val = portfolio_value(portfolio)
gain = total_val - STARTING_CASH
gain_pct = (gain / STARTING_CASH) * 100
st.sidebar.metric("שווי תיק", f"${total_val:,.2f}", f"{gain_pct:+.1f}%")
st.sidebar.metric("מזומן פנוי", f"${portfolio['cash']:,.2f}")
st.sidebar.metric("עסקאות בוצעו", len(portfolio['trades']))

if st.sidebar.button("🔄 איפוס תיק"):
    st.session_state.portfolio = {"cash": STARTING_CASH, "positions": {}, "trades": []}
    save_portfolio(st.session_state.portfolio)
    st.rerun()

# ============================================================
# Tab layout
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 גרף וניתוח",
    "🛒 מסחר וירטואלי",
    "📋 יומן עסקאות",
    "📊 השוואת ביצועים"
])


# ============================================================
# TAB 1: גרף
# ============================================================
with tab1:
    st.title(f"📈 {ticker} - ניתוח טכני")
    data = fetch_data(ticker, timeframe, ma_fast_val, ma_slow_val)

    if data is not None:
        close = data['Close'].squeeze()
        last_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        last_rsi = float(data['RSI'].iloc[-1])
        day_change = ((last_close - prev_close) / prev_close) * 100

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("מחיר", f"${last_close:.2f}", f"{day_change:+.2f}%")
        c2.metric("RSI", f"{last_rsi:.1f}",
                  "Overbought ⚠️" if last_rsi > 70 else ("Oversold 🟢" if last_rsi < 30 else "Neutral"))
        c3.metric("מגמה",
                  "📈 BULLISH" if last_close > float(data['MA_Slow'].iloc[-1]) else "📉 BEARISH")
        macd_val = float(data['MACD'].iloc[-1])
        c4.metric("MACD", f"{macd_val:.3f}", "Bullish" if macd_val > 0 else "Bearish")

        # סיגנלים אוטומטיים
        st.subheader("🚦 סיגנלים אוטומטיים")
        signals = detect_signals(data, ma_fast_val, ma_slow_val)
        for sig in signals:
            st.info(sig)

        # גרף
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            vertical_spacing=0.04, row_heights=[0.6, 0.2, 0.2],
                            subplot_titles=("Price Action", "RSI", "MACD"))

        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'].squeeze(), high=data['High'].squeeze(),
            low=data['Low'].squeeze(), close=close,
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            name="Price"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=data.index, y=data['MA_Fast'].squeeze(),
                                 name=f"MA{ma_fast_val}", line=dict(color='orange', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA_Slow'].squeeze(),
                                 name=f"MA{ma_slow_val}", line=dict(color='cyan', width=2)), row=1, col=1)

        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'].squeeze(),
                                 name="RSI", line=dict(color='magenta', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        colors_hist = ['#26a69a' if v >= 0 else '#ef5350'
                       for v in (data['MACD'] - data['MACD_Signal']).squeeze()]
        fig.add_trace(go.Bar(x=data.index, y=(data['MACD'] - data['MACD_Signal']).squeeze(),
                             marker_color=colors_hist, name="Hist"), row=3, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'].squeeze(),
                                 line=dict(color='yellow', width=1), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD_Signal'].squeeze(),
                                 line=dict(color='orange', width=1), name="Signal"), row=3, col=1)

        fig.update_layout(template='plotly_dark', plot_bgcolor='black', paper_bgcolor='black',
                          height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("לא ניתן להציג נתונים. בדקי את הסימול.")


# ============================================================
# TAB 2: מסחר וירטואלי
# ============================================================
with tab2:
    st.header("🛒 מסחר וירטואלי - Paper Trading")
    st.caption(f"תיק מתחיל ב-${STARTING_CASH:,.0f} | מחירים חיים מ-Yahoo Finance")

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
                st.metric(
                    f"אחזקה ב-{ticker}",
                    f"{pos['shares']} מניות (${ pos_val:,.2f})",
                    f"{pos_gain:+.1f}% מהכניסה (${pos['avg_price']:.2f})"
                )
            else:
                st.info(f"אין אחזקה ב-{ticker} כרגע.")

        with col_trade:
            st.subheader("ביצוע עסקה")
            action = st.radio("פעולה:", ["🟢 קנייה", "🔴 מכירה"], horizontal=True)
            shares_input = st.number_input("כמות מניות:", min_value=1, max_value=1000, value=1)
            trade_value = shares_input * current_price

            st.write(f"**עלות עסקה: ${trade_value:,.2f}**")

            note = st.text_input("הערה (אופציונלי):", placeholder="למה ביצעתי את העסקה?")

            if st.button("✅ בצע עסקה", type="primary"):
                p = st.session_state.portfolio

                if "קנייה" in action:
                    if p['cash'] >= trade_value:
                        p['cash'] -= trade_value
                        if ticker not in p['positions']:
                            p['positions'][ticker] = {"shares": 0, "avg_price": 0.0}
                        pos = p['positions'][ticker]
                        total_shares = pos['shares'] + shares_input
                        pos['avg_price'] = (
                            (pos['shares'] * pos['avg_price'] + shares_input * current_price)
                            / total_shares
                        )
                        pos['shares'] = total_shares
                        p['trades'].append({
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "symbol": ticker,
                            "action": "BUY",
                            "shares": shares_input,
                            "price": current_price,
                            "total": trade_value,
                            "note": note
                        })
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
                        p['trades'].append({
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "symbol": ticker,
                            "action": "SELL",
                            "shares": shares_input,
                            "price": current_price,
                            "total": trade_value,
                            "pnl": round(pnl, 2),
                            "note": note
                        })
                        save_portfolio(p)
                        color = "✅" if pnl >= 0 else "❌"
                        st.success(f"{color} מכרת {shares_input} מניות | רווח/הפסד: ${pnl:+.2f}")
                        st.rerun()
                    else:
                        st.error("אין מספיק מניות למכירה.")
    else:
        st.error("לא ניתן לטעון מחיר. בדקי את הסימול.")


# ============================================================
# TAB 3: יומן עסקאות
# ============================================================
with tab3:
    st.header("📋 יומן עסקאות")

    trades = portfolio['trades']
    if trades:
        df_trades = pd.DataFrame(trades)

        # סיכום מהיר
        sells = df_trades[df_trades['action'] == 'SELL']
        if not sells.empty and 'pnl' in sells.columns:
            total_pnl = sells['pnl'].sum()
            winners = (sells['pnl'] > 0).sum()
            losers = (sells['pnl'] < 0).sum()

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("סה\"כ רווח/הפסד ממומש", f"${total_pnl:+.2f}",
                      "רווח" if total_pnl >= 0 else "הפסד")
            s2.metric("עסקאות מנצחות", winners)
            s3.metric("עסקאות מפסידות", losers)
            win_r = winners / (winners + losers) * 100 if (winners + losers) > 0 else 0
            s4.metric("Win Rate", f"{win_r:.0f}%")

        st.divider()

        # טבלה עם צבעים
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

        # ייצוא
        csv = df_trades.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ הורד יומן כ-CSV", csv, "trades_journal.csv", "text/csv")
    else:
        st.info("עדיין אין עסקאות. עברי לטאב 'מסחר וירטואלי' כדי להתחיל.")


# ============================================================
# TAB 4: השוואת ביצועים
# ============================================================
with tab4:
    st.header("📊 השוואה: התיק שלך vs השוק")

    trades = portfolio['trades']
    if len(trades) >= 2:
        df_t = pd.DataFrame(trades)
        df_t['date'] = pd.to_datetime(df_t['date'])

        # ערך תיק לאורך זמן
        snapshots = []
        running_cash = STARTING_CASH
        running_positions = {}

        for _, row in df_t.sort_values('date').iterrows():
            if row['action'] == 'BUY':
                running_cash -= row['total']
                sym = row['symbol']
                if sym not in running_positions:
                    running_positions[sym] = {'shares': 0, 'avg_price': 0.0}
                p = running_positions[sym]
                new_shares = p['shares'] + row['shares']
                p['avg_price'] = (p['shares'] * p['avg_price'] + row['shares'] * row['price']) / new_shares
                p['shares'] = new_shares
            else:
                running_cash += row['total']
                sym = row['symbol']
                if sym in running_positions:
                    running_positions[sym]['shares'] -= row['shares']
                    if running_positions[sym]['shares'] <= 0:
                        del running_positions[sym]

            snapshots.append({
                'date': row['date'],
                'portfolio_value': running_cash + sum(
                    pos['shares'] * pos['avg_price']
                    for pos in running_positions.values()
                )
            })

        snap_df = pd.DataFrame(snapshots).set_index('date')
        snap_df['normalized'] = snap_df['portfolio_value'] / STARTING_CASH

        # נתוני השוק לאותה תקופה
        start_date = snap_df.index.min().strftime("%Y-%m-%d")
        try:
            spy = yf.download("SPY", start=start_date, progress=False, auto_adjust=True)
            if not spy.empty:
                spy_norm = spy['Close'].squeeze() / float(spy['Close'].squeeze().iloc[0])
            else:
                spy_norm = None
        except:
            spy_norm = None

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(
            x=snap_df.index, y=snap_df['normalized'],
            name="התיק שלי", line=dict(color='#26a69a', width=2.5)
        ))
        if spy_norm is not None:
            fig_comp.add_trace(go.Scatter(
                x=spy_norm.index, y=spy_norm,
                name="SPY (שוק)", line=dict(color='#aaaaaa', width=1.5, dash='dash')
            ))

        fig_comp.add_hline(y=1.0, line_dash="dot", line_color="#555555", annotation_text="נקודת פתיחה")
        fig_comp.update_layout(
            template='plotly_dark', plot_bgcolor='black', paper_bgcolor='black',
            height=450, title="ביצועי התיק לעומת ה-S&P 500",
            yaxis_title="צמיחה יחסית ($1 = התחלה)"
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # מדדים סופיים
        final_val = float(snap_df['portfolio_value'].iloc[-1])
        my_return = (final_val - STARTING_CASH) / STARTING_CASH * 100
        st.metric("תשואה כוללת שלך", f"{my_return:+.1f}%",
                  f"${final_val - STARTING_CASH:+,.2f} על ${STARTING_CASH:,.0f}")

    else:
        st.info("צריך לפחות 2 עסקאות כדי להציג השוואה. התחילי לסחור בטאב 'מסחר וירטואלי'!")
        st.write("**איך להתחיל:**")
        st.write("1. עברי לגרף, קראי את הסיגנלים")
        st.write("2. עברי לטאב 'מסחר וירטואלי' ובצעי קנייה וירטואלית")
        st.write("3. חזרי לכאן כדי לראות איך הביצועים שלך לעומת השוק")