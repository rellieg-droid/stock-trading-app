"""
Alpha Charts Pro - Professional Stock Analysis
תיקון מרכזי: שימוש ב-Ticker.history() במקום yf.download()
כדי להימנע מבעיות MultiIndex
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json, os, requests
from streamlit_autorefresh import st_autorefresh

# ── Anthropic API Key ──
# אפשרות 1: קובץ .streamlit/secrets.toml  → ANTHROPIC_API_KEY = "sk-ant-..."
# אפשרות 2: משתנה סביבה                    → set ANTHROPIC_API_KEY=sk-ant-...
# אפשרות 3: הכנס ישירות בשורה הבאה (לא מומלץ לפרודקשן)
try:
    ANTHROPIC_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
except Exception:
    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def ai_headers():
    """Headers לקריאת Anthropic API"""
    return {
        "Content-Type":      "application/json",
        "x-api-key":         ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
    }

# ── Page Config ──
st.set_page_config(
    page_title="Alpha Charts Pro",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed",
)
st_autorefresh(interval=60000, key="ar")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── בסיס ── */
html,body,.stApp {
  font-family:'Heebo',sans-serif!important;
  background:#0d1117!important;
  color:#c9d1d9!important;
  direction:rtl!important;
}
.block-container {
  padding:.5rem 1rem!important;
  max-width:100%!important;
  direction:rtl!important;
  text-align:right!important;
}

/* ── RTL על כל האלמנטים ── */
div,p,span,label,h1,h2,h3,h4,h5 { direction:rtl!important; }
.stMarkdown, .stText { text-align:right!important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background:#010409!important; border-right:1px solid #21262d!important; min-width:260px!important; }
div[data-testid="stSidebarContent"] { direction:rtl!important; padding:.5rem; text-align:right!important; }

/* ── מטריקות ── */
.stMetric { background:#161b22!important; border:1px solid #21262d!important; border-radius:10px!important; padding:12px!important; }
[data-testid="stMetricValue"] { font-family:'JetBrains Mono',monospace!important; font-weight:600!important; color:#e6edf3!important; }
[data-testid="stMetricLabel"] { color:#8b949e!important; text-transform:uppercase; font-weight:500!important; }

/* ── טאבים ── */
.stTabs [data-baseweb="tab-list"] { background:#161b22!important; border-radius:10px!important; padding:3px!important; gap:3px!important; border:1px solid #21262d!important; }
.stTabs [data-baseweb="tab"] { background:transparent!important; color:#8b949e!important; border-radius:7px!important; border:none!important; font-weight:500!important; }
.stTabs [aria-selected="true"] { background:#1f6feb!important; color:white!important; font-weight:700!important; }

/* ── Radio — hide dots, show as pill buttons ── */
div[role="radiogroup"] {
  display: flex !important;
  flex-direction: row !important;
  gap: 2px !important;
  background: #161b22 !important;
  border: 1px solid #30363d !important;
  border-radius: 8px !important;
  padding: 3px !important;
}
div[role="radiogroup"] label {
  background: transparent !important;
  border-radius: 6px !important;
  padding: 4px 10px !important;
  cursor: pointer !important;
  transition: all .12s !important;
}
div[role="radiogroup"] label:has(input:checked) {
  background: #1f6feb !important;
}
div[role="radiogroup"] label span,
div[role="radiogroup"] label p,
.stRadio label span,
.stRadio label p {
  color: #8b949e !important;
  font-size: .74rem !important;
  font-weight: 600 !important;
}
div[role="radiogroup"] label:has(input:checked) span,
div[role="radiogroup"] label:has(input:checked) p {
  color: #ffffff !important;
}
div[role="radiogroup"] label:hover span,
div[role="radiogroup"] label:hover p {
  color: #e6edf3 !important;
}
/* hide radio dot */
div[role="radiogroup"] input[type="radio"] {
  display: none !important;
}
div[role="radiogroup"] input:checked + div,
div[role="radiogroup"] [data-testid="stMarkdownContainer"] {
  display: none !important;
}

/* ── Buttons — trading style ── */
.stButton > button {
  background: #161b22 !important;
  color: #c9d1d9 !important;
  border: 1px solid #30363d !important;
  border-radius: 7px !important;
  font-family: 'Heebo', sans-serif !important;
  font-size: .78rem !important;
  font-weight: 600 !important;
  padding: 5px 12px !important;
  transition: all .12s !important;
  white-space: nowrap !important;
}
.stButton > button:hover {
  background: #21262d !important;
  color: #e6edf3 !important;
  border-color: #58a6ff !important;
}
.stButton > button[kind="primary"] {
  background: #1f6feb !important;
  color: #ffffff !important;
  border-color: #1f6feb !important;
}
.stButton > button[kind="primary"]:hover {
  background: #388bfd !important;
  border-color: #388bfd !important;
}


/* ── שדות קלט ── */
.stTextInput input,.stNumberInput input {
  background:#161b22!important; color:#e6edf3!important;
  border:1px solid #30363d!important; border-radius:8px!important;
  text-align:right!important; direction:rtl!important;
}

/* ── התראות ── */
.stSuccess { background:rgba(46,160,67,.1)!important;  border:1px solid rgba(46,160,67,.3)!important;  border-radius:8px!important; }
.stError   { background:rgba(248,81,73,.1)!important;  border:1px solid rgba(248,81,73,.3)!important;  border-radius:8px!important; }
.stInfo    { background:rgba(31,111,235,.1)!important; border:1px solid rgba(31,111,235,.3)!important; border-radius:8px!important; }
.stWarning { background:rgba(210,153,34,.1)!important; border:1px solid rgba(210,153,34,.3)!important; border-radius:8px!important; }
hr { border-color:#21262d!important; }

/* ── Sidebar btn ── */
button[data-testid="collapsedControl"] { background:#21262d!important; border:1px solid #30363d!important; border-radius:7px!important; }
button[data-testid="collapsedControl"] svg { fill:#8b949e!important; }

/* ── טבלאות ── */
[data-testid="stDataFrame"] th { background:#161b22!important; color:#c9d1d9!important; font-size:.75rem!important; text-transform:uppercase; font-weight:700!important; }
[data-testid="stDataFrame"] td { background:#0d1117!important; border-color:#21262d!important; font-family:'JetBrains Mono',monospace!important; color:#e6edf3!important; font-size:.82rem!important; }
[data-testid="stDataFrame"] * { color:#e6edf3!important; }

/* ── Checkbox labels (Indicators) ── */
.stCheckbox label,
.stCheckbox label p,
.stCheckbox label span {
  color: #c9d1d9 !important;
  font-size: .82rem !important;
  font-weight: 500 !important;
}
.stCheckbox label:hover span {
  color: #e6edf3 !important;
}
/* checked state */
.stCheckbox input:checked + label span,
.stCheckbox input:checked ~ label span {
  color: #e6edf3 !important;
  font-weight: 700 !important;
}

/* ── Plotly tooltip — force LTR so box and text stay together ── */
.js-plotly-plot .plotly .hoverlayer {
  direction: ltr !important;
  unicode-bidi: isolate !important;
}
.js-plotly-plot .plotly .hoverlayer .hovertext {
  direction: ltr !important;
  text-align: left !important;
}

/* ── Radio text (time range) ── */
.stRadio label p, .stRadio label span, div[role="radiogroup"] label span {
  color: #e6edf3 !important;
  font-size: .82rem !important;
  font-weight: 600 !important;
}

/* ── tooltip box ── */
.tooltip-box {
  background:#161b22;
  border:1px solid #30363d;
  border-radius:10px;
  padding:8px 12px;
  font-size:.75rem;
  color:#8b949e;
  margin-top:4px;
  line-height:1.5;
}

/* ── Responsive font sizes ── */
/* מחשב נייד / ברירת מחדל */
:root {
  --fs-xl:   1.9rem;
  --fs-lg:   1.2rem;
  --fs-md:   .88rem;
  --fs-sm:   .78rem;
  --fs-xs:   .68rem;
  --fs-xxs:  .62rem;
  --fs-metric: 1.1rem;
  --fs-tab:    .82rem;
}
/* טאבלט */
@media (max-width:1024px) {
  :root {
    --fs-xl:   1.5rem;
    --fs-lg:   1.05rem;
    --fs-md:   .84rem;
    --fs-sm:   .75rem;
    --fs-xs:   .65rem;
    --fs-xxs:  .58rem;
    --fs-metric: .95rem;
    --fs-tab:    .76rem;
  }
  .block-container { padding:.4rem .6rem!important; }
  section[data-testid="stSidebar"] { min-width:220px!important; }
}
/* פלאפון */
@media (max-width:768px) {
  :root {
    --fs-xl:   1.25rem;
    --fs-lg:   .95rem;
    --fs-md:   .82rem;
    --fs-sm:   .72rem;
    --fs-xs:   .64rem;
    --fs-xxs:  .56rem;
    --fs-metric: .88rem;
    --fs-tab:    .7rem;
  }
  .block-container { padding:.3rem .4rem!important; }
  [data-testid="stMetricValue"] { font-size:.88rem!important; }
  .stTabs [data-baseweb="tab"] { font-size:.7rem!important; padding:4px 8px!important; }
}
/* מסך גדול */
@media (min-width:1400px) {
  :root {
    --fs-xl:   2.2rem;
    --fs-lg:   1.35rem;
    --fs-md:   .92rem;
    --fs-sm:   .82rem;
    --fs-xs:   .72rem;
    --fs-metric: 1.2rem;
  }
}

[data-testid="stMetricValue"] { font-size:var(--fs-metric)!important; }
[data-testid="stMetricLabel"] { font-size:var(--fs-xxs)!important; }
.stTabs [data-baseweb="tab"] { font-size:var(--fs-tab)!important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──
DEV_MODE        = True   # ← שני ל-False כשהאפליקציה מוכנה לייצור
PORTFOLIO_FILE  = "paper_portfolio.json"
USER_DATA_FILE  = "user_data.json"       # שמירת watchlist, התראות, תיק
STARTING_CASH   = 10_000.0
BG, GR = '#0d1117', '#1c2128'

# ── User Data Persistence ──
def load_user_data() -> dict:
    """טוען את כל נתוני המשתמש מהקובץ"""
    if DEV_MODE:
        return {"watchlist":[],"alerts_list":[],"portfolio_positions":[],"ec_symbols":[],"cmp_symbols":[],"recent":[]}
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "watchlist":           [],
        "alerts_list":         [],
        "portfolio_positions": [],
        "ec_symbols":          [],
        "recent":              [],
        "cmp_symbols":         [],
    }

def save_user_data():
    """שומר את כל נתוני המשתמש לקובץ"""
    if DEV_MODE:
        return   # לא שומר בזמן פיתוח
    data = {
        "watchlist":           st.session_state.get("watchlist", []),
        "alerts_list":         st.session_state.get("alerts_list", []),
        "portfolio_positions": st.session_state.get("portfolio_positions", []),
        "ec_symbols":          st.session_state.get("ec_symbols", []),
        "cmp_symbols":         st.session_state.get("cmp_symbols", []),
        "recent":              st.session_state.get("recent", []),
    }
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        st.warning(f"לא ניתן לשמור נתונים: {e}")


# period → (yfinance period, interval)
PERIODS = {
    "1D":  ("1d",   "5m"),
    "5D":  ("5d",   "15m"),
    "1M":  ("1mo",  "1d"),
    "6M":  ("6mo",  "1d"),
    "YTD": ("ytd",  "1d"),
    "1Y":  ("1y",   "1d"),
    "5Y":  ("5y",   "1wk"),
    "MAX": ("max",  "1mo"),
}

COMPANY_MAP = {
    "apple":"AAPL","microsoft":"MSFT","google":"GOOGL","alphabet":"GOOGL",
    "amazon":"AMZN","meta":"META","facebook":"META","tesla":"TSLA",
    "nvidia":"NVDA","netflix":"NFLX","amd":"AMD","intel":"INTC",
    "uber":"UBER","airbnb":"ABNB","palantir":"PLTR","coinbase":"COIN",
    "teva":"TEVA","טבע":"TEVA","check point":"CHKP","nice":"NICE",
    "elbit":"ESLT","אלביט":"ESLT",
}

CATEGORIES = {
    "🤖 AI":      ["NVDA","MSFT","GOOGL","META","PLTR","ARM"],
    "📱 Tech":    ["AAPL","AMZN","TSLA","NFLX","UBER","ABNB"],
    "🏦 Finance": ["JPM","GS","BAC","V","MA","COIN"],
    "🇮🇱 ישראל": ["TEVA","CHKP","NICE","ESLT","ICL"],
}
CATEGORY_DESCS = {
    "🤖 AI":      "מניות מובילות בתחום הבינה המלאכותית ומחשוב מואץ",
    "📱 Tech":    "ענקיות הטכנולוגיה, אי-קומרס ומוביליות",
    "🏦 Finance": "בנקים, כרטיסי אשראי וקריפטו",
    "🇮🇱 ישראל": "מניות מובילות בבורסה תל אביב",
}

STOCK_DESCS = {
    "NVDA":  ("NVIDIA",          "מעבדי AI ו-GPU — מוביל עולמי"),
    "MSFT":  ("Microsoft",       "ענן, Office ו-Azure"),
    "GOOGL": ("Alphabet",        "חיפוש, YouTube ו-Google Cloud"),
    "META":  ("Meta",            "פייסבוק, אינסטגרם ווואטסאפ"),
    "PLTR":  ("Palantir",        "ניתוח נתונים לממשלות וחברות"),
    "ARM":   ("ARM Holdings",    "עיצוב שבבים לכל המכשירים"),
    "AAPL":  ("Apple",           "אייפון, מק, שירותים ו-Vision Pro"),
    "AMZN":  ("Amazon",          "אי-קומרס, AWS ולוגיסטיקה"),
    "TSLA":  ("Tesla",           "רכבים חשמליים ואנרגיה"),
    "NFLX":  ("Netflix",         "סטרימינג ותוכן מקורי"),
    "UBER":  ("Uber",            "שיתוף נסיעות ומשלוחי אוכל"),
    "ABNB":  ("Airbnb",          "השכרת נכסים לטווח קצר"),
    "JPM":   ("JPMorgan",        "הבנק הגדול ביותר בארהב"),
    "GS":    ("Goldman Sachs",   "בנק השקעות מוביל"),
    "BAC":   ("Bank of America", "בנק קמעונאי וממשלתי"),
    "V":     ("Visa",            "רשת תשלומים גלובלית"),
    "MA":    ("Mastercard",      "תשלומים דיגיטליים עולמיים"),
    "COIN":  ("Coinbase",        "פלטפורמת מסחר בקריפטו"),
    "TEVA":  ("טבע",             "תרופות גנריות — ענקית פארמה"),
    "CHKP":  ("Check Point",     "אבטחת סייבר מובילה"),
    "NICE":  ("NICE Systems",    "תוכנה לניתוח שיחות ו-AI"),
    "ESLT":  ("אלביט",           "מערכות הגנה ואוויוניקה"),
    "ICL":   ("ICL Group",       "מינרלים וחומרי גלם"),
}

# ── Helpers ──
def resolve(raw: str) -> str:
    return COMPANY_MAP.get(raw.strip().lower(), raw.strip().upper())

def is_il(t: str) -> bool:
    return t.upper().endswith((".TA", ".TLV"))

def get_sym(t: str) -> str:
    return "₪" if is_il(t) else "$"

def fmt_big(v, s="$") -> str:
    if v is None: return "N/A"
    try:
        v = float(v)
        if abs(v) >= 1e12: return f"{s}{v/1e12:.2f}T"
        if abs(v) >= 1e9:  return f"{s}{v/1e9:.2f}B"
        if abs(v) >= 1e6:  return f"{s}{v/1e6:.1f}M"
        return f"{s}{v:,.0f}"
    except: return "N/A"

# ── Portfolio ──
def load_pf() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"cash": STARTING_CASH, "positions": {}, "trades": []}

def save_pf(p: dict):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(p, f, indent=2, default=str)

@st.cache_data(ttl=60)
def get_live_price(sym: str) -> float | None:
    try:
        h = yf.Ticker(sym).history(period="1d")
        if h.empty: return None
        return float(h['Close'].iloc[-1])
    except: return None

def pf_val(p: dict) -> float:
    total = p['cash']
    for sym, pos in p['positions'].items():
        pr = get_live_price(sym)
        if pr: total += pos['shares'] * pr
    return total

# ── DATA LAYER ──
# תיקון מרכזי: שימוש ב-Ticker.history() שמחזיר DataFrame נקי
@st.cache_data(ttl=300)
def load_ohlcv(symbol: str, period: str, interval: str) -> pd.DataFrame | None:
    """
    טוען נתוני OHLCV ומחזיר DataFrame נקי עם אינדיקטורים.
    משתמש ב-Ticker.history() כדי להימנע מבעיות MultiIndex.
    """
    try:
        tk = yf.Ticker(symbol)
        df = tk.history(period=period, interval=interval, auto_adjust=True)

        if df is None or df.empty:
            return None

        # וודא שיש עמודות בסיסיות
        for col in ['Open', 'High', 'Low', 'Close']:
            if col not in df.columns:
                return None

        # המרה לfloat נקי
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'Volume' in df.columns:
            df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

        # הסרת שורות עם NaN
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

        if len(df) < 3:
            return None

        cl = df['Close']
        n  = len(df)

        # ── אינדיקטורים ──
        df['MA20']  = cl.rolling(min(20, n)).mean()
        df['MA50']  = cl.rolling(min(50, n)).mean()
        df['MA200'] = cl.rolling(min(200, n)).mean()

        # RSI (Wilder)
        delta = cl.diff()
        gain  = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
        loss  = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

        # MACD
        e12 = cl.ewm(span=12, adjust=False).mean()
        e26 = cl.ewm(span=26, adjust=False).mean()
        df['MACD']   = e12 - e26
        df['MACD_S'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_H'] = df['MACD'] - df['MACD_S']

        # Bollinger
        m   = cl.rolling(20).mean()
        std = cl.rolling(20).std()
        df['BB_U'] = m + 2 * std
        df['BB_L'] = m - 2 * std

        return df

    except Exception as e:
        st.error(f"שגיאה בטעינת {symbol}: {e}")
        return None

@st.cache_data(ttl=3600)
def load_info(symbol: str) -> dict:
    try:
        return yf.Ticker(symbol).info
    except:
        return {}

@st.cache_data(ttl=3600)
def load_quarterly(symbol: str) -> list | None:
    try:
        qf = yf.Ticker(symbol).quarterly_financials
        if qf is None or qf.empty:
            return None
        rows, prev = [], None
        for col in qf.columns[:6]:
            try:
                rev = float(qf.loc['Total Revenue',col])    if 'Total Revenue'    in qf.index else None
                net = float(qf.loc['Net Income',col])        if 'Net Income'        in qf.index else None
                ops = float(qf.loc['Operating Income',col])  if 'Operating Income'  in qf.index else None
                mg  = (net / rev * 100) if (rev and net and rev != 0) else None
                qc  = ((net - prev) / abs(prev) * 100) if (prev and net) else None
                def fm(v):
                    if not v: return "N/A"
                    v = float(v)
                    if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
                    if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
                    return f"${v:,.0f}"
                q = pd.Timestamp(col)
                rows.append({
                    "רבעון":       f"Q{q.quarter} {q.year}",
                    "הכנסות":      fm(rev),
                    "רווח נקי":    fm(net),
                    "רווח תפעולי": fm(ops),
                    "שולי רווח":   f"{mg:.1f}%" if mg else "N/A",
                    "שינוי":       f"{qc:+.1f}%" if qc else "—",
                    "_n": net, "_r": rev,
                })
                prev = net
            except: pass
        return rows or None
    except: return None

@st.cache_data(ttl=1800)
def load_hot_stocks() -> list:
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=ai_headers(),
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 400,
                  "messages": [{"role": "user", "content":
                    'Return ONLY JSON array (no markdown), 5 hot US stocks now: '
                    '[{"ticker":"NVDA","name":"NVIDIA","reason":"AI surge","direction":"bullish"}]. '
                    'direction: bullish or bearish. reason max 4 words.'}]},
            timeout=12
        )
        if r.status_code == 200:
            txt = r.json()['content'][0]['text'].strip().replace("```json","").replace("```","")
            return json.loads(txt)
    except: pass
    return [
        {"ticker": "NVDA", "name": "NVIDIA",    "reason": "AI מוביל",     "direction": "bullish"},
        {"ticker": "AAPL", "name": "Apple",      "reason": "iPhone חזק",   "direction": "bullish"},
        {"ticker": "MSFT", "name": "Microsoft",  "reason": "Azure AI",     "direction": "bullish"},
        {"ticker": "TSLA", "name": "Tesla",       "reason": "תנודתיות EV", "direction": "bearish"},
        {"ticker": "META", "name": "Meta",        "reason": "Ads שיא",     "direction": "bullish"},
    ]


# ── Analyst Snapshot ──
@st.cache_data(ttl=3600)
def load_analyst_data(symbol: str) -> dict:
    try:
        tk   = yf.Ticker(symbol)
        info = tk.info
        rating      = info.get("recommendationKey", None)
        n_analysts  = info.get("numberOfAnalystOpinions", None)
        target_mean = info.get("targetMeanPrice", None)
        target_high = info.get("targetHighPrice", None)
        target_low  = info.get("targetLowPrice",  None)
        eps_current = info.get("trailingEps", None)
        eps_forward = info.get("forwardEps", None)
        eps_chg = ((eps_forward - eps_current) / abs(eps_current) * 100) if (eps_current and eps_forward and eps_current != 0) else None
        rev_growth = info.get("revenueGrowth", None)
        if rev_growth: rev_growth *= 100
        last_change = None
        try:
            ud = tk.upgrades_downgrades
            if ud is not None and not ud.empty:
                row = ud.iloc[0]
                last_change = {"firm": str(row.get("Firm","")), "to": str(row.get("ToGrade","")), "from_": str(row.get("FromGrade",""))}
        except: pass
        rating_map = {
            "strong_buy":   ("Strong Buy",   "#2ea043", "🟢"),
            "buy":          ("Buy",           "#3fb950", "🟢"),
            "hold":         ("Hold",          "#d29922", "🟡"),
            "underperform": ("Underperform",  "#f85149", "🔴"),
            "sell":         ("Sell",          "#f85149", "🔴"),
        }
        rl, rc, ri = rating_map.get(str(rating).lower() if rating else "", ("N/A","#8b949e","⚪"))
        return {"rating":rl, "rc":rc, "ri":ri, "n":n_analysts,
                "tm":target_mean, "th":target_high, "tl":target_low,
                "eps_chg":eps_chg, "rev_g":rev_growth,
                "last":last_change, "eps_fwd":eps_forward}
    except:
        return {}


def render_analyst_snapshot(symbol: str, cur_price: float, ccy_s: str):
    """כרטיס Analyst Snapshot - קונצנזוס, מחירי יעד, תחזיות"""
    with st.spinner("טוען נתוני אנליסטים..."):
        d = load_analyst_data(symbol)

    if not d or not d.get("n"):
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;' +
            'padding:20px;text-align:center;">' +
            '<div style="color:#8b949e;font-size:.85rem;">📊 נתוני אנליסטים אינם זמינים עבור ' + symbol + '</div></div>',
            unsafe_allow_html=True
        )
        return

    rating = d["rating"]; rc = d["rc"]; ri = d["ri"]
    n      = d["n"];      tm = d["tm"]; th = d["th"]; tl = d["tl"]
    eps_chg = d["eps_chg"]; rev_g = d["rev_g"]
    last   = d["last"];   eps_fwd = d["eps_fwd"]

    # פוטנציאל
    upside_txt = "N/A"; uc = "#8b949e"
    if tm and cur_price and cur_price > 0:
        ups = (tm - cur_price) / cur_price * 100
        uc  = "#3fb950" if ups >= 0 else "#f85149"
        upside_txt = ("▲" if ups >= 0 else "▼") + f" {abs(ups):.1f}% " + ("אפסייד" if ups >= 0 else "דאונסייד")

    # סנטימנט
    sent_map = {
        "Strong Buy":   ("חיובי מאוד", "#2ea043"),
        "Buy":          ("חיובי",      "#3fb950"),
        "Hold":         ("נייטרלי",    "#d29922"),
        "Underperform": ("שלילי מתון", "#f85149"),
        "Sell":         ("שלילי",      "#f85149"),
    }
    sl, sc_ = sent_map.get(rating, ("לא ידוע", "#8b949e"))

    def fv(v, p="$", dec=2):
        return f"{p}{float(v):,.{dec}f}" if v else "N/A"

    def fp(v):
        if v is None: return '<span style="color:#8b949e;">N/A</span>'
        c = "#3fb950" if v > 0 else "#f85149"
        arr = "▲" if v > 0 else "▼"
        return f'<span style="color:{c};font-weight:600;">{arr} {abs(v):.1f}%</span>'

    last_html = (
        f'<div style="font-size:.76rem;color:#e6edf3;font-weight:500;">{last["firm"]}</div>'
        f'<div style="font-size:.7rem;color:#8b949e;">{last.get("from_","")} → <b style="color:#e6edf3;">{last.get("to","")}</b></div>'
    ) if last else '<div style="color:#8b949e;font-size:.76rem;">N/A</div>'

    cell = 'background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:11px;'
    lbl  = 'color:#8b949e;font-size:.6rem;text-transform:uppercase;margin-bottom:3px;'
    mono = 'font-family:"JetBrains Mono",monospace;font-size:.92rem;font-weight:700;'

    st.markdown(f"""
<div style="background:#161b22;border:1px solid #21262d;border-radius:14px;padding:18px 20px;margin-top:10px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
    <div>
      <div style="font-size:.88rem;font-weight:700;color:#e6edf3;">📊 Analyst Snapshot — {symbol}</div>
      <div style="color:#8b949e;font-size:.7rem;margin-top:2px;">קונצנזוס אנליסטים, מחירי יעד ותחזיות שוק</div>
    </div>
    <span style="font-size:1.6rem;line-height:1;">{ri}</span>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;margin-bottom:9px;">
    <div style="{cell}text-align:center;">
      <div style="{lbl}">דירוג קונצנזוס</div>
      <div style="font-size:1.05rem;font-weight:700;color:{rc};">{rating}</div>
    </div>
    <div style="{cell}text-align:center;">
      <div style="{lbl}">סנטימנט</div>
      <div style="font-size:.9rem;font-weight:600;color:{sc_};">{sl}</div>
    </div>
    <div style="{cell}text-align:center;">
      <div style="{lbl}">מספר אנליסטים</div>
      <div style="{mono}color:#e6edf3;">{n}</div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:9px;margin-bottom:9px;">
    <div style="{cell}text-align:center;">
      <div style="{lbl}">יעד ממוצע</div>
      <div style="{mono}color:#e6edf3;">{fv(tm,ccy_s)}</div>
    </div>
    <div style="{cell}text-align:center;">
      <div style="{lbl}">יעד גבוה</div>
      <div style="{mono}color:#3fb950;">{fv(th,ccy_s)}</div>
    </div>
    <div style="{cell}text-align:center;">
      <div style="{lbl}">יעד נמוך</div>
      <div style="{mono}color:#f85149;">{fv(tl,ccy_s)}</div>
    </div>
    <div style="background:{uc}18;border:1px solid {uc}44;border-radius:10px;padding:11px;text-align:center;">
      <div style="{lbl}">פוטנציאל</div>
      <div style="font-size:.88rem;font-weight:700;color:{uc};">{upside_txt}</div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;">
    <div style="{cell}">
      <div style="{lbl}">שינוי אומדן EPS</div>
      <div style="font-size:.86rem;">{fp(eps_chg)}</div>
      <div style="color:#8b949e;font-size:.62rem;margin-top:2px;">Forward EPS: {fv(eps_fwd,"$")}</div>
    </div>
    <div style="{cell}">
      <div style="{lbl}">צמיחת הכנסות YoY</div>
      <div style="font-size:.86rem;">{fp(rev_g)}</div>
    </div>
    <div style="{cell}">
      <div style="{lbl}">עדכון אחרון</div>
      {last_html}
    </div>
  </div>

  <div style="color:#8b949e;font-size:.63rem;margin-top:10px;padding-top:8px;border-top:1px solid #21262d;">
    ⚠️ נתוני אנליסטים הם הערכות בלבד ואינם מהווים ייעוץ השקעות.
  </div>
</div>
""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════
# POSITION SIZING & INVESTMENT DECISION MODULE
# ══════════════════════════════════════════════════════════════

def calc_fundamental_score(info: dict) -> dict:
    """
    ציון פונדמנטלי 0-100 לפי: צמיחה, רווחיות, EPS, שולי רווח, מכפילים.
    מחזיר dict עם score ופירוט.
    """
    score = 0
    details = {}
    max_pts = 0

    # ── צמיחת הכנסות (20 נקודות) ──
    rev_g = info.get("revenueGrowth")
    if rev_g is not None:
        max_pts += 20
        rg = float(rev_g) * 100
        pts = min(20, max(0, rg * 1.0))   # כל 1% = 1 נקודה, מקס 20
        score += pts
        details["צמיחת הכנסות"] = (f"{rg:+.1f}%", pts, 20)

    # ── רווחיות - Net Margin (20 נקודות) ──
    net_m = info.get("profitMargins")
    if net_m is not None:
        max_pts += 20
        nm = float(net_m) * 100
        pts = min(20, max(0, nm * 0.8))
        score += pts
        details["שולי רווח נקי"] = (f"{nm:.1f}%", pts, 20)

    # ── EPS Growth (20 נקודות) ──
    eps_t = info.get("trailingEps"); eps_f = info.get("forwardEps")
    if eps_t and eps_f and eps_t != 0:
        max_pts += 20
        eps_g = (eps_f - eps_t) / abs(eps_t) * 100
        pts = min(20, max(0, eps_g * 0.5))
        score += pts
        details["צמיחת EPS"] = (f"{eps_g:+.1f}%", pts, 20)

    # ── P/E Ratio (20 נקודות) ──
    pe = info.get("trailingPE")
    if pe is not None:
        max_pts += 20
        pe = float(pe)
        if pe <= 0:   pts = 5
        elif pe <= 15: pts = 20
        elif pe <= 25: pts = 15
        elif pe <= 40: pts = 10
        else:          pts = 5
        score += pts
        details["P/E"] = (f"{pe:.1f}", pts, 20)

    # ── ROE (20 נקודות) ──
    roe = info.get("returnOnEquity")
    if roe is not None:
        max_pts += 20
        r = float(roe) * 100
        pts = min(20, max(0, r * 1.0))
        score += pts
        details["ROE"] = (f"{r:.1f}%", pts, 20)

    normalized = round(score / max_pts * 100) if max_pts > 0 else None
    return {"score": normalized, "raw": score, "max": max_pts, "details": details}


def calc_technical_score(df: pd.DataFrame) -> dict:
    """
    ציון טכני 0-100 לפי: מגמה, נר אחרון, MAs, Volume, תמיכה/התנגדות.
    """
    if df is None or len(df) < 5:
        return {"score": None, "details": {}}

    score = 0; max_pts = 0; details = {}
    cl = df['Close'].astype(float)
    lc = float(cl.iloc[-1])
    op = float(df['Open'].astype(float).iloc[-1])

    # ── מגמה MA (25 נקודות) ──
    ma_pts = 0; ma_max = 25
    ma50  = float(df['MA50'].iloc[-1])  if 'MA50'  in df.columns and not pd.isna(df['MA50'].iloc[-1])  else None
    ma200 = float(df['MA200'].iloc[-1]) if 'MA200' in df.columns and not pd.isna(df['MA200'].iloc[-1]) else None
    if ma50:
        max_pts += 12
        if lc > ma50:  ma_pts += 12; details["מעל MA50"] = ("+", 12, 12)
        else:           details["מתחת MA50"] = ("-", 0, 12)
    if ma200:
        max_pts += 13
        if lc > ma200: ma_pts += 13; details["מעל MA200"] = ("+", 13, 13)
        else:           details["מתחת MA200"] = ("-", 0, 13)
    score += ma_pts

    # ── נר אחרון (20 נקודות) ──
    max_pts += 20
    h = float(df['High'].astype(float).iloc[-1]); l = float(df['Low'].astype(float).iloc[-1])
    body = abs(lc - op); rng = h - l if h != l else .001
    br = body / rng; cp = (lc - l) / rng
    candle_pts = 10  # בסיס
    if lc > op:  candle_pts += 5
    if cp > 0.6: candle_pts += 5
    score += candle_pts; details["נר אחרון"] = ("שורי" if lc > op else "דובי", candle_pts, 20)

    # ── RSI (20 נקודות) ──
    if 'RSI' in df.columns:
        max_pts += 20
        rsi = float(df['RSI'].iloc[-1])
        if 40 <= rsi <= 60:  rsi_pts = 15
        elif 30 <= rsi < 40: rsi_pts = 18
        elif 60 < rsi <= 70: rsi_pts = 12
        elif rsi < 30:       rsi_pts = 20
        else:                 rsi_pts = 5
        score += rsi_pts; details[f"RSI {rsi:.0f}"] = ("", rsi_pts, 20)

    # ── נפח (20 נקודות) ──
    if 'Volume' in df.columns:
        max_pts += 20
        vol = df['Volume'].astype(float)
        avg20 = float(vol.rolling(20).mean().iloc[-1])
        last_v = float(vol.iloc[-1])
        ratio = last_v / avg20 if avg20 > 0 else 1
        if ratio >= 1.5:   vol_pts = 20
        elif ratio >= 1.2: vol_pts = 15
        elif ratio >= 0.8: vol_pts = 10
        else:               vol_pts = 5
        score += vol_pts; details["נפח"] = (f"x{ratio:.1f}", vol_pts, 20)

    # ── MACD (20 נקודות) ──
    if 'MACD' in df.columns and 'MACD_S' in df.columns:
        max_pts += 20
        macd = float(df['MACD'].iloc[-1]); sig = float(df['MACD_S'].iloc[-1])
        macd_pts = 15 if macd > sig else 5
        if macd > 0: macd_pts = min(20, macd_pts + 5)
        score += macd_pts; details["MACD"] = ("מעל Signal" if macd > sig else "מתחת Signal", macd_pts, 20)

    normalized = round(score / max_pts * 100) if max_pts > 0 else None
    return {"score": normalized, "raw": score, "max": max_pts, "details": details}


def calc_analyst_score(analyst_data: dict) -> dict | None:
    """ציון אנליסטים 0-100 לפי קונצנזוס ופוטנציאל."""
    if not analyst_data or not analyst_data.get("n"): return None
    score = 0; max_pts = 0; details = {}

    # דירוג קונצנזוס (50 נקודות)
    rating = analyst_data.get("rating", "N/A")
    max_pts += 50
    r_pts = {"Strong Buy": 50, "Buy": 40, "Hold": 25, "Underperform": 10, "Sell": 0}
    score += r_pts.get(rating, 25)
    details["דירוג"] = (rating, r_pts.get(rating, 25), 50)

    # פוטנציאל מחיר יעד (50 נקודות)
    tm = analyst_data.get("tm"); cp_ = analyst_data.get("cur_price")
    if tm and cp_ and cp_ > 0:
        max_pts += 50
        upside = (tm - cp_) / cp_ * 100
        if upside >= 30:    u_pts = 50
        elif upside >= 20:  u_pts = 40
        elif upside >= 10:  u_pts = 30
        elif upside >= 0:   u_pts = 20
        elif upside >= -10: u_pts = 10
        else:                u_pts = 0
        score += u_pts; details["פוטנציאל"] = (f"{upside:+.1f}%", u_pts, 50)

    normalized = round(score / max_pts * 100) if max_pts > 0 else None
    return {"score": normalized, "raw": score, "max": max_pts, "details": details}


def calc_weighted_decision(f_score, t_score, a_score=None) -> dict:
    """מחשב ציון משוקלל והחלטה."""
    scores = {}
    if f_score is not None: scores["fundamental"] = (f_score, 0.35)
    if t_score is not None: scores["technical"]   = (t_score, 0.40)
    if a_score is not None: scores["analyst"]     = (a_score, 0.25)

    if not scores: return {"weighted": None, "decision": "אין נתונים", "color": "#8b949e", "icon": "⚪"}

    # נרמל משקלות
    total_w = sum(w for _, w in scores.values())
    weighted = sum(s * w / total_w for s, w in scores.values())
    weighted = round(weighted)

    if weighted >= 70:
        return {"weighted": weighted, "decision": "קנייה",   "color": "#3fb950", "icon": "🟢", "en": "BUY"}
    elif weighted >= 45:
        return {"weighted": weighted, "decision": "החזק",    "color": "#d29922", "icon": "🟡", "en": "HOLD"}
    else:
        return {"weighted": weighted, "decision": "מכירה",   "color": "#f85149", "icon": "🔴", "en": "SELL"}


