# -*- coding: utf-8 -*-
"""
strategy_data.py
================
מתאם הנתונים בין yfinance לבין strategy_engine.

עקרון מנחה אחד: **אין נפילה שקטה.**
כל שדה שלא נמשך מסומן ב-DataDiagnostics עם סיבה מפורשת, ונשלח למנוע
כ-None. המנוע יחזיר "אין נתון" ו-"?" בטבלה במקום להעמיד פנים שיש מידע.
זה בדיוק הכשל שכבר נתפס פעם בפותר ה-IV: fallback שקט לתנודתיות היסטורית.

הקובץ הזה הוא היחיד שנוגע ברשת. strategy_engine.py נשאר טהור.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

import strategy_engine as se

__version__ = "0.4.0"

BENCHMARK = "^GSPC"
VIX_SYMBOL = "^VIX"
LOOKBACK_PERIOD = "1y"      # מחרוזת תקנית של yfinance. לא "12M", לא "1Y".
LOOKBACK_INTERVAL = "1d"
IV_MIN_DTE = 20
IV_MAX_DTE = 60


# ---------------------------------------------------------------------------
# עטיפת קאש — עובדת גם בלי Streamlit, כדי שהמודול יהיה בר-בדיקה
# ---------------------------------------------------------------------------

try:
    import streamlit as st
    _cache = st.cache_data(ttl=900, show_spinner=False)
except Exception:  # pragma: no cover
    def _cache(fn):
        return fn


# ---------------------------------------------------------------------------
# אבחון
# ---------------------------------------------------------------------------

@dataclass
class DataDiagnostics:
    """מה נמשך, מה נכשל ולמה. מוצג ב-UI, לא נבלע."""
    ok: dict[str, bool] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)

    def mark(self, key: str, success: bool, reason: str = "") -> None:
        self.ok[key] = success
        if not success:
            self.reasons[key] = reason or "סיבה לא ידועה"

    @property
    def failures(self) -> list[str]:
        return [f"{k}: {self.reasons[k]}" for k, v in self.ok.items() if not v]

    def to_table(self) -> pd.DataFrame:
        labels = {
            "prices": "מחירי המניה",
            "benchmark": "מדד ייחוס (S&P 500)",
            "vix": "VIX",
            "earnings": "תאריך דוח",
            "iv": "IV משרשרת האופציות",
        }
        return pd.DataFrame(
            [
                {
                    "מקור": labels.get(k, k),
                    "סטטוס": "V" if v else "X",
                    "הערה": self.reasons.get(k, ""),
                }
                for k, v in self.ok.items()
            ]
        )


# ---------------------------------------------------------------------------
# משיכות בסיס
# ---------------------------------------------------------------------------

@_cache
def fetch_history(symbol: str, period: str = LOOKBACK_PERIOD,
                  interval: str = LOOKBACK_INTERVAL) -> Optional[pd.DataFrame]:
    """OHLCV גולמי. מחזיר None במפורש במקום DataFrame ריק."""
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval,
                                       auto_adjust=True)
    except Exception:
        return None
    if df is None or df.empty or "Close" not in df.columns:
        return None
    return df.dropna(subset=["Close"])


@_cache
def fetch_vix() -> Optional[float]:
    df = fetch_history(VIX_SYMBOL, period="5d", interval="1d")
    if df is None or df.empty:
        return None
    value = float(df["Close"].iloc[-1])
    return value if math.isfinite(value) else None


@_cache
def fetch_days_to_earnings(symbol: str) -> Optional[int]:
    """
    מחזיר ימים עד הדוח הבא, או None אם אין מידע.
    yfinance מחזיר כאן שלוש צורות שונות בגרסאות שונות, לכן שלושת הענפים.
    """
    try:
        cal = yf.Ticker(symbol).calendar
    except Exception:
        return None

    raw = None
    if isinstance(cal, dict):
        raw = cal.get("Earnings Date")
    elif isinstance(cal, pd.DataFrame) and not cal.empty:
        if "Earnings Date" in cal.index:
            raw = cal.loc["Earnings Date"].iloc[0]
        elif "Earnings Date" in cal.columns:
            raw = cal["Earnings Date"].iloc[0]

    if raw is None:
        return None
    if isinstance(raw, (list, tuple, np.ndarray, pd.Series)):
        raw = list(raw)[0] if len(raw) else None
    if raw is None:
        return None

    try:
        when = pd.Timestamp(raw).date()
    except Exception:
        return None

    delta = (when - date.today()).days
    return delta if delta >= 0 else None


@_cache
def fetch_atm_iv(symbol: str) -> Optional[float]:
    """
    IV נוכחי בכסף, חציון של קולים ופוטים סביב הספוט, בתפוגה 20-60 ימים.
    זהו IV נקודתי בלבד. אין כאן היסטוריה ולכן אין IV Rank אמיתי.
    """
    try:
        tk = yf.Ticker(symbol)
        expirations = list(tk.options or [])
        if not expirations:
            return None

        spot_df = fetch_history(symbol, period="5d", interval="1d")
        if spot_df is None or spot_df.empty:
            return None
        spot = float(spot_df["Close"].iloc[-1])

        today = datetime.today().date()
        candidates = []
        for exp in expirations:
            dte = (pd.Timestamp(exp).date() - today).days
            if IV_MIN_DTE <= dte <= IV_MAX_DTE:
                candidates.append((abs(dte - 35), exp))
        if not candidates:
            return None
        expiry = min(candidates)[1]

        chain = tk.option_chain(expiry)
        frames = []
        for side in (chain.calls, chain.puts):
            if side is None or side.empty or "impliedVolatility" not in side:
                continue
            side = side.copy()
            side["_dist"] = (side["strike"] - spot).abs()
            frames.append(side.nsmallest(3, "_dist")["impliedVolatility"])
        if not frames:
            return None

        iv = float(pd.concat(frames).replace(0.0, np.nan).dropna().median())
        return iv if math.isfinite(iv) and 0.0 < iv < 5.0 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# הרכבה
# ---------------------------------------------------------------------------

def build_report(
    ticker: str,
    portfolio_value: float,
    position_pct: float = 0.05,
    risk_profile: str = "medium",
    macro_event: Optional[str] = None,
    benchmark: str = BENCHMARK,
    config: Optional[se.StrategyConfig] = None,
) -> tuple[Optional[se.StrategyReport], DataDiagnostics]:
    """
    מושך הכל, מחשב הכל, מחזיר דוח מלא + אבחון.
    אם אין מחירים למניה מחזיר (None, diagnostics) — זה הכשל היחיד החוסם.
    """
    diag = DataDiagnostics()
    cfg = config or se.StrategyConfig.for_profile(risk_profile)

    # --- מחירי המניה (חובה) ---
    px = fetch_history(ticker)
    if px is None or len(px) < cfg.atr_period + 2:
        diag.mark("prices", False, f"אין מספיק נתוני מחיר עבור {ticker}")
        return None, diag
    diag.mark("prices", True)

    price = float(px["Close"].iloc[-1])
    atr_series = se.atr_wilder(px["High"], px["Low"], px["Close"], cfg.atr_period)
    atr = float(atr_series.dropna().iloc[-1]) if not atr_series.dropna().empty else float("nan")

    hv = se.annualized_vol(px["Close"], window=cfg.hv_window)
    hv_rank_value = se.hv_rank(px["Close"], window=cfg.hv_window,
                               lookback=cfg.hv_lookback)
    hv_pct_value = se.hv_percentile(px["Close"], window=cfg.hv_window,
                                    lookback=cfg.hv_lookback)
    if not math.isfinite(hv_pct_value):
        hv_pct_value = None
    if not math.isfinite(hv_rank_value):
        diag.mark("prices", False, "לא ניתן לחשב HV Rank — פחות מדי ימי מסחר")

    # --- מדד ייחוס ---
    bench = fetch_history(benchmark)
    if bench is None:
        diag.mark("benchmark", False, f"{benchmark} לא נטען")
        rel_std = None
        rel_std_rank = None
        rel_std_pct = None
    else:
        diag.mark("benchmark", True)
        rel_std = se.relative_std(px["Close"], bench["Close"], cfg.hv_lookback)
        if not math.isfinite(rel_std):
            diag.mark("benchmark", False, "יחס סטיות התקן לא ניתן לחישוב")
            rel_std = None
        rel_std_rank = se.relative_vol_rank(px["Close"], bench["Close"],
                                            window=cfg.hv_window,
                                            lookback=cfg.hv_lookback)
        rel_std_pct = se.relative_vol_percentile(px["Close"], bench["Close"],
                                                 window=cfg.hv_window,
                                                 lookback=cfg.hv_lookback)
        if not math.isfinite(rel_std_pct):
            rel_std_pct = None
        if not math.isfinite(rel_std_rank):
            diag.mark("benchmark", False,
                      "אין מספיק היסטוריה משותפת לדירוג — נופלים להשוואה מוחלטת")
            rel_std_rank = None

    # --- VIX ---
    vix = fetch_vix()
    diag.mark("vix", vix is not None, "VIX לא נטען")

    # --- דוח רווחים ---
    dte = fetch_days_to_earnings(ticker)
    diag.mark("earnings", dte is not None,
              "אין תאריך דוח ב-yfinance — הקריטריון מניח לוח נקי")

    # --- IV נקודתי ---
    iv = fetch_atm_iv(ticker)
    diag.mark("iv", iv is not None,
              "אין שרשרת אופציות מתאימה — יחס IV/HV לא יוצג")

    report = se.evaluate(
        ticker=ticker,
        price=price,
        atr=atr,
        rel_std=rel_std,
        rel_std_rank=rel_std_rank,
        rel_std_pct=rel_std_pct,
        hv_percentile_value=hv_pct_value,
        hv_rank_value=hv_rank_value,
        vix=vix,
        days_to_earnings=dte,
        macro_event=macro_event,
        iv=iv,
        hv=hv,
        portfolio_value=portfolio_value,
        position_pct=position_pct,
        risk_profile=risk_profile,
        config=cfg,
    )

    for f in diag.failures:
        report.notes.append(f"נתון חסר — {f}")

    return report, diag


# ---------------------------------------------------------------------------
# הרצה ידנית מהטרמינל: py strategy_data.py NVDA
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sym = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    rep, dg = build_report(sym, portfolio_value=100_000, position_pct=0.05)

    print("\n=== אבחון מקורות ===")
    print(dg.to_table().to_string(index=False))

    if rep is None:
        print("\nלא ניתן להפיק דוח.")
        sys.exit(1)

    print(f"\n=== {rep.ticker} ===")
    print(rep.headline)
    print(rep.flavor)
    print()
    print(rep.to_table().to_string(index=False))
    if rep.position:
        p = rep.position
        print(f"\nכניסה {p.entry_price:.2f} | Stop {p.stop_price:.2f} "
              f"({p.stop_pct:.1f}%) | TP {p.take_profit_price:.2f}")
        print(f"מניות: {p.final_shares} | הון בסיכון: "
              f"{p.capital_at_risk:,.0f} ({p.capital_at_risk_pct:.2f}% מהתיק)")
    for n in rep.notes:
        print(f"  • {n}")
