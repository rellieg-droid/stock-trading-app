# -*- coding: utf-8 -*-
"""
strategy_engine.py
==================
מנוע "הציון המשולב" — מודל קבלת החלטות לכניסה ללונג על בסיס תנודתיות.

עקרונות:
    * מודול טהור. אין כאן yfinance, אין Streamlit, אין קריאות רשת.
      כל הנתונים נכנסים כפרמטרים, כל התוצאות יוצאות כ-dataclasses.
    * self-contained בכוונה — אותו קובץ בדיוק נמצא בשני הפרויקטים.
      אם משנים אותו, מעלים __version__ ומסנכרנים את שני העותקים.
    * ה-UI אחראי לעיצוב בלבד. כל הלוגיקה והטקסטים כאן.

מקור הנתונים לשלב 2 (תנודתיות):
    IV Rank אמיתי דורש היסטוריית IV יומית לשנה, שלא קיימת ב-yfinance.
    לכן המנוע מחשב HV Rank (אחוזון תנודתיות ממומשת) ומסמן אותו
    כפרוקסי (is_proxy=True). ה-UI חייב להציג את התווית הזו.

__version__: 0.4.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
import pandas as pd

__version__ = "0.4.0"

TRADING_DAYS = 252


# ---------------------------------------------------------------------------
# 1. תצורה
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrategyConfig:
    """ספי ההחלטה. משתנים לפי פרופיל הסיכון."""

    risk_profile: str = "medium"          # low | medium | high

    # שלב 1 — תנודתיות יחסית ומרחק נשימה
    max_relative_std: float = 1.5         # fallback בלבד, כשאין דירוג
    high_risk_relative_std: float = 2.0   # מעל זה = סיכון גבוה מוצהר
    rel_vol_rank_pass_max: float = 60.0   # אחוזון התנודתיות היחסית מול עצמה
    rel_vol_rank_calm: float = 25.0       # מתחת לזה = שקטה מהרגיל
    atr_stop_multiplier: float = 2.0      # מרחק נשימה ל-Stop Loss
    atr_period: int = 14

    # שלב 2 — HV Rank
    hv_window: int = 21                   # ימי מסחר לחישוב HV נקודתי
    hv_lookback: int = TRADING_DAYS       # חלון הדירוג
    hv_rank_cheap: float = 20.0           # מתחת לזה = שוק רגוע
    hv_rank_pass_max: float = 50.0        # מעל זה = כישלון קריטריון
    hv_rank_stretched: float = 70.0       # מעל זה = מתוח
    iv_hv_ratio_rich: float = 1.30        # IV גבוה מ-HV ביותר מ-30% = יקר
    iv_hv_ratio_cheap: float = 0.85       # IV נמוך מהתנודתיות בפועל = השוק מפגר

    # שלב 3 — מאקרו
    vix_calm: float = 15.0
    vix_max: float = 22.0                 # סף המעבר לכישלון קריטריון
    vix_panic: float = 30.0               # וטו

    # שלב 3ב — לוח אירועים
    earnings_blackout_days: int = 7       # וטו אם דוח קרוב מזה
    earnings_horizon_days: int = 35       # אופק עסקה טיפוסי. דוח בתוכו = אזהרה, לא כישלון

    # ניהול סיכון
    max_risk_pct: float = 0.01            # כלל ה-1% על התיק
    reduced_size_factor: float = 0.5      # גודל פוזיציה כש-3/4

    @classmethod
    def for_profile(cls, risk_profile: str) -> "StrategyConfig":
        p = (risk_profile or "medium").strip().lower()
        if p in ("low", "נמוכה", "conservative"):
            return cls(
                risk_profile="low",
                max_relative_std=1.2,
                rel_vol_rank_pass_max=40.0,
                atr_stop_multiplier=2.5,
                hv_rank_pass_max=35.0,
                vix_max=18.0,
                earnings_blackout_days=10,
            )
        if p in ("high", "גבוהה", "aggressive"):
            return cls(
                risk_profile="high",
                max_relative_std=2.5,
                rel_vol_rank_pass_max=80.0,
                atr_stop_multiplier=1.5,
                hv_rank_pass_max=70.0,
                vix_max=30.0,
                earnings_blackout_days=3,
            )
        return cls(risk_profile="medium")


# ---------------------------------------------------------------------------
# 2. מבני פלט
# ---------------------------------------------------------------------------

@dataclass
class Criterion:
    """שורה אחת בטבלת הסיכום."""
    key: str
    label: str            # עמודה 1 — אינדיקטור
    optimal: str          # עמודה 2 — מצב אופטימלי ללונג
    current: str          # עמודה 3 — המצב הנוכחי
    passed: Optional[bool]  # עמודה 4 — V / X (None = אין נתון)
    meaning: str          # עמודה 5 — מה זה מלמד אותך
    value: Optional[float] = None
    is_proxy: bool = False

    @property
    def mark(self) -> str:
        if self.passed is None:
            return "?"
        return "V" if self.passed else "X"


@dataclass
class PositionPlan:
    """תרגום ההחלטה לגדלים בפועל."""
    entry_price: float
    stop_price: float
    stop_distance: float
    stop_pct: float
    take_profit_price: float
    risk_per_share: float
    max_shares_by_risk: int
    intended_shares: int
    final_shares: int
    capital_used: float
    capital_at_risk: float
    capital_at_risk_pct: float


@dataclass
class StrategyReport:
    ticker: str
    criteria: list[Criterion]
    passed_count: int
    total_count: int
    verdict: str            # INVEST | INVEST_REDUCED | WAIT | AVOID
    verdict_label: str
    headline: str
    flavor: str
    position: Optional[PositionPlan] = None
    vetoes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def score_text(self) -> str:
        return f"{self.passed_count}/{self.total_count}"

    def to_table(self) -> pd.DataFrame:
        """טבלת הסיכום התקנית, מוכנה ל-st.dataframe."""
        return pd.DataFrame(
            [
                {
                    "אינדיקטור": c.label,
                    "מצב אופטימלי (לונג)": c.optimal,
                    "המצב הנוכחי": c.current,
                    "עמידה": c.mark,
                    "מה זה מלמד אותך": c.meaning,
                }
                for c in self.criteria
            ]
        )


# ---------------------------------------------------------------------------
# 3. מתמטיקה — תנודתיות
# ---------------------------------------------------------------------------

def _as_series(x: Sequence[float] | pd.Series) -> pd.Series:
    s = x if isinstance(x, pd.Series) else pd.Series(list(x), dtype="float64")
    return s.astype("float64").dropna()


def true_range(high, low, close) -> pd.Series:
    """True Range קלאסי. סוגר פערי לילה, בניגוד ל-High-Low נאיבי."""
    h, l, c = _as_series(high), _as_series(low), _as_series(close)
    prev_close = c.shift(1)
    tr = pd.concat(
        [(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def atr_wilder(high, low, close, period: int = 14) -> pd.Series:
    """ATR עם החלקה אקספוננציאלית של Wilder (alpha = 1/period)."""
    tr = true_range(high, low, close)
    if len(tr) < 2:
        return pd.Series(dtype="float64")
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def annualized_vol(closes, window: Optional[int] = None) -> float:
    """סטיית תקן שנתית של תשואות לוגריתמיות."""
    c = _as_series(closes)
    if window is not None:
        c = c.tail(window + 1)
    rets = np.log(c / c.shift(1)).dropna()
    if len(rets) < 2:
        return float("nan")
    return float(rets.std(ddof=1) * math.sqrt(TRADING_DAYS))


def rolling_hv(closes, window: int = 21) -> pd.Series:
    """סדרת HV מתגלגלת, מנורמלת לשנה."""
    c = _as_series(closes)
    rets = np.log(c / c.shift(1))
    return rets.rolling(window).std(ddof=1) * math.sqrt(TRADING_DAYS)


def hv_rank(closes, window: int = 21, lookback: int = TRADING_DAYS) -> float:
    """
    אחוזון ה-HV הנוכחי בתוך חלון הדירוג. 0 = השקט ביותר בשנה, 100 = הסוער ביותר.
    זהו הפרוקסי ל-IV Rank. לא אותו מדד, אבל מתואם ומחושב מנתונים שיש לך.
    """
    series = rolling_hv(closes, window).dropna()
    if len(series) < 2:
        return float("nan")
    hist = series.tail(lookback)
    current = float(hist.iloc[-1])
    lo, hi = float(hist.min()), float(hist.max())
    if not math.isfinite(current) or hi <= lo:
        return float("nan")
    return float((current - lo) / (hi - lo) * 100.0)


def relative_std(stock_closes, benchmark_closes, window: int = TRADING_DAYS) -> float:
    """יחס סטיות התקן בין המניה למדד הייחוס. 2.0 = תנודתית פי 2 מה-S&P."""
    s = annualized_vol(stock_closes, window)
    b = annualized_vol(benchmark_closes, window)
    if not math.isfinite(s) or not math.isfinite(b) or b == 0:
        return float("nan")
    return float(s / b)


def rolling_relative_vol(stock_closes, benchmark_closes,
                         window: int = 21) -> pd.Series:
    """סדרת היחס בין תנודתיות המניה לתנודתיות המדד, יום אחר יום."""
    s = rolling_hv(stock_closes, window)
    b = rolling_hv(benchmark_closes, window)
    joined = pd.concat([s, b], axis=1, join="inner").dropna()
    if joined.empty:
        return pd.Series(dtype="float64")
    ratio = joined.iloc[:, 0] / joined.iloc[:, 1].replace(0.0, np.nan)
    return ratio.replace([np.inf, -np.inf], np.nan).dropna()


def _percentile_of_last(series: pd.Series, lookback: int) -> float:
    """כמה אחוז מהתצפיות בחלון היו נמוכות מהתצפית האחרונה."""
    s = series.dropna()
    if len(s) < 2:
        return float("nan")
    hist = s.tail(lookback)
    current = float(hist.iloc[-1])
    if not math.isfinite(current):
        return float("nan")
    return float((hist < current).sum() / len(hist) * 100.0)


def hv_percentile(closes, window: int = 21, lookback: int = TRADING_DAYS) -> float:
    """
    אחוזון עמיד לחריגים. בניגוד ל-hv_rank שנשען על שני ערכי קצה בלבד,
    כאן יום אחד חריג בשנה לא מעוות את כל הסולם.
    """
    return _percentile_of_last(rolling_hv(closes, window), lookback)


def relative_vol_percentile(stock_closes, benchmark_closes, window: int = 21,
                            lookback: int = TRADING_DAYS) -> float:
    return _percentile_of_last(
        rolling_relative_vol(stock_closes, benchmark_closes, window), lookback)


def relative_vol_rank(stock_closes, benchmark_closes, window: int = 21,
                      lookback: int = TRADING_DAYS) -> float:
    """
    אחוזון התנודתיות היחסית בתוך הטווח השנתי של עצמה.

    זה ההבדל בין "האם זו מניית צמיחה" לבין "האם המניה סוערת מהרגיל".
    מניה שתמיד פי 3 מהמדד תקבל דירוג נמוך כשהיא פי 2.9,
    ודירוג גבוה כשהיא פי 4.2. סיגנל תזמון, לא סיווג.
    """
    ratio = rolling_relative_vol(stock_closes, benchmark_closes, window)
    if len(ratio) < 2:
        return float("nan")
    hist = ratio.tail(lookback)
    current, lo, hi = float(hist.iloc[-1]), float(hist.min()), float(hist.max())
    if not math.isfinite(current) or hi <= lo:
        return float("nan")
    return float((current - lo) / (hi - lo) * 100.0)


# ---------------------------------------------------------------------------
# 4. בוני קריטריונים
# ---------------------------------------------------------------------------

def _fmt(x: Optional[float], suffix: str = "", digits: int = 2) -> str:
    if x is None or not math.isfinite(x):
        return "אין נתון"
    return f"{x:.{digits}f}{suffix}"


def build_atr_criterion(price: float, atr: float, rel_std: Optional[float],
                        cfg: StrategyConfig,
                        rel_std_rank: Optional[float] = None,
                        rel_std_pct: Optional[float] = None) -> Criterion:
    """
    שלב 1. הקריטריון נשען על הדירוג כשהוא קיים, ונופל חזרה
    להשוואה מוחלטת מול המדד רק כשאין מספיק היסטוריה לדירוג.
    """
    atr_pct = (atr / price * 100.0) if (price and math.isfinite(atr)) else float("nan")
    has_pct = rel_std_pct is not None and math.isfinite(rel_std_pct)
    metric = rel_std_pct if has_pct else rel_std_rank
    has_rank = metric is not None and math.isfinite(metric)
    has_abs = rel_std is not None and math.isfinite(rel_std)

    if has_rank:
        passed = metric <= cfg.rel_vol_rank_pass_max
    elif has_abs:
        passed = rel_std <= cfg.max_relative_std
    else:
        passed = None

    parts = []
    if has_abs:
        parts.append(f"פי {rel_std:.2f} מהמדד")
    if rel_std_rank is not None and math.isfinite(rel_std_rank):
        parts.append(f"דירוג {rel_std_rank:.0f}%")
    if has_pct:
        parts.append(f"אחוזון {rel_std_pct:.0f}%")
    if math.isfinite(atr_pct):
        parts.append(f"ATR {atr_pct:.2f}%")
    current = " | ".join(parts) if parts else "אין נתון"

    if passed is None:
        meaning = "אין נתוני מדד ייחוס. אי אפשר לדעת אם התנודתיות חריגה או נורמלית."
    elif has_rank and metric <= cfg.rel_vol_rank_calm:
        meaning = ("המניה שקטה מהרגיל ביחס למדד, בתחתית הטווח השנתי שלה. "
                   "התנועות כרגע קטנות בשבילה.")
    elif has_rank and not passed:
        meaning = ("המניה סוערת מהרגיל ביחס למדד. משהו קורה שלא קרה ברוב השנה, "
                   "וכניסה עכשיו נכנסת לתוך הרעש ולא לפניו.")
    elif has_rank:
        meaning = "התנודתיות היחסית באזור הנורמלי של המניה עצמה. אין כאן חריגה."
    elif passed:
        meaning = "התנודתיות בטווח הסביר מול המדד."
    else:
        meaning = f"מעל הסף שהגדרת לפרופיל {cfg.risk_profile}."

    if has_abs and rel_std >= cfg.high_risk_relative_std:
        meaning += (f" שימי לב: זו מניה תנודתית פי {rel_std:.1f} מהמדד בכל מקרה, "
                    f"ולכן Stop Loss דורש {cfg.atr_stop_multiplier:.1f}×ATR "
                    f"({_fmt(atr_pct * cfg.atr_stop_multiplier, '%')}) מרחק נשימה.")

    optimal = ((f"{'אחוזון' if has_pct else 'דירוג'} מתחת ל-"
                f"{cfg.rel_vol_rank_pass_max:.0f}% מול השנה של המניה")
               if has_rank else f"עד פי {cfg.max_relative_std:.1f} מה-S&P 500")

    return Criterion(
        key="atr",
        label="ATR / תנודתיות יחסית",
        optimal=optimal,
        current=current,
        passed=passed,
        meaning=meaning,
        value=metric if has_rank else rel_std,
    )


def build_hv_rank_criterion(rank: Optional[float], iv: Optional[float],
                            hv: Optional[float], cfg: StrategyConfig,
                            pct: Optional[float] = None) -> Criterion:
    has_pct = pct is not None and math.isfinite(pct)
    metric = pct if has_pct else rank
    passed = None
    if metric is not None and math.isfinite(metric):
        passed = metric <= cfg.hv_rank_pass_max

    ratio = None
    if iv and hv and math.isfinite(iv) and math.isfinite(hv) and hv > 0:
        ratio = iv / hv

    current = f"HV Rank {_fmt(rank, '%', 0)}"
    if has_pct:
        current += f" | אחוזון {pct:.0f}%"
    if ratio is not None:
        current += f" | IV/HV {ratio:.2f}"

    if metric is None or not math.isfinite(metric):
        meaning = "חסרים נתוני מחיר לשנה. בלי זה אין דירוג תנודתיות."
    elif metric <= cfg.hv_rank_cheap:
        meaning = "שוק רגוע. אם משהו עומד להתפרץ, את נכנסת לפני שהמחיר מגלם את זה."
    elif metric >= cfg.hv_rank_stretched:
        meaning = "התנודתיות באחוזון עליון. רוב החדשות כבר בפנים, את קונה יקר."
    else:
        meaning = "אזור אמצע. לא הזדמנות ולא מלכודת, פשוט אין כאן קצה."

    if ratio is not None and ratio >= cfg.iv_hv_ratio_rich:
        meaning += f" השוק מתמחר תנודתיות גבוהה ב-{(ratio - 1) * 100:.0f}% מהמצב בפועל."
    elif ratio is not None and ratio <= cfg.iv_hv_ratio_cheap:
        meaning += (f" שוק האופציות מתמחר תנודתיות נמוכה ב-{(1 - ratio) * 100:.0f}% "
                    f"ממה שקורה בפועל — התמחור מפגר אחרי התנועה.")

    return Criterion(
        key="hv_rank",
        label="HV Rank (פרוקסי ל-IV Rank)",
        optimal=f"מתחת ל-{cfg.hv_rank_pass_max:.0f}% (אידיאלי: מתחת ל-{cfg.hv_rank_cheap:.0f}%)",
        current=current,
        passed=passed,
        meaning=meaning,
        value=metric,
        is_proxy=True,
    )


def build_vix_criterion(vix: Optional[float], cfg: StrategyConfig) -> Criterion:
    passed = None
    if vix is not None and math.isfinite(vix):
        passed = vix <= cfg.vix_max

    if vix is None or not math.isfinite(vix):
        meaning = "אין נתון VIX. אין תמונת מאקרו."
    elif vix < cfg.vix_calm:
        meaning = "שוק רגוע. סביבה שמתאימה למניות צמיחה."
    elif vix >= cfg.vix_panic:
        meaning = "פאניקה. כל מניה זזה עם השוק, לא עם הסיפור שלה."
    elif passed:
        meaning = "מתח סביר. עדיין אפשר לעבוד, אבל בלי להתעלם מהרקע."
    else:
        meaning = "השוק לחוץ. עדיפות למניות ערך יציבות או להמתנה."

    return Criterion(
        key="vix",
        label="VIX",
        optimal=f"מתחת ל-{cfg.vix_max:.0f} (אידיאלי: מתחת ל-{cfg.vix_calm:.0f})",
        current=_fmt(vix, "", 1),
        passed=passed,
        meaning=meaning,
        value=vix,
    )


def build_events_criterion(days_to_earnings: Optional[int], macro_event: Optional[str],
                           cfg: StrategyConfig) -> Criterion:
    passed = None
    if days_to_earnings is None:
        passed = True if macro_event is None else False
    else:
        passed = days_to_earnings > cfg.earnings_blackout_days

    parts = []
    if days_to_earnings is None:
        parts.append("אין דוח ידוע")
    else:
        parts.append(f"דוח בעוד {days_to_earnings} ימים")
    if macro_event:
        parts.append(macro_event)
    current = " | ".join(parts)

    if days_to_earnings is not None and days_to_earnings <= cfg.earnings_blackout_days:
        meaning = ("דוח בפתח. ה-IV מנופח באופן מלאכותי וייקרוס למחרת. "
                   "כניסה עכשיו היא הימור על תוצאה, לא על מגמה.")
    elif macro_event:
        meaning = f"אירוע מאקרו בפתח ({macro_event}). השוק יזוז מסיבה שאין לה קשר למניה."
    elif days_to_earnings is not None and days_to_earnings <= cfg.earnings_horizon_days:
        meaning = (f"מחוץ לחלון החסימה, אבל הדוח ייפול בתוך עסקה באורך רגיל. "
                   f"או שיוצאים לפני יום {days_to_earnings}, או שמחזיקים דרך הדוח ביודעין.")
    else:
        meaning = "לוח האירועים נקי. מה שיקרה במחיר יהיה בגלל המניה עצמה."

    return Criterion(
        key="events",
        label="חדשות ודוחות",
        optimal=f"אין דוח או אירוע מאקרו ב-{cfg.earnings_blackout_days} הימים הקרובים",
        current=current,
        passed=passed,
        meaning=meaning,
        value=float(days_to_earnings) if days_to_earnings is not None else None,
    )


# ---------------------------------------------------------------------------
# 5. גודל פוזיציה
# ---------------------------------------------------------------------------

def build_position_plan(price: float, atr: float, portfolio_value: float,
                        position_pct: float, cfg: StrategyConfig,
                        size_factor: float = 1.0,
                        take_profit_multiplier: float = 3.0) -> Optional[PositionPlan]:
    if not all(math.isfinite(v) for v in (price, atr, portfolio_value)) or price <= 0 or atr <= 0:
        return None

    stop_distance = atr * cfg.atr_stop_multiplier
    stop_price = max(price - stop_distance, 0.0)
    take_profit = price + atr * take_profit_multiplier

    max_risk_cash = portfolio_value * cfg.max_risk_pct
    max_shares_by_risk = int(max_risk_cash // stop_distance)

    intended_cash = portfolio_value * position_pct * size_factor
    intended_shares = int(intended_cash // price)

    final_shares = max(min(max_shares_by_risk, intended_shares), 0)
    capital_used = final_shares * price
    capital_at_risk = final_shares * stop_distance

    return PositionPlan(
        entry_price=price,
        stop_price=stop_price,
        stop_distance=stop_distance,
        stop_pct=stop_distance / price * 100.0,
        take_profit_price=take_profit,
        risk_per_share=stop_distance,
        max_shares_by_risk=max_shares_by_risk,
        intended_shares=intended_shares,
        final_shares=final_shares,
        capital_used=capital_used,
        capital_at_risk=capital_at_risk,
        capital_at_risk_pct=(capital_at_risk / portfolio_value * 100.0) if portfolio_value else 0.0,
    )


# ---------------------------------------------------------------------------
# 6. פסק הדין
# ---------------------------------------------------------------------------

VERDICT_LABELS = {
    "INVEST": "להשקיע",
    "INVEST_REDUCED": "להשקיע בגודל מופחת",
    "WAIT": "להמתין",
    "AVOID": "להימנע",
}

VERDICT_FLAVOR = {
    "INVEST": "המניה מלמדת אותך: הדרך פנויה, התנודתיות בשליטה והמחיר לא מגלם דרמה.",
    "INVEST_REDUCED": "המניה מלמדת אותך: אפשר להיכנס, אבל עם יד אחת על הדלת.",
    "WAIT": "המניה מלמדת אותך: אני כרגע בקזינו, חכי שהרוחות יירגעו.",
    "AVOID": "המניה מלמדת אותך: כל מי שהיה צריך לדעת כבר יודע, ואת משלמת את החשבון.",
}


def decide(criteria: list[Criterion], vetoes: list[str]) -> str:
    """
    רוב של V קובע, אבל וטו גובר על רוב.
    רוב בלי וטו הוא ספירה עיוורת: 3/4 עם דוח מחר זה לא 'להשקיע'.
    """
    if vetoes:
        return "AVOID" if len(vetoes) > 1 else "WAIT"

    scored = [c for c in criteria if c.passed is not None]
    passed = sum(1 for c in scored if c.passed)
    total = len(scored)
    if total == 0:
        return "WAIT"

    ratio = passed / total
    if ratio == 1.0:
        return "INVEST"
    if ratio >= 0.75:
        return "INVEST_REDUCED"
    if ratio >= 0.5:
        return "WAIT"
    return "AVOID"


def evaluate(
    ticker: str,
    price: float,
    atr: float,
    rel_std: Optional[float],
    hv_rank_value: Optional[float],
    vix: Optional[float],
    days_to_earnings: Optional[int] = None,
    macro_event: Optional[str] = None,
    iv: Optional[float] = None,
    hv: Optional[float] = None,
    portfolio_value: float = 0.0,
    position_pct: float = 0.05,
    risk_profile: str = "medium",
    rel_std_rank: Optional[float] = None,
    rel_std_pct: Optional[float] = None,
    hv_percentile_value: Optional[float] = None,
    config: Optional[StrategyConfig] = None,
) -> StrategyReport:
    """הניתוח המלא. כל 4 השלבים, טבלת סיכום ופסק דין."""
    cfg = config or StrategyConfig.for_profile(risk_profile)

    criteria = [
        build_atr_criterion(price, atr, rel_std, cfg, rel_std_rank, rel_std_pct),
        build_hv_rank_criterion(hv_rank_value, iv, hv, cfg, hv_percentile_value),
        build_vix_criterion(vix, cfg),
        build_events_criterion(days_to_earnings, macro_event, cfg),
    ]

    vetoes: list[str] = []
    if days_to_earnings is not None and days_to_earnings <= cfg.earnings_blackout_days:
        vetoes.append(f"דוח רווחים בעוד {days_to_earnings} ימים")
    if vix is not None and math.isfinite(vix) and vix >= cfg.vix_panic:
        vetoes.append(f"VIX בפאניקה ({vix:.1f})")

    verdict = decide(criteria, vetoes)

    scored = [c for c in criteria if c.passed is not None]
    passed_count = sum(1 for c in scored if c.passed)

    size_factor = cfg.reduced_size_factor if verdict == "INVEST_REDUCED" else 1.0
    position = None
    if verdict in ("INVEST", "INVEST_REDUCED"):
        position = build_position_plan(price, atr, portfolio_value, position_pct,
                                       cfg, size_factor=size_factor)

    headline = f"{passed_count}/{len(scored)} קריטריונים מתקיימים — {VERDICT_LABELS[verdict]}"
    if vetoes:
        headline += f" (וטו: {', '.join(vetoes)})"

    notes = []
    if any(c.is_proxy for c in criteria):
        notes.append("HV Rank הוא פרוקסי ל-IV Rank ולא תחליף מלא. "
                     "IV Rank אמיתי דורש היסטוריית IV שנתית שאינה זמינה ב-yfinance.")
    failed = [c.label for c in scored if not c.passed]
    if failed:
        notes.append("קריטריונים שנכשלו: " + ", ".join(failed))

    return StrategyReport(
        ticker=ticker,
        criteria=criteria,
        passed_count=passed_count,
        total_count=len(scored),
        verdict=verdict,
        verdict_label=VERDICT_LABELS[verdict],
        headline=headline,
        flavor=VERDICT_FLAVOR[verdict],
        position=position,
        vetoes=vetoes,
        notes=notes,
    )
