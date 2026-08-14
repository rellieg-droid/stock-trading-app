import yfinance as yf

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

SYM = "NVDA"
print(f"{'label':<6}{'period':<7}{'interval':<9}{'rows':>6}  last")
print("-" * 52)
for label, (p, i) in PERIODS.items():
    try:
        df = yf.Ticker(SYM).history(period=p, interval=i, auto_adjust=True)
        if df is None or df.empty:
            print(f"{label:<6}{p:<7}{i:<9}{'EMPTY':>6}  ❌")
        else:
            last = str(df.index[-1])[:16]
            print(f"{label:<6}{p:<7}{i:<9}{len(df):>6}  {last}  ✅")
    except Exception as e:
        print(f"{label:<6}{p:<7}{i:<9}{'ERR':>6}  ❌ {type(e).__name__}: {e}")