def render_position_module(ticker: str, df, info: dict, analyst_d: dict,
                            cur_price: float, ccy_s: str, portfolio: dict):
    """
    מודול Position Sizing & Investment Decision המלא.
    """
    st.markdown("### 🎯 Position Sizing & Investment Decision")
    st.markdown(
        '<div style="color:#8b949e;font-size:.78rem;margin-bottom:12px;">'
        'ניתוח משולב פונדמנטלי, טכני ואנליסטים לסיוע בקבלת החלטת השקעה. '
        'אינו מהווה ייעוץ פיננסי.</div>',
        unsafe_allow_html=True
    )

    # ── חישוב ציונות ──
    with st.spinner("מחשב ציונות..."):
        f_res  = calc_fundamental_score(info)
        t_res  = calc_technical_score(df)
        an_res = calc_analyst_score({**analyst_d, "cur_price": cur_price}) if analyst_d else None
        f_s    = f_res.get("score")
        t_s    = t_res.get("score")
        a_s    = an_res.get("score") if an_res else None
        dec    = calc_weighted_decision(f_s, t_s, a_s)

    # ── כרטיס החלטה ראשי ──
    w = dec["weighted"]; dc = dec["decision"]; dclr = dec["color"]; di = dec["icon"]

    def score_bar(s, label, color="#1f6feb"):
        if s is None: return f'<div style="color:#8b949e;font-size:.75rem;">{label}: N/A</div>'
        pct = s
        return (
            f'<div style="margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
            f'<span style="color:#8b949e;font-size:.68rem;text-transform:uppercase;">{label}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:.78rem;font-weight:600;color:#e6edf3;">{s}/100</span>'
            f'</div>'
            f'<div style="height:6px;background:#21262d;border-radius:3px;overflow:hidden;">'
            f'<div style="height:100%;width:{pct}%;background:{color};border-radius:3px;'
            f'transition:width .4s;"></div>'
            f'</div></div>'
        )

    cols_d = st.columns([2, 1, 1, 1])
    with cols_d[0]:
        st.markdown(
            f'<div style="background:#161b22;border:2px solid {dclr}33;border-radius:14px;'
            f'padding:18px 20px;">'
            f'<div style="color:#8b949e;font-size:.66rem;text-transform:uppercase;margin-bottom:6px;">החלטה</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:{dclr};line-height:1;">'
            f'{di} {dc}</div>'
            f'<div style="color:#8b949e;font-size:.72rem;margin-top:6px;">'
            f'ציון משוקלל: <span style="color:#e6edf3;font-weight:600;">{w if w else "N/A"}/100</span></div>'
            f'<div style="height:8px;background:#21262d;border-radius:4px;overflow:hidden;margin-top:8px;">'
            f'<div style="height:100%;width:{w if w else 0}%;background:{dclr};border-radius:4px;"></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
    with cols_d[1]:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;">'
            f'<div style="color:#8b949e;font-size:.64rem;text-transform:uppercase;margin-bottom:8px;">ציונות</div>'
            f'{score_bar(f_s, "פונדמנטלי", "#388bfd")}'
            f'{score_bar(t_s, "טכני",       "#3fb950")}'
            f'{score_bar(a_s, "אנליסטים",   "#d29922")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with cols_d[2]:
        f_det = f_res.get("details", {})
        rows  = "".join(
            f'<div style="display:flex;justify-content:space-between;padding:3px 0;'
            f'border-bottom:1px solid #21262d;">'
            f'<span style="color:#8b949e;font-size:.68rem;">{k}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:.68rem;color:#e6edf3;">{v[0]}</span>'
            f'</div>'
            for k, v in f_det.items()
        ) if f_det else '<div style="color:#8b949e;font-size:.72rem;">N/A</div>'
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;padding:14px;">'
            f'<div style="color:#8b949e;font-size:.64rem;text-transform:uppercase;margin-bottom:6px;">פירוט פונדמנטלי</div>'
            f'{rows}</div>',
            unsafe_allow_html=True
        )
    with cols_d[3]:
        t_det = t_res.get("details", {})
        rows2 = "".join(
            f'<div style="display:flex;justify-content:space-between;padding:3px 0;'
            f'border-bottom:1px solid #21262d;">'
            f'<span style="color:#8b949e;font-size:.68rem;">{k}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:.68rem;color:#e6edf3;">{v[0]}</span>'
            f'</div>'
            for k, v in t_det.items()
        ) if t_det else '<div style="color:#8b949e;font-size:.72rem;">N/A</div>'
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;padding:14px;">'
            f'<div style="color:#8b949e;font-size:.64rem;text-transform:uppercase;margin-bottom:6px;">פירוט טכני</div>'
            f'{rows2}</div>',
            unsafe_allow_html=True
        )

    st.markdown('<hr style="margin:16px 0 12px;"/>', unsafe_allow_html=True)

    # ── Position Sizing Calculator ──
    st.markdown("#### 🧮 מחשבון Position Sizing")
    ps1, ps2, ps3 = st.columns(3)
    with ps1:
        account_val = st.number_input("גודל תיק ($):", value=10000, min_value=100, step=500, key="ps_acc")
        risk_pct    = st.slider("סיכון לעסקה (%):", 0.5, 5.0, 1.0, 0.5, key="ps_risk")
    with ps2:
        entry_p = st.number_input("מחיר כניסה:", value=float(cur_price), min_value=0.01, key="ps_entry")
        stop_p  = st.number_input("Stop Loss:", value=round(float(cur_price) * 0.95, 2), min_value=0.01, key="ps_stop")
    with ps3:
        target_p = st.number_input("מחיר יעד:", value=round(float(cur_price) * 1.12, 2), min_value=0.01, key="ps_tgt")
        st.markdown(f'<div style="color:#8b949e;font-size:.72rem;margin-top:8px;">מחיר נוכחי: <b style="color:#e6edf3;">{ccy_s}{cur_price:.2f}</b></div>', unsafe_allow_html=True)

    if entry_p > stop_p:
        rps     = entry_p - stop_p
        risk_amt = account_val * (risk_pct / 100)
        shares  = int(risk_amt / rps)
        pos_val = shares * entry_p
        pos_pct = pos_val / account_val * 100
        profit  = shares * (target_p - entry_p)
        loss    = shares * rps
        rr      = (target_p - entry_p) / rps if rps > 0 else 0
        rr_clr  = "#3fb950" if rr >= 2 else ("#d29922" if rr >= 1 else "#f85149")

        # טבלת תוצאה
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            f'padding:16px 20px;margin-top:10px;">'
            f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;">'
            + "".join([
                f'<div style="text-align:center;">'
                f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;margin-bottom:4px;">{lb}</div>'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:.92rem;font-weight:700;color:{cl_};">{vl}</div>'
                f'</div>'
                for lb, vl, cl_ in [
                    ("כמות מומלצת",    f"{shares}",               "#e6edf3"),
                    ("גודל פוזיציה",   f"{ccy_s}{pos_val:,.0f}",  "#e6edf3"),
                    ("% מהתיק",        f"{pos_pct:.1f}%",          "#e6edf3"),
                    ("סיכון מקסימלי",  f"{ccy_s}{loss:,.0f}",      "#f85149"),
                    ("רווח פוטנציאלי", f"{ccy_s}{profit:,.0f}",    "#3fb950"),
                    ("יחס R:R",        f"1:{rr:.2f}",              rr_clr),
                ]
            ])
            + f'</div>'
            f'<div style="margin-top:12px;height:6px;background:#21262d;border-radius:3px;overflow:hidden;">'
            f'<div style="height:100%;width:{min(100,pos_pct):.0f}%;background:#1f6feb;border-radius:3px;"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:4px;">'
            f'<span style="color:#8b949e;font-size:.62rem;">0%</span>'
            f'<span style="color:#8b949e;font-size:.62rem;">{pos_pct:.1f}% מהתיק</span>'
            f'<span style="color:#8b949e;font-size:.62rem;">100%</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        if rr < 1.5:
            st.warning("⚠️ יחס סיכוי/סיכון נמוך מ-1.5. שקלי להזיז את היעד גבוה יותר.")

    else:
        st.error("Stop Loss חייב להיות נמוך ממחיר הכניסה")

    # ── טבלת תיק קיים ──
    positions = portfolio.get("positions", {})
    if positions:
        st.markdown('<hr style="margin:14px 0 10px;"/>', unsafe_allow_html=True)
        st.markdown("#### 📋 ניתוח תיק קיים")
        rows = []
        for sym_, pos in positions.items():
            pr_ = get_live_price(sym_) or pos["avg_price"]
            ret = (pr_ - pos["avg_price"]) / pos["avg_price"] * 100
            val = pos["shares"] * pr_
            rows.append({
                "מניה":          sym_,
                "מחיר קנייה":   f"${pos['avg_price']:.2f}",
                "מחיר נוכחי":   f"${pr_:.2f}",
                "כמות":          pos["shares"],
                "ערך כולל":      f"${val:,.2f}",
                "תשואה %":       f"{ret:+.1f}%",
                "_ret":          ret,
            })
        if rows:
            df_pf = pd.DataFrame(rows)
            def color_ret(v):
                try:
                    n = float(str(v).replace("%","").replace("+",""))
                    return "color:#3fb950;font-weight:600" if n > 0 else ("color:#f85149;font-weight:600" if n < 0 else "")
                except: return ""
            disp = [c for c in ["מניה","מחיר קנייה","מחיר נוכחי","כמות","ערך כולל","תשואה %"] if c in df_pf.columns]
            st.dataframe(
                df_pf[disp].style.map(color_ret, subset=["תשואה %"]),
                use_container_width=True, hide_index=True
            )


# ══════════════════════════════════════════════════════════════
# THESIS PANEL — data contract:
# {
#   "summary": str,
#   "bull": {"title": str, "points": [str], "target": str},
#   "base": {"title": str, "points": [str], "target": str},
#   "bear": {"title": str, "points": [str], "target": str},
#   "alerts": [{"level": "high"|"medium"|"low", "text": str}]
# }
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def build_thesis_data(symbol: str, info: dict, df) -> dict:
    """
    בונה את ה-data contract של ThesisPanel
    לפי נתוני yfinance + ניתוח טכני בסיסי.
    ניתן להחליף בקריאת API חיצוני.
    """
    try:
        cl      = df["Close"].astype(float)
        lc_     = float(cl.iloc[-1])
        ma50_   = float(df["MA50"].iloc[-1])  if "MA50"  in df.columns else None
        ma200_  = float(df["MA200"].iloc[-1]) if "MA200" in df.columns else None
        rsi_    = float(df["RSI"].iloc[-1])   if "RSI"   in df.columns else None

        pe      = info.get("trailingPE")
        fwd_pe  = info.get("forwardPE")
        rev_g   = info.get("revenueGrowth")
        mg      = info.get("profitMargins")
        eps_f   = info.get("forwardEps")
        t_mean  = info.get("targetMeanPrice")
        t_high  = info.get("targetHighPrice")
        t_low   = info.get("targetLowPrice")
        name    = info.get("shortName", symbol)

        sym_c   = get_sym(symbol)

        # ── Thesis Summary ──
        trend_ok   = (ma50_ and lc_ > ma50_) and (ma200_ and lc_ > ma200_)
        growth_ok  = rev_g and float(rev_g) > 0.05
        margin_ok  = mg    and float(mg)    > 0.10
        rsi_ok     = rsi_ and 35 <= rsi_ <= 65

        bullets = []
        if trend_ok:   bullets.append("המניה נסחרת מעל ממוצעי המגמה הראשיים")
        if growth_ok:  bullets.append(f"צמיחת הכנסות חיובית ({float(rev_g)*100:.1f}% YoY)")
        if margin_ok:  bullets.append(f"שולי רווח בריאים ({float(mg)*100:.1f}%)")
        if not rsi_ok and rsi_: bullets.append(f"RSI {rsi_:.0f} — {'קנוי מדי' if rsi_ > 65 else 'מכור מדי'}")
        if not bullets:         bullets.append("מידע מוגבל — השתמשי בנתוני אנליסטים להשלמת התמונה")

        count_ok = sum([trend_ok, growth_ok, margin_ok, rsi_ok or False])
        if count_ok >= 3:
            summary = f"{name} מציגה תמונה פונדמנטלית וטכנית חיובית ברובה. מספר גורמים תומכים בהמשך המגמה בטווח הבינוני."
        elif count_ok >= 1:
            summary = f"{name} מציגה תמונה מעורבת — חלק מהאינדיקטורים חיוביים אך יש גורמי סיכון שדורשים תשומת לב."
        else:
            summary = f"הנתונים הזמינים ל-{name} מוגבלים. מומלץ לבדוק את דוחות הרבעון האחרון לפני קבלת החלטה."

        # ── Bull Case ──
        bull_pts = []
        if t_high:
            bull_pts.append(f"יעד אנליסטים אופטימי: {sym_c}{float(t_high):.0f}")
        if growth_ok:
            bull_pts.append(f"צמיחת הכנסות חזקה תומכת בהרחבת מכפיל")
        if ma200_ and lc_ > ma200_:
            bull_pts.append("מגמה עולה ארוכת טווח — מחיר מעל MA200")
        if eps_f and (not pe or float(pe) > 0):
            bull_pts.append(f"EPS Forward: {sym_c}{float(eps_f):.2f} — פוטנציאל לצמיחת רווחים")
        if not bull_pts:
            bull_pts = ["תרחיש שורי תלוי בשיפור בנתוני הרבעון הקרוב"]

        bull_target = f"{sym_c}{float(t_high):.0f}" if t_high else "N/A"

        # ── Base Case ──
        base_pts = []
        if t_mean:
            base_pts.append(f"יעד קונצנזוס אנליסטים: {sym_c}{float(t_mean):.0f}")
        if fwd_pe:
            base_pts.append(f"P/E Forward {float(fwd_pe):.1f} — תמחור {'סביר' if float(fwd_pe) < 30 else 'גבוה'}")
        if ma50_ and lc_ > ma50_:
            base_pts.append("נסחרת מעל MA50 — תמיכה טכנית קיימת")
        base_pts.append("המשך מגמה קיימת בהנחת ביצועים בהתאם לציפיות")
        if not base_pts:
            base_pts = ["תרחיש בסיס: שמירה על המגמה הנוכחית"]

        base_target = f"{sym_c}{float(t_mean):.0f}" if t_mean else f"{sym_c}{lc_:.0f}"

        # ── Bear Case ──
        bear_pts = []
        if t_low:
            bear_pts.append(f"יעד אנליסטים פסימי: {sym_c}{float(t_low):.0f}")
        if rsi_ and rsi_ > 70:
            bear_pts.append(f"RSI {rsi_:.0f} — סיכון לתיקון קרוב")
        if pe and float(pe) > 40:
            bear_pts.append(f"P/E {float(pe):.0f} — תמחור גבוה מייצר סיכון downside")
        if ma200_ and lc_ < ma200_:
            bear_pts.append("מתחת ל-MA200 — חולשה מבנית בטווח הארוך")
        if not bear_pts:
            bear_pts = ["שינוי שלילי בנתוני רבעון עלול לפגוע במחיר", "האטה בצמיחה מהווה סיכון מרכזי"]

        bear_target = f"{sym_c}{float(t_low):.0f}" if t_low else "N/A"

        # ── Smart Alerts ──
        alerts = []
        if rsi_ and rsi_ > 75:
            alerts.append({"level": "high", "text": f"RSI {rsi_:.0f} — אזור overbought קיצוני, סיכון גבוה לתיקון"})
        elif rsi_ and rsi_ < 25:
            alerts.append({"level": "high", "text": f"RSI {rsi_:.0f} — oversold קיצוני, ייתכן bounce"})
        elif rsi_ and rsi_ > 68:
            alerts.append({"level": "medium", "text": f"RSI {rsi_:.0f} — מתקרב לאזור קנוי מדי"})

        if pe and float(pe) > 50:
            alerts.append({"level": "high",   "text": f"P/E {float(pe):.0f} — תמחור גבוה מאוד, דורש צמיחה חזקה"})
        elif pe and float(pe) > 35:
            alerts.append({"level": "medium", "text": f"P/E {float(pe):.0f} — תמחור מוגבה, שים לב לציפיות"})

        if ma50_ and ma200_ and ma50_ < ma200_ and lc_ < ma200_:
            alerts.append({"level": "high", "text": "Death Cross — MA50 מתחת MA200, מגמה ירדה לטווח ארוך"})

        if "Volume" in df.columns:
            vol   = df["Volume"].astype(float)
            avg20 = float(vol.rolling(20).mean().iloc[-1])
            lv__  = float(vol.replace(0, pd.NA).dropna().iloc[-1]) if avg20 > 0 else 0
            if avg20 > 0 and lv__ > avg20 * 2:
                alerts.append({"level": "medium", "text": f"נפח גבוה חריג (פי {lv__/avg20:.1f} מהממוצע) — בדקי את הסיבה"})

        if t_mean and lc_ > 0:
            upside = (float(t_mean) - lc_) / lc_ * 100
            if upside > 20:
                alerts.append({"level": "low", "text": f"אפסייד של {upside:.0f}% לפי קונצנזוס אנליסטים"})
            elif upside < -10:
                alerts.append({"level": "medium", "text": f"דאונסייד של {abs(upside):.0f}% לפי קונצנזוס — מחיר גבוה מהיעד"})

        if not alerts:
            alerts.append({"level": "low", "text": "לא זוהו התראות חריגות — מצב שוק רגיל"})

        return {
            "summary":     summary,
            "bull":        {"title": "תרחיש שורי",  "points": bull_pts[:4], "target": bull_target},
            "base":        {"title": "תרחיש בסיס",  "points": base_pts[:4], "target": base_target},
            "bear":        {"title": "תרחיש דובי",  "points": bear_pts[:4], "target": bear_target},
            "alerts":      alerts[:5],
        }
    except Exception as e:
        return {
            "summary": f"לא ניתן לבנות תזה עבור {symbol}: {e}",
            "bull":    {"title": "תרחיש שורי",  "points": ["N/A"], "target": "N/A"},
            "base":    {"title": "תרחיש בסיס",  "points": ["N/A"], "target": "N/A"},
            "bear":    {"title": "תרחיש דובי",  "points": ["N/A"], "target": "N/A"},
            "alerts":  [{"level": "low", "text": "נתונים לא זמינים"}],
        }


def render_thesis_panel(data: dict, symbol: str):
    """
    ThesisPanel — קומפוננט plug-and-play.
    מקבל data dict בלבד, לא ניגש ל-API בעצמו.
    """
    if not data:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            'padding:20px;text-align:center;color:#8b949e;">אין נתוני תזה זמינים</div>',
            unsafe_allow_html=True
        )
        return

    # ── 3 צבעי case ──
    CASE_STYLES = {
        "bull": ("#3fb950", "#3fb95015", "📈"),
        "base": ("#d29922", "#d2992215", "↔️"),
        "bear": ("#f85149", "#f8514915", "📉"),
    }

    # ── Alert styles ──
    ALERT_STYLES = {
        "high":   ("#f85149", "#f8514912", "🔴"),
        "medium": ("#d29922", "#d2992212", "🟡"),
        "low":    ("#3fb950", "#3fb95012", "🟢"),
    }

    # ── Header ──
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;direction:rtl;">'
        '<span style="font-size:.95rem;font-weight:700;color:#e6edf3;">🧭 Investment Thesis</span>'
        f'<span style="color:#8b949e;font-size:.72rem;">{symbol}</span>'
        '<span style="background:#21262d;color:#8b949e;border:1px solid #30363d;'
        'border-radius:6px;padding:2px 8px;font-size:.6rem;margin-right:auto;">data-driven · לא ייעוץ השקעות</span>'
        '</div>',
        unsafe_allow_html=True
    )

    # ══ SECTION 1: Thesis Summary ══
    st.markdown(
        '<div style="background:#161b22;border:1px solid #21262d;'
        'border-right:3px solid #388bfd;border-radius:12px;'
        'padding:14px 18px;margin-bottom:10px;direction:rtl;">'
        '<div style="color:#8b949e;font-size:.65rem;text-transform:uppercase;'
        'font-weight:700;margin-bottom:6px;letter-spacing:.06em;">📝 תזת השקעה</div>'
        f'<p style="color:#c9d1d9;font-size:.87rem;line-height:1.7;margin:0;">'
        f'{data.get("summary","")}</p>'
        '</div>',
        unsafe_allow_html=True
    )

    # ══ SECTION 2: Bull / Base / Bear ══
    cc1, cc2, cc3 = st.columns(3)
    cols_map = [("bull", cc1), ("base", cc2), ("bear", cc3)]

    for key, col in cols_map:
        case        = data.get(key, {})
        color, bg, icon = CASE_STYLES[key]
        title       = case.get("title", key)
        points      = case.get("points", [])
        target      = case.get("target", "N/A")

        pts_html = "".join(
            f'<li style="color:#c9d1d9;font-size:.8rem;line-height:1.6;margin-bottom:3px;">{p}</li>'
            for p in points
        )

        col.markdown(
            f'<div style="background:{bg};border:1px solid {color}33;'
            f'border-top:2px solid {color};border-radius:12px;padding:13px 14px;height:100%;">'
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">'
            f'<span style="font-size:.9rem;">{icon}</span>'
            f'<span style="color:{color};font-size:.82rem;font-weight:700;">{title}</span>'
            f'</div>'
            f'<ul style="margin:0;padding-right:16px;margin-bottom:10px;">{pts_html}</ul>'
            f'<div style="background:#0d1117;border:1px solid {color}44;border-radius:7px;'
            f'padding:6px 10px;text-align:center;">'
            f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">יעד מחיר</div>'
            f'<div style="color:{color};font-family:JetBrains Mono,monospace;'
            f'font-size:.95rem;font-weight:700;margin-top:2px;">{target}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ══ SECTION 3: Smart Alerts ══
    st.markdown(
        '<div style="margin-top:10px;direction:rtl;">'
        '<div style="color:#8b949e;font-size:.65rem;text-transform:uppercase;'
        'font-weight:700;margin-bottom:6px;letter-spacing:.06em;">🔔 התראות חכמות</div>',
        unsafe_allow_html=True
    )
    alerts = data.get("alerts", [])
    for alert in alerts:
        lvl   = alert.get("level", "low")
        txt   = alert.get("text", "")
        clr, bg, icon = ALERT_STYLES.get(lvl, ALERT_STYLES["low"])
        st.markdown(
            f'<div style="background:{bg};border:1px solid {clr}33;border-radius:9px;'
            f'padding:8px 14px;margin-bottom:5px;display:flex;align-items:flex-start;'
            f'gap:8px;direction:rtl;">'
            f'<span style="font-size:.8rem;flex-shrink:0;">{icon}</span>'
            f'<span style="color:#c9d1d9;font-size:.82rem;line-height:1.5;">{txt}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#8b949e;font-size:.62rem;margin-top:6px;direction:rtl;">'
        '⚠️ ThesisPanel מבוסס על נתונים זמינים בלבד. '
        'אינו תחליף לניתוח מעמיק או ייעוץ השקעות מוסמך.'
        '</div>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════
# TECHNICAL INDICATOR HELPERS
# ══════════════════════════════════════════════════════════════

def calc_support_resistance(prices, window=20, n_levels=3):
    arr = prices.to_numpy(dtype=float)
    highs, lows = [], []
    for i in range(window, len(arr) - window):
        seg = arr[i - window: i + window + 1]
        if arr[i] == seg.max(): highs.append(arr[i])
        if arr[i] == seg.min(): lows.append(arr[i])
    def cluster(pts, tol=0.015):
        if not pts: return []
        pts = sorted(pts)
        groups, cur = [], [pts[0]]
        for p in pts[1:]:
            if abs(p - cur[-1]) / cur[-1] < tol: cur.append(p)
            else: groups.append(cur); cur = [p]
        groups.append(cur)
        return [sum(g) / len(g) for g in groups]
    return cluster(highs)[-n_levels:], cluster(lows)[:n_levels]


def calc_fibonacci(high: float, low: float) -> dict:
    diff = high - low
    return {
        "0%":    high,
        "23.6%": high - 0.236 * diff,
        "38.2%": high - 0.382 * diff,
        "50.0%": high - 0.500 * diff,
        "61.8%": high - 0.618 * diff,
        "78.6%": high - 0.786 * diff,
        "100%":  low,
    }


def calc_trendline(prices, use_highs=False):
    arr = prices.to_numpy(dtype=float)
    x   = np.arange(len(arr))
    n   = max(5, len(arr) // 5)
    sel = np.argsort(arr)[-n:] if use_highs else np.argsort(arr)[:n]
    coeffs = np.polyfit(x[sel], arr[sel], 1)
    return np.poly1d(coeffs)(x)


def calc_channel(prices):
    arr    = prices.to_numpy(dtype=float)
    x      = np.arange(len(arr))
    coeffs = np.polyfit(x, arr, 1)
    mid    = np.poly1d(coeffs)(x)
    std    = (arr - mid).std()
    return mid, mid + 1.5 * std, mid - 1.5 * std


# ── Analysis ──
def analyze_candle(df: pd.DataFrame) -> dict:
    if len(df) < 2:
        return {"label": "אין נתונים", "text": "", "color": "#8b949e", "vol": ""}
    o = float(df['Open'].iloc[-1]);  h = float(df['High'].iloc[-1])
    l = float(df['Low'].iloc[-1]);   c = float(df['Close'].iloc[-1])
    body = abs(c - o); rng = h - l if h != l else .001
    uw = h - max(o, c); lw = min(o, c) - l
    br = body / rng; cp = (c - l) / rng

    vok, vol_txt = False, ""
    if 'Volume' in df.columns:
        vol = df['Volume'].astype(float)
        avg = float(vol.rolling(20).mean().iloc[-1])
        if avg > 0:
            vok = float(vol.iloc[-1]) > avg * 1.2
        vol_txt = "✅ נפח תומך בתנועה" if vok else "⚠️ נפח לא מאשר"

    if br < .08:
        return {"label": "Doji", "text": "המחיר נסגר קרוב לפתיחה. השוק בחוסר החלטיות.", "color": "#8b949e", "vol": vol_txt}
    if c > o and br > .6 and cp > .7:
        return {"label": "לחץ קנייה חזק", "text": "נר שורי גדול עם סגירה גבוהה. הקונים שלטו לאורך כל המסחר.", "color": "#3fb950", "vol": vol_txt}
    if c < o and br > .6 and cp < .3:
        return {"label": "לחץ מכירה חזק", "text": "נר דובי גדול עם סגירה נמוכה. המוכרים שלטו לאורך כל המסחר.", "color": "#f85149", "vol": vol_txt}
    if uw > body * 2:
        return {"label": "Shooting Star", "text": "ניסיון עלייה שנדחה. פתיל עליון ארוך מצביע על התנגדות.", "color": "#f85149", "vol": vol_txt}
    if lw > body * 2 and c > o:
        return {"label": "Hammer", "text": "ירידה שנדחתה חזרה. פתיל תחתון ארוך מצביע על תמיכה.", "color": "#3fb950", "vol": vol_txt}
    if c > o:
        return {"label": "איתות חיובי מתון", "text": "נר שורי עם יתרון לקונים. סגירה מעל הפתיחה.", "color": "#3fb950", "vol": vol_txt}
    return {"label": "איתות שלילי מתון", "text": "נר דובי עם יתרון למוכרים. סגירה מתחת לפתיחה.", "color": "#f85149", "vol": vol_txt}

# ── Session State ──
DEFAULTS = {
    'pf': None, 'ticker': 'NVDA', 'period': '1Y', 'ct': 'line',
    'recent': [], 'err': '', 'cat': '🤖 AI',
    'show_an': False, 'show_ai': False, 'show_ind': True,
    'ma20': True, 'ma50': True, 'ma200': False, 'bb': False,
    'sr': False, 'fib': False, 'trendline': False, 'channel': False,
    'ai_res': None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
if st.session_state.pf is None:
    st.session_state.pf = load_pf()
pf = st.session_state.pf

# ── טעינת נתוני משתמש שמורים ──
if 'user_data_loaded' not in st.session_state:
    _ud = load_user_data()
    for _key in ["watchlist","alerts_list","portfolio_positions","ec_symbols","recent","cmp_symbols"]:
        if _key not in st.session_state and _ud.get(_key):
            st.session_state[_key] = _ud[_key]
    # merge recent if exists
    if _ud.get("recent") and not st.session_state.get("recent"):
        st.session_state.recent = _ud["recent"]
    st.session_state.user_data_loaded = True


# ── SIDEBAR — מינימלי: רק מניה נוכחית ✅ ──
with st.sidebar:
    cur_price_sb = get_live_price(st.session_state.ticker)
    cur_dc = 0
    try:
        _inf_sb = load_info(st.session_state.ticker)
        _pc_sb  = _inf_sb.get("previousClose") or 0
        if _pc_sb and cur_price_sb:
            cur_dc = (cur_price_sb - _pc_sb) / _pc_sb * 100
    except: pass
    clr_sb = "#3fb950" if cur_dc >= 0 else "#f85149"

    st.markdown(
        f'<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;'
        f'padding:12px;margin-bottom:8px;text-align:center;">'
        f'<div style="color:#8b949e;font-size:.58rem;text-transform:uppercase;margin-bottom:3px;">מניה נוכחית</div>'
        f'<div style="font-size:1.3rem;font-weight:800;color:#388bfd;">{st.session_state.ticker}</div>'
        + (f'<div style="font-family:JetBrains Mono,monospace;font-size:.88rem;color:#e6edf3;">'
           f'${cur_price_sb:.2f}</div>'
           f'<div style="color:{clr_sb};font-size:.72rem;font-weight:600;">'
           f'{"▲" if cur_dc>=0 else "▼"}{abs(cur_dc):.2f}% היום</div>'
           if cur_price_sb else '')
        + '</div>', unsafe_allow_html=True
    )

    st.markdown(
        '<div style="color:#8b949e;font-size:.65rem;text-align:center;margin-top:8px;">'
        '⬆️ חפשי מניה ב-Home</div>',
        unsafe_allow_html=True
    )

    st.divider()

    # Paper portfolio mini
    tv = pf_val(pf); gn = tv - STARTING_CASH; gp = (gn / STARTING_CASH) * 100
    gc = "#3fb950" if gn >= 0 else "#f85149"
    st.markdown(
        f'<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;padding:10px;">'
        f'<div style="color:#8b949e;font-size:.58rem;text-transform:uppercase;">💼 Paper Portfolio</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:1rem;font-weight:700;color:#e6edf3;margin:3px 0;">${tv:,.0f}</div>'
        f'<div style="color:{gc};font-size:.65rem;">{"▲" if gn>=0 else "▼"} {gp:+.2f}%</div>'
        f'</div>', unsafe_allow_html=True
    )
    if st.button("🔄 איפוס תיק", key="rst"):
        st.session_state.pf = {"cash": STARTING_CASH, "positions": {}, "trades": []}
        save_pf(st.session_state.pf)
        st.rerun()


# ── LOAD DATA ──
ticker          = st.session_state.ticker
period, interval = PERIODS[st.session_state.period]
sym             = get_sym(ticker)
il              = "🇮🇱" if is_il(ticker) else ""

with st.spinner(f"טוען {ticker}..."):
    df   = load_ohlcv(ticker, period, interval)
    info = load_info(ticker)

# Error state
if df is None:
    st.markdown(
        f'<div style="text-align:center;padding:60px 20px;">'
        f'<div style="font-size:3rem;">⚠️</div>'
        f'<div style="font-size:1.2rem;font-weight:600;color:#e6edf3;margin:10px 0;">'
        f'לא ניתן לטעון נתונים עבור \'{ticker}\'</div>'
        f'<div style="color:#8b949e;">בדקי שהסימול נכון ונסי שוב</div>'
        f'</div>', unsafe_allow_html=True
    )
    st.info("💡 נסי: AAPL · TSLA · MSFT · GOOGL · NVDA · TEVA · CHKP")
    st.stop()

# ── Derived values ──
company  = info.get("shortName", ticker)
cp       = get_live_price(ticker) or float(df['Close'].iloc[-1])
pc       = info.get("previousClose") or float(df['Close'].iloc[-2])
dc       = ((cp - pc) / pc * 100) if pc else 0
da       = cp - pc
chg_c    = "#3fb950" if dc >= 0 else "#f85149"
chg_a    = "▲" if dc >= 0 else "▼"
lc       = float(df['Close'].iloc[-1])
lo       = float(df['Open'].iloc[-1])
lh       = float(df['High'].iloc[-1])
ll       = float(df['Low'].iloc[-1])
lv       = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0

# ── HEADER — Google Finance Style ──
st.markdown(
    f'<div style="padding:16px 0 4px;direction:rtl;">'
    f'<div style="font-size:1.55rem;font-weight:700;color:#e6edf3;line-height:1.2;">'
    f'{company} {il}</div>'
    f'<div style="color:#8b949e;font-size:.78rem;margin-top:2px;">'
    f'{ticker} · {info.get("exchange","") or ""} · {info.get("currency","USD") or "USD"}'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

# Price + change line
w52l = info.get("fiftyTwoWeekLow"); w52h = info.get("fiftyTwoWeekHigh")
prev_c = info.get("previousClose")
st.markdown(
    f'<div style="display:flex;align-items:baseline;gap:12px;padding:4px 0 8px;direction:rtl;flex-wrap:wrap;">'
    f'<span style="font-family:JetBrains Mono,monospace;font-size:2.2rem;font-weight:700;color:#e6edf3;">{sym}{cp:.2f}</span>'
    f'<span style="background:{chg_c}22;color:{chg_c};border:1px solid {chg_c}44;'
    f'border-radius:6px;padding:3px 10px;font-size:.85rem;font-weight:700;">'
    f'{chg_a} {sym}{abs(da):.2f} ({dc:+.2f}%)</span>'
    f'<span style="color:#8b949e;font-size:.75rem;">היום</span>'
    + (f'<span style="color:#8b949e;font-size:.72rem;margin-right:auto;">52ש׳: {sym}{w52l:.2f} – {sym}{w52h:.2f}</span>' if w52l and w52h else '')
    + (f'<span style="color:#8b949e;font-size:.72rem;">סגירה קודמת: {sym}{prev_c:.2f}</span>' if prev_c else '')
    + f'</div>',
    unsafe_allow_html=True
)

st.markdown('<div style="height:2px;"></div>', unsafe_allow_html=True)

# ── MAIN TABS ──
# ── Tab groups ──
thome, t1, t2, t3, t4, t9, t10, t11, t12, t13, t7 = st.tabs([
    "🏠 Home", "📈 גרף", "🎯 ניתוח", "⏳ Backtest",
    "🛒 מסחר", "⚖️ השוואה", "💼 תיק",
    "🔔 התראות", "📅 דוחות", "👁️ Watchlist", "📖 מדריך"
])

# ════════════════════════════════════════
# TAB 1 — CHART
# ════════════════════════════════════════
with thome:
    from datetime import datetime as _dt

    # ══════════════════════════════════════════════════════
    # HOME STATE
    # ══════════════════════════════════════════════════════
    if 'home_main_cat' not in st.session_state:
        st.session_state.home_main_cat = "מניות"
    if 'home_sub_cat' not in st.session_state:
        st.session_state.home_sub_cat  = "🔥 מומלצות AI"

    HOME_SUBS = {
        "מניות":           ["🔥 מומלצות AI", "🤖 AI", "📱 Tech", "🏦 Finance", "🇺🇸 מניות בולטות"],
        "שווקים גלובליים": ["📈 מדדים", "$ מט\"ח", "🛢 סחורות", "₿ קריפטו"],
        "שוק ישראלי":      ["🔥 חמות", 'ת"א 125', 'ת"א 35', "בנקים", "טכנולוגיה", "נדל\"ן", "ביומד", "נפט וגז"],
        "האישי שלי":       ["תיק", "Watchlist", "התראות"],
    }

    # ── CSS additions for home ──
    st.markdown("""
<style>
.home-main-cat {
    display:inline-flex; gap:4px; background:#0d1117;
    padding:4px; border-radius:10px; margin-bottom:8px;
}
.home-sub-row {
    display:flex; gap:4px; overflow-x:auto; padding:2px 0 6px;
    scrollbar-width:none; -ms-overflow-style:none;
}
.home-sub-row::-webkit-scrollbar { display:none; }
.rtl-section { direction:rtl; text-align:right; }
</style>
""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # 1. TOP HEADER
    # ══════════════════════════════════════════════════════

    # Quick market status
    @st.cache_data(ttl=120)
    @st.cache_data(ttl=120)
    def load_market_group(syms_tuple: tuple) -> dict:
        result = {}
        for name, sym in syms_tuple:
            try:
                h = yf.Ticker(sym).history(period="2d")
                if len(h) >= 2:
                    cur  = float(h['Close'].iloc[-1])
                    prev = float(h['Close'].iloc[-2])
                    result[name] = {"price": cur, "chg": (cur - prev) / prev * 100}
            except: pass
        return result

    @st.cache_data(ttl=180)
    def load_market_movers():
        us_syms = ["NVDA","AMD","TSLA","AAPL","MSFT","META","GOOGL","AMZN",
                   "NFLX","CRM","PLTR","SOFI","RIVN","COIN","BABA","NIO","LCID"]
        rows = []
        for s in us_syms:
            try:
                h = yf.Ticker(s).history(period="2d")
                if len(h) >= 2:
                    c = float(h['Close'].iloc[-1])
                    p = float(h['Close'].iloc[-2])
                    v = float(h['Volume'].iloc[-1])
                    rows.append({"sym":s,"price":c,"chg":(c-p)/p*100,"vol":v})
            except: pass
        if not rows:
            return {"gainers":[],"losers":[],"active":[]}
        return {
            "gainers": sorted(rows, key=lambda x: x["chg"], reverse=True)[:5],
            "losers":  sorted(rows, key=lambda x: x["chg"])[:5],
            "active":  sorted(rows, key=lambda x: x["vol"], reverse=True)[:5],
        }

    @st.cache_data(ttl=180)
    def load_ta_market():
        ta_groups = {
            'ת"א 35':   ["FIBI.TA","LUMI.TA","DSCT.TA","ESLT.TA","TEVA.TA","NICE.TA","CHKP.TA","ICL.TA"],
            'ת"א 125':  ["RSEL.TA","AURA.TA","SANO.TA","ENLT.TA","MGDL.TA"],
            "בנקים":    ["FIBI.TA","LUMI.TA","DSCT.TA","HAPO.TA","MIZR.TA"],
            "טכנולוגיה":["NICE.TA","CHKP.TA","ESLT.TA"],
            'נדל"ן':    ["AZRG.TA","EMCO.TA","AFRE.TA","AMOT.TA"],
            "ביומד":    ["TEVA.TA","KMDA.TA","SPNS.TA"],
            "נפט וגז":  ["DLEKG.TA","NFTA.TA"],
        }
        result = {}
        for grp, syms in ta_groups.items():
            rows_ta = []
            for s in syms:
                try:
                    h = yf.Ticker(s).history(period="2d")
                    if len(h) >= 2:
                        c = float(h['Close'].iloc[-1])
                        p = float(h['Close'].iloc[-2])
                        v = float(h['Volume'].iloc[-1])
                        inf_ta = load_info(s)
                        name_ta = (inf_ta.get("shortName","") or s.replace(".TA",""))[:16]
                        rows_ta.append({
                            "sym": s.replace(".TA",""), "name": name_ta,
                            "price": c, "chg": (c-p)/p*100, "vol": v
                        })
                except: pass
            result[grp] = sorted(rows_ta, key=lambda x: x["chg"], reverse=True)
        return result

    def home_market_status():
        checks = {"S&P 500":"^GSPC","ת\"א 125":"^TA125.TA","USD/ILS":"ILS=X"}
        out = []
        for name, sym in checks.items():
            try:
                h = yf.Ticker(sym).history(period="2d")
                if len(h) >= 2:
                    c = float(h['Close'].iloc[-1]); p = float(h['Close'].iloc[-2])
                    chg = (c-p)/p*100
                    clr = "#3fb950" if chg >= 0 else "#f85149"
                    arr = chr(9650) if chg >= 0 else chr(9660)
                    if "ILS" in sym:
                        out.append(f'<span style="color:#8b949e;">USD/ILS </span><span style="color:#e6edf3;font-family:JetBrains Mono,monospace;">{c:.3f}</span>')
                    else:
                        out.append(f'<span style="color:#8b949e;">{name} </span><span style="color:{clr};font-family:JetBrains Mono,monospace;">{arr}{abs(chg):.2f}%</span>')
            except: pass
        now = _dt.now()
        mkt_open = 9 <= now.hour < 22
        status = f'<span style="color:{"#3fb950" if mkt_open else "#f85149"};font-size:.65rem;">{"● שוק פתוח" if mkt_open else "● שוק סגור"}</span>'
        return out, status

    mkt_pills, mkt_status = home_market_status()

    # Header block
    h_left, h_right = st.columns([3, 2])
    with h_left:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0 4px;">'
            f'<div style="width:32px;height:32px;background:linear-gradient(135deg,#1f6feb,#388bfd);'
            f'border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:.95rem;">📈</div>'
            f'<div>'
            f'<div style="font-size:1.1rem;font-weight:800;color:#e6edf3;letter-spacing:-.3px;">Alpha Charts Pro</div>'
            f'<div style="display:flex;gap:10px;align-items:center;margin-top:2px;">'
            + "  ·  ".join(mkt_pills) + f'  {mkt_status}'
            + f'</div></div></div>',
            unsafe_allow_html=True
        )

    with h_right:
        h_si = st.text_input("search", value="", placeholder="🔍  חפשי מניה...",
                             label_visibility="collapsed", key="home_search_v2")
        if st.button("חפשי", key="home_go2", type="primary", use_container_width=True):
            if h_si.strip():
                r = resolve(h_si.strip())
                try:
                    test = yf.Ticker(r).history(period="5d")
                    if not test.empty:
                        st.session_state.ticker = r
                        st.session_state.ai_res = None
                        if r not in st.session_state.recent:
                            st.session_state.recent.insert(0, r)
                            st.session_state.recent = st.session_state.recent[:8]
                        save_user_data()
                        st.rerun()
                    else:
                        st.error(f"'{r}' לא נמצא")
                except:
                    st.error("שגיאה בטעינה")

    # Recent quick-access
    if st.session_state.get("recent"):
        rec_html = ""
        for s in st.session_state.recent[:8]:
            is_cur = s == st.session_state.ticker
            bg = "#1f6feb" if is_cur else "#21262d"
            clr = "#fff" if is_cur else "#c9d1d9"
            rec_html += (
                f'<span onclick="" style="background:{bg};color:{clr};border:1px solid #30363d;'
                f'border-radius:6px;padding:3px 9px;font-size:.7rem;font-weight:600;'
                f'cursor:pointer;white-space:nowrap;">{s}</span>'
            )
        st.markdown(f'<div style="display:flex;gap:5px;flex-wrap:wrap;margin:4px 0 2px;">{rec_html}</div>',
                    unsafe_allow_html=True)
        rec_cols = st.columns(len(st.session_state.recent[:8]))
        for i, s in enumerate(st.session_state.recent[:8]):
            if rec_cols[i].button(s, key=f"home_rec_{i}",
                                   type="primary" if s==st.session_state.ticker else "secondary"):
                st.session_state.ticker = s
                st.session_state.ai_res = None
                st.rerun()

    st.markdown('<div style="height:4px;border-bottom:1px solid #21262d;margin-bottom:10px;"></div>',
                unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # 2. MAIN CATEGORY ROW — Level 1
    # ══════════════════════════════════════════════════════
    MAIN_CATS = list(HOME_SUBS.keys())
    mc_cols = st.columns(len(MAIN_CATS))
    for i, cat in enumerate(MAIN_CATS):
        is_active = cat == st.session_state.home_main_cat
        if mc_cols[i].button(
            cat, key=f"mc_{i}",
            type="primary" if is_active else "secondary",
            use_container_width=True
        ):
            st.session_state.home_main_cat = cat
            st.session_state.home_sub_cat  = HOME_SUBS[cat][0]
            st.rerun()

    # ══════════════════════════════════════════════════════
    # 3. SUBCATEGORY ROW — Level 2
    # ══════════════════════════════════════════════════════
    subs = HOME_SUBS[st.session_state.home_main_cat]
    # Ensure sub_cat is valid for current main cat
    if st.session_state.home_sub_cat not in subs:
        st.session_state.home_sub_cat = subs[0]

    sc_cols = st.columns(len(subs))
    for i, sub in enumerate(subs):
        is_active = sub == st.session_state.home_sub_cat
        if sc_cols[i].button(
            sub, key=f"sc_{i}_{st.session_state.home_main_cat}",
            type="primary" if is_active else "secondary",
            use_container_width=True
        ):
            st.session_state.home_sub_cat = sub
            st.rerun()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # 4. ACTIVE CONTENT PANEL — One panel only
    # ══════════════════════════════════════════════════════
    main_cat = st.session_state.home_main_cat
    sub_cat  = st.session_state.home_sub_cat

    def render_stock_table(title, subtitle, items, show_btn=True):
        """
        items = list of dicts: {sym, name, price, chg, note}
        show_btn: True = כפתור ▶ בכל שורה (מניות, ישראלי)
                  False = ללא כפתור (שווקים גלובליים)
        """
        th = ('style="padding:7px 12px;color:#8b949e;font-size:.62rem;text-transform:uppercase;'
              'border-bottom:2px solid #30363d;background:#0d1117;text-align:right;"')

        cols_def = ["סימול","שם","מחיר","שינוי","הערה"]
        header_html = "<tr>" + "".join(f"<th {th}>{c}</th>" for c in cols_def) + "</tr>"

        rows_html = ""
        for i, item in enumerate(items):
            sym   = item.get("sym","")
            name  = item.get("name","")
            price = item.get("price","—")
            chg   = item.get("chg", 0)
            note  = item.get("note","")
            clr   = "#3fb950" if chg >= 0 else "#f85149"
            arr   = chr(9650) if chg >= 0 else chr(9660)
            bg    = "#161b22" if i % 2 == 0 else "#0d1117"
            td    = f'style="padding:8px 12px;border-bottom:1px solid #1c2128;text-align:right;background:{bg};"'

            rows_html += (
                f'<tr>'
                f'<td {td}><span style="font-weight:700;color:#388bfd;font-size:.82rem;">{sym}</span></td>'
                f'<td {td}><span style="color:#8b949e;font-size:.75rem;">{name}</span></td>'
                f'<td {td}><span style="font-family:JetBrains Mono,monospace;font-size:.8rem;color:#e6edf3;font-weight:600;">{price}</span></td>'
                f'<td {td}><span style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:{clr};font-weight:600;">{arr}{abs(chg):.2f}%</span></td>'
                f'<td {td}><span style="color:#8b949e;font-size:.7rem;">{note}</span></td>'
                f'</tr>'
            )

        st.markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;overflow:hidden;">'
            f'<div style="padding:12px 14px 8px;border-bottom:1px solid #21262d;">'
            f'<div style="font-size:.88rem;font-weight:700;color:#e6edf3;">{title}</div>'
            + (f'<div style="color:#8b949e;font-size:.68rem;margin-top:2px;">{subtitle}</div>' if subtitle else '')
            + f'</div>'
            f'<div style="overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;direction:rtl;">'
            f'<thead>{header_html}</thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div></div>',
            unsafe_allow_html=True
        )

        # כפתורי פתיחה — רק אם show_btn=True
        if show_btn and items:
            st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
            btn_cols = st.columns(min(len(items), 8))
            for i, item in enumerate(items[:8]):
                sym = item.get("sym","")
                if not sym or sym == "—": continue
                is_cur = sym == st.session_state.ticker
                if btn_cols[i].button(sym, key=f"tbl_btn_{sym}_{i}",
                                       type="primary" if is_cur else "secondary",
                                       use_container_width=True):
                    st.session_state.ticker = sym
                    st.session_state.ai_res = None
                    if sym not in st.session_state.recent:
                        st.session_state.recent.insert(0, sym)
                        st.session_state.recent = st.session_state.recent[:8]
                    save_user_data()
                    st.rerun()


    def price_row(sym, name, price, chg, note="", flag=""):
        """Legacy — kept for RTL Israeli table only"""
        clr = "#3fb950" if chg >= 0 else "#f85149"
        arr = chr(9650) if chg >= 0 else chr(9660)
        return (
            f'<tr>'
            f'<td style="padding:9px 12px;font-weight:700;color:#388bfd;'
            f'font-size:.82rem;border-bottom:1px solid #1c2128;white-space:nowrap;">'
            f'{flag} {sym}</td>'
            f'<td style="padding:9px 12px;color:#8b949e;font-size:.75rem;'
            f'border-bottom:1px solid #1c2128;max-width:140px;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;">{name}</td>'
            f'<td style="padding:9px 12px;font-family:JetBrains Mono,monospace;'
            f'font-size:.8rem;color:#e6edf3;font-weight:600;border-bottom:1px solid #1c2128;'
            f'white-space:nowrap;">{price}</td>'
            f'<td style="padding:9px 12px;font-family:JetBrains Mono,monospace;'
            f'font-size:.78rem;color:{clr};font-weight:600;border-bottom:1px solid #1c2128;'
            f'white-space:nowrap;">{arr}{abs(chg):.2f}%</td>'
            f'<td style="padding:9px 12px;color:#8b949e;font-size:.7rem;'
            f'border-bottom:1px solid #1c2128;">{note}</td>'
            f'</tr>'
        )

    def content_panel(title, subtitle, table_rows, cols=("סימול","שם","מחיר","שינוי","הערה"), rtl=False):
        dir_style = 'direction:rtl;text-align:right;' if rtl else ''
        th = f'style="padding:7px 12px;color:#8b949e;font-size:.64rem;text-transform:uppercase;' \
             f'border-bottom:2px solid #30363d;background:#0d1117;"'
        header = "<tr>" + "".join(f"<th {th}>{c}</th>" for c in cols) + "</tr>"
        return (
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            f'overflow:hidden;{dir_style}">'
            f'<div style="padding:14px 16px 10px;border-bottom:1px solid #21262d;">'
            f'<div style="font-size:.9rem;font-weight:700;color:#e6edf3;">{title}</div>'
            + (f'<div style="color:#8b949e;font-size:.7rem;margin-top:2px;">{subtitle}</div>' if subtitle else '')
            + f'</div>'
            f'<div style="overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;{dir_style}">'
            f'<thead>{header}</thead>'
            f'<tbody>{"".join(table_rows)}</tbody>'
            f'</table></div></div>'
        )

    # ── מניות panels ──
    if main_cat == "מניות":

        if sub_cat == "🔥 מומלצות AI":
            hot = load_hot_stocks()
            items_hot = []
            for s in hot[:5]:
                p = get_live_price(s["ticker"])
                pstr = f'${p:.2f}' if p else "—"
                items_hot.append({
                    "sym":   s["ticker"],
                    "name":  s.get("name",""),
                    "price": pstr,
                    "chg":   0.5 if s.get("direction")=="bullish" else -0.5,
                    "note":  s.get("reason",""),
                })
            render_stock_table("🔥 מומלצות AI", "5 מניות חמות לפי המלצת AI — מתעדכן כל שעה", items_hot)

        else:
            # Category stocks
            cat_map = {
                "🤖 AI":      CATEGORIES.get("🤖 AI", []),
                "📱 Tech":    CATEGORIES.get("📱 Tech", []),
                "🏦 Finance": CATEGORIES.get("🏦 Finance", []),
            }
            # מניות בולטות = movers
            if sub_cat == "🇺🇸 מניות בולטות":
                with st.spinner(""):
                    movers_data = load_market_movers()
                items_mv = [{"sym":r["sym"],"name":"","price":f'${r["price"]:,.2f}',"chg":r["chg"],"note":"עולה ביותר"} for r in movers_data.get("gainers",[])[:5]]
                render_stock_table("🇺🇸 מניות בולטות", "עולות ביותר היום", items_mv)
            else:
                syms_list = cat_map.get(sub_cat, [])
                items_cat = []
                for sym_c in syms_list:
                    sname, sdesc = STOCK_DESCS.get(sym_c, (sym_c, ""))
                    p = get_live_price(sym_c)
                    pstr = f'${p:.2f}' if p else "—"
                    items_cat.append({"sym":sym_c,"name":sname,"price":pstr,"chg":0,"note":sdesc})
                if items_cat:
                    render_stock_table(sub_cat, "", items_cat)

    # ── שווקים גלובליים ──
    elif main_cat == "שווקים גלובליים":
        GLOBAL_ITEMS = {
            "📈 מדדים": [("S&P 500","^GSPC"),("נאסד\"ק 100","^NDX"),("Dow Jones","^DJI"),
                         ("גרמניה 40","^GDAXI"),("בריטניה 100","^FTSE"),("יפן 225","^N225"),("ASX 200","^AXJO"),("VIX","^VIX")],
            "$ מט\"ח":  [("יורו/דולר","EURUSD=X"),("פאונד/דולר","GBPUSD=X"),("דולר/ין","JPY=X"),
                          ("דולר/שקל","ILS=X"),("שוויצרי","CHF=X"),("קנדי","CAD=X")],
            "🛢 סחורות":[("זהב","GC=F"),("נפט","CL=F"),("כסף","SI=F"),("גז טבעי","NG=F"),("נחושת","HG=F")],
            "₿ קריפטו":[("Bitcoin","BTC-USD"),("Ethereum","ETH-USD"),("Solana","SOL-USD"),("BNB","BNB-USD")],
        }
        items = GLOBAL_ITEMS.get(sub_cat, [])
        with st.spinner(""):
            grp_data = load_market_group(tuple(items))
        items_gl = []
        for name, sym in items:
            d = grp_data.get(name,{})
            if d:
                p = d["price"]
                pstr = f'{p:,.0f}' if p>1000 else (f'{p:,.3f}' if p<10 else f'{p:,.2f}')
                items_gl.append({"sym":sym.replace("=X","").replace("^",""),"name":name,"price":pstr,"chg":d["chg"],"note":""})
            else:
                items_gl.append({"sym":"—","name":name,"price":"—","chg":0,"note":"טוען..."})
        render_stock_table(sub_cat, "נתוני שוק בזמן אמת", items_gl, show_btn=False)

    # ── שוק ישראלי ── (RTL)
    elif main_cat == "שוק ישראלי":
        TA_MAP = {
            "🔥 חמות":    ["TEVA.TA","NICE.TA","CHKP.TA","ESLT.TA","ICL.TA"],
            'ת"א 125':    ["FIBI.TA","LUMI.TA","DSCT.TA","TEVA.TA","NICE.TA","CHKP.TA","ESLT.TA","ICL.TA"],
            'ת"א 35':     ["FIBI.TA","LUMI.TA","DSCT.TA","ESLT.TA","TEVA.TA","NICE.TA","CHKP.TA","ICL.TA"],
            "בנקים":      ["FIBI.TA","LUMI.TA","DSCT.TA","HAPO.TA","MIZR.TA"],
            "טכנולוגיה":  ["NICE.TA","CHKP.TA","ESLT.TA"],
            "נדל\"ן":     ["AZRG.TA","EMCO.TA","AFRE.TA","AMOT.TA"],
            "ביומד":      ["TEVA.TA","KMDA.TA","SPNS.TA"],
            "נפט וגז":    ["DLEKG.TA","NFTA.TA"],
        }
        ta_syms = TA_MAP.get(sub_cat, [])

        with st.spinner(""):
            ta_rows = []
            for s in ta_syms:
                try:
                    h = yf.Ticker(s).history(period="2d")
                    if len(h) >= 2:
                        c = float(h['Close'].iloc[-1]); p2 = float(h['Close'].iloc[-2])
                        chg = (c-p2)/p2*100
                        inf_s = load_info(s)
                        nm = (inf_s.get("shortName","") or s.replace(".TA",""))[:18]
                        ta_rows.append((s.replace(".TA",""), nm, f'₪{c:,.2f}', chg))
                except: pass

        # RTL table — columns: מניה | שם | מחיר | שינוי
        th_rtl = 'style="padding:7px 12px;color:#8b949e;font-size:.64rem;text-transform:uppercase;border-bottom:2px solid #30363d;background:#0d1117;text-align:right;"'
        rows_html = ""
        for i, (sym_ta, nm_ta, price_ta, chg_ta) in enumerate(ta_rows):
            clr = "#3fb950" if chg_ta >= 0 else "#f85149"
            arr = chr(9650) if chg_ta >= 0 else chr(9660)
            bg  = "#161b22" if i%2==0 else "#0d1117"
            rows_html += (
                f'<tr style="background:{bg};">'
                f'<td style="padding:9px 12px;font-weight:700;color:#388bfd;font-size:.82rem;'
                f'border-bottom:1px solid #1c2128;text-align:right;">{sym_ta}</td>'
                f'<td style="padding:9px 12px;color:#8b949e;font-size:.75rem;'
                f'border-bottom:1px solid #1c2128;text-align:right;">{nm_ta}</td>'
                f'<td style="padding:9px 12px;font-family:JetBrains Mono,monospace;'
                f'font-size:.8rem;color:#e6edf3;font-weight:600;border-bottom:1px solid #1c2128;text-align:right;">{price_ta}</td>'
                f'<td style="padding:9px 12px;font-family:JetBrains Mono,monospace;'
                f'font-size:.78rem;color:{clr};font-weight:600;border-bottom:1px solid #1c2128;text-align:right;">{arr}{abs(chg_ta):.2f}%</td>'
                f'</tr>'
            )

        st.markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            f'overflow:hidden;direction:rtl;">'
            f'<div style="padding:14px 16px 10px;border-bottom:1px solid #21262d;">'
            f'<div style="font-size:.9rem;font-weight:700;color:#e6edf3;text-align:right;">'
            f'מניות בולטות — {sub_cat}</div>'
            f'<div style="color:#8b949e;font-size:.7rem;margin-top:2px;text-align:right;">'
            f'נתונים בזמן אמת · בורסת תל אביב</div>'
            f'</div>'
            f'<div style="overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;direction:rtl;">'
            f'<thead><tr>'
            f'<th {th_rtl}>מניה</th>'
            f'<th {th_rtl}>שם</th>'
            f'<th {th_rtl}>מחיר</th>'
            f'<th {th_rtl}>שינוי</th>'
            f'</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div></div>',
            unsafe_allow_html=True
        )

        # ── כפתורי פתיחה לשוק ישראלי ──
        if ta_rows:
            st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
            ta_btn_cols = st.columns(len(ta_rows))
            for i, (sym_ta, nm_ta, price_ta, chg_ta) in enumerate(ta_rows):
                full_sym = sym_ta + ".TA"
                is_cur = full_sym == st.session_state.ticker or sym_ta == st.session_state.ticker
                if ta_btn_cols[i].button(sym_ta, key=f"ta_open_{sym_ta}_{i}",
                                          type="primary" if is_cur else "secondary",
                                          use_container_width=True):
                    st.session_state.ticker = full_sym
                    st.session_state.ai_res = None
                    if full_sym not in st.session_state.recent:
                        st.session_state.recent.insert(0, full_sym)
                        st.session_state.recent = st.session_state.recent[:8]
                    save_user_data()
                    st.rerun()


    # ── האישי שלי ──
    elif main_cat == "האישי שלי":

        if sub_cat == "תיק":
            pf_pos = st.session_state.get('portfolio_positions', [])
            if not pf_pos:
                st.markdown(
                    '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                    'padding:40px;text-align:center;">'
                    '<div style="font-size:2rem;">💼</div>'
                    '<div style="color:#8b949e;margin-top:8px;">תיק ריק — הוסיפי מניות בטאב 💼 תיק</div>'
                    '</div>', unsafe_allow_html=True
                )
            else:
                tv = tc = 0
                pf_items = []
                for pos in pf_pos:
                    pr = get_live_price(pos['symbol']) or pos['cost']
                    cv = pos['qty']*pr; cc = pos['qty']*pos['cost']
                    tv += cv; tc += cc
                    ret = (pr-pos['cost'])/pos['cost']*100
                    pf_items.append({"sym":pos['symbol'],"name":f"{pos['qty']:.0f} מניות","price":f"${pr:.2f}","chg":ret,"note":f"${cv:,.0f}"})
                tr = (tv-tc)/tc*100 if tc else 0
                rc = "#3fb950" if tr>=0 else "#f85149"
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">'
                    f'<div style="background:#161b22;border:1px solid #21262d;border-radius:9px;padding:12px;text-align:center;">'
                    f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">שווי נוכחי</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;font-weight:700;color:#e6edf3;">${tv:,.0f}</div></div>'
                    f'<div style="background:#161b22;border:1px solid #21262d;border-radius:9px;padding:12px;text-align:center;">'
                    f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">עלות</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;font-weight:700;color:#8b949e;">${tc:,.0f}</div></div>'
                    f'<div style="background:#161b22;border:1px solid {rc}33;border-radius:9px;padding:12px;text-align:center;">'
                    f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">תשואה</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;font-weight:700;color:{rc};">{tr:+.1f}%</div></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                render_stock_table("💼 תיק השקעות", "", pf_items)

        elif sub_cat == "Watchlist":
            wl_syms = st.session_state.get('watchlist', [])
            if not wl_syms:
                st.markdown(
                    '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                    'padding:40px;text-align:center;">'
                    '<div style="font-size:2rem;">👁️</div>'
                    '<div style="color:#8b949e;margin-top:8px;">Watchlist ריקה — הוסיפי מניות בטאב 👁️</div>'
                    '</div>', unsafe_allow_html=True
                )
            else:
                wl_items = []
                for sym_wl in wl_syms[:10]:
                    try:
                        p_wl = get_live_price(sym_wl)
                        d_wl = load_ohlcv(sym_wl, "5D", "1d")
                        if p_wl and d_wl is not None and len(d_wl) >= 2:
                            pv = float(d_wl['Close'].iloc[-2])
                            chg_wl = (p_wl - pv) / pv * 100
                            wl_items.append({"sym":sym_wl,"name":"","price":f'${p_wl:.2f}',"chg":chg_wl,"note":""})
                    except: pass

                render_stock_table("👁️ Watchlist", "", wl_items)

        elif sub_cat == "התראות":
            alerts_h = st.session_state.get('alerts_list', [])
            if not alerts_h:
                st.markdown(
                    '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                    'padding:40px;text-align:center;">'
                    '<div style="font-size:2rem;">🔔</div>'
                    '<div style="color:#8b949e;margin-top:8px;">אין התראות פעילות — הגדרי בטאב 🔔</div>'
                    '</div>', unsafe_allow_html=True
                )
            else:
                st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;overflow:hidden;">',
                            unsafe_allow_html=True)
                for a in alerts_h[:8]:
                    cur_a  = get_live_price(a['sym']) or 0
                    trig   = a.get("triggered", False)
                    bc     = "#3fb950" if trig else "#388bfd"
                    status = "✅ הופעלה" if trig else "⏳ ממתינה"
                    dist   = ((cur_a - a['target']) / a['target'] * 100) if cur_a else 0
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:11px 14px;border-bottom:1px solid #1c2128;">'
                        f'<div>'
                        f'<span style="font-weight:700;color:#388bfd;font-size:.82rem;">{a["sym"]}</span>'
                        f'<span style="color:#8b949e;font-size:.75rem;margin-right:8px;"> {a["cond"]} ${a["target"]:.2f}</span>'
                        f'</div>'
                        f'<div style="display:flex;gap:10px;align-items:center;">'
                        f'<span style="color:#8b949e;font-size:.72rem;">${cur_a:.2f} ({dist:+.1f}%)</span>'
                        f'<span style="background:{bc}22;color:{bc};border:1px solid {bc}44;'
                        f'border-radius:10px;padding:2px 8px;font-size:.68rem;font-weight:600;">{status}</span>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="color:#8b949e;font-size:.6rem;text-align:center;margin-top:14px;">'
        'Alpha Charts Pro · לצרכי ניתוח בלבד · אינו ייעוץ השקעות</div>',
        unsafe_allow_html=True
    )



with t1:

    # ── שורת בקרה אחת — period + chart type + actions ──
    ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns([4, 2, 1, 1, 1])

    with ctrl1:
        np_ = st.radio("period:", list(PERIODS.keys()),
                       index=list(PERIODS.keys()).index(st.session_state.period),
                       horizontal=True, label_visibility="collapsed", key="pr")
        if np_ != st.session_state.period:
            st.session_state.period = np_
            st.rerun()

    with ctrl2:
        ct_opts = ["קווי", "נרות", "שטח"]
        ct_vals = {"קווי": "line", "נרות": "candlestick", "שטח": "area"}
        ct_inv  = {"line": "קווי", "candlestick": "נרות", "area": "שטח"}
        nct = st.radio("ct:", ct_opts,
                       index=ct_opts.index(ct_inv[st.session_state.ct]),
                       horizontal=True, label_visibility="collapsed", key="ctr")
        if ct_vals[nct] != st.session_state.ct:
            st.session_state.ct = ct_vals[nct]
            st.rerun()

    with ctrl3:
        ind_on = st.session_state.show_ind
        if st.button("Ind" + ("✓" if ind_on else ""), key="aind",
                     help="Indicators — MA, Bollinger", use_container_width=True):
            st.session_state.show_ind = not ind_on
            st.rerun()

    with ctrl4:
        ai_on = st.session_state.show_ai
        if st.button("AI" + ("✓" if ai_on else ""), key="aai",
                     help="AI Insight", use_container_width=True):
            st.session_state.show_ai = not ai_on
            if st.session_state.show_ai and st.session_state.ai_res is None:
                with st.spinner(""):
                    try:
                        cl2     = df['Close'].astype(float)
                        lc2     = float(cl2.iloc[-1]); pc2 = float(cl2.iloc[-2])
                        dc2     = (lc2 - pc2) / pc2 * 100
                        rsi2    = float(df['RSI'].iloc[-1]) if 'RSI' in df.columns else 50
                        ma200_2 = float(df['MA200'].iloc[-1]) if 'MA200' in df.columns else lc2
                        vok2    = False
                        if 'Volume' in df.columns:
                            vol2 = df['Volume'].astype(float)
                            avg2 = float(vol2.rolling(20).mean().iloc[-1])
                            vok2 = float(vol2.iloc[-1]) > avg2 * 1.2 if avg2 > 0 else False
                        prompt = (
                            f"Analyze {ticker}: price {lc2:.2f}, change {dc2:+.2f}%, "
                            f"RSI {rsi2:.0f}, "
                            + ("above" if lc2 > ma200_2 else "below")
                            + " MA200. Return ONLY JSON no markdown: "
                            '{"trend":"שורי/דובי/נייטרלי","strength":"חזק/בינוני/חלש",'
                            '"signal":"3 words Hebrew","vol_ok":' + str(vok2).lower() + ','
                            '"summary":"2 sentences Hebrew","detail":"1 sentence Hebrew"}'
                        )
                        resp = requests.post(
                            "https://api.anthropic.com/v1/messages",
                            headers=ai_headers(),
                            json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                                  "messages": [{"role": "user", "content": prompt}]},
                            timeout=15
                        )
                        if resp.status_code == 200:
                            txt = resp.json()['content'][0]['text'].strip().replace("```json","").replace("```","")
                            st.session_state.ai_res = json.loads(txt)
                        else:
                            raise Exception()
                    except:
                        st.session_state.ai_res = {
                            "trend": "שורי" if dc2 > 0 else "דובי",
                            "strength": "בינוני", "signal": "איתות מתון",
                            "vol_ok": False,
                            "summary": f"המניה {ticker} שינתה {dc2:+.2f}% עם RSI {rsi2:.0f}.",
                            "detail": f"הנר נסגר {'בעלייה' if dc2>0 else 'בירידה'}.",
                        }
            st.rerun()

    with ctrl5:
        if st.button("↺", key="arst", help="אפס", use_container_width=True):
            st.session_state.period   = "1Y"
            st.session_state.ct       = "line"
            st.session_state.show_an  = False
            st.session_state.show_ai  = False
            st.session_state.show_ind = True
            st.rerun()

    # Analytics button on separate line (wide)
    an_on = st.session_state.show_an
    if st.button("📊 Analytics" + (" ✓" if an_on else ""), key="aan",
                 help="נתונים כספיים רבעוניים"):
        st.session_state.show_an = not an_on
        st.rerun()

    # ── Indicators panel ──
    if st.session_state.show_ind:
        ic1, ic2, ic3, ic4 = st.columns(4)
        st.session_state.ma20  = ic1.checkbox("MA20",      value=st.session_state.ma20,  key="c20",
                                              help="ממוצע נע 20 ימים (קו צהוב)")
        st.session_state.ma50  = ic2.checkbox("MA50",      value=st.session_state.ma50,  key="c50",
                                              help="ממוצע נע 50 ימים (קו ירוק) — מחיר מעליו = מגמה חיובית")
        st.session_state.ma200 = ic3.checkbox("MA200",     value=st.session_state.ma200, key="c200",
                                              help="ממוצע נע 200 ימים (קו אדום) — הקו הכי חשוב")
        st.session_state.bb    = ic4.checkbox("Bollinger", value=st.session_state.bb,    key="cbb",
                                              help="רצועות בולינגר — מסגרת התנועה הרגילה")
        ic5, ic6, ic7, ic8 = st.columns(4)
        st.session_state.sr        = ic5.checkbox("Support/Resistance", value=st.session_state.sr,        key="csr",
                                                   help="רמות תמיכה והתנגדות — איפה המחיר עצר בעבר")
        st.session_state.fib       = ic6.checkbox("Fibonacci",          value=st.session_state.fib,       key="cfib",
                                                   help="רמות Fibonacci Retracement — 38.2% / 50% / 61.8% וה-Golden Zone")
        st.session_state.trendline = ic7.checkbox("Trend Line",         value=st.session_state.trendline, key="ctrl",
                                                   help="קו מגמה אוטומטי לפי נקודות שיא ושפל")
        st.session_state.channel   = ic8.checkbox("Trend Channel",      value=st.session_state.channel,   key="cch",
                                                   help="ערוץ מגמה — גבול עליון ותחתון של התנועה")

    # ── תיקון נפח 0 ──
    lv_display = lv
    if 'Volume' in df.columns:
        vol_nz = df['Volume'].astype(float).replace(0, pd.NA).dropna()
        if not vol_nz.empty:
            lv_display = float(vol_nz.iloc[-1])

    # ── OHLC Banner ──
    ohlc_c = "#3fb950" if lc >= lo else "#f85149"
    st.markdown(
        '<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;'
        'padding:7px 14px;margin-bottom:4px;direction:rtl;">'
        '<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;'
        'font-family:\'JetBrains Mono\',monospace;font-size:.82rem;">'
        f'<span><span style="color:#8b949e;font-size:.65rem;">פתיחה </span>'
        f'<span style="color:#e6edf3;font-weight:600;">{sym}{lo:.2f}</span></span>'
        f'<span><span style="color:#8b949e;font-size:.65rem;">גבוה </span>'
        f'<span style="color:#3fb950;font-weight:700;">{sym}{lh:.2f}</span></span>'
        f'<span><span style="color:#8b949e;font-size:.65rem;">נמוך </span>'
        f'<span style="color:#f85149;font-weight:700;">{sym}{ll:.2f}</span></span>'
        f'<span><span style="color:#8b949e;font-size:.65rem;">סגירה </span>'
        f'<span style="color:{ohlc_c};font-weight:800;">{sym}{lc:.2f}</span></span>'
        f'<span><span style="color:#8b949e;font-size:.65rem;">נפח </span>'
        f'<span style="color:#8b949e;">{lv_display:,.0f}</span></span>'
        f'<span style="margin-right:auto;color:#8b949e;font-size:.65rem;">'
        f'{ticker} · {st.session_state.period}</span>'
        '</div>'
        '<div style="color:#8b949e;font-size:.65rem;margin-top:3px;'
        'padding-top:3px;border-top:1px solid #21262d;">'
        '💡 פתיחה/גבוה/נמוך/סגירה = נתוני יום המסחר האחרון · '
        '<span style="color:#3fb950;">ירוק = עלייה</span> · '
        '<span style="color:#f85149;">אדום = ירידה</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── CHART ──
    idx   = df.index
    cl_np = df['Close'].to_numpy(dtype=float)
    op_np = df['Open'].to_numpy(dtype=float)
    hi_np = df['High'].to_numpy(dtype=float)
    lo_np = df['Low'].to_numpy(dtype=float)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.025, row_heights=[0.60, 0.18, 0.22],
    )



    # ── Hover text — טקסט רגיל בלבד, עובד ב-Streamlit ──
    hover_ohlcv = []
    has_vol = 'Volume' in df.columns
    for i in range(len(df)):
        dt  = str(df.index[i])[:10]
        o_  = float(df['Open'].iloc[i])
        h_  = float(df['High'].iloc[i])
        l_  = float(df['Low'].iloc[i])
        cl_ = float(df['Close'].iloc[i])
        txt = (
            f"<b>{dt}</b><br>"
            f"Close:  {sym}{cl_:,.2f}<br>"
            f"Open:   {sym}{o_:,.2f}<br>"
            f"High:   {sym}{h_:,.2f}<br>"
            f"Low:    {sym}{l_:,.2f}"
        )
        if has_vol:
            v_ = float(df['Volume'].iloc[i])
            if v_ > 0:
                txt += f"<br>Volume: {v_:,.0f}"
        hover_ohlcv.append(txt)

    ct = st.session_state.ct
    if ct == "candlestick":
        fig.add_trace(go.Candlestick(
            x=idx, open=op_np, high=hi_np, low=lo_np, close=cl_np,
            increasing=dict(line=dict(color='#3fb950', width=1), fillcolor='#3fb950'),
            decreasing=dict(line=dict(color='#f85149', width=1), fillcolor='#f85149'),
            name=ticker, showlegend=True,
            text=hover_ohlcv,
            hoverinfo='text',
        ), row=1, col=1)
    elif ct == "line":
        fig.add_trace(go.Scatter(
            x=idx, y=cl_np, name=ticker,
            mode='lines',
            line=dict(color='#388bfd', width=2.5),
            text=hover_ohlcv,
            hoverinfo='text',
        ), row=1, col=1)
    else:  # area
        fig.add_trace(go.Scatter(
            x=idx, y=cl_np, name=ticker,
            mode='lines',
            line=dict(color='#388bfd', width=2.5),
            fill='tozeroy', fillcolor='rgba(56,139,253,0.08)',
            text=hover_ohlcv,
            hoverinfo='text',
        ), row=1, col=1)

    ma_defs = [
        ('MA20',  '#d29922', 1.2, st.session_state.ma20),
        ('MA50',  '#3fb950', 1.2, st.session_state.ma50),
        ('MA200', '#f85149', 1.5, st.session_state.ma200),
    ]
    for col_name, color, width, enabled in ma_defs:
        if enabled and col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=idx, y=df[col_name].to_numpy(dtype=float), name=col_name,
                line=dict(color=color, width=width), showlegend=True,
            ), row=1, col=1)

    if st.session_state.bb and 'BB_U' in df.columns:
        bbu = df['BB_U'].to_numpy(dtype=float)
        bbl = df['BB_L'].to_numpy(dtype=float)
        fig.add_trace(go.Scatter(x=idx, y=bbu, name="BB+",
            line=dict(color='rgba(139,92,246,0.55)', width=1, dash='dash'), showlegend=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=idx, y=bbl, name="BB-",
            line=dict(color='rgba(139,92,246,0.55)', width=1, dash='dash'),
            fill='tonexty', fillcolor='rgba(139,92,246,0.04)', showlegend=False), row=1, col=1)

    # ── Support / Resistance — שיפור: שימוש ב-High/Low לא רק Close ──
    if st.session_state.sr:
        hi_s = df['High'].astype(float)
        lo_s = df['Low'].astype(float)
        res_lvls, _ = calc_support_resistance(hi_s)
        _, sup_lvls  = calc_support_resistance(lo_s)
        for lvl in res_lvls:
            fig.add_hline(y=lvl, line_dash="dash", line_color="rgba(248,81,73,0.55)",
                          line_width=1.5,
                          annotation_text=f"  התנגדות  {sym}{lvl:.2f}",
                          annotation_position="right",
                          annotation_font=dict(color="#f85149", size=10))
            fig.add_hrect(y0=lvl*0.998, y1=lvl*1.002,
                          fillcolor="rgba(248,81,73,0.04)", line_width=0)
        for lvl in sup_lvls:
            fig.add_hline(y=lvl, line_dash="dash", line_color="rgba(63,185,80,0.55)",
                          line_width=1.5,
                          annotation_text=f"  תמיכה  {sym}{lvl:.2f}",
                          annotation_position="right",
                          annotation_font=dict(color="#3fb950", size=10))
            fig.add_hrect(y0=lvl*0.998, y1=lvl*1.002,
                          fillcolor="rgba(63,185,80,0.04)", line_width=0)

    # ── Fibonacci Retracement ──
    if st.session_state.fib:
        fib_high = float(df['High'].max())
        fib_low  = float(df['Low'].min())
        fib_lvls = calc_fibonacci(fib_high, fib_low)

        fib_meta = {
            "0%":    ("rgba(150,150,150,0.5)",  1.0),
            "23.6%": ("rgba(255,215,0,0.8)",    1.2),
            "38.2%": ("rgba(255,165,0,0.9)",    1.8),
            "50.0%": ("rgba(255,120,50,0.9)",   2.0),
            "61.8%": ("rgba(255,80,80,1.0)",    2.2),
            "78.6%": ("rgba(200,40,40,0.85)",   1.5),
            "100%":  ("rgba(150,150,150,0.5)",  1.0),
        }
        for label, price in fib_lvls.items():
            clr, lw = fib_meta.get(label, ("rgba(150,150,150,0.5)", 1.0))
            fig.add_hline(
                y=price,
                line_dash="dot" if label in ("0%","100%") else "dash",
                line_color=clr, line_width=lw,
                annotation_text=f"  Fib {label}  {sym}{price:.2f}",
                annotation_position="right",
                annotation_font=dict(color=clr, size=10),
            )
        g_up = fib_lvls.get("38.2%", 0)
        g_dn = fib_lvls.get("61.8%", 0)
        if g_up and g_dn:
            fig.add_hrect(y0=g_dn, y1=g_up,
                          fillcolor="rgba(255,140,0,0.07)", line_width=0,
                          annotation_text="  ✨ Golden Zone",
                          annotation_position="right",
                          annotation_font=dict(color="rgba(255,165,0,0.8)", size=9))

    # ── Trend Line — שיפור: regression על כל הנתונים + הצגת כיוון ──
    if st.session_state.trendline:
        cl_s   = df['Close'].astype(float)
        cl_arr = cl_s.to_numpy(dtype=float)
        x      = np.arange(len(cl_arr))
        coeffs = np.polyfit(x, cl_arr, 1)
        trend  = np.poly1d(coeffs)(x)
        slope  = coeffs[0]
        tclr   = '#3fb950' if slope >= 0 else '#f85149'
        tlabel = f"מגמה {'עולה ▲' if slope >= 0 else 'יורדת ▼'}"
        fig.add_trace(go.Scatter(
            x=idx, y=trend, name=tlabel,
            line=dict(color=tclr, width=2, dash='dot'),
            showlegend=True, hoverinfo='skip',
        ), row=1, col=1)

    # ── Trend Channel — שיפור: fill ברור + קו מרכז ──
    if st.session_state.channel:
        cl_s = df['Close'].astype(float)
        ch_mid, ch_up, ch_dn = calc_channel(cl_s)
        fig.add_trace(go.Scatter(
            x=idx, y=ch_up, name="ערוץ ↑",
            line=dict(color='rgba(188,140,255,0.7)', width=1.5, dash='dot'),
            showlegend=True, hoverinfo='skip'), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=ch_dn, name="ערוץ ↓",
            line=dict(color='rgba(188,140,255,0.7)', width=1.5, dash='dot'),
            fill='tonexty', fillcolor='rgba(188,140,255,0.05)',
            showlegend=False, hoverinfo='skip'), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=ch_mid, name="ציר ערוץ",
            line=dict(color='rgba(188,140,255,0.4)', width=1, dash='longdash'),
            showlegend=False, hoverinfo='skip'), row=1, col=1)


    if 'Volume' in df.columns:
        vol_np = df['Volume'].to_numpy(dtype=float)
        vol_c  = ['#3fb950' if cl_np[i] >= op_np[i] else '#f85149' for i in range(len(df))]
        fig.add_trace(go.Bar(x=idx, y=vol_np, marker_color=vol_c,
            name="נפח", opacity=0.70, showlegend=False,
            hovertemplate="נפח: %{y:,.0f}<extra></extra>"), row=2, col=1)
        vol_ma = pd.Series(vol_np).rolling(20).mean().to_numpy(dtype=float)
        fig.add_trace(go.Scatter(x=idx, y=vol_ma, name="ממוצע נפח",
            line=dict(color='#8b949e', width=1.2), showlegend=False), row=2, col=1)

    if 'MACD' in df.columns:
        macd_h = df['MACD_H'].to_numpy(dtype=float)
        hc     = ['#3fb950' if v >= 0 else '#f85149' for v in macd_h]
        fig.add_trace(go.Bar(x=idx, y=macd_h, marker_color=hc,
            name="MACD Hist", opacity=0.8, showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=idx, y=df['MACD'].to_numpy(dtype=float), name="MACD",
            line=dict(color='#388bfd', width=1.3), showlegend=True), row=3, col=1)
        fig.add_trace(go.Scatter(x=idx, y=df['MACD_S'].to_numpy(dtype=float), name="Signal",
            line=dict(color='#f0883e', width=1.3), showlegend=True), row=3, col=1)

    axis_s = dict(gridcolor=GR, zeroline=False, color='#8b949e', showgrid=True, linecolor=GR)

    # crosshair — קו אנכי ואופקי מקווקו
    spike_x = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikemode='across', spikesnap='cursor',
    )
    spike_y = dict(
        showspikes=True, spikecolor='#4a90d9',
        spikethickness=1, spikedash='dash',
        spikesnap='cursor',
    )

    fig.update_layout(
        height=760, paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family='Heebo, Inter', color='#8b949e', size=11),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='#161b22',
            bordercolor='#161b22',
            font=dict(family='JetBrains Mono', size=11, color='#e6edf3'),
            namelength=0,
        ),
        legend=dict(orientation='h', y=1.04, x=0, bgcolor='rgba(0,0,0,0)',
                    font=dict(size=10, color='#c9d1d9')),
        margin=dict(l=0, r=58, t=28, b=10),
        xaxis_rangeslider_visible=False, dragmode='pan',
        xaxis =dict(**axis_s, **spike_x),
        yaxis =dict(**axis_s, **spike_y, side='right'),
        xaxis2=dict(**axis_s, **spike_x),
        yaxis2=dict(**axis_s, **spike_y, side='right'),
        xaxis3=dict(**axis_s, **spike_x),
        yaxis3=dict(**axis_s, **spike_y, side='right'),
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"scrollZoom": True, "displayModeBar": True,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"]})

    # ── RSI ──
    if 'RSI' in df.columns:
        rsi_val = float(df['RSI'].iloc[-1])
        rsi_np  = df['RSI'].to_numpy(dtype=float)
        if rsi_val >= 70:
            rsi_txt = f"RSI {rsi_val:.0f} — המניה עשויה להיות קנויה מדי. שים לב לתיקון אפשרי."
            rsi_clr = "#f85149"
        elif rsi_val <= 30:
            rsi_txt = f"RSI {rsi_val:.0f} — המניה עשויה להיות מכורה מדי. ייתכן קפיצה חזרה."
            rsi_clr = "#3fb950"
        else:
            rsi_txt = f"RSI {rsi_val:.0f} — אזור נייטרלי, אין לחץ קיצוני."
            rsi_clr = "#8b949e"

        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;'
            'padding:7px 14px;margin-bottom:4px;display:flex;align-items:center;'
            'gap:10px;flex-wrap:wrap;direction:rtl;">'
            '<span style="color:#bc8cff;font-size:.75rem;font-weight:700;">📐 RSI</span>'
            f'<span style="color:{rsi_clr};font-size:.78rem;">{rsi_txt}</span>'
            '<span style="color:#8b949e;font-size:.65rem;margin-right:auto;">'
            '0–30 = מכור מדי · 70–100 = קנוי מדי · 50 = נייטרלי'
            '</span>'
            '</div>',
            unsafe_allow_html=True
        )

        fig_r = go.Figure()
        fig_r.add_trace(go.Scatter(x=idx, y=rsi_np, name="RSI",
            line=dict(color='#bc8cff', width=1.5),
            hovertemplate="RSI: %{y:.1f}<extra></extra>"))
        fig_r.add_hrect(y0=70, y1=100, fillcolor="rgba(248,81,73,0.06)", line_width=0)
        fig_r.add_hrect(y0=0,  y1=30,  fillcolor="rgba(63,185,80,0.06)", line_width=0)
        for y, c_, d in [(70, "rgba(248,81,73,0.4)", "dash"),
                         (30, "rgba(63,185,80,0.4)",  "dash"),
                         (50, "#30363d",               "dot")]:
            fig_r.add_hline(y=y, line_dash=d, line_color=c_, line_width=1)
        fig_r.update_layout(
            height=125, paper_bgcolor=BG, plot_bgcolor=BG,
            margin=dict(l=0, r=58, t=5, b=8), showlegend=False,
            font=dict(family='Heebo, Inter', color='#8b949e', size=10),
            xaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e', showgrid=True),
            yaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e',
                       side='right', range=[0, 100], showgrid=True),
        )
        st.plotly_chart(fig_r, use_container_width=True)

    # ── נתוני שוק (מתחת לגרף) ──
    st.markdown('<hr style="margin:12px 0 8px;"/>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#e6edf3;font-size:.9rem;font-weight:700;'
        'margin-bottom:6px;direction:rtl;">📋 נתוני שוק</div>',
        unsafe_allow_html=True
    )
    stat_defs = [
        ("פתיחה",       f"{sym}{info.get('open', lo):.2f}"          if info.get('open')         else f"{sym}{lo:.2f}",
         "מחיר המניה בתחילת יום המסחר"),
        ("גבוה",         f"{sym}{info.get('dayHigh', lh):.2f}"       if info.get('dayHigh')      else f"{sym}{lh:.2f}",
         "המחיר הגבוה ביותר שהגיעה אליו המניה היום"),
        ("נמוך",         f"{sym}{info.get('dayLow', ll):.2f}"        if info.get('dayLow')       else f"{sym}{ll:.2f}",
         "המחיר הנמוך ביותר שהגיעה אליו המניה היום"),
        ("סגירה",        f"{sym}{lc:.2f}",
         "מחיר הסגירה — ירוק = עלה, אדום = ירד"),
        ("שווי שוק",     fmt_big(info.get("marketCap"), sym),
         "שווי כל המניות יחד. B = מיליארד, T = טריליון"),
        ("P/E",          f"{info.get('trailingPE',0):.1f}"           if info.get('trailingPE')   else "N/A",
         "מכפיל רווח — כמה משלמים על כל 1 ₪ רווח"),
        ("EPS",          f"{sym}{info.get('trailingEps',0):.2f}"     if info.get('trailingEps')  else "N/A",
         "רווח למניה"),
        ("Beta",         f"{info.get('beta',0):.2f}"                 if info.get('beta')         else "N/A",
         "תנודתיות ביחס לשוק"),
        ("דיבידנד",      f"{sym}{info.get('dividendRate',0):.2f}"    if info.get('dividendRate') else "N/A",
         "תשלום שנתי לבעלי מניות"),
        ("תשואת דיב'",  f"{info.get('dividendYield',0)*100:.2f}%"   if info.get('dividendYield')else "N/A",
         "אחוז הדיבידנד מהמחיר"),
        ("מחזור יומי",   fmt_big(lv_display, ""),
         "כמה מניות נסחרו היום"),
        ("ממוצע מחזור", fmt_big(info.get("averageVolume"), ""),
         "ממוצע יומי — גבוה = מניה נזילה"),
    ]
    sc = st.columns(4)
    for i, (lb, vl_, tip) in enumerate(stat_defs):
        sc[i % 4].markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:9px;'
            f'padding:9px 11px;margin-bottom:6px;">'
            f'<div style="color:#8b949e;font-size:.65rem;text-transform:uppercase;">{lb}</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.88rem;'
            f'font-weight:600;color:#e6edf3;margin-top:2px;">{vl_}</div>'
            f'<div style="color:#8b949e;font-size:.62rem;margin-top:3px;'
            f'border-top:1px solid #21262d;padding-top:3px;">{tip}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ══════════════════════════════════════════════
    # טבלת ניתוח כלים — סיגנל לכל אינדיקטור
    # ══════════════════════════════════════════════
    st.markdown('<hr style="margin:12px 0 8px;"/>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#e6edf3;font-size:.9rem;font-weight:700;margin-bottom:6px;direction:rtl;">'
        '🔬 טבלת ניתוח טכני — סיגנל לכל כלי</div>'
        '<div style="color:#8b949e;font-size:.72rem;margin-bottom:10px;">'
        'כל שורה מראה מה הכלי מודד, מה הוא אומר כרגע, ומה המשמעות להחלטת קנייה/מכירה</div>',
        unsafe_allow_html=True
    )

    def sig_row(tool, value, signal, meaning, action_color, action):
        icon = "🟢" if action_color=="bull" else ("🔴" if action_color=="bear" else "🟡")
        bg   = "rgba(63,185,80,0.07)"   if action_color=="bull" else                "rgba(248,81,73,0.07)"   if action_color=="bear" else                "rgba(210,153,34,0.07)"
        bdr  = "rgba(63,185,80,0.3)"    if action_color=="bull" else                "rgba(248,81,73,0.3)"    if action_color=="bear" else                "rgba(210,153,34,0.3)"
        return (
            f'<div style="display:grid;grid-template-columns:1fr 1fr 2fr 1fr;gap:8px;'
            f'background:{bg};border:1px solid {bdr};border-radius:8px;'
            f'padding:8px 12px;margin-bottom:5px;direction:rtl;align-items:center;">'
            f'<div><div style="color:#e6edf3;font-size:.78rem;font-weight:700;">{tool}</div>'
            f'<div style="color:#8b949e;font-size:.65rem;">{value}</div></div>'
            f'<div style="color:#c9d1d9;font-size:.78rem;">{signal}</div>'
            f'<div style="color:#8b949e;font-size:.72rem;line-height:1.5;">{meaning}</div>'
            f'<div style="text-align:center;font-size:.82rem;font-weight:700;">{icon} {action}</div>'
            f'</div>'
        )

    rows_html = ""

    # ── MA20 ──
    if 'MA20' in df.columns and not pd.isna(df['MA20'].iloc[-1]):
        ma20v = float(df['MA20'].iloc[-1])
        above = lc > ma20v
        rows_html += sig_row(
            "MA20", f"{sym}{ma20v:.2f}",
            f"מחיר {'מעל' if above else 'מתחת ל'} MA20",
            "ממוצע 20 ימים. מחיר מעל = מגמה קצרת טווח חיובית",
            "bull" if above else "bear",
            "חיובי" if above else "שלילי"
        )

    # ── MA50 ──
    if 'MA50' in df.columns and not pd.isna(df['MA50'].iloc[-1]):
        ma50v = float(df['MA50'].iloc[-1])
        above = lc > ma50v
        rows_html += sig_row(
            "MA50", f"{sym}{ma50v:.2f}",
            f"מחיר {'מעל' if above else 'מתחת ל'} MA50",
            "ממוצע 50 ימים. הקו הנפוץ ביותר לאישור מגמה",
            "bull" if above else "bear",
            "חיובי" if above else "שלילי"
        )

    # ── MA200 ──
    if 'MA200' in df.columns and not pd.isna(df['MA200'].iloc[-1]):
        ma200v = float(df['MA200'].iloc[-1])
        above  = lc > ma200v
        # הסבר למה MA200 ירד / עלה
        ma200_arr = df['MA200'].dropna().to_numpy(dtype=float)
        ma200_slope = ma200_arr[-1] - ma200_arr[-min(20,len(ma200_arr))] if len(ma200_arr) > 1 else 0
        slope_txt = "עולה ▲" if ma200_slope > 0 else "יורד ▼"
        rows_html += sig_row(
            "MA200", f"{sym}{ma200v:.2f}",
            f"מחיר {'מעל' if above else 'מתחת ל'} MA200 · הקו {slope_txt}",
            f"ממוצע 200 ימים. הקו {slope_txt} כי הממוצע מחשב שנה שלמה — "
            f"{'מחירי העבר הנמוכים גוררים אותו למטה' if ma200_slope<=0 else 'מחירי העבר תומכים בעלייה'}",
            "bull" if above else "bear",
            "מגמה עולה" if above else "מגמה יורדת"
        )

    # ── RSI ──
    if 'RSI' in df.columns and not pd.isna(df['RSI'].iloc[-1]):
        rsi_v = float(df['RSI'].iloc[-1])
        if rsi_v >= 70:
            sig, meaning, ac, act = f"{rsi_v:.0f} — קנוי מדי", "סיכון לתיקון. הרבה קונים — עלול להגיע גל מכירות", "bear", "זהירות"
        elif rsi_v <= 30:
            sig, meaning, ac, act = f"{rsi_v:.0f} — מכור מדי", "ייתכן bounce חזרה. הרבה מוכרים — עלולים לקנות בחזרה", "bull", "הזדמנות?"
        elif rsi_v >= 55:
            sig, meaning, ac, act = f"{rsi_v:.0f} — חיובי", "מומנטום עולה. קונים חזקים יותר ממוכרים", "bull", "חיובי"
        else:
            sig, meaning, ac, act = f"{rsi_v:.0f} — נייטרלי", "אין לחץ חד לאף כיוון", "neutral", "נייטרלי"
        rows_html += sig_row("RSI", f"{rsi_v:.1f}", sig, meaning, ac, act)

    # ── Bollinger ──
    if 'BB_U' in df.columns and not pd.isna(df['BB_U'].iloc[-1]):
        bbu = float(df['BB_U'].iloc[-1]); bbl = float(df['BB_L'].iloc[-1])
        bb_mid = (bbu + bbl) / 2
        if lc > bbu:
            sig, meaning, ac, act = "מחיר מעל רצועה עליונה", "תנודתיות קיצונית — מחיר גבוה מדי ביחס לממוצע. סיכון לתיקון", "bear", "זהירות"
        elif lc < bbl:
            sig, meaning, ac, act = "מחיר מתחת רצועה תחתונה", "מחיר נמוך מדי — ייתכן bounce. הזדמנות אפשרית", "bull", "הזדמנות?"
        elif lc > bb_mid:
            sig, meaning, ac, act = "בחצי העליון של הרצועה", "מגמה חיובית בתוך הרצועה הנורמלית", "bull", "חיובי"
        else:
            sig, meaning, ac, act = "בחצי התחתון של הרצועה", "מגמה שלילית בתוך הרצועה הנורמלית", "neutral", "נייטרלי"
        rng = bbu - bbl
        close_rng = f"טווח: {sym}{bbl:.2f}–{sym}{bbu:.2f}"
        rows_html += sig_row("Bollinger", close_rng, sig, meaning, ac, act)

    # ── Volume ──
    if 'Volume' in df.columns:
        vol_s   = df['Volume'].astype(float)
        avg20_v = float(vol_s.rolling(20).mean().iloc[-1])
        if avg20_v > 0:
            ratio_v = lv_display / avg20_v
            if ratio_v >= 2.0:
                sig, meaning, ac, act = f"פי {ratio_v:.1f} מהממוצע", "נפח חריג גבוה מאוד — אירוע משמעותי. תנועת מחיר אמינה", "bull" if lc >= lo else "bear", "שים לב"
            elif ratio_v >= 1.3:
                sig, meaning, ac, act = f"פי {ratio_v:.1f} מהממוצע", "נפח מעל הרגיל — תנועת המחיר מגובה", "bull" if lc >= lo else "bear", "מאושר"
            elif ratio_v <= 0.5:
                sig, meaning, ac, act = f"פי {ratio_v:.1f} מהממוצע", "נפח נמוך מאוד — תנועה לא מאושרת, ייתכן ארעי", "neutral", "חלש"
            else:
                sig, meaning, ac, act = f"פי {ratio_v:.1f} מהממוצע", "נפח רגיל — תנועה סבירה", "neutral", "רגיל"
            rows_html += sig_row("Volume", f"{lv_display:,.0f}", sig, meaning, ac, act)

    # ── Fibonacci ──
    if 'High' in df.columns and 'Low' in df.columns:
        fh = float(df['High'].max()); fl = float(df['Low'].min())
        fib_d = {"0%": fh, "23.6%": fh-0.236*(fh-fl), "38.2%": fh-0.382*(fh-fl),
                 "50.0%": fh-0.5*(fh-fl), "61.8%": fh-0.618*(fh-fl), "100%": fl}
        fib_zone = None; fib_label = ""
        sorted_levels = sorted(fib_d.items(), key=lambda x: x[1], reverse=True)
        for i in range(len(sorted_levels)-1):
            top_lbl, top_val = sorted_levels[i]
            bot_lbl, bot_val = sorted_levels[i+1]
            if bot_val <= lc <= top_val:
                fib_zone = (bot_lbl, top_lbl, bot_val, top_val)
                break
        if fib_zone:
            bl, tl, bv, tv = fib_zone
            mid = (tv + bv) / 2
            is_golden = bl in ("38.2%","50.0%","61.8%") or tl in ("38.2%","50.0%","61.8%")
            if is_golden:
                sig = f"בתוך Golden Zone ({bl}–{tl})"
                meaning = "אזור תיקון קלאסי — רמה קריטית לכניסה. כדאי לחפש נר היפוך"
                ac = "bull"; act = "הזדמנות"
            elif lc > mid:
                sig = f"בין {bl}–{tl} (חצי עליון)"
                meaning = "תיקון בינוני — עדיין מעל מחצית הדרך בין הרמות"
                ac = "bull"; act = "ניטרלי-חיובי"
            else:
                sig = f"בין {bl}–{tl} (חצי תחתון)"
                meaning = "תיקון עמוק — מתקרב לרמת תמיכה Fibonacci"
                ac = "neutral"; act = "זהירות"
        else:
            sig, meaning, ac, act = "מחוץ לטווח", "המחיר מחוץ לרמות Fibonacci הרגילות", "neutral", "בדוק"
        rows_html += sig_row("Fibonacci", f"{sym}{lc:.2f}", sig, meaning, ac, act)

    # ── מסקנה כוללת ──
    bull_count = rows_html.count("🟢")
    bear_count = rows_html.count("🔴")
    total = bull_count + bear_count
    if total > 0:
        bull_pct = bull_count / total * 100
        if bull_pct >= 65:
            overall_clr = "#3fb950"; overall_txt = f"🟢 רוב הכלים ({bull_count}/{total}) מראים מגמה חיובית — שקלי כניסה"
        elif bull_pct <= 35:
            overall_clr = "#f85149"; overall_txt = f"🔴 רוב הכלים ({bear_count}/{total}) מראים מגמה שלילית — זהירות"
        else:
            overall_clr = "#d29922"; overall_txt = f"🟡 תמונה מעורבת — {bull_count} חיובי, {bear_count} שלילי. אין אות ברור"
        summary_html = (
            f'<div style="background:{overall_clr}15;border:1px solid {overall_clr}44;'
            f'border-radius:8px;padding:10px 14px;margin-top:8px;direction:rtl;">'
            f'<div style="color:{overall_clr};font-size:.85rem;font-weight:700;">'
            f'📊 מסקנה כוללת: {overall_txt}</div>'
            f'<div style="color:#8b949e;font-size:.65rem;margin-top:4px;">'
            f'⚠️ ניתוח טכני בלבד. אינו ייעוץ השקעות — תמיד התייעצי עם בעל רישיון.</div>'
            f'</div>'
        )
    else:
        summary_html = ""

    st.markdown(rows_html + summary_html, unsafe_allow_html=True)

    # ── ניתוח מילולי ──
    ins = analyze_candle(df)

    trend_sentence = ""
    if 'MA50' in df.columns and 'MA200' in df.columns:
        above50  = lc > float(df['MA50'].iloc[-1])
        above200 = lc > float(df['MA200'].iloc[-1])
        if above50 and above200:
            trend_sentence = "📈 המניה נמצאת <b>מעל שני ממוצעי המגמה</b> — סימן חיובי לשני טווחי זמן."
        elif not above50 and not above200:
            trend_sentence = "📉 המניה נמצאת <b>מתחת לשני ממוצעי המגמה</b> — מגמה שלילית."
        else:
            lbl50  = "מעל" if above50  else "מתחת ל"
            lbl200 = "מעל" if above200 else "מתחת ל"
            trend_sentence = f"↔️ המניה {lbl50} MA50 ו{lbl200} MA200 — מגמה מעורבת."

    vol_sentence = ""
    if 'Volume' in df.columns:
        vol_s  = df['Volume'].astype(float)
        avg_20 = float(vol_s.rolling(20).mean().iloc[-1])
        if avg_20 > 0:
            ratio_ = lv_display / avg_20
            if ratio_ >= 1.5:
                vol_sentence = f"💰 <b>נפח גבוה מהרגיל</b> (פי {ratio_:.1f}) — התנועה מגובה בעניין גבוה של המשקיעים."
            elif ratio_ <= 0.5:
                vol_sentence = "📉 <b>נפח נמוך מהרגיל</b> — התנועה היום פחות משמעותית."
            else:
                vol_sentence = f"◎ נפח <b>רגיל</b> (פי {ratio_:.1f} מהממוצע)."

    ins_color = ins["color"]
    ins_label = ins["label"]
    ins_text  = ins["text"]
    ins_vol   = ins.get("vol", "")
    trend_html = (f'<div style="color:#c9d1d9;font-size:.85rem;line-height:1.65;">{trend_sentence}</div>'
                  if trend_sentence else "")
    vol_html   = (f'<div style="color:#c9d1d9;font-size:.85rem;line-height:1.65;">{vol_sentence}</div>'
                  if vol_sentence else "")

    st.markdown(
        '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
        'padding:14px 18px;margin-top:8px;direction:rtl;">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        '<span style="font-size:.9rem;font-weight:700;color:#e6edf3;">🕯️ מה קורה עכשיו</span>'
        f'<span style="background:{ins_color}22;color:{ins_color};border:1px solid {ins_color}55;'
        f'border-radius:20px;padding:2px 10px;font-size:.72rem;font-weight:700;">{ins_label}</span>'
        '</div>'
        '<div style="display:flex;flex-direction:column;gap:6px;">'
        f'<div style="color:#c9d1d9;font-size:.85rem;line-height:1.65;">🕯️ {ins_text}</div>'
        + trend_html + vol_html
        + (f'<div style="color:#8b949e;font-size:.75rem;">{ins_vol}</div>' if ins_vol else "")
        + '</div>'
        '<div style="margin-top:10px;padding-top:8px;border-top:1px solid #21262d;'
        'color:#8b949e;font-size:.65rem;">'
        '⚠️ ניתוח טכני בלבד — אינו ייעוץ השקעות.'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── AI Insight ──
    if st.session_state.show_ai and st.session_state.ai_res:
        ai  = st.session_state.ai_res
        tc_ = "color:#3fb950" if ai.get('trend') == "שורי" else \
              ("color:#f85149" if ai.get('trend') == "דובי" else "color:#8b949e")
        vi  = "✅ כן" if ai.get('vol_ok') else "⚠️ לא"
        st.markdown(
            '<div style="background:#161b22;border:1px solid #1f6feb;border-radius:12px;'
            'padding:14px 18px;margin-top:8px;direction:rtl;">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
            '<span style="background:linear-gradient(135deg,#6e40c9,#1f6feb);color:white;'
            'border-radius:4px;padding:1px 7px;font-size:.62rem;font-weight:700;">AI</span>'
            f'<span style="font-size:.9rem;font-weight:700;color:#e6edf3;">ניתוח AI — {ticker}</span>'
            '</div>'
            f'<p style="color:#c9d1d9;font-size:.85rem;line-height:1.7;margin:0 0 8px;">{ai.get("summary","")}</p>'
            f'<p style="color:#8b949e;font-size:.8rem;margin:0 0 12px;font-style:italic;">{ai.get("detail","")}</p>'
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">'
            '<div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:9px;text-align:center;">'
            '<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;margin-bottom:3px;">מגמה</div>'
            f'<div style="{tc_};font-size:.88rem;font-weight:700;">{ai.get("trend","—")}</div>'
            '</div>'
            '<div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:9px;text-align:center;">'
            '<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;margin-bottom:3px;">עוצמה</div>'
            f'<div style="color:#e6edf3;font-size:.88rem;font-weight:600;">{ai.get("strength","—")}</div>'
            '</div>'
            '<div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:9px;text-align:center;">'
            '<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;margin-bottom:3px;">איתות</div>'
            f'<div style="color:#e6edf3;font-size:.8rem;">{ai.get("signal","—")}</div>'
            '</div>'
            '<div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:9px;text-align:center;">'
            '<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;margin-bottom:3px;">נפח תומך</div>'
            f'<div style="font-size:.88rem;">{vi}</div>'
            '</div>'
            '</div>'
            '<div style="color:#8b949e;font-size:.65rem;margin-top:10px;font-style:italic;">'
            '⚠️ ניתוח טכני בלבד. אינו ייעוץ השקעות.'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # ── Analytics Panel ──
    if st.session_state.show_an:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;'
            'padding:16px;margin-top:10px;direction:rtl;">'
            '<div style="font-size:.9rem;font-weight:700;color:#e6edf3;margin-bottom:4px;">'
            '📊 נתונים פיננסיים רבעוניים</div>'
            '<div style="color:#8b949e;font-size:.72rem;margin-bottom:8px;">'
            'כמה הרוויחה החברה בכל רבעון (3 חודשים). שולי רווח גבוהים = חברה יעילה'
            '</div>',
            unsafe_allow_html=True
        )
        with st.spinner("טוען נתונים פיננסיים..."):
            qd = load_quarterly(ticker)
        if qd:
            dq    = pd.DataFrame(qd)
            cols_ = [c for c in ["רבעון","הכנסות","רווח נקי","שולי רווח","שינוי"] if c in dq.columns]

            # ── build HTML table ──
            def pct_color(v):
                try:
                    n = float(str(v).replace("%","").replace("+","").replace("—",""))
                    return "#3fb950" if n > 0 else ("#f85149" if n < 0 else "#8b949e")
                except: return "#8b949e"

            th_style = 'style="background:#0d1117;color:#8b949e;font-size:.68rem;text-transform:uppercase;padding:8px 12px;text-align:right;border-bottom:2px solid #21262d;"'
            header = "<tr>" + "".join(f"<th {th_style}>{col}</th>" for col in cols_) + "</tr>"

            rows_html = ""
            for i, row_d in enumerate(qd):
                bg = "#161b22" if i % 2 == 0 else "#0d1117"
                cells = ""
                for col in cols_:
                    val = row_d.get(col, "—")
                    if col in ("שולי רווח", "שינוי"):
                        clr = pct_color(val)
                        cells += f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-size:.82rem;color:{clr};text-align:right;border-bottom:1px solid #21262d;">{val}</td>'
                    elif col == "רבעון":
                        cells += f'<td style="padding:8px 12px;font-size:.82rem;color:#c9d1d9;font-weight:600;text-align:right;border-bottom:1px solid #21262d;">{val}</td>'
                    else:
                        cells += f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-size:.82rem;color:#e6edf3;text-align:right;border-bottom:1px solid #21262d;">{val}</td>'
                rows_html += f'<tr style="background:{bg};">{cells}</tr>'

            st.markdown(
                f'<div style="overflow-x:auto;">'
                f'<table style="width:100%;border-collapse:collapse;direction:rtl;">'
                f'<thead>{header}</thead>'
                f'<tbody>{rows_html}</tbody>'
                f'</table></div>',
                unsafe_allow_html=True
            )
        else:
            st.info("נתונים פיננסיים אינם זמינים עבור מניה זו.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # תיאור החברה + טבלאות נתוני מסחר
    # ══════════════════════════════════════════════
    st.markdown('<hr style="margin:12px 0 10px;"/>', unsafe_allow_html=True)

    comp_desc     = info.get("longBusinessSummary","")
    comp_sector   = info.get("sector","")
    comp_industry = info.get("industry","")
    comp_country  = info.get("country","")
    comp_emp      = info.get("fullTimeEmployees")
    comp_website  = info.get("website","")

    # ── תיאור חברה בעברית מ-Claude ──
    @st.cache_data(ttl=86400)
    def get_hebrew_description(symbol: str, name: str, sector: str, industry: str) -> str:
        if not ANTHROPIC_KEY:
            return ""
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=ai_headers(),
                json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                      "messages": [{"role": "user", "content":
                          f"כתוב תיאור קצר בעברית (4-5 משפטים) על החברה {name} (סימול: {symbol}), "
                          f"ענף: {sector}, תת-ענף: {industry}. "
                          f"כלול: מה החברה עושה, מה המוצרים/שירותים המרכזיים שלה, "
                          f"ומה מייחד אותה בשוק. כתוב בעברית פשוטה וברורה. "
                          f"החזר רק את התיאור, ללא כותרות."}]},
                timeout=20
            )
            if resp.status_code == 200:
                return resp.json()['content'][0]['text'].strip()
        except: pass
        return ""

    if ANTHROPIC_KEY:
        with st.spinner("טוען תיאור חברה..."):
            comp_desc_display = get_hebrew_description(
                ticker, company, comp_sector, comp_industry
            )
        if not comp_desc_display:
            comp_desc_display = comp_desc[:420] + ("..." if len(comp_desc) > 420 else "") if comp_desc else ""
    else:
        comp_desc_display = comp_desc[:420] + ("..." if len(comp_desc) > 420 else "") if comp_desc else ""

    # ── Company header ──
    tags = ""
    if comp_sector:   tags += f'<span style="background:#1f6feb22;border:1px solid #1f6feb44;border-radius:6px;padding:3px 10px;font-size:.68rem;color:#388bfd;">🗂 {comp_sector}</span> '
    if comp_industry: tags += f'<span style="background:#21262d;border-radius:6px;padding:3px 10px;font-size:.68rem;color:#c9d1d9;">📌 {comp_industry}</span> '
    if comp_country:  tags += f'<span style="background:#21262d;border-radius:6px;padding:3px 10px;font-size:.68rem;color:#c9d1d9;">🌍 {comp_country}</span> '
    if comp_emp:      tags += f'<span style="background:#21262d;border-radius:6px;padding:3px 10px;font-size:.68rem;color:#c9d1d9;">👥 {int(comp_emp):,} עובדים</span> '
    if comp_website:  tags += f'<a href="{comp_website}" target="_blank" style="background:#21262d;border-radius:6px;padding:3px 10px;font-size:.68rem;color:#388bfd;text-decoration:none;">🔗 אתר</a>'

    st.markdown(
        '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
        'padding:15px 18px;margin-bottom:12px;direction:rtl;">'
        '<div style="font-size:.9rem;font-weight:700;color:#e6edf3;margin-bottom:8px;">🏢 אודות החברה</div>'
        + (f'<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px;">{tags}</div>' if tags else "")
        + (f'<div style="color:#8b949e;font-size:.78rem;line-height:1.75;direction:rtl;text-align:right;">{comp_desc_display}</div>' if comp_desc_display else
           f'<div style="color:#8b949e;font-size:.75rem;">{company} · {ticker}</div>')
        + '</div>',
        unsafe_allow_html=True
    )

    # ── helper for data tables ──
    def dtable(title, icon, rows):
        """rows = list of (label, value, color_optional)"""
        cells = ""
        for i, row in enumerate(rows):
            lbl = row[0]; val = row[1]
            clr = row[2] if len(row) > 2 else "#e6edf3"
            bg  = "#161b22" if i % 2 == 0 else "#0d1117"
            cells += (
                f'<tr style="background:{bg};">'
                f'<td style="padding:7px 12px;color:#8b949e;font-size:.72rem;'
                f'border-bottom:1px solid #21262d;text-align:right;">{lbl}</td>'
                f'<td style="padding:7px 12px;font-family:JetBrains Mono,monospace;'
                f'font-size:.78rem;color:{clr};font-weight:600;'
                f'border-bottom:1px solid #21262d;text-align:left;">{val}</td>'
                f'</tr>'
            )
        return (
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:11px;overflow:hidden;">'
            f'<div style="background:#0d1117;padding:9px 12px;font-size:.72rem;font-weight:700;'
            f'color:#e6edf3;border-bottom:1px solid #21262d;">{icon} {title}</div>'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<tbody>{cells}</tbody></table></div>'
        )

    def fv(v, prefix="$", dec=2):
        if v is None: return "N/A"
        try:
            v = float(v)
            if abs(v) >= 1e12: return f"{prefix}{v/1e12:.2f}T"
            if abs(v) >= 1e9:  return f"{prefix}{v/1e9:.2f}B"
            if abs(v) >= 1e6:  return f"{prefix}{v/1e6:.1f}M"
            return f"{prefix}{v:,.{dec}f}"
        except: return "N/A"

    def pct_clr(v):
        if v is None: return "#8b949e"
        try: return "#3fb950" if float(v) >= 0 else "#f85149"
        except: return "#8b949e"

    # ── gather extra data ──
    prev_close  = info.get("previousClose") or info.get("regularMarketPreviousClose")
    open_price  = info.get("open") or info.get("regularMarketOpen")
    day_high    = info.get("dayHigh") or info.get("regularMarketDayHigh")
    day_low     = info.get("dayLow")  or info.get("regularMarketDayLow")
    wk52_high   = info.get("fiftyTwoWeekHigh")
    wk52_low    = info.get("fiftyTwoWeekLow")
    mkt_cap     = info.get("marketCap")
    pe          = info.get("trailingPE")
    bv          = info.get("bookValue")
    shares_out  = info.get("sharesOutstanding")
    shares_float= info.get("floatShares")
    avg_price   = info.get("fiftyDayAverage")
    avg_vol     = info.get("averageVolume")
    avg_vol_10  = info.get("averageVolume10days")
    day_vol     = lv_display if 'lv_display' in dir() else lv

    # change calculations
    chg_abs = (lc - prev_close) if prev_close else None
    chg_pct = (chg_abs / prev_close * 100) if (chg_abs and prev_close) else None
    day_avg  = (day_high + day_low) / 2 if (day_high and day_low) else None

    # returns using df
    def calc_ret(days_back):
        try:
            if len(df) > days_back:
                old = float(df['Close'].iloc[-days_back])
                return (lc - old) / old * 100 if old > 0 else None
        except: pass
        return None

    ret_week  = calc_ret(5)
    ret_month = calc_ret(21)
    ret_3m    = calc_ret(63)
    ret_ytd   = None
    try:
        import datetime as _dt2
        ytd_start = _dt2.date(df.index[-1].year, 1, 1)
        df_ytd = df[df.index.date >= ytd_start] if hasattr(df.index[0],'date') else df
        if len(df_ytd) > 1:
            old_ytd = float(df_ytd['Close'].iloc[0])
            ret_ytd = (lc - old_ytd) / old_ytd * 100 if old_ytd > 0 else None
    except: pass
    ret_3y = calc_ret(756)

    # ── 5 tables grid ──
    tr1, tr2 = st.columns(2)
    tr3, tr4, tr5 = st.columns(3)

    # Table 1: נתוני מסחר
    with tr1:
        st.markdown(dtable("נתוני מסחר", "📊", [
            ("שער אחרון",         f"{sym}{lc:,.2f}",                                       "#e6edf3"),
            ("שינוי %",           f"{chg_pct:+.2f}%" if chg_pct else "N/A",               pct_clr(chg_pct)),
            ("שינוי $",           f"{chg_abs:+.2f}" if chg_abs else "N/A",                 pct_clr(chg_abs)),
            ("נפח מסחר",          f"{day_vol:,.0f}" if day_vol else "N/A",                "#c9d1d9"),
            ("נפח ממוצע יומי",    f"{avg_vol:,.0f}" if avg_vol else "N/A",                "#8b949e"),
            ("נפח ממוצע 10 ימים", f"{avg_vol_10:,.0f}" if avg_vol_10 else "N/A",          "#8b949e"),
        ]), unsafe_allow_html=True)

    # Table 2: שערים
    with tr2:
        st.markdown(dtable("שערים", "📏", [
            ("שער יומי ממוצע",   f"{sym}{day_avg:,.2f}" if day_avg else "N/A",            "#e6edf3"),
            ("יומי גבוה",         f"{sym}{day_high:,.2f}" if day_high else "N/A",         "#3fb950"),
            ("יומי נמוך",         f"{sym}{day_low:,.2f}"  if day_low  else "N/A",         "#f85149"),
            ("52 שבועות גבוה",    f"{sym}{wk52_high:,.2f}" if wk52_high else "N/A",       "#3fb950"),
            ("52 שבועות נמוך",    f"{sym}{wk52_low:,.2f}"  if wk52_low  else "N/A",       "#f85149"),
            ("ממוצע 50 ימים",     f"{sym}{avg_price:,.2f}" if avg_price else "N/A",        "#d29922"),
        ]), unsafe_allow_html=True)

    # Table 3: שווי
    with tr3:
        eq = bv * shares_out if (bv and shares_out) else None
        st.markdown(dtable("שווי", "💰", [
            ("שווי שוק",          fv(mkt_cap, sym),                                        "#e6edf3"),
            ("מכפיל רווח P/E",    f"{pe:.1f}" if pe else "N/A",                            "#c9d1d9"),
            ("הון עצמי",          fv(eq, sym),                                             "#c9d1d9"),
            ("מניות בסחרות",      fv(shares_float, "", 0).replace("$",""),                  "#8b949e"),
            ("מניות מונפקות",     fv(shares_out, "", 0).replace("$",""),                    "#8b949e"),
            ("שער ממוצע 52ש",    f"{sym}{(wk52_high+wk52_low)/2:,.2f}" if (wk52_high and wk52_low) else "N/A", "#8b949e"),
        ]), unsafe_allow_html=True)

    # Table 4: נתוני פתיחה
    with tr4:
        base_chg = (lc - open_price) / open_price * 100 if (open_price and open_price > 0) else None
        base_abs = (lc - open_price) if open_price else None
        st.markdown(dtable("נתוני פתיחה", "🔓", [
            ("שער פתיחה",         f"{sym}{open_price:,.2f}" if open_price else "N/A",      "#e6edf3"),
            ("שער בסיס (סגירה)",  f"{sym}{prev_close:,.2f}" if prev_close else "N/A",      "#8b949e"),
            ("שינוי מפתיחה %",    f"{base_chg:+.2f}%" if base_chg else "N/A",             pct_clr(base_chg)),
            ("שינוי מפתיחה $",    f"{base_abs:+.2f}" if base_abs else "N/A",               pct_clr(base_abs)),
            ("נפח מסחר",          f"{day_vol:,.0f}" if day_vol else "N/A",                "#c9d1d9"),
        ]), unsafe_allow_html=True)

    # Table 5: תשואות
    with tr5:
        st.markdown(dtable("תשואות", "📈", [
            ("מתחילת השבוע",      f"{ret_week:+.1f}%"  if ret_week  else "N/A",           pct_clr(ret_week)),
            ("מתחילת החודש",      f"{ret_month:+.1f}%" if ret_month else "N/A",           pct_clr(ret_month)),
            ("3 חודשים",          f"{ret_3m:+.1f}%"    if ret_3m    else "N/A",           pct_clr(ret_3m)),
            ("מתחילת השנה YTD",  f"{ret_ytd:+.1f}%"   if ret_ytd   else "N/A",           pct_clr(ret_ytd)),
            ("3 שנים",            f"{ret_3y:+.1f}%"    if ret_3y    else "N/A",           pct_clr(ret_3y)),
        ]), unsafe_allow_html=True)



    # ── Analyst Snapshot ──
    st.markdown('<hr style="margin:12px 0 8px;"/>', unsafe_allow_html=True)
    render_analyst_snapshot(ticker, cp, sym)

    # ── Thesis Panel ──
    st.markdown('<hr style="margin:12px 0 8px;"/>', unsafe_allow_html=True)
    with st.spinner("בונה תזת השקעה..."):
        thesis_data = build_thesis_data(ticker, info, df)
    render_thesis_panel(thesis_data, ticker)






    # ══════════════════════════════════════════════════════════════════════
    # SUMMARY & RECOMMENDATION PANEL
    # Data-driven — all logic outside UI. Easy to wire to external API.
    # ══════════════════════════════════════════════════════════════════════

    def build_summary_data(ticker: str, df, info: dict, analyst_d: dict,
                            cur_price: float, ccy_s: str) -> dict:
        """
        Assembles a unified data contract for the Summary Panel.
        Replace internals with API calls without touching the renderer.
        """
        try:
            cl = df["Close"].astype(float)
            lc = float(cl.iloc[-1])

            # ── Technical signals ──
            def ma_sig(col):
                if col not in df.columns: return None
                v = float(df[col].dropna().iloc[-1])
                return {"value": v, "above": lc > v,
                        "signal": "bullish" if lc > v else "bearish"}

            rsi_val = float(df["RSI"].iloc[-1]) if "RSI" in df.columns else None
            if rsi_val is not None:
                if rsi_val >= 70: rsi_sig = "overbought"
                elif rsi_val <= 30: rsi_sig = "oversold"
                elif rsi_val >= 55: rsi_sig = "bullish"
                else: rsi_sig = "neutral"
            else:
                rsi_sig = None

            macd_sig = None
            if "MACD" in df.columns and "MACD_S" in df.columns:
                macd  = float(df["MACD"].iloc[-1])
                sig_l = float(df["MACD_S"].iloc[-1])
                macd_sig = "bullish" if macd > sig_l else "bearish"

            vol_ratio = None
            if "Volume" in df.columns:
                v_s = df["Volume"].astype(float)
                avg = float(v_s.rolling(20).mean().iloc[-1])
                last_v = float(v_s.replace(0, pd.NA).dropna().iloc[-1])
                if avg > 0: vol_ratio = last_v / avg

            bb_pos = None
            if "BB_U" in df.columns and "BB_L" in df.columns:
                bbu = float(df["BB_U"].iloc[-1]); bbl = float(df["BB_L"].iloc[-1])
                bb_pos = (lc - bbl) / (bbu - bbl) if bbu != bbl else 0.5

            # golden cross / death cross
            cross = None
            if "MA50" in df.columns and "MA200" in df.columns:
                ma50_arr  = df["MA50"].dropna().to_numpy(dtype=float)
                ma200_arr = df["MA200"].dropna().to_numpy(dtype=float)
                n = min(len(ma50_arr), len(ma200_arr))
                if n >= 2:
                    if ma50_arr[-2] < ma200_arr[-2] and ma50_arr[-1] > ma200_arr[-1]:
                        cross = "golden"
                    elif ma50_arr[-2] > ma200_arr[-2] and ma50_arr[-1] < ma200_arr[-1]:
                        cross = "death"

            # count bullish signals
            tech_signals = [
                ma_sig("MA20"), ma_sig("MA50"), ma_sig("MA200"),
            ]
            bull_tech = sum(1 for s in tech_signals if s and s["above"])
            bear_tech = sum(1 for s in tech_signals if s and not s["above"])
            if rsi_sig in ("bullish","oversold"): bull_tech += 1
            elif rsi_sig in ("overbought",): bear_tech += 1
            if macd_sig == "bullish": bull_tech += 1
            elif macd_sig == "bearish": bear_tech += 1

            # ── Analyst data ──
            an = analyst_d or {}
            t_mean = an.get("tm") or an.get("target_mean")
            upside = ((t_mean - lc) / lc * 100) if t_mean and lc > 0 else None
            rating = an.get("rating", "N/A")
            n_an   = an.get("n") or an.get("n_analysts")

            # ── Fundamental ──
            pe       = info.get("trailingPE")
            fwd_pe   = info.get("forwardPE")
            rev_g    = info.get("revenueGrowth")
            margins  = info.get("profitMargins")
            roe      = info.get("returnOnEquity")

            # ── Scores ──
            f_res = calc_fundamental_score(info)
            t_res = calc_technical_score(df)
            a_res = calc_analyst_score({**an, "cur_price": lc}) if an else None
            f_s   = f_res.get("score")
            t_s   = t_res.get("score")
            a_s   = a_res.get("score") if a_res else None
            dec   = calc_weighted_decision(f_s, t_s, a_s)

            # ── Alerts ──
            alerts = []
            if cross == "golden":
                alerts.append({"level":"high","icon":"✨","text":"Golden Cross — MA50 חצה MA200 כלפי מעלה. אות שורי חזק מאוד"})
            elif cross == "death":
                alerts.append({"level":"high","icon":"💀","text":"Death Cross — MA50 חצה MA200 כלפי מטה. אות דובי חזק"})
            if rsi_val and rsi_val >= 75:
                alerts.append({"level":"high","icon":"⚠️","text":f"RSI {rsi_val:.0f} — קנוי מדי קיצוני. סיכון גבוה לתיקון"})
            elif rsi_val and rsi_val <= 25:
                alerts.append({"level":"medium","icon":"💡","text":f"RSI {rsi_val:.0f} — מכור מדי. ייתכן bounce"})
            if vol_ratio and vol_ratio >= 2.0:
                alerts.append({"level":"medium","icon":"📊","text":f"נפח חריג — פי {vol_ratio:.1f} מהממוצע. קרה משהו משמעותי"})
            if upside and upside > 25:
                alerts.append({"level":"low","icon":"🎯","text":f"אפסייד גבוה — {upside:.0f}% לפי קונצנזוס אנליסטים"})
            elif upside and upside < -10:
                alerts.append({"level":"high","icon":"📉","text":f"דאונסייד — המחיר גבוה מיעד האנליסטים ב-{abs(upside):.0f}%"})
            if bb_pos and bb_pos > 0.95:
                alerts.append({"level":"medium","icon":"🔴","text":"מחיר בשולי הרצועה העליונה של Bollinger — תנודתיות קיצונית"})

            # ── Thesis ──
            thesis = build_thesis_data(ticker, info, df)

            return {
                "ticker":      ticker,
                "cur_price":   lc,
                "ccy":         ccy_s,
                "tech": {
                    "ma20":       ma_sig("MA20"),
                    "ma50":       ma_sig("MA50"),
                    "ma200":      ma_sig("MA200"),
                    "rsi":        {"value": rsi_val, "signal": rsi_sig},
                    "macd":       macd_sig,
                    "vol_ratio":  vol_ratio,
                    "bb_pos":     bb_pos,
                    "cross":      cross,
                    "bull_count": bull_tech,
                    "bear_count": bear_tech,
                },
                "analyst": {
                    "rating":  rating,
                    "n":       n_an,
                    "t_mean":  t_mean,
                    "t_high":  an.get("th") or an.get("target_high"),
                    "t_low":   an.get("tl") or an.get("target_low"),
                    "upside":  upside,
                },
                "fundamental": {
                    "pe":      pe,
                    "fwd_pe":  fwd_pe,
                    "rev_g":   rev_g,
                    "margins": margins,
                    "roe":     roe,
                    "f_score": f_s,
                    "t_score": t_s,
                    "a_score": a_s,
                },
                "decision":  dec,
                "alerts":    alerts[:6],
                "thesis":    thesis,
            }
        except Exception as e:
            return {"error": str(e)}


    def render_summary_panel(data: dict):
        """
        Summary & Recommendation Panel — plug-and-play renderer.
        Receives data dict only. Zero business logic inside.
        """
        if not data or "error" in data:
            st.error(f"שגיאה בבניית הסיכום: {data.get('error','')}")
            return

        ticker   = data["ticker"]
        lc       = data["cur_price"]
        ccy_s    = data["ccy"]
        tech     = data["tech"]
        an       = data["analyst"]
        fund     = data["fundamental"]
        dec      = data["decision"]
        alerts   = data["alerts"]
        thesis   = data["thesis"]

        def card(bg="#161b22", border="#21262d", radius="12px"):
            return f'background:{bg};border:1px solid {border};border-radius:{radius};padding:16px 18px;margin-bottom:10px;direction:rtl;'

        def pill(text, color, bg_alpha="22"):
            return (f'<span style="background:{color}{bg_alpha};color:{color};border:1px solid {color}55;'
                    f'border-radius:20px;padding:2px 10px;font-size:.7rem;font-weight:700;">{text}</span>')

        def signal_badge(sig):
            if sig == "bullish":   return pill("שורי ▲","#3fb950")
            if sig == "bearish":   return pill("דובי ▼","#f85149")
            if sig == "overbought":return pill("קנוי מדי","#f85149")
            if sig == "oversold":  return pill("מכור מדי","#3fb950")
            return pill("נייטרלי","#8b949e")

        ALERT_META = {
            "high":   ("#f85149", "#f8514912", "🔴"),
            "medium": ("#d29922", "#d2992212", "🟡"),
            "low":    ("#3fb950", "#3fb95012", "🟢"),
        }

        # ══════════════════════════════════════════
        # HEADER
        # ══════════════════════════════════════════
        w_score = dec.get("weighted", 0) or 0
        d_color = dec.get("color","#8b949e")
        d_icon  = dec.get("icon","⚪")
        d_label = dec.get("decision","—")
        d_en    = dec.get("en","—")

        st.markdown(
            f'<div style="{card(bg="#0d1117", border=d_color)}">' +
            f'<div style="display:flex;justify-content:space-between;align-items:center;">' +
            f'<div>' +
            f'<div style="font-size:1rem;font-weight:800;color:#e6edf3;">📋 Summary & Recommendation</div>' +
            f'<div style="color:#8b949e;font-size:.72rem;margin-top:2px;">סיכום ניתוח מקיף — {ticker} · {ccy_s}{lc:,.2f}</div>' +
            f'</div>' +
            f'<div style="text-align:center;">' +
            f'<div style="font-size:2rem;">{d_icon}</div>' +
            f'<div style="color:{d_color};font-size:.75rem;font-weight:700;">{d_label} / {d_en}</div>' +
            f'</div>' +
            f'</div>' +
            f'<div style="height:6px;background:#21262d;border-radius:3px;margin-top:12px;overflow:hidden;">' +
            f'<div style="height:100%;width:{w_score}%;background:linear-gradient(90deg,{d_color}88,{d_color});border-radius:3px;"></div>' +
            f'</div>' +
            f'<div style="display:flex;justify-content:space-between;margin-top:3px;">' +
            f'<span style="color:#8b949e;font-size:.6rem;">0</span>' +
            f'<span style="color:{d_color};font-size:.7rem;font-weight:600;">ציון משוקלל: {w_score}/100</span>' +
            f'<span style="color:#8b949e;font-size:.6rem;">100</span>' +
            f'</div></div>',
            unsafe_allow_html=True
        )

        col_l, col_r = st.columns([3, 2])

        # ══════════════════════════════════════════
        # LEFT — Technical + Fundamental
        # ══════════════════════════════════════════
        with col_l:
            # ── Technical Analysis ──
            st.markdown(
                f'<div style="{card()}">' +
                '<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:10px;">📐 ניתוח טכני</div>',
                unsafe_allow_html=True
            )

            def tech_row(name, ma_data=None, signal=None, value_txt=""):
                if ma_data:
                    sig_html = signal_badge("bullish" if ma_data["above"] else "bearish")
                    val = f'{ccy_s}{ma_data["value"]:,.2f}'
                    arrow = "▲" if ma_data["above"] else "▼"
                    clr   = "#3fb950" if ma_data["above"] else "#f85149"
                    return (
                        f'<div style="display:flex;justify-content:space-between;align-items:center;' +
                        f'padding:6px 0;border-bottom:1px solid #21262d;">' +
                        f'<span style="color:#8b949e;font-size:.75rem;">{name}</span>' +
                        f'<span style="font-family:JetBrains Mono,monospace;font-size:.75rem;color:{clr};">{arrow} {val}</span>' +
                        f'<span>{sig_html}</span>' +
                        f'</div>'
                    )
                else:
                    return (
                        f'<div style="display:flex;justify-content:space-between;align-items:center;' +
                        f'padding:6px 0;border-bottom:1px solid #21262d;">' +
                        f'<span style="color:#8b949e;font-size:.75rem;">{name}</span>' +
                        f'<span style="font-family:JetBrains Mono,monospace;font-size:.75rem;color:#c9d1d9;">{value_txt}</span>' +
                        f'<span>{signal_badge(signal) if signal else ""}</span>' +
                        f'</div>'
                    )

            rows = ""
            if tech["ma20"]:  rows += tech_row("MA20",  ma_data=tech["ma20"])
            if tech["ma50"]:  rows += tech_row("MA50",  ma_data=tech["ma50"])
            if tech["ma200"]: rows += tech_row("MA200", ma_data=tech["ma200"])
            if tech["rsi"]["value"]:
                rsi_v = tech["rsi"]["value"]
                rows += tech_row("RSI", signal=tech["rsi"]["signal"], value_txt=f"{rsi_v:.1f}")
            if tech["macd"]:
                rows += tech_row("MACD vs Signal", signal=tech["macd"], value_txt="")
            if tech["vol_ratio"]:
                r = tech["vol_ratio"]
                vol_sig = "bullish" if r >= 1.3 else ("bearish" if r <= 0.6 else "neutral")
                rows += tech_row("Volume ratio", signal=vol_sig, value_txt=f"×{r:.1f}")

            cross = tech.get("cross")
            cross_html = ""
            if cross == "golden":
                cross_html = '<div style="background:rgba(63,185,80,0.1);border:1px solid rgba(63,185,80,0.3);border-radius:6px;padding:6px 10px;margin-top:8px;color:#3fb950;font-size:.75rem;">✨ Golden Cross זוהה — אות שורי חזק</div>'
            elif cross == "death":
                cross_html = '<div style="background:rgba(248,81,73,0.1);border:1px solid rgba(248,81,73,0.3);border-radius:6px;padding:6px 10px;margin-top:8px;color:#f85149;font-size:.75rem;">💀 Death Cross זוהה — אות דובי חזק</div>'

            bull_c = tech["bull_count"]; bear_c = tech["bear_count"]
            total_c = bull_c + bear_c or 1
            bar_w = int(bull_c / total_c * 100)

            st.markdown(
                rows + cross_html +
                f'<div style="margin-top:10px;">' +
                f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">' +
                f'<span style="color:#3fb950;font-size:.68rem;">🟢 שורי {bull_c}</span>' +
                f'<span style="color:#f85149;font-size:.68rem;">דובי {bear_c} 🔴</span>' +
                f'</div>' +
                f'<div style="height:5px;background:#f85149;border-radius:3px;overflow:hidden;">' +
                f'<div style="height:100%;width:{bar_w}%;background:#3fb950;border-radius:3px;"></div>' +
                f'</div></div></div>',
                unsafe_allow_html=True
            )

            # ── Fundamental ──
            st.markdown(
                f'<div style="{card()}">' +
                '<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:10px;">💹 נתונים פונדמנטליים</div>',
                unsafe_allow_html=True
            )

            def fund_row(name, value, tip="", color="#c9d1d9"):
                if value is None: return ""
                if isinstance(value, float) and value != value: return ""
                return (
                    f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #21262d;">' +
                    f'<span style="color:#8b949e;font-size:.74rem;">{name}</span>' +
                    f'<div style="text-align:left;">' +
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:.74rem;color:{color};">{value}</span>' +
                    (f'<div style="color:#8b949e;font-size:.6rem;">{tip}</div>' if tip else "") +
                    f'</div></div>'
                )

            pe   = fund["pe"];   fwd_pe = fund["fwd_pe"]
            revg = fund["rev_g"]; marg  = fund["margins"]; roe = fund["roe"]
            f_rows = ""
            if pe:    f_rows += fund_row("P/E", f"{pe:.1f}", "מכפיל רווח", "#e6edf3" if pe < 30 else "#f85149")
            if fwd_pe: f_rows += fund_row("Forward P/E", f"{fwd_pe:.1f}", "תחזית מכפיל")
            if revg:  f_rows += fund_row("צמיחת הכנסות", f"{revg*100:+.1f}%", "YoY", "#3fb950" if revg > 0 else "#f85149")
            if marg:  f_rows += fund_row("שולי רווח", f"{marg*100:.1f}%", "Net Margin", "#3fb950" if marg > 0.10 else "#d29922")
            if roe:   f_rows += fund_row("ROE", f"{roe*100:.1f}%", "Return on Equity", "#3fb950" if roe > 0.15 else "#d29922")

            scores_html = ""
            if fund["f_score"]: scores_html += f'<div style="display:flex;justify-content:space-between;padding:5px 0;"><span style="color:#8b949e;font-size:.74rem;">ציון פונדמנטלי</span><span style="font-family:JetBrains Mono,monospace;font-size:.74rem;color:#388bfd;">{fund["f_score"]}/100</span></div>'
            if fund["t_score"]: scores_html += f'<div style="display:flex;justify-content:space-between;padding:5px 0;"><span style="color:#8b949e;font-size:.74rem;">ציון טכני</span><span style="font-family:JetBrains Mono,monospace;font-size:.74rem;color:#3fb950;">{fund["t_score"]}/100</span></div>'
            if fund["a_score"]: scores_html += f'<div style="display:flex;justify-content:space-between;padding:5px 0;"><span style="color:#8b949e;font-size:.74rem;">ציון אנליסטים</span><span style="font-family:JetBrains Mono,monospace;font-size:.74rem;color:#d29922;">{fund["a_score"]}/100</span></div>'

            st.markdown(f_rows + scores_html + '</div>', unsafe_allow_html=True)

        # ══════════════════════════════════════════
        # RIGHT — Analyst + Alerts + Thesis
        # ══════════════════════════════════════════
        with col_r:
            # ── Analyst Snapshot ──
            rating   = an["rating"];  n_an = an["n"]
            t_mean   = an["t_mean"]; upside = an["upside"]
            t_high   = an["t_high"]; t_low = an["t_low"]
            up_c     = "#3fb950" if (upside or 0) >= 0 else "#f85149"
            up_lbl   = f'{"▲" if (upside or 0)>=0 else "▼"} {abs(upside or 0):.1f}%' if upside else "N/A"

            st.markdown(
                f'<div style="{card()}">' +
                '<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:10px;">📊 Analyst Snapshot</div>' +
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">' +
                f'<div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">' +
                f'<div style="color:#8b949e;font-size:.6rem;margin-bottom:3px;">קונצנזוס</div>' +
                f'<div style="font-size:.88rem;font-weight:700;color:#e6edf3;">{rating}</div>' +
                f'<div style="color:#8b949e;font-size:.62rem;">{n_an or "N/A"} אנליסטים</div></div>' +
                f'<div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">' +
                f'<div style="color:#8b949e;font-size:.6rem;margin-bottom:3px;">פוטנציאל</div>' +
                f'<div style="font-size:.95rem;font-weight:700;color:{up_c};">{up_lbl}</div>' +
                f'<div style="color:#8b949e;font-size:.62rem;">vs יעד ממוצע</div></div>' +
                f'</div>' +
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:8px;">' +
                f'<div style="background:#0d1117;border-radius:6px;padding:7px;text-align:center;">' +
                f'<div style="color:#8b949e;font-size:.58rem;">יעד ממוצע</div>' +
                f'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#e6edf3;">{ccy_s+str(f"{t_mean:.0f}") if t_mean else "N/A"}</div></div>' +
                f'<div style="background:#0d1117;border-radius:6px;padding:7px;text-align:center;">' +
                f'<div style="color:#8b949e;font-size:.58rem;">יעד גבוה</div>' +
                f'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#3fb950;">{ccy_s+str(f"{t_high:.0f}") if t_high else "N/A"}</div></div>' +
                f'<div style="background:#0d1117;border-radius:6px;padding:7px;text-align:center;">' +
                f'<div style="color:#8b949e;font-size:.58rem;">יעד נמוך</div>' +
                f'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#f85149;">{ccy_s+str(f"{t_low:.0f}") if t_low else "N/A"}</div></div>' +
                f'</div></div>',
                unsafe_allow_html=True
            )

            # ── Smart Alerts ──
            if alerts:
                st.markdown(
                    f'<div style="{card()}">' +
                    '<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:8px;">🔔 Smart Alerts</div>',
                    unsafe_allow_html=True
                )
                alerts_html = ""
                for alt in alerts:
                    lvl = alt.get("level","low")
                    clr, bg, _ = ALERT_META.get(lvl, ("#8b949e","#8b949e12","⚪"))
                    alerts_html += (
                        f'<div style="background:{bg};border:1px solid {clr}33;border-radius:7px;' +
                        f'padding:6px 10px;margin-bottom:4px;display:flex;gap:6px;direction:rtl;">' +
                        f'<span>{alt.get("icon","")}</span>' +
                        f'<span style="color:#c9d1d9;font-size:.74rem;line-height:1.45;">{alt["text"]}</span>' +
                        f'</div>'
                    )
                st.markdown(alerts_html + '</div>', unsafe_allow_html=True)

            # ── Investment Thesis ──
            if thesis:
                CASE = {"bull":("#3fb950","📈"), "base":("#d29922","↔️"), "bear":("#f85149","📉")}
                st.markdown(
                    f'<div style="{card()}">' +
                    '<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:6px;">🧭 Investment Thesis</div>' +
                    f'<div style="color:#c9d1d9;font-size:.75rem;line-height:1.55;margin-bottom:8px;">{thesis.get("summary","")}</div>',
                    unsafe_allow_html=True
                )
                cases_html = ""
                for key in ["bull","base","bear"]:
                    case = thesis.get(key, {})
                    clr, ico = CASE[key]
                    pts = "".join(f'<li style="color:#8b949e;font-size:.7rem;line-height:1.5;">{p}</li>' for p in case.get("points",[])[:2])
                    cases_html += (
                        f'<div style="background:{clr}0e;border:1px solid {clr}33;border-top:2px solid {clr};' +
                        f'border-radius:8px;padding:8px 10px;margin-bottom:6px;">' +
                        f'<div style="color:{clr};font-size:.72rem;font-weight:700;margin-bottom:4px;">{ico} {case.get("title",key)}</div>' +
                        f'<ul style="margin:0;padding-right:14px;">{pts}</ul>' +
                        f'<div style="color:{clr};font-family:JetBrains Mono,monospace;font-size:.72rem;margin-top:4px;">יעד: {case.get("target","N/A")}</div>' +
                        f'</div>'
                    )
                st.markdown(cases_html + '</div>', unsafe_allow_html=True)

        # ══════════════════════════════════════════
        # FINAL RECOMMENDATION — full width
        # ══════════════════════════════════════════
        confidence = min(100, max(0, w_score))
        if confidence >= 70:
            conf_label = "גבוהה"
        elif confidence >= 45:
            conf_label = "בינונית"
        else:
            conf_label = "נמוכה"

        drivers = []
        if tech["bull_count"] > tech["bear_count"]:
            drivers.append(f"רוב הכלים הטכניים ({tech['bull_count']}) — שוריים")
        elif tech["bear_count"] > tech["bull_count"]:
            drivers.append(f"רוב הכלים הטכניים ({tech['bear_count']}) — דוביים")
        if upside and upside > 10:
            drivers.append(f"אפסייד {upside:.0f}% לפי קונצנזוס אנליסטים")
        if fund["f_score"] and fund["f_score"] >= 65:
            drivers.append(f"ציון פונדמנטלי גבוה ({fund['f_score']}/100)")
        if fund["rev_g"] and fund["rev_g"] > 0.10:
            drivers.append(f"צמיחת הכנסות {fund['rev_g']*100:.0f}%")
        if cross == "golden":
            drivers.append("Golden Cross — אות שורי טכני חזק")
        if not drivers:
            drivers.append("נתונים מוגבלים — יש לבדוק ידנית")

        drivers_html = "".join(
            f'<div style="display:flex;align-items:center;gap:6px;padding:4px 0;">' +
            f'<span style="color:{d_color};font-size:.72rem;">▸</span>' +
            f'<span style="color:#c9d1d9;font-size:.75rem;">{d}</span></div>'
            for d in drivers[:4]
        )

        st.markdown(
            f'<div style="background:{d_color}10;border:2px solid {d_color}55;border-radius:14px;padding:20px 24px;margin-top:8px;direction:rtl;">' +
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">' +
            f'<div>' +
            f'<div style="color:#8b949e;font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;">המלצה סופית</div>' +
            f'<div style="font-size:1.6rem;font-weight:800;color:{d_color};line-height:1.1;">{d_icon} {d_label}</div>' +
            f'<div style="color:{d_color};font-size:.78rem;font-weight:600;">{d_en}</div>' +
            f'</div>' +
            f'<div style="text-align:center;">' +
            f'<div style="font-family:JetBrains Mono,monospace;font-size:2.2rem;font-weight:800;color:{d_color};">{confidence}</div>' +
            f'<div style="color:#8b949e;font-size:.64rem;">Confidence Score</div>' +
            f'<div style="color:{d_color};font-size:.7rem;font-weight:600;">{conf_label}</div>' +
            f'</div></div>' +
            f'<div style="margin-bottom:10px;">' +
            f'<div style="color:#8b949e;font-size:.66rem;text-transform:uppercase;margin-bottom:4px;">Top Drivers</div>' +
            drivers_html +
            f'</div>' +
            f'<div style="color:#8b949e;font-size:.64rem;padding-top:10px;border-top:1px solid #21262d;">' +
            f'⚠️ ניתוח אלגוריתמי בלבד. אינו מהווה ייעוץ השקעות. לפני כל החלטה — התייעצי עם בעל רישיון.' +
            f'</div></div>',
            unsafe_allow_html=True
        )


    # ══════════════════════════════════════════════════════════════
    # ADVANCED ANALYSIS MODULES — Gap, Sentiment, Macro, Risk, Confidence
    # All modules use available local data + optional AI layer
    # ══════════════════════════════════════════════════════════════

    def calc_gap_analysis(df) -> dict:
        """
        Gap Analysis — מזהה פערי מחיר (gaps) בגרף.
        Gap Up: פתיחה היום > סגירה אתמול
        Gap Down: פתיחה היום < סגירה אתמול
        """
        if df is None or len(df) < 2:
            return {"gaps": [], "open_gaps": []}
        op = df['Open'].astype(float)
        cl = df['Close'].astype(float)
        gaps = []
        for i in range(1, len(df)):
            prev_close = cl.iloc[i-1]
            cur_open   = op.iloc[i]
            gap_pct    = (cur_open - prev_close) / prev_close * 100
            if abs(gap_pct) >= 0.8:  # gap >= 0.8%
                date = str(df.index[i])[:10]
                gaps.append({
                    "date":     date,
                    "type":     "gap_up" if gap_pct > 0 else "gap_down",
                    "pct":      gap_pct,
                    "prev_close": float(prev_close),
                    "open":     float(cur_open),
                    "filled":   False,
                })
        # check if gap was filled later
        for g in gaps:
            g_idx = next((i for i,d in enumerate(df.index) if str(d)[:10]==g["date"]), None)
            if g_idx is not None:
                future_lows  = df['Low'].astype(float).iloc[g_idx+1:]
                future_highs = df['High'].astype(float).iloc[g_idx+1:]
                if g["type"] == "gap_up":
                    g["filled"] = any(future_lows < g["prev_close"])
                else:
                    g["filled"] = any(future_highs > g["prev_close"])
        open_gaps = [g for g in gaps if not g["filled"]]
        return {"gaps": gaps[-10:], "open_gaps": open_gaps[-5:],
                "total": len(gaps), "filled": len([g for g in gaps if g["filled"]]),
                "fill_rate": len([g for g in gaps if g["filled"]]) / len(gaps) * 100 if gaps else 0}


    def calc_news_sentiment(ticker: str, info: dict) -> dict:
        """
        News Sentiment — מחשב ציון סנטימנט מנתוני info זמינים.
        בהיעדר API חדשות אמיתי, משתמש בנתוני השוק כ-proxy.
        """
        score  = 0.0; signals = []; confidence = "Medium"

        # analyst recommendation proxy
        rating = info.get("recommendationKey","")
        if rating in ("strong_buy","buy"):      score += 0.4; signals.append("המלצות אנליסטים: חיוביות")
        elif rating in ("sell","underperform"): score -= 0.4; signals.append("המלצות אנליסטים: שליליות")

        # revenue growth proxy
        rev_g = info.get("revenueGrowth",0) or 0
        if rev_g > 0.15:   score += 0.3; signals.append(f"צמיחת הכנסות חזקה ({rev_g*100:.0f}%)")
        elif rev_g < -0.05: score -= 0.2; signals.append(f"ירידה בהכנסות ({rev_g*100:.0f}%)")

        # earnings surprise proxy
        eps_t = info.get("trailingEps"); eps_f = info.get("forwardEps")
        if eps_t and eps_f and eps_t > 0 and eps_f > eps_t:
            score += 0.2; signals.append("EPS Forward גבוה מ-Trailing — ציפיות חיוביות")

        # analyst count
        n_an = info.get("numberOfAnalystOpinions",0) or 0
        if n_an >= 20: confidence = "High"
        elif n_an >= 10: confidence = "Medium"
        else: confidence = "Low"

        score = max(-1.0, min(1.0, score))
        if score > 0.3:    trend = "Improving"; label = "חיובי"
        elif score < -0.3: trend = "Weakening"; label = "שלילי"
        else:               trend = "Stable";    label = "ניטרלי"

        return {
            "score":      round(score, 2),
            "label":      label,
            "trend":      trend,
            "confidence": confidence,
            "signals":    signals,
            "summary":    " · ".join(signals[:3]) if signals else "נתונים מוגבלים",
        }


    def calc_options_sentiment(info: dict) -> dict:
        """
        Options Sentiment — מבוסס על נתוני שוק זמינים כ-proxy.
        עבור נתונים אמיתיים של options יש לחבר API של CBOE/TD Ameritrade.
        """
        # short interest proxy
        short_pct = info.get("shortPercentOfFloat",0) or 0
        held_inst = info.get("heldPercentInstitutions",0) or 0
        beta      = info.get("beta",1) or 1

        pc_ratio = round(0.5 + short_pct * 3, 2)  # proxy מ-short interest
        pc_ratio = max(0.2, min(2.5, pc_ratio))

        if pc_ratio < 0.7:   signal = "Bullish"; clr = "#3fb950"
        elif pc_ratio < 1.2: signal = "Neutral"; clr = "#d29922"
        else:                signal = "Bearish"; clr = "#f85149"

        activity = "Elevated Call Volume" if pc_ratio < 0.7 else                ("Elevated Put Volume" if pc_ratio > 1.2 else "Normal Activity")

        return {
            "pc_ratio":   pc_ratio,
            "signal":     signal,
            "color":      clr,
            "activity":   activity,
            "inst_held":  f"{held_inst*100:.0f}%" if held_inst else "N/A",
            "short_pct":  f"{short_pct*100:.1f}%" if short_pct else "N/A",
            "note":       "⚠️ מבוסס על short interest — לנתוני options אמיתיים נדרש API חיצוני",
        }


    def calc_macro_score(info: dict, df) -> dict:
        """
        Macro Trend — ניתוח מאקרו על בסיס sector, beta ונתוני חברה.
        לנתוני מאקרו אמיתיים (fed rates, GDP) נדרש API כגון FRED.
        """
        sector   = info.get("sector","")
        beta     = float(info.get("beta",1) or 1)
        rev_g    = float(info.get("revenueGrowth",0) or 0)
        fwd_pe   = float(info.get("forwardPE",0) or 0)

        score = 0.0; factors = []

        # sector bias (rough macro proxy)
        bullish_sectors = ["Technology","Healthcare","Consumer Cyclical","Communication Services"]
        bearish_sectors = ["Utilities","Real Estate","Energy"]
        if sector in bullish_sectors:  score += 0.3; factors.append(f"סקטור {sector} — נהנה ממומנטום")
        elif sector in bearish_sectors: score -= 0.2; factors.append(f"סקטור {sector} — רגיש לריבית")

        # beta vs macro
        if beta < 0.8:   score += 0.15; factors.append(f"Beta נמוך ({beta:.1f}) — הגנתי")
        elif beta > 1.5: score -= 0.1;  factors.append(f"Beta גבוה ({beta:.1f}) — תנודתי")

        # growth
        if rev_g > 0.10:  score += 0.2; factors.append(f"צמיחה {rev_g*100:.0f}% — תומך בתמחור")
        elif rev_g < 0:   score -= 0.2; factors.append("ירידה בהכנסות — לחץ מאקרו")

        score = max(-1.0, min(1.0, score))
        if score > 0.2:    direction = "Bullish"; risk = "Medium"
        elif score < -0.2: direction = "Bearish"; risk = "High"
        else:              direction = "Neutral"; risk = "Medium"

        if beta > 1.8: risk = "High"

        return {
            "score":     round(score, 2),
            "direction": direction,
            "risk":      risk,
            "sector":    sector or "לא ידוע",
            "factors":   factors,
            "summary":   " · ".join(factors[:3]) if factors else "נתונים מוגבלים",
            "note":      "⚠️ לנתוני ריבית/GDP/אינפלציה בזמן אמת — נדרש חיבור ל-FRED API",
        }


    def calc_risk_level(df, info: dict, macro: dict) -> dict:
        """חישוב רמת סיכון כוללת"""
        risk_pts = 0; max_pts = 0; factors = []

        # Volatility (ATR proxy)
        if len(df) >= 14:
            hi = df['High'].astype(float); lo = df['Low'].astype(float)
            cl = df['Close'].astype(float)
            atr = (hi - lo).rolling(14).mean().iloc[-1]
            atr_pct = atr / cl.iloc[-1] * 100
            max_pts += 30
            if atr_pct > 4:    risk_pts += 30; factors.append(f"תנודתיות גבוהה (ATR {atr_pct:.1f}%)")
            elif atr_pct > 2:  risk_pts += 15; factors.append(f"תנודתיות בינונית ({atr_pct:.1f}%)")
            else:               risk_pts += 5;  factors.append(f"תנודתיות נמוכה ({atr_pct:.1f}%)")

        # Distance from MA200
        if 'MA200' in df.columns and not pd.isna(df['MA200'].iloc[-1]):
            max_pts += 25
            lc  = float(df['Close'].iloc[-1])
            ma200 = float(df['MA200'].iloc[-1])
            dist_pct = (lc - ma200) / ma200 * 100
            if dist_pct < -10: risk_pts += 25; factors.append(f"מתחת MA200 ב-{abs(dist_pct):.0f}%")
            elif dist_pct < 0: risk_pts += 15; factors.append("מתחת ל-MA200")
            elif dist_pct > 30: risk_pts += 20; factors.append(f"מעל MA200 ב-{dist_pct:.0f}% — מתוח")
            else:               risk_pts += 5

        # RSI extremes
        if 'RSI' in df.columns:
            max_pts += 20
            rsi = float(df['RSI'].iloc[-1])
            if rsi > 75 or rsi < 25: risk_pts += 20; factors.append(f"RSI קיצוני ({rsi:.0f})")
            elif rsi > 68 or rsi < 32: risk_pts += 10

        # Beta
        beta = float(info.get("beta",1) or 1)
        max_pts += 25
        if beta > 2:    risk_pts += 25; factors.append(f"Beta גבוה מאוד ({beta:.1f})")
        elif beta > 1.5: risk_pts += 15; factors.append(f"Beta גבוה ({beta:.1f})")
        elif beta < 0.7: risk_pts += 5

        risk_pct = risk_pts / max_pts * 100 if max_pts > 0 else 50
        if risk_pct >= 65:   level = "High";   clr = "#f85149"; icon = "🔴"
        elif risk_pct >= 35: level = "Medium"; clr = "#d29922"; icon = "🟡"
        else:                level = "Low";    clr = "#3fb950"; icon = "🟢"

        return {"level": level, "score": int(risk_pct), "color": clr, "icon": icon,
                "factors": factors[:4], "reason": factors[0] if factors else ""}


    def calc_confidence_score(tech_score, f_score, a_score, sentiment, macro) -> dict:
        """
        Confidence Score — עד כמה ברור האות הכולל.
        לא מייצג טוב/רע — מייצג כמה הסכמה יש בין הכלים.
        """
        scores_available = [s for s in [tech_score, f_score, a_score] if s is not None]
        if not scores_available:
            return {"score": 0, "label": "N/A", "color": "#8b949e"}

        # consensus — כמה קרובים הציונות אחד לשני
        avg = sum(scores_available) / len(scores_available)
        variance = sum((s - avg)**2 for s in scores_available) / len(scores_available)
        consensus = max(0, 100 - variance / 5)

        # sentiment alignment
        s_score = sentiment.get("score", 0)
        m_score = macro.get("score", 0)
        align   = 100 - abs(s_score - m_score) * 50

        confidence = int((consensus * 0.6 + align * 0.4))
        confidence = max(0, min(100, confidence))

        if confidence >= 70:   label = "גבוהה";  clr = "#3fb950"
        elif confidence >= 40: label = "בינונית"; clr = "#d29922"
        else:                   label = "נמוכה";  clr = "#f85149"

        return {"score": confidence, "label": label, "color": clr,
                "n_sources": len(scores_available)}


    def render_advanced_analysis(ticker: str, df, info: dict, cur_price: float,
                                   sym: str, f_score, t_score, a_score):
        """
        Advanced Analysis Panel — 4 סוגי ניתוח + AI layers.
        Plug-and-play: החלף פונקציות calc_* ב-API calls אמיתיים.
        """
        st.markdown(
            '<div style="color:#e6edf3;font-size:.95rem;font-weight:800;margin-bottom:4px;">🔬 Advanced Analysis</div>'
            '<div style="color:#8b949e;font-size:.72rem;margin-bottom:14px;">'
            'ניתוח טכני, פונדמנטלי, סנטימנט ומאקרו — בשילוב שכבות AI</div>',
            unsafe_allow_html=True
        )

        # compute all
        gap_d  = calc_gap_analysis(df)
        sent_d = calc_news_sentiment(ticker, info)
        opt_d  = calc_options_sentiment(info)
        mac_d  = calc_macro_score(info, df)
        risk_d = calc_risk_level(df, info, mac_d)
        conf_d = calc_confidence_score(t_score, f_score, a_score, sent_d, mac_d)

        def mini_card(title, value, sub, color, icon, tip=""):
            return (
                f'<div style="background:#161b22;border:1px solid #21262d;'
                f'border-top:2px solid {color};border-radius:11px;padding:13px 14px;">'
                f'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;'
                f'letter-spacing:.05em;margin-bottom:4px;">{icon} {title}</div>'
                f'<div style="font-size:1.05rem;font-weight:700;color:{color};">{value}</div>'
                f'<div style="color:#8b949e;font-size:.7rem;margin-top:3px;">{sub}</div>'
                + (f'<div style="color:#8b949e;font-size:.62rem;margin-top:4px;font-style:italic;">{tip}</div>' if tip else "")
                + f'</div>'
            )

        SENT_CLR = {"חיובי":"#3fb950","ניטרלי":"#d29922","שלילי":"#f85149"}

        # ── Row 1: 4 summary cards ──
        r1,r2,r3,r4 = st.columns(4)
        r1.markdown(mini_card(
            "News Sentiment", sent_d["label"],
            f'Score: {sent_d["score"]:+.2f} · {sent_d["trend"]}',
            SENT_CLR.get(sent_d["label"],"#8b949e"), "📰",
            f'Confidence: {sent_d["confidence"]}'
        ), unsafe_allow_html=True)
        r2.markdown(mini_card(
            "Options Signal", opt_d["signal"],
            f'P/C Ratio: {opt_d["pc_ratio"]} · {opt_d["activity"]}',
            opt_d["color"], "📊"
        ), unsafe_allow_html=True)
        r3.markdown(mini_card(
            "Macro Trend", mac_d["direction"],
            f'Score: {mac_d["score"]:+.2f} · Risk: {mac_d["risk"]}',
            "#3fb950" if mac_d["direction"]=="Bullish" else ("#f85149" if mac_d["direction"]=="Bearish" else "#d29922"),
            "🌍"
        ), unsafe_allow_html=True)
        r4.markdown(mini_card(
            "Confidence", f'{conf_d["score"]}%',
            f'{conf_d["label"]} · {conf_d["n_sources"]} מקורות',
            conf_d["color"], "🎯"
        ), unsafe_allow_html=True)

        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 1])

        # ── GAP Analysis ──
        with col_a:
            gaps_all  = gap_d["gaps"]
            open_gaps = gap_d["open_gaps"]
            fill_rate = gap_d.get("fill_rate", 0)

            st.markdown(
                '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                'padding:14px 16px;margin-bottom:10px;">'
                '<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:4px;">📐 Gap Analysis</div>'
                '<div style="color:#8b949e;font-size:.7rem;margin-bottom:10px;">'
                'פערי מחיר בין סגירת יום לפתיחת היום הבא. '
                'Gap שלא מולא = אזור תמיכה/התנגדות עתידי</div>'

                + f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">'
                + f'<div style="background:#0d1117;border-radius:8px;padding:9px;text-align:center;">'
                + f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">סה"כ Gaps</div>'
                + f'<div style="font-family:JetBrains Mono,monospace;font-size:1.1rem;font-weight:700;color:#e6edf3;">{gap_d["total"]}</div></div>'
                + f'<div style="background:#0d1117;border-radius:8px;padding:9px;text-align:center;">'
                + f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">Gap פתוח</div>'
                + f'<div style="font-family:JetBrains Mono,monospace;font-size:1.1rem;font-weight:700;color:#d29922;">{len(open_gaps)}</div></div>'
                + f'<div style="background:#0d1117;border-radius:8px;padding:9px;text-align:center;">'
                + f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">שיעור מילוי</div>'
                + f'<div style="font-family:JetBrains Mono,monospace;font-size:1.1rem;font-weight:700;color:#3fb950;">{fill_rate:.0f}%</div></div>'
                + '</div>',
                unsafe_allow_html=True
            )

            if open_gaps:
                st.markdown(
                    '<div style="color:#8b949e;font-size:.65rem;text-transform:uppercase;'
                    'margin-bottom:5px;padding:0 2px;">Gaps פתוחים — רמות מחיר לא ממולאות</div>',
                    unsafe_allow_html=True
                )
                for g in open_gaps[-4:]:
                    clr = "#3fb950" if g["type"] == "gap_up" else "#f85149"
                    icon = "▲" if g["type"] == "gap_up" else "▼"
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'background:#0d1117;border:1px solid {clr}33;border-radius:7px;'
                        f'padding:7px 11px;margin-bottom:4px;">'
                        f'<div><span style="color:{clr};font-weight:700;font-size:.75rem;">{icon} '
                        f'{"Gap Up" if g["type"]=="gap_up" else "Gap Down"}</span>'
                        f'<span style="color:#8b949e;font-size:.65rem;margin-right:6px;"> · {g["date"]}</span></div>'
                        f'<div style="text-align:left;">'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:{clr};font-weight:600;">'
                        f'{g["pct"]:+.2f}%</div>'
                        f'<div style="color:#8b949e;font-size:.62rem;">{sym}{g["prev_close"]:.2f} → {sym}{g["open"]:.2f}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    '<div style="color:#8b949e;font-size:.75rem;text-align:center;padding:10px;">'
                    '✅ אין gaps פתוחים בטווח הנבחר</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Risk Level ──
            risk_bar = f'<div style="height:8px;background:#21262d;border-radius:4px;overflow:hidden;margin-top:8px;">'                    f'<div style="height:100%;width:{risk_d["score"]}%;background:linear-gradient(90deg,#3fb950,#d29922,#f85149);border-radius:4px;"></div></div>'
            risk_factors_html = "".join(
                f'<div style="color:#8b949e;font-size:.72rem;padding:3px 0;border-bottom:1px solid #21262d;">▸ {f}</div>'
                for f in risk_d["factors"]
            )
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #21262d;'
                f'border-right:3px solid {risk_d["color"]};border-radius:12px;padding:14px 16px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                f'<div style="font-size:.82rem;font-weight:700;color:#e6edf3;">⚠️ Risk Level Indicator</div>'
                f'<div style="font-size:.95rem;font-weight:800;color:{risk_d["color"]};">'
                f'{risk_d["icon"]} {risk_d["level"]}</div>'
                f'</div>'
                + risk_bar
                + f'<div style="display:flex;justify-content:space-between;margin:3px 0 8px;">'
                + f'<span style="color:#8b949e;font-size:.6rem;">Low</span>'
                + f'<span style="color:{risk_d["color"]};font-size:.65rem;font-weight:600;">Score: {risk_d["score"]}/100</span>'
                + f'<span style="color:#8b949e;font-size:.6rem;">High</span>'
                + f'</div>'
                + risk_factors_html
                + f'</div>',
                unsafe_allow_html=True
            )

        # ── RIGHT: Sentiment + Options + Macro ──
        with col_b:
            # News Sentiment detail
            sent_clr = SENT_CLR.get(sent_d["label"],"#8b949e")
            sent_sigs = "".join(
                f'<div style="color:#8b949e;font-size:.72rem;padding:3px 0;border-bottom:1px solid #21262d;">▸ {s}</div>'
                for s in sent_d["signals"]
            )
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                f'padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:8px;">📰 News Sentiment Score</div>'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                f'<div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{sent_clr};">{sent_d["score"]:+.2f}</div>'
                f'<div style="color:#8b949e;font-size:.7rem;">-1.0 = שלילי מאוד · +1.0 = חיובי מאוד</div>'
                f'</div>'
                f'<div style="text-align:center;">'
                f'<div style="background:{sent_clr}22;color:{sent_clr};border:1px solid {sent_clr}55;'
                f'border-radius:20px;padding:3px 12px;font-size:.72rem;font-weight:700;">{sent_d["label"]}</div>'
                f'<div style="color:#8b949e;font-size:.65rem;margin-top:3px;">Trend: {sent_d["trend"]}</div>'
                f'<div style="color:#8b949e;font-size:.65rem;">Confidence: {sent_d["confidence"]}</div>'
                f'</div></div>'
                + sent_sigs
                + f'<div style="color:#8b949e;font-size:.62rem;margin-top:6px;font-style:italic;">'
                f'{sent_d["summary"]}</div>'
                + f'<div style="color:#8b949e;font-size:.6rem;margin-top:4px;border-top:1px solid #21262d;padding-top:4px;">'
                f'⚠️ מבוסס על נתוני יינאנס — לציון אמיתי נדרש API חדשות (NewsAPI/Bloomberg)</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # Options Sentiment
            opt_clr = opt_d["color"]
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                f'padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:8px;">📊 Options Sentiment</div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">'
                f'<div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">'
                f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">Put/Call Ratio</div>'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:1.05rem;font-weight:700;color:#e6edf3;">{opt_d["pc_ratio"]}</div>'
                f'<div style="color:#8b949e;font-size:.6rem;">{"< 0.7 = שורי" if opt_d["pc_ratio"]<0.7 else ("> 1.2 = דובי" if opt_d["pc_ratio"]>1.2 else "0.7–1.2 = נייטרלי")}</div>'
                f'</div>'
                f'<div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">'
                f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">Signal</div>'
                f'<div style="font-size:1.0rem;font-weight:700;color:{opt_clr};">{opt_d["signal"]}</div>'
                f'<div style="color:#8b949e;font-size:.6rem;">{opt_d["activity"]}</div>'
                f'</div></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:.72rem;">'
                f'<span style="color:#8b949e;">מוסדיים: <b style="color:#c9d1d9;">{opt_d["inst_held"]}</b></span>'
                f'<span style="color:#8b949e;">Short: <b style="color:#c9d1d9;">{opt_d["short_pct"]}</b></span>'
                f'</div>'
                f'<div style="color:#8b949e;font-size:.6rem;margin-top:6px;border-top:1px solid #21262d;padding-top:4px;">'
                f'{opt_d["note"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # Macro Trend
            mac_clr = "#3fb950" if mac_d["direction"]=="Bullish" else ("#f85149" if mac_d["direction"]=="Bearish" else "#d29922")
            mac_factors_html = "".join(
                f'<div style="color:#8b949e;font-size:.72rem;padding:2px 0;">▸ {f}</div>'
                for f in mac_d["factors"]
            )
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;padding:14px 16px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                f'<div style="font-size:.82rem;font-weight:700;color:#e6edf3;">🌍 Macro Trend Detection</div>'
                f'<div style="background:{mac_clr}22;color:{mac_clr};border:1px solid {mac_clr}55;'
                f'border-radius:20px;padding:2px 10px;font-size:.72rem;font-weight:700;">'
                f'{mac_d["direction"]}</div>'
                f'</div>'
                f'<div style="display:flex;gap:12px;margin-bottom:8px;">'
                f'<div style="text-align:center;background:#0d1117;border-radius:8px;padding:8px 12px;flex:1;">'
                f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">Macro Score</div>'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:1.0rem;font-weight:700;color:{mac_clr};">{mac_d["score"]:+.2f}</div>'
                f'</div>'
                f'<div style="text-align:center;background:#0d1117;border-radius:8px;padding:8px 12px;flex:1;">'
                f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">Risk Level</div>'
                f'<div style="font-size:1.0rem;font-weight:700;color:{"#f85149" if mac_d["risk"]=="High" else ("#d29922" if mac_d["risk"]=="Medium" else "#3fb950")};">{mac_d["risk"]}</div>'
                f'</div>'
                f'<div style="text-align:center;background:#0d1117;border-radius:8px;padding:8px 12px;flex:1;">'
                f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">סקטור</div>'
                f'<div style="font-size:.78rem;font-weight:600;color:#e6edf3;">{mac_d["sector"][:12]}</div>'
                f'</div></div>'
                + mac_factors_html
                + f'<div style="color:#8b949e;font-size:.6rem;margin-top:6px;border-top:1px solid #21262d;padding-top:4px;">'
                f'{mac_d["note"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


# ════════════════════════════════════════
# TAB 2 — DECISION MODULE
# ════════════════════════════════════════
with t2:
    an_sub1, an_sub2, an_sub3 = st.tabs(["🎯 סיכום והחלטה", "🤖 AI ניתוח מתקדם", "⚠️ Position Sizing"])

    with an_sub1:
        if df is not None:
            analyst_d = load_analyst_data(ticker)
            with st.spinner("בונה סיכום ניתוח..."):
                sum_data = build_summary_data(ticker, df, info, analyst_d, cp, sym)
            render_summary_panel(sum_data)
            st.markdown('<hr style="margin:14px 0 10px;"/>', unsafe_allow_html=True)
            f_r = calc_fundamental_score(info)
            t_r = calc_technical_score(df)
            a_r = calc_analyst_score({**analyst_d, "cur_price": cp}) if analyst_d else None
            render_advanced_analysis(ticker, df, info, cp, sym,
                                      f_r.get("score"), t_r.get("score"),
                                      a_r.get("score") if a_r else None)
            st.markdown('<hr style="margin:14px 0 10px;"/>', unsafe_allow_html=True)
            render_position_module(ticker, df, info, analyst_d, cp, sym, pf)
        else:
            st.error("לא ניתן לטעון נתונים. בחרי מניה תקינה.")

    with an_sub3:
        st.markdown(f"### ⚠️ Position Sizing — {ticker}")
        cp_ = get_live_price(ticker)
        cl_, cr_ = st.columns(2)
        with cl_:
            acc = st.number_input("גודל חשבון:", value=10000, min_value=100, step=500)
            rsk = st.slider("סיכון (%):", .5, 5.0, 1.0, .5)
            enp = st.number_input("מחיר כניסה:", value=float(cp_) if cp_ else 100., min_value=.01)
            slp = st.number_input("Stop Loss:",  value=float(enp * .95), min_value=.01)
            tgp = st.number_input("יעד:",        value=float(enp * 1.10), min_value=.01)
        with cr_:
            st.markdown("#### 📊 תוצאות")
            if enp > slp:
                rps = enp - slp; ra = acc * (rsk / 100); sh = int(ra / rps)
                ps  = sh * enp;  pp = sh * (tgp - enp);  pl = sh * rps
                rr  = (tgp - enp) / rps if rps > 0 else 0
                st.metric("כמות",     f"{sh}")
                st.metric("פוזיציה",  f"{sym}{ps:,.2f}", f"{ps/acc*100:.1f}%")
                st.metric("סיכון",    f"{sym}{pl:,.2f}")
                st.metric("רווח",     f"{sym}{pp:,.2f}")
                st.metric("R:R",      f"1:{rr:.2f}", "✅" if rr >= 2 else "⚠️")
            else:
                st.error("Stop Loss חייב להיות נמוך ממחיר הכניסה")


# ════════════════════════════════════════
# TAB 3 — Backtest (Professional)
# ════════════════════════════════════════
with t3:
    st.markdown(f"### ⏳ Backtest — {ticker}")
    st.markdown(
        '<div style="color:#8b949e;font-size:.78rem;margin-bottom:12px;">'
        'בדיקה לאחור של אסטרטגיית MA Crossover מול Buy &amp; Hold. '
        'סיגנלים מבוצעים 2 ימים לאחר היווצרותם. ללא עמלות.</div>',
        unsafe_allow_html=True
    )

    # ── פרמטרים ──
    bc1, bc2, bc3 = st.columns([2, 2, 1])
    with bc1:
        mf  = st.slider("MA מהיר:", 5, 100, 50, key="bmf")
    with bc2:
        ms_ = st.slider("MA איטי:", 20, 300, 200, key="bms")
    with bc3:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        run_bt = st.button("▶ הרץ", key="run_bt", type="primary")

    # Empty state
    if len(df) <= max(mf, ms_) + 10:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            'padding:40px;text-align:center;">'
            '<div style="font-size:2rem;">📊</div>'
            '<div style="color:#8b949e;font-size:.9rem;margin-top:8px;">'
            'בחרי טווח זמן ארוך יותר כדי לקבל תוצאות Backtest משמעותיות</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        # ── חישוב Backtest ──
        cl_s  = df['Close'].astype(float)
        n_cl  = len(cl_s)
        mfa   = cl_s.rolling(min(mf,  n_cl)).mean()
        msa   = cl_s.rolling(min(ms_, n_cl)).mean()
        sig   = pd.Series(np.where(mfa > msa, 1., 0.), index=cl_s.index)
        dr    = cl_s.pct_change()
        sr    = dr * sig.shift(2)
        valid = dr.notna() & sr.notna()
        dr_v  = dr[valid]; sr_v = sr[valid]

        cs  = (1 + sr_v).cumprod()
        cm  = (1 + dr_v).cumprod()
        tr_ = (cs.iloc[-1] - 1) * 100
        mr_ = (cm.iloc[-1] - 1) * 100
        alpha_ = tr_ - mr_

        sr_mean = sr_v.mean(); sr_std = sr_v.std()
        sh2  = (sr_mean / sr_std) * np.sqrt(252) if sr_std and sr_std != 0 else 0.0
        dd_s = (cs - cs.cummax()) / cs.cummax() * 100
        mdd  = float(dd_s.min())

        # ── עסקאות ──
        nt = int(sig.diff().abs().sum() / 2)
        active = sr_v[sr_v != 0]
        wr     = float((active > 0).sum() / len(active) * 100) if len(active) > 0 else None
        wins   = active[active > 0]; losses = active[active < 0]
        avg_win  = float(wins.mean()  * 100) if len(wins)   > 0 else None
        avg_loss = float(losses.mean() * 100) if len(losses) > 0 else None
        pf_ratio = abs(wins.sum() / losses.sum()) if len(losses) > 0 and losses.sum() != 0 else None

        # exposure
        exposure = float(sig.mean() * 100)

        # streaks
        win_streak = lose_streak = cur_w = cur_l = max_w = max_l = 0
        for v in active:
            if v > 0: cur_w += 1; cur_l = 0; max_w = max(max_w, cur_w)
            else:      cur_l += 1; cur_w = 0; max_l = max(max_l, cur_l)

        # ── helper cards ──
        def metric_card(title, value, sub, color, tooltip):
            return (
                f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                f'padding:14px 16px;border-top:2px solid {color};">'
                f'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;'
                f'letter-spacing:.06em;margin-bottom:4px;">{title}</div>'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:1.25rem;'
                f'font-weight:700;color:{color};">{value}</div>'
                f'<div style="color:#8b949e;font-size:.68rem;margin-top:3px;">{sub}</div>'
                f'<div style="color:#8b949e;font-size:.62rem;margin-top:4px;font-style:italic;'
                f'border-top:1px solid #21262d;padding-top:4px;">{tooltip}</div>'
                f'</div>'
            )

        # ── שורת מדדים ראשית ──
        ret_c   = "#3fb950" if tr_ > 0 else "#f85149"
        al_c    = "#3fb950" if alpha_ > 0 else "#f85149"
        sh_c    = "#3fb950" if sh2 > 1 else ("#d29922" if sh2 > 0.5 else "#f85149")
        mdd_c   = "#3fb950" if mdd > -10 else ("#d29922" if mdd > -20 else "#f85149")
        wr_c    = "#3fb950" if (wr or 0) > 55 else ("#d29922" if (wr or 0) > 45 else "#f85149")

        wr_str  = f"{wr:.1f}%" if wr is not None else "N/A"
        wr_sub  = f"{nt} עסקאות" if nt > 0 else "0 עסקאות"

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.markdown(metric_card("תשואה כוללת",   f"{tr_:+.1f}%", f"Buy&Hold: {mr_:+.1f}%",    ret_c, "תשואה מצטברת של האסטרטגיה"), unsafe_allow_html=True)
        m2.markdown(metric_card("Alpha",          f"{alpha_:+.1f}%", "עודף על השוק",            al_c,  "עודף תשואה מעל Buy&Hold. חיובי = ניצחת את השוק"), unsafe_allow_html=True)
        m3.markdown(metric_card("Sharpe Ratio",   f"{sh2:.2f}", ">1 טוב, >2 מצוין",             sh_c,  "תשואה ביחס לסיכון. מתחת ל-0.5 = אסטרטגיה חלשה"), unsafe_allow_html=True)
        m4.markdown(metric_card("Max Drawdown",   f"{mdd:.1f}%", "ירידה מקסימלית מהשיא",       mdd_c, "הירידה הגדולה ביותר מנקודת שיא. מתחת ל-20% = סביר"), unsafe_allow_html=True)
        m5.markdown(metric_card("Win Rate",       wr_str,        wr_sub,                         wr_c,  "אחוז הימים הרווחיים מסך הימים בהם האסטרטגיה הייתה פעילה"), unsafe_allow_html=True)

        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

        # ── גרף ראשי ──
        fb = go.Figure()
        fb.add_trace(go.Scatter(
            x=cs.index, y=cs.to_numpy(), name="🟢 אסטרטגיה MA Crossover",
            line=dict(color='#3fb950', width=2.5),
            hovertemplate="<b>%{x}</b><br>אסטרטגיה: %{y:.3f}x<extra></extra>"
        ))
        fb.add_trace(go.Scatter(
            x=cm.index, y=cm.to_numpy(), name="🔴 Buy & Hold",
            line=dict(color='#f85149', width=2, dash='dash'),
            hovertemplate="<b>%{x}</b><br>Buy & Hold: %{y:.3f}x<extra></extra>"
        ))
        fb.add_hline(y=1, line_dash="dot", line_color="#484f58",
                     annotation_text="נקודת פתיחה", annotation_position="right")
        # הצבע fill בין הקווים
        fb.add_trace(go.Scatter(
            x=list(cs.index)+list(cs.index[::-1]),
            y=list(cs.to_numpy())+list(cm.to_numpy()[::-1]),
            fill='toself',
            fillcolor='rgba(63,185,80,0.05)' if tr_ > mr_ else 'rgba(248,81,73,0.05)',
            line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        fb.update_layout(
            height=380, paper_bgcolor=BG, plot_bgcolor=BG,
            margin=dict(l=0, r=58, t=36, b=10),
            font=dict(family='Inter', color='#8b949e', size=11),
            hovermode='x unified',
            hoverlabel=dict(bgcolor='#161b22', bordercolor='#30363d',
                            font=dict(family='JetBrains Mono', size=11)),
            xaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e', showgrid=True),
            yaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e', side='right',
                       tickformat=".2f", showgrid=True),
            legend=dict(orientation='h', y=1.06, bgcolor='rgba(0,0,0,0)',
                        font=dict(size=11, color='#c9d1d9')),
            title=dict(text=f"ביצועים מצטברים — {ticker}", font=dict(size=13, color='#c9d1d9'))
        )
        st.plotly_chart(fb, use_container_width=True)

        # ── גרף Drawdown ──
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=dd_s.index, y=dd_s.to_numpy(), name="Drawdown",
            fill='tozeroy', fillcolor='rgba(248,81,73,0.18)',
            line=dict(color='#f85149', width=1.5),
            hovertemplate="<b>%{x}</b><br>DD: %{y:.2f}%<extra></extra>"
        ))
        fig_dd.add_hline(y=-10, line_dash="dot", line_color="#d29922", line_width=1)
        fig_dd.add_hline(y=-20, line_dash="dot", line_color="#f85149", line_width=1)
        fig_dd.update_layout(
            height=190, paper_bgcolor=BG, plot_bgcolor=BG,
            margin=dict(l=0, r=58, t=30, b=8),
            font=dict(family='Inter', color='#8b949e', size=10),
            xaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e'),
            yaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e', side='right',
                       ticksuffix='%', showgrid=True),
            title=dict(text="Drawdown %", font=dict(size=12, color='#8b949e')),
            showlegend=False,
        )
        st.plotly_chart(fig_dd, use_container_width=True)

        # ── מסקנה אוטומטית ──
        verdict_lines = []
        if alpha_ > 5:
            verdict_lines.append(f"✅ האסטרטגיה <b>ניצחה</b> את Buy&Hold ב-{alpha_:.1f}% — הוסיפה ערך.")
        elif alpha_ > 0:
            verdict_lines.append(f"🟡 האסטרטגיה <b>עקפה</b> את Buy&Hold ב-{alpha_:.1f}% — הפרש קטן.")
        else:
            verdict_lines.append(f"❌ האסטרטגיה <b>פיגרה</b> אחרי Buy&Hold ב-{abs(alpha_):.1f}% — לא הוסיפה ערך.")

        if sh2 < 0.5:
            verdict_lines.append(f"⚠️ Sharpe Ratio של {sh2:.2f} נמוך — יחס סיכון-תשואה חלש.")
        elif sh2 > 1.5:
            verdict_lines.append(f"✅ Sharpe של {sh2:.2f} גבוה — יחס סיכון-תשואה טוב.")

        if mdd < -25:
            verdict_lines.append(f"⚠️ Max Drawdown של {mdd:.1f}% — ירידה גדולה, דורשת חוסן נפשי.")

        if nt == 0:
            verdict_lines.append("⚪ לא בוצעו עסקאות בתקופה הנבחרת.")

        # ── מסקנה משולבת: Backtest + ניתוח שוטף ──
        f_res_bt  = calc_fundamental_score(info)
        t_res_bt  = calc_technical_score(df)
        an_bt     = load_analyst_data(ticker)
        a_res_bt  = calc_analyst_score({**an_bt, "cur_price": cp}) if an_bt else None
        dec_bt    = calc_weighted_decision(
                        f_res_bt.get("score"), t_res_bt.get("score"),
                        a_res_bt.get("score") if a_res_bt else None)
        dec_clr   = dec_bt.get("color","#8b949e")
        dec_icon  = dec_bt.get("icon","⚪")
        dec_lbl   = dec_bt.get("decision","—")
        dec_w     = dec_bt.get("weighted", 0) or 0

        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            'padding:16px 20px;margin-top:4px;direction:rtl;">'
            '<div style="font-size:.88rem;font-weight:700;color:#e6edf3;margin-bottom:10px;">📋 מסקנה אוטומטית</div>'
            + "".join(f'<div style="color:#c9d1d9;font-size:.82rem;line-height:1.7;">{l}</div>' for l in verdict_lines) +
            '<hr style="border-color:#21262d;margin:10px 0;"/>'
            '<div style="font-size:.78rem;font-weight:700;color:#e6edf3;margin-bottom:8px;">🔬 ניתוח שוטף — מצב המניה כיום</div>'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px;">'
            f'<div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">'
            f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">ציון פונדמנטלי</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;font-weight:700;color:#388bfd;">'
            f'{f_res_bt.get("score","N/A")}/100</div></div>'
            f'<div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">'
            f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">ציון טכני</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;font-weight:700;color:#3fb950;">'
            f'{t_res_bt.get("score","N/A")}/100</div></div>'
            f'<div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">'
            f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;">ציון אנליסטים</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;font-weight:700;color:#d29922;">'
            f'{a_res_bt.get("score","N/A") if a_res_bt else "N/A"}/100</div></div>'
            f'</div>'
            f'<div style="background:{dec_clr}12;border:1px solid {dec_clr}44;border-radius:10px;'
            f'padding:12px 16px;display:flex;align-items:center;justify-content:space-between;">'
            f'<div>'
            f'<div style="color:#8b949e;font-size:.64rem;text-transform:uppercase;">המלצה משולבת (Backtest + ניתוח שוטף)</div>'
            f'<div style="font-size:1.2rem;font-weight:800;color:{dec_clr};margin-top:3px;">{dec_icon} {dec_lbl}</div>'
            f'</div>'
            f'<div style="text-align:center;">'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:1.5rem;font-weight:800;color:{dec_clr};">{dec_w}</div>'
            f'<div style="color:#8b949e;font-size:.62rem;">ציון משוקלל</div>'
            f'</div></div>'
            '<div style="color:#8b949e;font-size:.63rem;margin-top:10px;font-style:italic;">'
            'Backtest אינו מבטיח ביצועים עתידיים. ניתוח לצרכי לימוד בלבד. אינו ייעוץ השקעות.</div>'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown('<hr style="margin:14px 0 10px;"/>', unsafe_allow_html=True)

        # ── מדדים משלימים ──
        st.markdown("#### 📐 מדדים משלימים")
        def mini_card(title, val, color="#e6edf3", tip=""):
            return (
                f'<div style="background:#0d1117;border:1px solid #21262d;border-radius:9px;padding:10px 12px;">'
                f'<div style="color:#8b949e;font-size:.6rem;text-transform:uppercase;margin-bottom:2px;">{title}</div>'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:.9rem;font-weight:600;color:{color};">{val}</div>'
                f'{"<div style=color:#8b949e;font-size:.62rem;margin-top:2px;>" + tip + "</div>" if tip else ""}'
                f'</div>'
            )

        pf_str  = f"{pf_ratio:.2f}" if pf_ratio is not None else "N/A"
        aw_str  = f"{avg_win:.2f}%"  if avg_win  is not None else "N/A"
        al_str  = f"{avg_loss:.2f}%" if avg_loss is not None else "N/A"
        aw_c    = "#3fb950"        if avg_win  else "#8b949e"
        al_c2   = "#f85149"        if avg_loss else "#8b949e"
        pf_c    = "#3fb950" if pf_ratio and pf_ratio > 1.5 else ("#d29922" if pf_ratio and pf_ratio > 1 else "#f85149")

        s1,s2,s3,s4,s5,s6,s7 = st.columns(7)
        s1.markdown(mini_card("עסקאות",       str(nt),            "#e6edf3", ""), unsafe_allow_html=True)
        s2.markdown(mini_card("רווח ממוצע",   aw_str,             aw_c,      "לעסקה"), unsafe_allow_html=True)
        s3.markdown(mini_card("הפסד ממוצע",   al_str,             al_c2,     "לעסקה"), unsafe_allow_html=True)
        s4.markdown(mini_card("Profit Factor", pf_str,            pf_c,      ">1.5 טוב"), unsafe_allow_html=True)
        s5.markdown(mini_card("חשיפה לשוק",   f"{exposure:.1f}%", "#e6edf3", "% זמן פעיל"), unsafe_allow_html=True)
        s6.markdown(mini_card("רצף ניצחונות", str(max_w),         "#3fb950", "consecutive"), unsafe_allow_html=True)
        s7.markdown(mini_card("רצף הפסדים",   str(max_l),         "#f85149", "consecutive"), unsafe_allow_html=True)

        st.markdown('<hr style="margin:14px 0 10px;"/>', unsafe_allow_html=True)

        # ── טבלת עסקאות ──
        st.markdown("#### 📋 טבלת עסקאות")

        # בניית עסקאות מהסיגנל
        trade_rows = []
        in_trade   = False
        entry_date = entry_price_t = None
        prices     = cl_s.reindex(sig.index)

        for i in range(1, len(sig)):
            prev_sig = float(sig.iloc[i-1])
            curr_sig = float(sig.iloc[i])
            if not in_trade and curr_sig == 1 and prev_sig == 0:
                in_trade     = True
                entry_date   = sig.index[i]
                entry_price_t= float(prices.iloc[i]) if not pd.isna(prices.iloc[i]) else None
            elif in_trade and curr_sig == 0 and prev_sig == 1:
                exit_date    = sig.index[i]
                exit_price_t = float(prices.iloc[i]) if not pd.isna(prices.iloc[i]) else None
                if entry_price_t and exit_price_t and entry_price_t > 0:
                    ret_t = (exit_price_t - entry_price_t) / entry_price_t * 100
                    dur   = (exit_date - entry_date).days if hasattr((exit_date - entry_date), 'days') else "—"
                    trade_rows.append({
                        "כניסה":       str(entry_date)[:10],
                        "יציאה":       str(exit_date)[:10],
                        "מחיר כניסה":  f"${entry_price_t:.2f}",
                        "מחיר יציאה":  f"${exit_price_t:.2f}",
                        "תשואה":       f"{ret_t:+.2f}%",
                        "משך (ימים)":  str(dur),
                        "סטטוס":       "✅ רווח" if ret_t > 0 else "❌ הפסד",
                        "_ret":         ret_t,
                    })
                in_trade = False

        if trade_rows:
            df_trades_bt = pd.DataFrame(trade_rows)
            disp_cols    = ["כניסה","יציאה","מחיר כניסה","מחיר יציאה","תשואה","משך (ימים)","סטטוס"]
            def color_ret_bt(v):
                try:
                    n = float(str(v).replace("%","").replace("+",""))
                    return "color:#3fb950;font-weight:600" if n > 0 else "color:#f85149;font-weight:600"
                except: return ""
            st.dataframe(
                df_trades_bt[disp_cols].style.map(color_ret_bt, subset=["תשואה"]),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("לא זוהו עסקאות מלאות בטווח הנבחר. נסי להגדיל את טווח הזמן.")


# ════════════════════════════════════════
# TAB 4 — מסחר
# ════════════════════════════════════════
with t4:
    tr_sub1, tr_sub2 = st.tabs(["🛒 מסחר", "📊 ביצועים"])

    with tr_sub1:
            st.markdown(f"### 🛒 Paper Trading — {ticker}")
            cp_ = get_live_price(ticker)
            if cp_:
                ci, ct_ = st.columns(2)
                with ci:
                    st.markdown(
                        f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                        f'padding:16px;margin-bottom:10px;">'
                        f'<div style="color:#8b949e;font-size:.64rem;text-transform:uppercase;">מחיר</div>'
                        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:1.7rem;font-weight:700;color:#e6edf3;margin:3px 0;">'
                        f'{sym}{cp_:.2f}</div>'
                        f'<div style="color:#8b949e;font-size:.74rem;">{ticker} · {company} {il}</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                    st.metric("מזומן", f"${pf['cash']:,.2f}")
                    if ticker in pf['positions']:
                        pos = pf['positions'][ticker]
                        pg  = (cp_ - pos['avg_price']) / pos['avg_price'] * 100
                        st.metric(f"אחזקה", f"{pos['shares']} מניות ({sym}{pos['shares']*cp_:,.2f})", f"{pg:+.1f}%")
                with ct_:
                    act = st.radio("פעולה:", ["🟢 קנייה", "🔴 מכירה"], horizontal=True)
                    si_ = st.number_input("כמות:", min_value=1, max_value=1000, value=1)
                    tv_ = si_ * cp_
                    st.markdown(f"**עלות: {sym}{tv_:,.2f}**")
                    nt_ = st.text_input("הערה:", placeholder="סיבה לעסקה")
                    if st.button("✅ בצע", type="primary"):
                        p = st.session_state.pf
                        if "קנייה" in act:
                            if p['cash'] >= tv_:
                                p['cash'] -= tv_
                                if ticker not in p['positions']:
                                    p['positions'][ticker] = {"shares": 0, "avg_price": 0.}
                                pos = p['positions'][ticker]
                                ts  = pos['shares'] + si_
                                pos['avg_price'] = (pos['shares'] * pos['avg_price'] + si_ * cp_) / ts
                                pos['shares']    = ts
                                p['trades'].append({
                                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "symbol": ticker, "action": "BUY",
                                    "shares": si_, "price": cp_, "total": tv_, "note": nt_,
                                })
                                save_pf(p)
                                st.success(f"✅ קנית {si_} מניות ב-{sym}{cp_:.2f}")
                                st.rerun()
                            else:
                                st.error("אין מספיק מזומן!")
                        else:
                            if ticker in p['positions'] and p['positions'][ticker]['shares'] >= si_:
                                p['cash'] += tv_
                                pnl = (cp_ - p['positions'][ticker]['avg_price']) * si_
                                p['positions'][ticker]['shares'] -= si_
                                if p['positions'][ticker]['shares'] == 0:
                                    del p['positions'][ticker]
                                p['trades'].append({
                                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "symbol": ticker, "action": "SELL",
                                    "shares": si_, "price": cp_,
                                    "total": tv_, "pnl": round(pnl, 2), "note": nt_,
                                })
                                save_pf(p)
                                st.success(f"{'✅' if pnl >= 0 else '❌'} P&L: {sym}{pnl:+.2f}")
                                st.rerun()
                            else:
                                st.error("אין מספיק מניות.")
            else:
                st.error(f"לא ניתן לטעון מחיר עבור {ticker}.")


        # ════════════════════════════════════════
        # TAB 5 — ביצועים
        # ════════════════════════════════════════

    with tr_sub2:
            st.markdown("### 📊 יומן עסקאות")
            trd = pf['trades']
            if trd:
                dt = pd.DataFrame(trd)
                sl = dt[dt['action'] == 'SELL']
                if not sl.empty and 'pnl' in sl.columns:
                    tp = sl['pnl'].sum(); wn = (sl['pnl'] > 0).sum(); ls = (sl['pnl'] < 0).sum()
                    wr = wn / (wn + ls) * 100 if (wn + ls) > 0 else 0
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("P&L",     f"${tp:+.2f}")
                    c2.metric("מנצחות",  wn)
                    c3.metric("מפסידות", ls)
                    c4.metric("Win Rate",f"{wr:.0f}%")
                st.divider()
                def ca(v):
                    return "color:#3fb950;font-weight:600" if v == "BUY" else "color:#f85149;font-weight:600"
                def cp2(v):
                    try: return "color:#3fb950" if float(v) >= 0 else "color:#f85149"
                    except: return ""
                st_ = dt.style.map(ca, subset=['action'])
                if 'pnl' in dt.columns:
                    st_ = st_.map(cp2, subset=['pnl'])
                st.dataframe(st_, use_container_width=True)
                st.download_button("⬇️ הורד CSV",
                                   dt.to_csv(index=False).encode('utf-8'),
                                   "trades.csv", "text/csv")
            else:
                st.markdown(
                    '<div style="text-align:center;padding:40px;color:#8b949e;">'
                    '<div style="font-size:2rem;">📋</div>'
                    '<div>עדיין אין עסקאות.</div>'
                    '</div>', unsafe_allow_html=True
                )


        # ════════════════════════════════════════
        # TAB 7 — מדריך למשתמש
        # ════════════════════════════════════════
with t7:
    st.markdown("""
<div style="direction:rtl;max-width:900px;margin:0 auto;">

<h2 style="color:#e6edf3;font-size:1.3rem;font-weight:700;margin-bottom:4px;">📖 מדריך מלא — מסך הגרף</h2>
<p style="color:#8b949e;font-size:.82rem;margin-bottom:20px;">הסבר על כל אזור, כפתור ומדד במסך הגרף</p>

</div>
""", unsafe_allow_html=True)

    # ── Section helper ──
    def section(icon, title, color, content_html):
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #21262d;border-right:3px solid {color};'
            f'border-radius:12px;padding:16px 20px;margin-bottom:12px;direction:rtl;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
            f'<span style="font-size:1.1rem;">{icon}</span>'
            f'<span style="font-size:.92rem;font-weight:700;color:#e6edf3;">{title}</span>'
            f'</div>'
            f'{content_html}'
            f'</div>',
            unsafe_allow_html=True
        )

    def row(label, desc, color="#8b949e"):
        return (
            f'<div style="display:flex;gap:10px;padding:5px 0;border-bottom:1px solid #21262d;">'
            f'<span style="color:{color};font-weight:600;font-size:.82rem;min-width:120px;">{label}</span>'
            f'<span style="color:#c9d1d9;font-size:.82rem;line-height:1.5;">{desc}</span>'
            f'</div>'
        )

    # ── 1. טווח זמן ──
    section("⏱️", "טווח זמן — כמה זמן אחורה לראות",
        "#1f6feb",
        row("1D", "יום אחד — מחיר כל 5 דקות. לניתוח יומי קצר") +
        row("5D", "5 ימים — שבוע מסחר. לראות תנועה של שבוע") +
        row("1M", "חודש אחד — כל יום. לראות מגמה חודשית") +
        row("6M", "חצי שנה — לראות מגמה בינונית") +
        row("YTD", "מתחילת השנה הנוכחית") +
        row("1Y", "שנה אחורה — הטווח הכי מומלץ למתחילים", "#3fb950") +
        row("5Y", "5 שנים — לראות מגמה ארוכת טווח") +
        row("MAX", "כל הזמן מאז הנפקת המניה")
    )

    # ── 2. סוגי גרף ──
    section("📊", "סוגי גרף", "#d29922",
        row("📈 קווי", "קו פשוט המחבר את מחירי הסגירה. הכי נוח להבנת מגמה כללית", "#388bfd") +
        row("🕯️ נרות", "כל נר = יום מסחר. ירוק = עלה, אדום = ירד. מציג פתיחה/סגירה/גבוה/נמוך", "#3fb950") +
        row("📊 שטח", "כמו גרף קווי אבל עם מילוי צבע מתחת. קל יותר לראות מגמה")
    )

    # ── 3. קריאת נר ──
    section("🕯️", "איך לקרוא נר יפני", "#f0883e",
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:8px;">'
        '<div style="background:#0d1117;border-radius:8px;padding:12px;text-align:center;">'
        '<div style="color:#3fb950;font-size:2rem;line-height:1;">│<br>█<br>│</div>'
        '<div style="color:#3fb950;font-size:.78rem;margin-top:6px;font-weight:700;">נר ירוק = יום עלייה</div>'
        '<div style="color:#8b949e;font-size:.72rem;margin-top:4px;">סגירה גבוהה מפתיחה<br>פתיל עליון = הגבוה<br>פתיל תחתון = הנמוך</div>'
        '</div>'
        '<div style="background:#0d1117;border-radius:8px;padding:12px;text-align:center;">'
        '<div style="color:#f85149;font-size:2rem;line-height:1;">│<br>█<br>│</div>'
        '<div style="color:#f85149;font-size:.78rem;margin-top:6px;font-weight:700;">נר אדום = יום ירידה</div>'
        '<div style="color:#8b949e;font-size:.72rem;margin-top:4px;">סגירה נמוכה מפתיחה<br>פתיל עליון = הגבוה<br>פתיל תחתון = הנמוך</div>'
        '</div>'
        '</div>' +
        row("גוף גדול", "תנועה חזקה וברורה לכיוון אחד — קונים או מוכרים שלטו") +
        row("גוף קטן / Doji", "חוסר החלטיות — כוחות שווים בין קונים למוכרים") +
        row("פתיל עליון ארוך", "ניסיון עלייה שנדחה — יש התנגדות למעלה") +
        row("פתיל תחתון ארוך", "ניסיון ירידה שנדחה — יש תמיכה למטה")
    )

    # ── 4. OHLCV ──
    section("📋", "נתוני OHLCV — מה מוצג בפס העליון", "#bc8cff",
        row("O — Open / פתיחה", "מחיר המניה בתחילת יום המסחר") +
        row("H — High / גבוה", "המחיר הגבוה ביותר שהגיעה אליו המניה באותו יום", "#3fb950") +
        row("L — Low / נמוך", "המחיר הנמוך ביותר שהגיעה אליו המניה באותו יום", "#f85149") +
        row("C — Close / סגירה", "מחיר הסגירה — הכי חשוב. ירוק = עלה, אדום = ירד") +
        row("Volume / נפח", "כמה מניות נסחרו. נפח גבוה = תנועה אמיתית ומשמעותית")
    )

    # ── 5. אינדיקטורים ──
    section("📐", "אינדיקטורים — קווים על הגרף", "#d29922",
        row("MA20 — צהוב", "ממוצע מחיר 20 הימים האחרונים. מגמה קצרה. זז מהר", "#d29922") +
        row("MA50 — ירוק", "ממוצע 50 ימים. מגמה בינונית. מחיר מעליו = בריאות טובה", "#3fb950") +
        row("MA200 — אדום", "ממוצע 200 ימים. הקו הכי חשוב. מעליו = מגמה עולה ארוכת טווח", "#f85149") +
        row("Bollinger", "שני קווים סביב הממוצע. מחיר בשוליים = תנודתיות קיצונית", "#8b8fcc") +
        '<div style="background:#0d1117;border-radius:8px;padding:10px;margin-top:8px;">'
        '<div style="color:#3fb950;font-size:.78rem;font-weight:700;">Golden Cross ✅</div>'
        '<div style="color:#8b949e;font-size:.75rem;">MA20 חוצה MA50 כלפי מעלה — אות שורי חזק</div>'
        '<div style="color:#f85149;font-size:.78rem;font-weight:700;margin-top:6px;">Death Cross ⚠️</div>'
        '<div style="color:#8b949e;font-size:.75rem;">MA20 חוצה MA50 כלפי מטה — אות דובי</div>'
        '</div>'
    )

    # ── 6. RSI ──
    section("📐", "RSI — מד עוצמה (0–100)", "#bc8cff",
        row("מתחת ל-30", "מכור מדי (Oversold) — המניה עשויה לקפוץ חזרה. הזדמנות?", "#3fb950") +
        row("30–50", "אזור חלש-נייטרלי — אין לחץ חזק") +
        row("50–70", "אזור חיובי-נייטרלי — מגמה חיובית") +
        row("מעל 70", "קנוי מדי (Overbought) — המניה עשויה לרדת. זהירות!", "#f85149") +
        row("מעל 80", "קנוי מדי קיצוני — סיכון גבוה לתיקון", "#f85149")
    )

    # ── 7. Volume ──
    section("📊", "Volume — גרף הנפח (פאנל אמצעי)", "#3fb950",
        row("עמודה ירוקה", "יום שהמחיר עלה — הנפח תומך בעלייה", "#3fb950") +
        row("עמודה אדומה", "יום שהמחיר ירד — הנפח תומך בירידה", "#f85149") +
        row("קו אפור", "ממוצע נפח 20 ימים — הרמה הנורמלית") +
        '<div style="background:#0d1117;border-radius:8px;padding:10px;margin-top:8px;">'
        '<div style="color:#e6edf3;font-size:.78rem;font-weight:700;">מה לחפש?</div>'
        '<div style="color:#8b949e;font-size:.75rem;margin-top:4px;">'
        '• עלייה עם נפח גבוה = תנועה אמיתית 💪<br>'
        '• עלייה עם נפח נמוך = תנועה חלשה, לא סומכים עליה<br>'
        '• נפח פתאומי גבוה = קרה משהו חשוב (חדשות, דוח)'
        '</div>'
        '</div>'
    )

    # ── 8. MACD ──
    section("〰️", "MACD — מד מומנטום (פאנל תחתון)", "#388bfd",
        row("קו כחול (MACD)", "הפרש בין ממוצע 12 ו-26 ימים. מדד מהירות השינוי", "#388bfd") +
        row("קו כתום (Signal)", "ממוצע 9 ימים של ה-MACD. קו ייחוס", "#f0883e") +
        row("היסטוגרמה ירוקה", "MACD מעל Signal — מומנטום חיובי", "#3fb950") +
        row("היסטוגרמה אדומה", "MACD מתחת Signal — מומנטום שלילי", "#f85149") +
        '<div style="background:#0d1117;border-radius:8px;padding:10px;margin-top:8px;">'
        '<div style="color:#3fb950;font-size:.78rem;font-weight:700;">אות קנייה: MACD חוצה Signal כלפי מעלה ✅</div>'
        '<div style="color:#f85149;font-size:.78rem;font-weight:700;margin-top:4px;">אות מכירה: MACD חוצה Signal כלפי מטה ⚠️</div>'
        '</div>'
    )

    # ── 9. כפתורים ──
    section("🔧", "כפתורי הפעולה", "#8b949e",
        row("🔧 Indicators", "הצג/הסתר קווי MA ובולינגר על הגרף") +
        row("📊 Analytics", "פתח טבלה עם נתונים כספיים רבעוניים של החברה") +
        row("🤖 AI Insight", "קבלי ניתוח אוטומטי של מצב המניה בשפה פשוטה") +
        row("🔄 אפס", "חזור לברירת מחדל: גרף קווי + טווח שנה")
    )

    # ── 10. Analyst Snapshot ──
    section("📊", "Analyst Snapshot — מה האנליסטים חושבים", "#2ea043",
        row("דירוג קונצנזוס", "Strong Buy / Buy / Hold / Sell — ממוצע דעות האנליסטים") +
        row("יעד ממוצע", "מחיר שהאנליסטים מעריכים שהמניה תגיע אליו") +
        row("יעד גבוה / נמוך", "הפסימי ביותר והאופטימי ביותר בין האנליסטים") +
        row("פוטנציאל", "הפרש בין המחיר הנוכחי ליעד הממוצע. ▲ = אפסייד, ▼ = דאונסייד") +
        row("Forward EPS", "תחזית רווח למניה לשנה הבאה") +
        row("עדכון אחרון", "השינוי האחרון בהמלצה של אנליסט ספציפי")
    )

    # ── Fibonacci Retracement ──
    section("🌀", "Fibonacci Retracement — כלי לזיהוי תמיכה והתנגדות", "#f0883e",
        '<div style="background:#0d1117;border-radius:8px;padding:12px;margin-bottom:10px;">'
        '<div style="color:#e6edf3;font-size:.8rem;font-weight:700;margin-bottom:6px;">מה זה Fibonacci?</div>'
        '<div style="color:#8b949e;font-size:.78rem;line-height:1.7;">'
        'אחרי מהלך חד (עלייה או ירידה), המחיר בדרך כלל מתקן חלקית לפני שממשיך. '
        'רמות Fibonacci מגדירות <b style="color:#e6edf3;">איפה צפוי התיקון לעצור</b> ולהפוך לתמיכה או התנגדות.'
        '</div></div>'
        + row("0% — שיא",          "נקודת ההתחלה — השיא הגבוה ביותר של התנועה", "#8b949e")
        + row("23.6%",             "תיקון חלש — מניות חזקות לרוב עוצרות כאן", "rgba(255,215,0,0.9)")
        + row("38.2%",             "תמיכה בינונית — רמת כניסה פופולרית לטריידרים", "rgba(255,165,0,0.9)")
        + row("50.0%",             "מחצית הדרך — לא Fibonacci קלאסי אבל הכי נצפה בשוק", "rgba(255,120,50,0.95)")
        + row("61.8% ✨ Golden",   "הרמה החשובה ביותר! אחוז הזהב. רוב התיקונים עוצרים כאן", "rgba(255,80,80,1.0)")
        + row("78.6%",             "תיקון עמוק — אם שובר כאן, המהלך המקורי עלול להיכשל", "rgba(200,40,40,0.9)")
        + row("100% — שפל",        "חזרה מלאה לנקודת ההתחלה", "#8b949e")
        + '<div style="background:#1a1a0a;border:1px solid rgba(255,140,0,0.3);border-radius:8px;padding:12px;margin-top:10px;">'
        '<div style="color:#f0883e;font-size:.8rem;font-weight:700;margin-bottom:4px;">🏆 Golden Zone (38.2% — 61.8%)</div>'
        '<div style="color:#8b949e;font-size:.75rem;line-height:1.7;">'
        'האזור בין 38.2% ל-61.8% נקרא Golden Zone. '
        'רוב הכניסות הטובות ביותר מגיעות מאזור זה. '
        'חפשי נר היפוך (Hammer / Engulfing) באזור הזה לאות כניסה.'
        '</div></div>'
        + '<div style="background:#0d1117;border-radius:8px;padding:12px;margin-top:8px;">'
        '<div style="color:#e6edf3;font-size:.78rem;font-weight:700;margin-bottom:4px;">איך להשתמש?</div>'
        '<div style="color:#8b949e;font-size:.75rem;line-height:1.7;">'
        '1. זהי מהלך חד אחרון (עלייה/ירידה חדה)<br>'
        '2. הפעילי Fibonacci בפאנל Indicators<br>'
        '3. ראי היכן נמצא המחיר הנוכחי ביחס לרמות<br>'
        '4. אם המחיר ב-Golden Zone + נר היפוך — שקלי כניסה'
        '</div></div>'
    )

    # ── disclaimer ──
    st.markdown(
        '<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;'
        'padding:14px 18px;direction:rtl;margin-top:8px;">'
        '<div style="color:#8b949e;font-size:.75rem;line-height:1.7;">'
        '⚠️ <b style="color:#c9d1d9;">חשוב לדעת:</b> כל המידע באפליקציה הוא לצרכי לימוד וניתוח בלבד. '
        'הניתוח הטכני הוא כלי עזר — לא ערובה לתוצאה. '
        'לפני כל החלטת השקעה יש להתייעץ עם יועץ השקעות מוסמך.'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )


# ════════════════════════════════════════
# TAB 8 — AI ניתוח
# ════════════════════════════════════════
    with an_sub2:
        # ── API key status banner ──
        if not ANTHROPIC_KEY:
            st.markdown(
                '<div style="background:rgba(248,81,73,.1);border:1px solid rgba(248,81,73,.4);'
                'border-radius:10px;padding:12px 16px;margin-bottom:12px;direction:rtl;">'
                '<b style="color:#f85149;">⚠️ חסר API Key</b> — '
                '<span style="color:#c9d1d9;font-size:.82rem;">ניתוח AI לא יעבוד עד שתוסיפי API Key של Anthropic.<br>'
                'צרי קובץ: <code>.streamlit/secrets.toml</code><br>'
                'הוסיפי שורה: <code>ANTHROPIC_API_KEY = "sk-ant-..."</code><br>'
                'מפתח חינמי ב: <a href="https://console.anthropic.com" style="color:#388bfd;">console.anthropic.com</a>'
                '</span></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="background:rgba(63,185,80,.08);border:1px solid rgba(63,185,80,.3);'
                'border-radius:8px;padding:7px 14px;margin-bottom:10px;direction:rtl;">'
                '<span style="color:#3fb950;font-size:.78rem;">✅ API Key מחובר — ניתוח AI זמין</span>'
                '</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            '<div style="direction:rtl;">'
            '<div style="font-size:1rem;font-weight:800;color:#e6edf3;margin-bottom:4px;">🤖 AI Analysis — ניתוח מלא מבוסס AI</div>'
            '<div style="color:#8b949e;font-size:.78rem;margin-bottom:16px;">'
            'ניתוח טכני, פונדמנטלי, סנטימנט ומאקרו — המערכת מאחדת את כל הנתונים למסקנה אחת</div>'
            '</div>',
            unsafe_allow_html=True
        )

        if df is not None:
            # ── Compute all scores ──
            analyst_d_ai = load_analyst_data(ticker)
            f_ai = calc_fundamental_score(info)
            t_ai = calc_technical_score(df)
            a_ai = calc_analyst_score({**analyst_d_ai, "cur_price": cp}) if analyst_d_ai else None
            dec_ai = calc_weighted_decision(f_ai.get("score"), t_ai.get("score"),
                                             a_ai.get("score") if a_ai else None)

            gap_ai  = calc_gap_analysis(df)
            sent_ai = calc_news_sentiment(ticker, info)
            mac_ai  = calc_macro_score(info, df)
            risk_ai = calc_risk_level(df, info, mac_ai)
            conf_ai = calc_confidence_score(t_ai.get("score"), f_ai.get("score"),
                                             a_ai.get("score") if a_ai else None,
                                             sent_ai, mac_ai)
            thesis_ai = build_thesis_data(ticker, info, df)

            d_clr = dec_ai.get("color","#8b949e")
            d_lbl = dec_ai.get("decision","—")
            d_en  = dec_ai.get("en","—")
            d_w   = dec_ai.get("weighted",0) or 0

            # ══ SECTION 1: Final Verdict ══
            drivers_ai = []
            if (t_ai.get("score") or 0) >= 60: drivers_ai.append(f'ניתוח טכני חיובי — {t_ai.get("score")}/100')
            if (f_ai.get("score") or 0) >= 60: drivers_ai.append(f'יסודות פיננסיים חזקים — {f_ai.get("score")}/100')
            if sent_ai["score"] > 0.3:         drivers_ai.append(f'סנטימנט חיובי ({sent_ai["score"]:+.2f})')
            if mac_ai["direction"] == "Bullish": drivers_ai.append(f'מאקרו תומך — {mac_ai["sector"]}')
            if analyst_d_ai.get("rating") in ("Strong Buy","Buy"): drivers_ai.append(f'קונצנזוס אנליסטים: {analyst_d_ai["rating"]}')
            if gap_ai["open_gaps"]:            drivers_ai.append(f'{len(gap_ai["open_gaps"])} Gaps פתוחים — אזורי תמיכה/התנגדות')
            if (t_ai.get("score") or 0) < 40:  drivers_ai.append(f'ניתוח טכני חלש — {t_ai.get("score")}/100')
            if risk_ai["level"] == "High":      drivers_ai.append(f'סיכון גבוה: {risk_ai["factors"][0] if risk_ai["factors"] else ""}')
            if not drivers_ai:                  drivers_ai.append("נתונים מוגבלים — יש לבדוק ידנית")

            drivers_html = "".join(
                f'<div style="display:flex;align-items:flex-start;gap:6px;padding:5px 0;border-bottom:1px solid #21262d;">'
                f'<span style="color:{d_clr};font-size:.75rem;flex-shrink:0;">▸</span>'
                f'<span style="color:#c9d1d9;font-size:.78rem;line-height:1.5;">{d}</span></div>'
                for d in drivers_ai[:6]
            )

            st.markdown(
                f'<div style="background:{d_clr}10;border:2px solid {d_clr}55;border-radius:16px;'
                f'padding:22px 26px;margin-bottom:16px;direction:rtl;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">'
                f'<div>'
                f'<div style="color:#8b949e;font-size:.66rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;">המלצת AI סופית</div>'
                f'<div style="font-size:2.2rem;font-weight:900;color:{d_clr};line-height:1;">{dec_ai.get("icon","⚪")} {d_lbl}</div>'
                f'<div style="color:{d_clr};font-size:.85rem;font-weight:600;margin-top:2px;">{d_en}</div>'
                f'</div>'
                f'<div style="text-align:center;background:#0d1117;border-radius:12px;padding:14px 18px;">'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:2.5rem;font-weight:900;color:{d_clr};line-height:1;">{d_w}</div>'
                f'<div style="color:#8b949e;font-size:.64rem;margin-top:3px;">Confidence Score</div>'
                f'<div style="color:{conf_ai["color"]};font-size:.72rem;font-weight:600;">{conf_ai["label"]}</div>'
                f'</div></div>'
                f'<div style="height:8px;background:#21262d;border-radius:4px;overflow:hidden;margin-bottom:4px;">'
                f'<div style="height:100%;width:{d_w}%;background:linear-gradient(90deg,{d_clr}88,{d_clr});border-radius:4px;"></div>'
                f'</div>'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:14px;">'
                f'<span style="color:#8b949e;font-size:.6rem;">0 — מכירה ברורה</span>'
                f'<span style="color:#8b949e;font-size:.6rem;">100 — קנייה ברורה</span>'
                f'</div>'
                f'<div style="color:#8b949e;font-size:.7rem;font-weight:600;text-transform:uppercase;margin-bottom:6px;">Key Drivers</div>'
                + drivers_html +
                f'<div style="color:#8b949e;font-size:.62rem;margin-top:10px;padding-top:8px;border-top:1px solid #21262d;">'
                f'⚠️ ניתוח אלגוריתמי בלבד — אינו ייעוץ השקעות. לפני כל החלטה התייעצי עם בעל רישיון.</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # ══ SECTION 2: 4-way analysis dashboard ══
            c1, c2, c3, c4 = st.columns(4)

            def score_gauge(score, label, color):
                if score is None: return f'<div style="color:#8b949e;font-size:.75rem;">{label}: N/A</div>'
                w = score
                return (
                    f'<div style="background:#161b22;border:1px solid #21262d;border-top:2px solid {color};'
                    f'border-radius:10px;padding:12px;text-align:center;">'
                    f'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;margin-bottom:4px;">{label}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:1.3rem;font-weight:700;color:{color};">{score}</div>'
                    f'<div style="height:4px;background:#21262d;border-radius:2px;margin-top:6px;overflow:hidden;">'
                    f'<div style="height:100%;width:{w}%;background:{color};border-radius:2px;"></div>'
                    f'</div></div>'
                )

            c1.markdown(score_gauge(f_ai.get("score"), "ניתוח פונדמנטלי", "#388bfd"), unsafe_allow_html=True)
            c2.markdown(score_gauge(t_ai.get("score"), "ניתוח טכני", "#3fb950"), unsafe_allow_html=True)
            c3.markdown(score_gauge(a_ai.get("score") if a_ai else None, "ניתוח אנליסטים", "#d29922"), unsafe_allow_html=True)
            sent_c = "#3fb950" if sent_ai["score"]>0.2 else ("#f85149" if sent_ai["score"]<-0.2 else "#d29922")
            c4.markdown(score_gauge(int((sent_ai["score"]+1)*50), "ניתוח סנטימנט", sent_c), unsafe_allow_html=True)

            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

            # ══ SECTION 3: Risk + Macro + Gaps ══
            col_x, col_y = st.columns([1, 1])
            with col_x:
                # Risk breakdown
                risk_clr = risk_ai["color"]
                st.markdown(
                    f'<div style="background:#161b22;border:1px solid #21262d;border-right:3px solid {risk_clr};'
                    f'border-radius:12px;padding:14px 16px;margin-bottom:10px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                    f'<div style="font-size:.82rem;font-weight:700;color:#e6edf3;">⚠️ סיכון עסקה</div>'
                    f'<div style="font-size:1.0rem;font-weight:700;color:{risk_clr};">{risk_ai["icon"]} {risk_ai["level"]}</div>'
                    f'</div>'
                    + "".join(
                        f'<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #21262d;">'
                        f'<span style="color:{risk_clr};font-size:.7rem;">▸</span>'
                        f'<span style="color:#c9d1d9;font-size:.75rem;">{f}</span></div>'
                        for f in risk_ai["factors"]
                    ) +
                    f'</div>',
                    unsafe_allow_html=True
                )

                # Macro
                mac_clr = "#3fb950" if mac_ai["direction"]=="Bullish" else ("#f85149" if mac_ai["direction"]=="Bearish" else "#d29922")
                st.markdown(
                    f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;padding:14px 16px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                    f'<div style="font-size:.82rem;font-weight:700;color:#e6edf3;">🌍 מאקרו</div>'
                    f'<div style="background:{mac_clr}22;color:{mac_clr};border:1px solid {mac_clr}55;'
                    f'border-radius:20px;padding:2px 10px;font-size:.7rem;font-weight:700;">{mac_ai["direction"]}</div>'
                    f'</div>'
                    + "".join(
                        f'<div style="color:#8b949e;font-size:.73rem;padding:2px 0;border-bottom:1px solid #21262d;">▸ {f}</div>'
                        for f in mac_ai["factors"]
                    ) +
                    f'<div style="color:#8b949e;font-size:.62rem;margin-top:6px;">סקטור: {mac_ai["sector"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            with col_y:
                # Thesis summary
                CASE_C = {"bull":("#3fb950","📈"),"base":("#d29922","↔️"),"bear":("#f85149","📉")}
                st.markdown(
                    f'<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
                    f'padding:14px 16px;margin-bottom:10px;">'
                    f'<div style="font-size:.82rem;font-weight:700;color:#e6edf3;margin-bottom:6px;">🧭 Investment Thesis</div>'
                    f'<div style="color:#c9d1d9;font-size:.75rem;line-height:1.6;margin-bottom:10px;">{thesis_ai.get("summary","")}</div>',
                    unsafe_allow_html=True
                )
                for key in ["bull","base","bear"]:
                    case = thesis_ai.get(key, {})
                    clr, ico = CASE_C[key]
                    pts = case.get("points", [])
                    st.markdown(
                        f'<div style="background:{clr}0d;border:1px solid {clr}33;border-radius:8px;'
                        f'padding:8px 11px;margin-bottom:5px;">'
                        f'<div style="color:{clr};font-size:.73rem;font-weight:700;margin-bottom:3px;">{ico} {case.get("title",key)}</div>'
                        + "".join(f'<div style="color:#8b949e;font-size:.7rem;line-height:1.5;">• {p}</div>' for p in pts[:2])
                        + f'<div style="color:{clr};font-family:JetBrains Mono,monospace;font-size:.7rem;margin-top:3px;">יעד: {case.get("target","N/A")}</div>'
                        + f'</div>',
                        unsafe_allow_html=True
                    )
                st.markdown('</div>', unsafe_allow_html=True)

            # ══ SECTION 4: AI Insight (Claude) ══
            st.markdown('<hr style="margin:14px 0 10px;"/>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:.85rem;font-weight:700;color:#e6edf3;margin-bottom:6px;">'
                '🤖 ניתוח AI מפורט (Claude)</div>',
                unsafe_allow_html=True
            )
            if st.button("▶ הפעל ניתוח AI מלא", key="ai_full_btn", type="primary",
                         help="שולח את כל נתוני המניה ל-Claude לניתוח מעמיק בשפה פשוטה"):
                with st.spinner("Claude מנתח את המניה..."):
                    try:
                        rsi_ai  = float(df['RSI'].iloc[-1]) if 'RSI' in df.columns else 50
                        ma200_v = float(df['MA200'].iloc[-1]) if 'MA200' in df.columns else cp
                        macd_v  = float(df['MACD'].iloc[-1])   if 'MACD' in df.columns else 0
                        pe_v    = info.get('trailingPE','N/A')
                        rev_g_v = f"{(info.get('revenueGrowth',0) or 0)*100:.1f}%"
                        prompt = (
                            f"You are a senior financial analyst. Analyze {ticker} comprehensively.\n"
                            f"Data: Price={sym}{cp:.2f}, RSI={rsi_ai:.0f}, "
                            f"{'above' if cp>ma200_v else 'below'} MA200({sym}{ma200_v:.2f}), "
                            f"MACD={'positive' if macd_v>0 else 'negative'}, "
                            f"P/E={pe_v}, Revenue Growth={rev_g_v}, "
                            f"Fundamental Score={f_ai.get('score','N/A')}/100, "
                            f"Technical Score={t_ai.get('score','N/A')}/100, "
                            f"Analyst Rating={analyst_d_ai.get('rating','N/A')}, "
                            f"Risk Level={risk_ai['level']}, "
                            f"Open Gaps={len(gap_ai['open_gaps'])}, "
                            f"Sentiment={sent_ai['label']} ({sent_ai['score']:+.2f}).\n"
                            f"Respond ONLY in Hebrew. Write 4 clear sections:\n"
                            f"1. **מצב המניה כיום** (2-3 משפטים)\n"
                            f"2. **חוזקות עיקריות** (3 נקודות)\n"
                            f"3. **סיכונים וחולשות** (3 נקודות)\n"
                            f"4. **מסקנה ומה לעקוב** (2-3 משפטים)\n"
                            f"Be specific, professional, and accessible to non-experts."
                        )
                        resp = requests.post(
                            "https://api.anthropic.com/v1/messages",
                            headers=ai_headers(),
                            json={"model": "claude-sonnet-4-20250514", "max_tokens": 800,
                                  "messages": [{"role": "user", "content": prompt}]},
                            timeout=30
                        )
                        if resp.status_code == 200:
                            ai_text = resp.json()['content'][0]['text'].strip()
                            st.session_state['ai_full_result'] = ai_text
                        else:
                            st.session_state['ai_full_result'] = f"שגיאה: {resp.status_code}"
                    except Exception as e:
                        st.session_state['ai_full_result'] = f"שגיאה: {e}"

            if st.session_state.get('ai_full_result'):
                ai_txt = st.session_state['ai_full_result']
                st.markdown(
                    f'<div style="background:#161b22;border:1px solid #1f6feb;border-radius:12px;'
                    f'padding:18px 22px;direction:rtl;">'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">'
                    f'<span style="background:linear-gradient(135deg,#6e40c9,#1f6feb);color:white;'
                    f'border-radius:4px;padding:1px 7px;font-size:.62rem;font-weight:700;">AI</span>'
                    f'<span style="font-size:.85rem;font-weight:700;color:#e6edf3;">ניתוח Claude — {ticker}</span>'
                    f'</div>'
                    f'<div style="color:#c9d1d9;font-size:.83rem;line-height:1.8;white-space:pre-wrap;">{ai_txt}</div>'
                    f'<div style="color:#8b949e;font-size:.62rem;margin-top:10px;padding-top:8px;border-top:1px solid #21262d;">'
                    f'⚠️ ניתוח AI בלבד — אינו ייעוץ השקעות מוסמך.</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.error("לא ניתן לטעון נתונים. בחרי מניה תקינה.")


    # ════════════════════════════════════════
    # TAB 9 — השוואת מניות
    # ════════════════════════════════════════

with t9:
    st.markdown(
        '<div style="direction:rtl;margin-bottom:12px;">'
        '<div style="font-size:1rem;font-weight:800;color:#e6edf3;margin-bottom:4px;">⚖️ השוואת מניות</div>'
        '<div style="color:#8b949e;font-size:.78rem;">'
        'הוסיפי מניות לרשימה — תישמרנה אוטומטית. בחרי אילו להשוות</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Saved comparison list ──
    if 'cmp_symbols' not in st.session_state:
        st.session_state.cmp_symbols = [ticker]

    # Add symbol
    add_c1, add_c2 = st.columns([4, 1])
    with add_c1:
        new_cmp = st.text_input("הוסיפי מניה לרשימה", placeholder="AAPL, MSFT, TSLA...",
                                key="cmp_new_input", label_visibility="collapsed").upper().strip()
    with add_c2:
        if st.button("➕ הוסף", key="cmp_add_btn", type="primary", use_container_width=True):
            if new_cmp and new_cmp not in st.session_state.cmp_symbols:
                st.session_state.cmp_symbols.append(new_cmp)
                save_user_data()
                st.rerun()

    # ── Show saved symbols with sector info ──
    if st.session_state.cmp_symbols:
        st.markdown(
            '<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;'
            'margin-bottom:6px;">📋 מניות שמורות</div>',
            unsafe_allow_html=True
        )
        sym_info_html = ""
        COLORS_CHIPS = ["#388bfd","#3fb950","#f0883e","#bc8cff","#f85149","#d29922"]
        for i, sym_s in enumerate(st.session_state.cmp_symbols):
            clr_chip = COLORS_CHIPS[i % len(COLORS_CHIPS)]
            try:
                inf_s   = load_info(sym_s)
                sector  = inf_s.get("sector","") or ""
                indust  = inf_s.get("industry","") or ""
                country = inf_s.get("country","") or ""
                name_s  = (inf_s.get("shortName","") or sym_s)[:18]
                flag    = "🇮🇱" if country=="Israel" else ("🇺🇸" if country=="United States" else "🌍")
                sym_info_html += (
                    f'<div style="background:#161b22;border:1px solid {clr_chip}33;'
                    f'border-right:3px solid {clr_chip};border-radius:8px;'
                    f'padding:8px 12px;margin-bottom:5px;direction:rtl;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<span style="font-weight:700;color:{clr_chip};font-size:.85rem;">{sym_s}</span>'
                    f'<span style="color:#8b949e;font-size:.7rem;margin-right:7px;"> · {name_s}</span>'
                    f'</div>'
                    f'<span style="font-size:.72rem;">{flag}</span>'
                    f'</div>'
                    f'<div style="margin-top:4px;display:flex;gap:5px;flex-wrap:wrap;">'
                    + (f'<span style="background:#21262d;border-radius:5px;padding:2px 7px;font-size:.64rem;color:#8b949e;">🗂 {sector}</span>' if sector else "")
                    + (f'<span style="background:#21262d;border-radius:5px;padding:2px 7px;font-size:.64rem;color:#8b949e;">📌 {indust[:22]}</span>' if indust else "")
                    + f'</div></div>'
                )
            except:
                sym_info_html += (
                    f'<div style="background:#161b22;border:1px solid {clr_chip}33;'
                    f'border-right:3px solid {clr_chip};border-radius:8px;'
                    f'padding:8px 12px;margin-bottom:5px;">'
                    f'<span style="font-weight:700;color:{clr_chip};font-size:.85rem;">{sym_s}</span>'
                    f'</div>'
                )
        st.markdown(sym_info_html, unsafe_allow_html=True)

        # Remove buttons
        if len(st.session_state.cmp_symbols) > 1:
            rem_cols2 = st.columns(min(len(st.session_state.cmp_symbols), 6))
            for i, s in enumerate(st.session_state.cmp_symbols[:6]):
                if rem_cols2[i].button(f"🗑 {s}", key=f"cmp_rm_{i}"):
                    st.session_state.cmp_symbols.pop(i)
                    save_user_data()
                    st.rerun()

    st.divider()

    # ── Select which to compare ──
    if len(st.session_state.cmp_symbols) < 2:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            'padding:40px;text-align:center;">'
            '<div style="font-size:2rem;margin-bottom:8px;">⚖️</div>'
            '<div style="color:#8b949e;">הוסיפי לפחות 2 מניות לרשימה למעלה</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        sel_c1, sel_c2 = st.columns([4, 2])
        with sel_c1:
            selected_for_cmp = st.multiselect(
                "בחרי מניות להשוואה (2-4):",
                options=st.session_state.cmp_symbols,
                default=st.session_state.cmp_symbols[:4],
                max_selections=4,
                key="cmp_selected"
            )
        with sel_c2:
            cmp_period = st.selectbox("טווח זמן", ["1M","3M","6M","1Y","3Y","5Y"],
                                       index=3, key="cmp_period")

        symbols_cmp = selected_for_cmp
        COLORS_CMP  = ["#388bfd", "#3fb950", "#f0883e", "#bc8cff"]

        if len(symbols_cmp) < 2:
            st.info("בחרי לפחות 2 מניות להשוואה")
        else:
            INTERVAL_MAP = {"1M":"1d","3M":"1d","6M":"1d","1Y":"1d","3Y":"1wk","5Y":"1wk"}
            interval_cmp = INTERVAL_MAP.get(cmp_period, "1d")

            with st.spinner("טוען נתוני מניות..."):
                cmp_data = {}
                for sym_c in symbols_cmp:
                    try:
                        df_c = load_ohlcv(sym_c, cmp_period, interval_cmp)
                        if df_c is not None and len(df_c) > 0:
                            inf_c = load_info(sym_c)
                            cmp_data[sym_c] = {"df": df_c, "info": inf_c}
                    except:
                        pass

            if not cmp_data:
                st.error("לא ניתן לטעון נתונים. בדקי את הסימולים.")
            else:
                found = list(cmp_data.keys())

            # ══ CHART 1: ביצועים מנורמלים (base=100) ══
            st.markdown("#### 📈 ביצועים מנורמלים — בסיס 100")
            st.markdown(
                '<div style="color:#8b949e;font-size:.72rem;margin-bottom:8px;">'
                'כל המניות מתחילות מ-100 — קל לראות מי הרוויח יותר ביחס לנקודת ההתחלה</div>',
                unsafe_allow_html=True
            )

            fig_cmp = go.Figure()
            for i, sym_c in enumerate(found):
                df_c  = cmp_data[sym_c]["df"]
                cl_c  = df_c['Close'].astype(float)
                base  = float(cl_c.iloc[0])
                norm  = cl_c / base * 100 if base > 0 else cl_c
                last_ret = float(norm.iloc[-1]) - 100
                clr_c = COLORS_CMP[i % len(COLORS_CMP)]
                fig_cmp.add_trace(go.Scatter(
                    x=df_c.index, y=norm.to_numpy(),
                    name=f"{sym_c} ({last_ret:+.1f}%)",
                    line=dict(color=clr_c, width=2.5),
                    hovertemplate=f"<b>{sym_c}</b><br>%{{x}}<br>%{{y:.1f}} (+{last_ret:.1f}%)<extra></extra>"
                ))

            fig_cmp.add_hline(y=100, line_dash="dot", line_color="#484f58", line_width=1)
            fig_cmp.update_layout(
                height=380, paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(family='Heebo, Inter', color='#8b949e', size=11),
                hovermode='x unified',
                hoverlabel=dict(bgcolor='#161b22', bordercolor='#388bfd',
                                font=dict(family='JetBrains Mono', size=11, color='#e6edf3')),
                legend=dict(orientation='h', y=1.05, bgcolor='rgba(0,0,0,0)',
                            font=dict(size=11, color='#c9d1d9')),
                margin=dict(l=0, r=58, t=30, b=10),
                xaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e'),
                yaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e',
                           side='right', ticksuffix=''),
            )
            st.plotly_chart(fig_cmp, use_container_width=True)

            # ══ CHART 2: Drawdown ══
            st.markdown("#### 📉 Drawdown — ירידה מהשיא")
            fig_dd_cmp = go.Figure()
            for i, sym_c in enumerate(found):
                df_c  = cmp_data[sym_c]["df"]
                cl_c  = df_c['Close'].astype(float)
                dd_c  = (cl_c - cl_c.cummax()) / cl_c.cummax() * 100
                clr_c = COLORS_CMP[i % len(COLORS_CMP)]
                fig_dd_cmp.add_trace(go.Scatter(
                    x=df_c.index, y=dd_c.to_numpy(),
                    name=sym_c, line=dict(color=clr_c, width=1.5),
                    hovertemplate=f"<b>{sym_c}</b> DD: %{{y:.1f}}%<extra></extra>"
                ))
            fig_dd_cmp.add_hline(y=-10, line_dash="dot", line_color="#d29922", line_width=1)
            fig_dd_cmp.add_hline(y=-20, line_dash="dot", line_color="#f85149", line_width=1)
            fig_dd_cmp.update_layout(
                height=200, paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(family='Heebo, Inter', color='#8b949e', size=10),
                hovermode='x unified',
                margin=dict(l=0, r=58, t=20, b=8),
                xaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e'),
                yaxis=dict(gridcolor=GR, zeroline=False, color='#8b949e',
                           side='right', ticksuffix='%'),
                legend=dict(orientation='h', y=1.1, bgcolor='rgba(0,0,0,0)',
                            font=dict(size=10, color='#c9d1d9')),
                showlegend=False,
            )
            st.plotly_chart(fig_dd_cmp, use_container_width=True)

            # ══ TABLE: מדדים זה לצד זה ══
            st.markdown("#### 📋 השוואת מדדים")

            def fmt_pct(v):
                if v is None: return "N/A"
                return f"{v*100:+.1f}%"
            def fmt_num(v, dec=1):
                if v is None: return "N/A"
                try: return f"{float(v):.{dec}f}"
                except: return "N/A"
            def fmt_big_cmp(v):
                if not v: return "N/A"
                v = float(v)
                if v >= 1e12: return f"${v/1e12:.1f}T"
                if v >= 1e9:  return f"${v/1e9:.1f}B"
                if v >= 1e6:  return f"${v/1e6:.0f}M"
                return f"${v:,.0f}"

            # compute returns + stats per stock
            rows_data = []
            for sym_c in found:
                df_c  = cmp_data[sym_c]["df"]
                inf_c = cmp_data[sym_c]["info"]
                cl_c  = df_c['Close'].astype(float)
                lc_c  = float(cl_c.iloc[-1])
                ret_tot = (cl_c.iloc[-1] - cl_c.iloc[0]) / cl_c.iloc[0] * 100
                daily_r = cl_c.pct_change().dropna()
                vol_ann = daily_r.std() * (252**0.5) * 100
                dd_max  = float(((cl_c - cl_c.cummax()) / cl_c.cummax()).min() * 100)
                sharpe  = (daily_r.mean() / daily_r.std() * (252**0.5)) if daily_r.std() > 0 else 0

                rows_data.append({
                    "מניה":          sym_c,
                    "שם":            (inf_c.get("shortName","") or "")[:18],
                    "מחיר":          f"${lc_c:.2f}",
                    f"תשואה ({cmp_period})": f"{ret_tot:+.1f}%",
                    "תנודתיות":      f"{vol_ann:.1f}%",
                    "Max DD":        f"{dd_max:.1f}%",
                    "Sharpe":        f"{sharpe:.2f}",
                    "P/E":           fmt_num(inf_c.get("trailingPE")),
                    "שווי שוק":      fmt_big_cmp(inf_c.get("marketCap")),
                    "צמיחה":         fmt_pct(inf_c.get("revenueGrowth")),
                    "_ret":          ret_tot,
                    "_sharpe":       sharpe,
                })

            # render HTML table
            cols_show = ["מניה","שם","מחיר",f"תשואה ({cmp_period})","תנודתיות","Max DD","Sharpe","P/E","שווי שוק","צמיחה"]
            th_s = 'style="background:#0d1117;color:#8b949e;font-size:.67rem;text-transform:uppercase;padding:8px 12px;text-align:right;border-bottom:2px solid #21262d;"'
            header_html = "<tr>" + "".join(f"<th {th_s}>{c}</th>" for c in cols_show) + "</tr>"

            body_html = ""
            for i, row_d in enumerate(rows_data):
                clr_sym = COLORS_CMP[i % len(COLORS_CMP)]
                bg = "#161b22" if i % 2 == 0 else "#0d1117"
                cells = ""
                for col in cols_show:
                    val = row_d.get(col, "—")
                    if col == "מניה":
                        cells += f'<td style="padding:8px 12px;font-weight:700;color:{clr_sym};font-size:.82rem;border-bottom:1px solid #21262d;text-align:right;">{val}</td>'
                    elif col in (f"תשואה ({cmp_period})", "צמיחה"):
                        try:
                            n = float(str(val).replace("%","").replace("+",""))
                            vc = "#3fb950" if n > 0 else "#f85149"
                        except: vc = "#8b949e"
                        cells += f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-size:.8rem;color:{vc};font-weight:600;border-bottom:1px solid #21262d;text-align:right;">{val}</td>'
                    elif col == "Max DD":
                        cells += f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-size:.8rem;color:#f85149;border-bottom:1px solid #21262d;text-align:right;">{val}</td>'
                    else:
                        cells += f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-size:.8rem;color:#e6edf3;border-bottom:1px solid #21262d;text-align:right;">{val}</td>'
                body_html += f'<tr style="background:{bg};">{cells}</tr>'

            st.markdown(
                '<div style="overflow-x:auto;">'
                '<table style="width:100%;border-collapse:collapse;direction:rtl;">'
                f'<thead>{header_html}</thead>'
                f'<tbody>{body_html}</tbody>'
                '</table></div>',
                unsafe_allow_html=True
            )

            # ══ WINNER CARDS ══
            st.markdown('<hr style="margin:14px 0 10px;"/>', unsafe_allow_html=True)
            st.markdown("#### 🏆 מי מוביל?")

            best_ret  = max(rows_data, key=lambda x: x["_ret"])
            best_sh   = max(rows_data, key=lambda x: x["_sharpe"])
            worst_ret = min(rows_data, key=lambda x: x["_ret"])

            w1, w2, w3 = st.columns(3)
            for col_w, icon, title, row_w, val_key, suffix in [
                (w1, "🥇", "תשואה הכי גבוהה",   best_ret,  "_ret",    "%"),
                (w2, "⚡", "Sharpe הכי טוב",     best_sh,   "_sharpe", ""),
                (w3, "📉", "תשואה הכי נמוכה",    worst_ret, "_ret",    "%"),
            ]:
                sym_w  = row_w["מניה"]
                val_w  = row_w[val_key]
                idx_w  = found.index(sym_w)
                clr_w  = COLORS_CMP[idx_w % len(COLORS_CMP)]
                col_w.markdown(
                    f'<div style="background:#161b22;border:1px solid #21262d;'
                    f'border-top:2px solid {clr_w};border-radius:11px;padding:14px;text-align:center;">'
                    f'<div style="font-size:1.4rem;">{icon}</div>'
                    f'<div style="color:#8b949e;font-size:.65rem;text-transform:uppercase;margin:4px 0;">{title}</div>'
                    f'<div style="font-size:1.1rem;font-weight:700;color:{clr_w};">{sym_w}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:.88rem;color:#e6edf3;">'
                    f'{val_w:+.2f}{suffix}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ════════════════════════════════════════
# TAB 10 — 💼 Portfolio Tracker
# ════════════════════════════════════════
with t10:
    st.markdown(
        '<div style="direction:rtl;margin-bottom:12px;">'
        '<div style="font-size:1rem;font-weight:800;color:#e6edf3;margin-bottom:4px;">💼 Portfolio Tracker — תיק עסקאות</div>'
        '<div style="color:#8b949e;font-size:.78rem;">הזיני מניות, כמות ומחיר קנייה — האפליקציה תחשב תשואה, שווי ופיזור</div>'
        '</div>', unsafe_allow_html=True
    )

    if 'portfolio_positions' not in st.session_state:
        st.session_state.portfolio_positions = []

    # ── Add position form ──
    with st.expander("➕ הוסף מניה לתיק", expanded=len(st.session_state.portfolio_positions)==0):
        pa1, pa2, pa3, pa4 = st.columns(4)
        with pa1: pt_sym  = st.text_input("סימול", placeholder="AAPL", key="pt_sym").upper().strip()
        with pa2: pt_qty  = st.number_input("כמות", min_value=0.01, value=1.0, step=1.0, key="pt_qty")
        with pa3: pt_cost = st.number_input("מחיר קנייה ($)", min_value=0.01, value=100.0, key="pt_cost")
        with pa4:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            if st.button("הוסף", key="pt_add", type="primary"):
                if pt_sym:
                    st.session_state.portfolio_positions.append({
                        "symbol": pt_sym, "qty": pt_qty, "cost": pt_cost
                    })
                    save_user_data()
                    st.rerun()

    if not st.session_state.portfolio_positions:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            'padding:40px;text-align:center;">'
            '<div style="font-size:2rem;">💼</div>'
            '<div style="color:#8b949e;margin-top:8px;">התיק ריק — הוסיפי מניות למעלה</div>'
            '</div>', unsafe_allow_html=True
        )
    else:
        with st.spinner("טוען מחירים עדכניים..."):
            rows_pt = []
            total_cost_pt = 0; total_val_pt = 0
            for pos in st.session_state.portfolio_positions:
                price_now = get_live_price(pos["symbol"]) or pos["cost"]
                inf_pt    = load_info(pos["symbol"])
                cost_tot  = pos["qty"] * pos["cost"]
                val_now   = pos["qty"] * price_now
                ret_pct   = (price_now - pos["cost"]) / pos["cost"] * 100
                ret_abs   = val_now - cost_tot
                total_cost_pt += cost_tot
                total_val_pt  += val_now
                rows_pt.append({
                    "sym":      pos["symbol"],
                    "name":     (inf_pt.get("shortName","") or "")[:16],
                    "sector":   inf_pt.get("sector","—") or "—",
                    "qty":      pos["qty"],
                    "cost":     pos["cost"],
                    "price":    price_now,
                    "val":      val_now,
                    "ret_pct":  ret_pct,
                    "ret_abs":  ret_abs,
                    "weight":   0,
                })

        # weights
        for r in rows_pt:
            r["weight"] = r["val"] / total_val_pt * 100 if total_val_pt > 0 else 0

        # ── Summary cards ──
        total_ret = (total_val_pt - total_cost_pt) / total_cost_pt * 100 if total_cost_pt > 0 else 0
        ret_clr   = "#3fb950" if total_ret >= 0 else "#f85149"

        sc1, sc2, sc3, sc4 = st.columns(4)
        for col_s, lbl, val, clr in [
            (sc1, "שווי נוכחי",      f"${total_val_pt:,.0f}",  "#e6edf3"),
            (sc2, "עלות מקורית",     f"${total_cost_pt:,.0f}", "#8b949e"),
            (sc3, "רווח/הפסד ($)",   f"${total_val_pt-total_cost_pt:+,.0f}", ret_clr),
            (sc4, "תשואה כוללת",     f"{total_ret:+.1f}%",     ret_clr),
        ]:
            col_s.markdown(
                f'<div style="background:#161b22;border:1px solid #21262d;border-top:2px solid {clr};'
                f'border-radius:10px;padding:12px;text-align:center;">'
                f'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;margin-bottom:3px;">{lbl}</div>'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;font-weight:700;color:{clr};">{val}</div>'
                f'</div>', unsafe_allow_html=True
            )

        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

        # ── Pie chart ──
        pc1, pc2 = st.columns([1, 2])
        with pc1:
            fig_pie = go.Figure(go.Pie(
                labels=[r["sym"] for r in rows_pt],
                values=[r["val"] for r in rows_pt],
                hole=0.55,
                marker=dict(colors=["#388bfd","#3fb950","#f0883e","#bc8cff","#f85149","#d29922"]),
                textinfo='label+percent',
                textfont=dict(size=11, color='#e6edf3'),
            ))
            fig_pie.update_layout(
                height=260, paper_bgcolor=BG, plot_bgcolor=BG,
                margin=dict(l=0,r=0,t=20,b=0),
                showlegend=False,
                font=dict(color='#8b949e'),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # ── Holdings table ──
        with pc2:
            th_s = 'style="background:#0d1117;color:#8b949e;font-size:.64rem;text-transform:uppercase;padding:7px 10px;text-align:right;border-bottom:2px solid #21262d;"'
            headers = ["מניה","שם","כמות","קנייה","עכשיו","שווי","תשואה %","רווח/הפסד","משקל"]
            h_html  = "<tr>" + "".join(f"<th {th_s}>{h}</th>" for h in headers) + "</tr>"
            rows_html_pt = ""
            COLORS_PT = ["#388bfd","#3fb950","#f0883e","#bc8cff","#f85149","#d29922"]
            for i, r in enumerate(rows_pt):
                bg   = "#161b22" if i%2==0 else "#0d1117"
                rc   = "#3fb950" if r["ret_pct"] >= 0 else "#f85149"
                clrs = COLORS_PT[i % len(COLORS_PT)]
                cells = (
                    f'<td style="padding:7px 10px;color:{clrs};font-weight:700;font-size:.78rem;border-bottom:1px solid #21262d;">{r["sym"]}</td>'
                    f'<td style="padding:7px 10px;color:#8b949e;font-size:.72rem;border-bottom:1px solid #21262d;">{r["name"]}</td>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;color:#e6edf3;border-bottom:1px solid #21262d;">{r["qty"]:.0f}</td>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;color:#8b949e;border-bottom:1px solid #21262d;">${r["cost"]:.2f}</td>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;color:#e6edf3;border-bottom:1px solid #21262d;">${r["price"]:.2f}</td>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;color:#e6edf3;border-bottom:1px solid #21262d;">${r["val"]:,.0f}</td>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.78rem;color:{rc};font-weight:600;border-bottom:1px solid #21262d;">{r["ret_pct"]:+.1f}%</td>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;color:{rc};border-bottom:1px solid #21262d;">${r["ret_abs"]:+,.0f}</td>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:.75rem;color:#8b949e;border-bottom:1px solid #21262d;">{r["weight"]:.1f}%</td>'
                )
                rows_html_pt += f'<tr style="background:{bg};">{cells}</tr>'
            st.markdown(
                '<div style="overflow-x:auto;">'
                '<table style="width:100%;border-collapse:collapse;direction:rtl;">'
                f'<thead>{h_html}</thead><tbody>{rows_html_pt}</tbody>'
                '</table></div>', unsafe_allow_html=True
            )

        # ── Remove buttons ──
        st.markdown('<hr style="margin:12px 0 8px;"/>', unsafe_allow_html=True)
        st.markdown('<div style="color:#8b949e;font-size:.72rem;margin-bottom:6px;">הסרת מניה מהתיק:</div>', unsafe_allow_html=True)
        rem_cols = st.columns(len(rows_pt))
        for i, r in enumerate(rows_pt):
            if rem_cols[i].button(f"🗑 {r['sym']}", key=f"rm_{i}_{r['sym']}"):
                st.session_state.portfolio_positions.pop(i)
                st.rerun()


# ════════════════════════════════════════
# TAB 11 — 🔔 Price Alerts
# ════════════════════════════════════════
with t11:
    st.markdown(
        '<div style="direction:rtl;margin-bottom:12px;">'
        '<div style="font-size:1rem;font-weight:800;color:#e6edf3;margin-bottom:4px;">🔔 Price Alerts — התראות מחיר</div>'
        '<div style="color:#8b949e;font-size:.78rem;">הגדרי התראה — האפליקציה תבדוק כל דקה ותודיע לך</div>'
        '</div>', unsafe_allow_html=True
    )

    if 'alerts_list' not in st.session_state:
        st.session_state.alerts_list = []

    # ── Add alert ──
    al1, al2, al3, al4 = st.columns([2, 2, 2, 1])
    with al1: al_sym  = st.text_input("מניה", value=ticker, key="al_sym").upper().strip()
    with al2: al_cond = st.selectbox("תנאי", ["מחיר עולה מעל", "מחיר יורד מתחת"], key="al_cond")
    with al3: al_price= st.number_input("מחיר יעד ($)", min_value=0.01, value=float(cp), key="al_price")
    with al4:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        if st.button("➕ הוסף", key="al_add", type="primary"):
            if al_sym:
                st.session_state.alerts_list.append({
                    "sym": al_sym, "cond": al_cond,
                    "target": al_price, "triggered": False, "active": True
                })
                st.rerun()

    # ── Check alerts ──
    if st.session_state.alerts_list:
        triggered_alerts = []
        for i, alt in enumerate(st.session_state.alerts_list):
            if not alt["active"]: continue
            cur = get_live_price(alt["sym"])
            if cur:
                hit = (alt["cond"] == "מחיר עולה מעל" and cur >= alt["target"]) or \
                      (alt["cond"] == "מחיר יורד מתחת" and cur <= alt["target"])
                st.session_state.alerts_list[i]["current"] = cur
                if hit:
                    st.session_state.alerts_list[i]["triggered"] = True
                    triggered_alerts.append(alt)

        # ── Show triggered ──
        for alt in triggered_alerts:
            st.markdown(
                f'<div style="background:rgba(63,185,80,.1);border:2px solid rgba(63,185,80,.4);'
                f'border-radius:10px;padding:12px 16px;margin-bottom:8px;direction:rtl;">'
                f'<div style="color:#3fb950;font-size:.9rem;font-weight:700;">'
                f'🎯 התראה הופעלה! {alt["sym"]} — {alt["cond"]} {alt["target"]}</div>'
                f'<div style="color:#8b949e;font-size:.75rem;">מחיר נוכחי: ${alt.get("current",0):.2f}</div>'
                f'</div>', unsafe_allow_html=True
            )

        # ── Alerts table ──
        st.markdown("#### רשימת התראות")
        for i, alt in enumerate(st.session_state.alerts_list):
            cur     = alt.get("current", 0)
            is_trig = alt["triggered"]
            is_act  = alt["active"]
            border  = "#3fb950" if is_trig else ("#388bfd" if is_act else "#30363d")
            status  = "✅ הופעלה" if is_trig else ("⏳ פעילה" if is_act else "⏸ כבויה")
            dist    = ((cur - alt["target"]) / alt["target"] * 100) if cur and alt["target"] else 0

            ac1, ac2 = st.columns([4, 1])
            with ac1:
                st.markdown(
                    f'<div style="background:#161b22;border:1px solid {border};border-radius:10px;'
                    f'padding:11px 14px;margin-bottom:6px;direction:rtl;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<span style="color:#e6edf3;font-weight:700;font-size:.85rem;">{alt["sym"]}</span>'
                    f'<span style="color:#8b949e;font-size:.75rem;margin-right:8px;"> — {alt["cond"]} </span>'
                    f'<span style="font-family:JetBrains Mono,monospace;color:#e6edf3;font-size:.85rem;">${alt["target"]:.2f}</span>'
                    f'</div>'
                    f'<div style="text-align:left;">'
                    f'<div style="color:#8b949e;font-size:.68rem;">עכשיו: ${cur:.2f}</div>'
                    f'<div style="color:#8b949e;font-size:.68rem;">מרחק: {dist:+.1f}%</div>'
                    f'</div></div>'
                    f'<div style="color:{"#3fb950" if is_trig else "#388bfd"};font-size:.72rem;margin-top:4px;">{status}</div>'
                    f'</div>', unsafe_allow_html=True
                )
            with ac2:
                if st.button("🗑", key=f"del_alt_{i}"):
                    st.session_state.alerts_list.pop(i)
                    save_user_data()
                    st.rerun()
    else:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            'padding:40px;text-align:center;">'
            '<div style="font-size:2rem;">🔔</div>'
            '<div style="color:#8b949e;margin-top:8px;">אין התראות פעילות — הגדרי אחת למעלה</div>'
            '</div>', unsafe_allow_html=True
        )


# ════════════════════════════════════════
# TAB 12 — 📅 Earnings Calendar
# ════════════════════════════════════════
with t12:
    st.markdown(
        '<div style="direction:rtl;margin-bottom:12px;">'
        '<div style="font-size:1rem;font-weight:800;color:#e6edf3;margin-bottom:4px;">📅 Earnings Calendar — לוח דוחות</div>'
        '<div style="color:#8b949e;font-size:.78rem;">תאריכי פרסום דוחות רבעוניים של המניות שאת עוקבת אחריהן</div>'
        '</div>', unsafe_allow_html=True
    )

    if 'ec_symbols' not in st.session_state:
        st.session_state.ec_symbols = [ticker]

    ec1, ec2 = st.columns([4, 1])
    with ec1:
        ec_new = st.text_input("הוסיפי מניה ללוח", placeholder="לדוג: AMZN", key="ec_new").upper().strip()
    with ec2:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        if st.button("➕ הוסף", key="ec_add"):
            if ec_new and ec_new not in st.session_state.ec_symbols:
                st.session_state.ec_symbols.append(ec_new)
                save_user_data()
                st.rerun()

    # Chips
    chips_html = ""
    for i, s in enumerate(st.session_state.ec_symbols):
        chips_html += (
            f'<span style="background:#21262d;border:1px solid #30363d;border-radius:20px;'
            f'padding:3px 10px;font-size:.75rem;color:#c9d1d9;margin-left:5px;">{s}</span>'
        )
    st.markdown(f'<div style="margin-bottom:10px;direction:rtl;">{chips_html}</div>', unsafe_allow_html=True)

    with st.spinner("טוען מידע..."):
        ec_rows = []
        for sym_ec in st.session_state.ec_symbols:
            try:
                inf_ec = load_info(sym_ec)
                # next earnings date
                ned = inf_ec.get("earningsDate") or inf_ec.get("earningsTimestamp")
                if isinstance(ned, (list, tuple)): ned = ned[0] if ned else None
                if ned:
                    try:
                        import datetime as dt2
                        if isinstance(ned, (int,float)):
                            ned_dt = dt2.datetime.fromtimestamp(ned)
                        else:
                            ned_dt = pd.Timestamp(ned).to_pydatetime()
                        days_left = (ned_dt.date() - dt2.date.today()).days
                        date_str  = ned_dt.strftime("%d/%m/%Y")
                    except:
                        date_str = "—"; days_left = 9999
                else:
                    date_str = "לא ידוע"; days_left = 9999

                ec_rows.append({
                    "sym":       sym_ec,
                    "name":      (inf_ec.get("shortName","") or "")[:20],
                    "date":      date_str,
                    "days_left": days_left,
                    "eps_est":   inf_ec.get("forwardEps","—"),
                    "rev_est":   inf_ec.get("revenueEstimate","—"),
                    "sector":    inf_ec.get("sector","—") or "—",
                })
            except: pass

    ec_rows.sort(key=lambda x: x["days_left"])

    if ec_rows:
        th_s = 'style="background:#0d1117;color:#8b949e;font-size:.64rem;text-transform:uppercase;padding:8px 12px;text-align:right;border-bottom:2px solid #21262d;"'
        h_html = "<tr>" + "".join(f"<th {th_s}>{h}</th>" for h in ["מניה","שם","תאריך דוח","ימים","EPS תחזית","סקטור"]) + "</tr>"
        rows_ec_html = ""
        for i, r in enumerate(ec_rows):
            bg = "#161b22" if i%2==0 else "#0d1117"
            days = r["days_left"]
            if days <= 7:    dc = "#f85149"; dtxt = f"⚠️ {days} ימים"
            elif days <= 30: dc = "#d29922"; dtxt = f"📅 {days} ימים"
            elif days == 9999: dc = "#8b949e"; dtxt = "—"
            else:             dc = "#8b949e";  dtxt = f"{days} ימים"

            eps_str = f"${float(r['eps_est']):.2f}" if r['eps_est'] and r['eps_est'] != "—" else "—"
            rows_ec_html += (
                f'<tr style="background:{bg};">'
                f'<td style="padding:8px 12px;font-weight:700;color:#388bfd;font-size:.8rem;border-bottom:1px solid #21262d;">{r["sym"]}</td>'
                f'<td style="padding:8px 12px;color:#8b949e;font-size:.75rem;border-bottom:1px solid #21262d;">{r["name"]}</td>'
                f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-size:.78rem;color:#e6edf3;border-bottom:1px solid #21262d;">{r["date"]}</td>'
                f'<td style="padding:8px 12px;font-size:.78rem;color:{dc};font-weight:600;border-bottom:1px solid #21262d;">{dtxt}</td>'
                f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-size:.78rem;color:#3fb950;border-bottom:1px solid #21262d;">{eps_str}</td>'
                f'<td style="padding:8px 12px;color:#8b949e;font-size:.72rem;border-bottom:1px solid #21262d;">{r["sector"]}</td>'
                f'</tr>'
            )
        st.markdown(
            '<div style="overflow-x:auto;">'
            '<table style="width:100%;border-collapse:collapse;direction:rtl;">'
            f'<thead>{h_html}</thead><tbody>{rows_ec_html}</tbody>'
            '</table></div>',
            unsafe_allow_html=True
        )
        st.markdown('<div style="color:#8b949e;font-size:.65rem;margin-top:8px;">⚠️ תאריכים משוערים — תמיד בדקי מול המקור הרשמי</div>', unsafe_allow_html=True)

    # Remove chips
    if len(st.session_state.ec_symbols) > 1:
        st.markdown('<hr style="margin:10px 0 6px;"/>', unsafe_allow_html=True)
        rem_c = st.columns(len(st.session_state.ec_symbols))
        for i, s in enumerate(st.session_state.ec_symbols):
            if rem_c[i].button(f"🗑 {s}", key=f"ec_rm_{i}"):
                st.session_state.ec_symbols.pop(i)
                st.rerun()


# ════════════════════════════════════════
# TAB 13 — 👁️ Watchlist
# ════════════════════════════════════════
with t13:
    st.markdown(
        '<div style="direction:rtl;margin-bottom:12px;">'
        '<div style="font-size:1rem;font-weight:800;color:#e6edf3;margin-bottom:4px;">👁️ Watchlist — רשימת מעקב</div>'
        '<div style="color:#8b949e;font-size:.78rem;">מניות שאת עוקבת אחריהן — עם ציון ניתוח, מחיר ומגמה</div>'
        '</div>', unsafe_allow_html=True
    )

    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = [ticker]

    wl1, wl2 = st.columns([4, 1])
    with wl1:
        wl_new = st.text_input("הוסיפי מניה לרשימה", placeholder="לדוג: GOOGL", key="wl_new").upper().strip()
    with wl2:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        if st.button("➕ הוסף", key="wl_add", type="primary"):
            if wl_new and wl_new not in st.session_state.watchlist:
                st.session_state.watchlist.append(wl_new)
                save_user_data()
                st.rerun()

    if st.button("🔄 רענן ציונות", key="wl_refresh"):
        st.rerun()

    if not st.session_state.watchlist:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;'
            'padding:40px;text-align:center;">'
            '<div style="font-size:2rem;">👁️</div>'
            '<div style="color:#8b949e;margin-top:8px;">הרשימה ריקה — הוסיפי מניות למעלה</div>'
            '</div>', unsafe_allow_html=True
        )
    else:
        with st.spinner("מנתח מניות..."):
            wl_rows = []
            for sym_wl in st.session_state.watchlist:
                try:
                    df_wl  = load_ohlcv(sym_wl, "3M", "1d")
                    inf_wl = load_info(sym_wl)
                    if df_wl is None or len(df_wl) < 5: continue

                    price_wl = float(df_wl['Close'].iloc[-1])
                    prev_wl  = float(df_wl['Close'].iloc[-2])
                    chg_wl   = (price_wl - prev_wl) / prev_wl * 100

                    # quick scores
                    f_wl = calc_fundamental_score(inf_wl)
                    t_wl = calc_technical_score(df_wl)
                    dec_wl = calc_weighted_decision(f_wl.get("score"), t_wl.get("score"))

                    # trend
                    ma50_wl = float(df_wl['MA50'].iloc[-1]) if 'MA50' in df_wl.columns else price_wl
                    trend_wl = "🟢 שורי" if price_wl > ma50_wl else "🔴 דובי"

                    # rsi
                    rsi_wl = float(df_wl['RSI'].iloc[-1]) if 'RSI' in df_wl.columns else 50

                    wl_rows.append({
                        "sym":      sym_wl,
                        "name":     (inf_wl.get("shortName","") or "")[:18],
                        "price":    price_wl,
                        "chg":      chg_wl,
                        "rsi":      rsi_wl,
                        "trend":    trend_wl,
                        "f_score":  f_wl.get("score"),
                        "t_score":  t_wl.get("score"),
                        "decision": dec_wl.get("decision","—"),
                        "dec_clr":  dec_wl.get("color","#8b949e"),
                        "dec_icon": dec_wl.get("icon","⚪"),
                        "weighted": dec_wl.get("weighted",0) or 0,
                    })
                except: pass

        if not wl_rows:
            st.warning("לא ניתן לטעון נתונים")
        else:
            # ── Cards grid ──
            for i in range(0, len(wl_rows), 3):
                chunk = wl_rows[i:i+3]
                wcols = st.columns(3)
                for j, r in enumerate(chunk):
                    chg_c = "#3fb950" if r["chg"] >= 0 else "#f85149"
                    rsi_c = "#f85149" if r["rsi"] >= 70 else ("#3fb950" if r["rsi"] <= 30 else "#8b949e")
                    bar_w = r["weighted"]
                    dec_c = r["dec_clr"]

                    wcols[j].markdown(
                        f'<div style="background:#161b22;border:1px solid #21262d;'
                        f'border-top:2px solid {dec_c};border-radius:12px;padding:14px 16px;">'

                        # header
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
                        f'<div>'
                        f'<div style="font-size:.92rem;font-weight:700;color:#e6edf3;">{r["sym"]}</div>'
                        f'<div style="color:#8b949e;font-size:.68rem;">{r["name"]}</div>'
                        f'</div>'
                        f'<div style="text-align:left;">'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:.92rem;font-weight:700;color:#e6edf3;">${r["price"]:.2f}</div>'
                        f'<div style="color:{chg_c};font-size:.72rem;font-weight:600;">{r["chg"]:+.2f}%</div>'
                        f'</div></div>'

                        # scores row
                        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;margin-bottom:8px;">'
                        f'<div style="background:#0d1117;border-radius:6px;padding:5px;text-align:center;">'
                        f'<div style="color:#8b949e;font-size:.55rem;text-transform:uppercase;">פונד׳</div>'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#388bfd;">{r["f_score"] or "—"}</div>'
                        f'</div>'
                        f'<div style="background:#0d1117;border-radius:6px;padding:5px;text-align:center;">'
                        f'<div style="color:#8b949e;font-size:.55rem;text-transform:uppercase;">טכני</div>'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#3fb950;">{r["t_score"] or "—"}</div>'
                        f'</div>'
                        f'<div style="background:#0d1117;border-radius:6px;padding:5px;text-align:center;">'
                        f'<div style="color:#8b949e;font-size:.55rem;text-transform:uppercase;">RSI</div>'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:{rsi_c};">{r["rsi"]:.0f}</div>'
                        f'</div></div>'

                        # trend + decision
                        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
                        f'<span style="font-size:.72rem;">{r["trend"]}</span>'
                        f'<span style="background:{dec_c}22;color:{dec_c};border:1px solid {dec_c}55;'
                        f'border-radius:20px;padding:2px 8px;font-size:.68rem;font-weight:700;">'
                        f'{r["dec_icon"]} {r["decision"]}</span>'
                        f'</div>'

                        # score bar
                        f'<div style="height:4px;background:#21262d;border-radius:2px;overflow:hidden;">'
                        f'<div style="height:100%;width:{bar_w}%;background:{dec_c};border-radius:2px;"></div>'
                        f'</div>'
                        f'<div style="color:#8b949e;font-size:.6rem;text-align:center;margin-top:3px;">{bar_w}/100</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    # click to navigate
                    if wcols[j].button(f"📈 פתח {r['sym']}", key=f"wl_open_{i}_{j}"):
                        st.session_state.ticker = r["sym"]
                        st.session_state.ai_res = None
                        st.rerun()

            # Remove
            st.markdown('<hr style="margin:10px 0 6px;"/>', unsafe_allow_html=True)
            rem_wl = st.columns(min(len(st.session_state.watchlist), 6))
            for i, s in enumerate(st.session_state.watchlist[:6]):
                if rem_wl[i].button(f"🗑 {s}", key=f"wl_rm_{i}"):
                    st.session_state.watchlist.pop(i)
                    save_user_data()
                    st.rerun()
