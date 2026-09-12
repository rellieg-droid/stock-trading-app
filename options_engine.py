"""
options_engine.py
=================
מנוע החישוב של RiskShield. מודול עצמאי לחלוטין:
אין בו Streamlit, אין yfinance, אין מצב גלובלי.
מקבל מספרים, מחזיר מספרים. ניתן לבדיקה מלאה ב-pytest.

תלויות: ספריית התקן של פייתון בלבד.
מקור אמת (source of truth): rellieg-droid/options-analysis.
שינויים בלוגיקה שייכים לשם קודם, ומסונכרנים לכאן ידנית.

מבנה
----
1. Black-Scholes  : מחיר וגריקס לאופציה בודדת
2. היפוך דלתא     : סטרייק מדלתא רצויה (מחליף את current_price * (1 - delta))
3. מודל הרגליים   : Leg / Position, ומהן נגזרות כל האסטרטגיות
4. עקומת תשלום    : payoff, max_loss, max_profit, breakevens
5. מנוע הסיכון    : חוק ה-1% + רצפת תיק, שני דליים נפרדים
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log, sqrt, isfinite
from statistics import NormalDist
from typing import Literal, Sequence

_N = NormalDist()          # התפלגות נורמלית תקנית
CONTRACT_MULTIPLIER = 100  # חוזה אופציה אחד = 100 מניות

Kind = Literal["stock", "call", "put"]


def norm_cdf(x: float) -> float:
    """התפלגות נורמלית תקנית מצטברת. נחשף כדי שקוד קיים יוכל לייבא במקום להגדיר."""
    return _N.cdf(x)


# =============================================================================
# 1. BLACK-SCHOLES
# =============================================================================

def _d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float):
    """מחזיר (d1, d2). קלט חייב להיות חיובי ממש."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        raise ValueError(f"S, K, T, sigma must all be > 0 (got S={S}, K={K}, T={T}, sigma={sigma})")
    vol_t = sigma * sqrt(T)
    d1 = (log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / vol_t
    return d1, d1 - vol_t


@dataclass(frozen=True)
class Greeks:
    """גריקס בקונבנציות שמוצגות למשתמש (לא ביחידות גולמיות)."""
    price: float    # מחיר האופציה למניה אחת
    delta: float    # שינוי במחיר האופציה על כל $1 בנכס הבסיס
    gamma: float    # שינוי בדלתא על כל $1
    vega: float     # שינוי במחיר על כל 1% שינוי ב-IV
    theta: float    # שחיקה יומית בדולרים (ליום קלנדרי)
    prob_otm: float  # הסתברות ניטרלית לסיכון לפקיעה מחוץ לכסף


def bs_greeks(
    kind: Kind,
    S: float,
    K: float,
    T: float,
    sigma: float,
    r: float = 0.045,
    q: float = 0.0,
) -> Greeks:
    """
    מחיר וגריקס לאופציה אירופאית.

    kind  : "call" או "put"
    S     : מחיר הנכס
    K     : סטרייק
    T     : זמן לפקיעה בשנים (30 יום = 30/365)
    sigma : תנודתיות גלומה כשבר עשרוני (54% -> 0.54)
    r     : ריבית חסרת סיכון
    q     : תשואת דיבידנד שנתית
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")

    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    disc_r, disc_q = exp(-r * T), exp(-q * T)
    pdf_d1 = _N.pdf(d1)
    vol_t = sigma * sqrt(T)

    # רכיבים משותפים
    gamma = disc_q * pdf_d1 / (S * vol_t)
    vega = S * disc_q * pdf_d1 * sqrt(T) / 100.0          # ל-1% שינוי ב-IV
    theta_common = -S * disc_q * pdf_d1 * sigma / (2 * sqrt(T))

    if kind == "call":
        price = S * disc_q * _N.cdf(d1) - K * disc_r * _N.cdf(d2)
        delta = disc_q * _N.cdf(d1)
        theta_yr = theta_common - r * K * disc_r * _N.cdf(d2) + q * S * disc_q * _N.cdf(d1)
        prob_otm = _N.cdf(-d2)      # P(S_T < K)
    else:
        price = K * disc_r * _N.cdf(-d2) - S * disc_q * _N.cdf(-d1)
        delta = -disc_q * _N.cdf(-d1)
        theta_yr = theta_common + r * K * disc_r * _N.cdf(-d2) - q * S * disc_q * _N.cdf(-d1)
        prob_otm = _N.cdf(d2)       # P(S_T > K)

    return Greeks(
        price=price,
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta_yr / 365.0,
        prob_otm=prob_otm,
    )


# =============================================================================
# 1b. תנודתיות: גלומה מול ממומשת
# =============================================================================

def implied_vol(
    kind: Kind,
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float = 0.045,
    q: float = 0.0,
    lo: float = 1e-4,
    hi: float = 6.0,
    tol: float = 1e-8,
    max_iter: int = 200,
) -> float:
    """
    התנודתיות שמייצרת התאמה בין המודל למחיר שראית בשוק.
    חציית ביסקציה. מחיר האופציה עולה מונוטונית ב-sigma, לכן החיפוש יציב.
    """
    if market_price <= 0:
        raise ValueError(f"market_price must be > 0, got {market_price}")
    if not 0 < lo < hi:
        raise ValueError("need 0 < lo < hi")

    price = lambda v: bs_greeks(kind, S, K, T, v, r, q).price
    if market_price > price(hi):
        raise ValueError(
            f"price ${market_price:,.4f} exceeds the model at sigma={hi:.0%}; "
            "widen hi or check the quote"
        )

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if hi - lo < tol:
            return mid
        if price(mid) < market_price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def realized_vol(closes: Sequence[float], window: int = 252,
                 periods_per_year: int = 252) -> float:
    """
    תנודתיות ממומשת מהיסטוריית המחירים עצמה, במונחים שנתיים.
    זה הצד ה-RV בתנאי הכניסה IV > RV.
    סדרה שטוחה לגמרי מחזירה 0.0.
    """
    tail = list(closes[-window:]) if len(closes) > window else list(closes)
    if len(tail) < 3:
        return 0.0
    if any(c <= 0 for c in tail):
        raise ValueError("closes must all be positive")

    rets = [log(tail[i] / tail[i - 1]) for i in range(1, len(tail))]
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)
    return sqrt(var * periods_per_year)


def iv_rv_ratio(iv: float, rv: float) -> float:
    """
    יחס IV/RV. מעל 1 אומר שהשוק מתמחר יותר תנודתיות ממה שהמניה עשתה בפועל,
    וזה מה שמצדיק מכירת תנודתיות. rv אפס מחזיר אינסוף.
    """
    return float("inf") if rv <= 0 else iv / rv


# =============================================================================
# 1d. RV Rank / RV Percentile - תחליף זמני ומוצהר ל-IV Rank
# =============================================================================
#
# אין ל-yfinance/Yahoo ארכיון היסטורי של IV (הם נותנים רק שרשרת אופציות
# נוכחית - חוזים ישנים נעלמים ברגע שהם פוקעים). RV, לעומת זאת, נגזר ממחיר
# המניה שיש לו ארכיון מלא. לכן RV Rank זמין מיד, אבל הוא מודד דבר אחר
# (מה שקרה בפועל) לעומת IV Rank (מה שהשוק מצפה) - חובה לתייג בהתאם בממשק.


def _rolling_rv_series(
    closes: Sequence[float],
    vol_window: int = 20,
    lookback_days: int = 252,
) -> list[float]:
    """סדרת RV מתגלגלת: לכל יום בטווח ה-lookback, ה-RV שחושב מ-vol_window הימים שקדמו לו."""
    needed = lookback_days + vol_window
    tail = list(closes[-needed:]) if len(closes) >= needed else list(closes)
    series = []
    for i in range(vol_window, len(tail)):
        window_slice = tail[i - vol_window: i + 1]
        series.append(realized_vol(window_slice, window=vol_window))
    return series


def rv_rank(
    closes: Sequence[float],
    vol_window: int = 20,
    lookback_days: int = 252,
) -> float | None:
    """
    (RV הנוכחי - RV מינימלי בטווח) / (RV מקסימלי - RV מינימלי) * 100.
    None אם אין מספיק נתונים לבניית סדרה, או שה-RV לא זז כלל בטווח (max==min).
    """
    series = _rolling_rv_series(closes, vol_window, lookback_days)
    if len(series) < 2:
        return None
    current, lo, hi = series[-1], min(series), max(series)
    if hi == lo:
        return None
    return (current - lo) / (hi - lo) * 100.0


def rv_percentile(
    closes: Sequence[float],
    vol_window: int = 20,
    lookback_days: int = 252,
) -> float | None:
    """אחוז הימים בטווח שבהם ה-RV היה נמוך או שווה ל-RV הנוכחי. None אם אין מספיק נתונים."""
    series = _rolling_rv_series(closes, vol_window, lookback_days)
    if len(series) < 2:
        return None
    current = series[-1]
    count_leq = sum(1 for v in series if v <= current)
    return count_leq / len(series) * 100.0


# =============================================================================
# 1c. הסתברות היסטורית ו-Fat-tail
# =============================================================================
#
# עקרון: כל מודל מוצג בנפרד. אין מיזוג למספר/ציון יחיד, ואין "המלצה" -
# ראי /projects/.../ways-of-working.md: "RiskShield rejects composite scores...
# displays raw metrics separately".

from math import lgamma


@dataclass(frozen=True)
class HistoricalProbability:
    """הסתברות היסטורית ל-OTM של פוט, לפי חלון זמן. לא ממוזג לציון יחיד."""
    by_period: dict            # שנות-לוקבאק -> הסתברות OTM (או None אם אין מספיק נתונים)
    weighted_otm: float | None  # ממוצע משוקלל של התקופות הזמינות בלבד, מוצג לצד הפירוט
    periods_available: int
    note: str = ""


def historical_put_otm_probability(
    closes: Sequence[float],
    strike: float,
    dte_days: int,
    trading_days_per_year: int = 252,
) -> HistoricalProbability:
    """
    לכל יום מסחר היסטורי: האם המחיר dte_days ימי-מסחר קדימה נשאר מעל הסטרייק (OTM)?
    מחושב בנפרד לחלונות 1/3/5/10 שנים אחרונות (משתמש בכל ההיסטוריה הזמינה בכל חלון).

    אם אין מספיק היסטוריה לתקופה מסוימת - היא None, לא מומצאת.
    ה-weighted_otm משוקלל רק על התקופות הזמינות (40/30/20/10 מנורמל מחדש),
    ומוצג *לצד* הפירוט המלא, לא במקומו.
    """
    periods_years = (1, 3, 5, 10)
    base_weights = {1: 0.40, 3: 0.30, 5: 0.20, 10: 0.10}
    n = len(closes)
    by_period: dict = {}

    for years in periods_years:
        window_days = years * trading_days_per_year
        needed = window_days + dte_days
        tail = list(closes[-needed:]) if n >= needed else list(closes)
        total = len(tail) - dte_days
        if total <= 0:
            by_period[years] = None
            continue
        breaches = sum(1 for i in range(total) if tail[i + dte_days] <= strike)
        by_period[years] = 1.0 - (breaches / total)

    available = {y: p for y, p in by_period.items() if p is not None}
    if not available:
        return HistoricalProbability(
            by_period, None, 0, "אין מספיק היסטוריה לחישוב הסתברות היסטורית"
        )

    weight_sum = sum(base_weights[y] for y in available)
    weighted = sum(base_weights[y] * p for y, p in available.items()) / weight_sum

    note = ""
    if len(available) < len(periods_years):
        note = (
            f"היסטוריה זמינה: {len(available)} מתוך {len(periods_years)} תקופות "
            "(1/3/5/10 שנים). ביטחון מופחת בהתאם."
        )

    return HistoricalProbability(by_period, weighted, len(available), note)


# ---- Fat-tail (Student-t), ללא scipy ------------------------------------

def _betacf(a: float, b: float, x: float, max_iter: int = 200, eps: float = 1e-12) -> float:
    """שבר משולב לפונקציית הבטא הבלתי-שלמה (Numerical Recipes, betacf)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_front = lgamma(a + b) - lgamma(a) - lgamma(b) + a * log(x) + b * log(1.0 - x)
    front = exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(x: float, df: float) -> float:
    """
    CDF של התפלגות t-Student, בלי scipy - דרך הבטא הבלתי-שלמה המוסדרת
    (math.gamma/lgamma הם ספריית תקן, אין תלות חיצונית).
    """
    if df <= 0:
        raise ValueError(f"df must be > 0, got {df}")
    x_beta = df / (df + x * x)
    ib = _regularized_incomplete_beta(x_beta, df / 2.0, 0.5)
    return 1.0 - 0.5 * ib if x >= 0 else 0.5 * ib


@dataclass(frozen=True)
class FatTailProbability:
    """הסתברות ל-OTM לפי מודל Fat-tail. קירוב מוצהר, לא מדויק - ראי note."""
    otm_probability: float | None
    degrees_of_freedom: float | None
    excess_kurtosis: float | None
    note: str = ""


def fat_tail_otm_probability(
    daily_log_returns: Sequence[float],
    S: float,
    K: float,
    dte_days: int,
    min_observations: int = 30,
) -> FatTailProbability:
    """
    הסתברות ל-OTM של פוט לפי התפלגות t-Student, עם דרגות חופש שנאמדות
    מהקורטוזיס העודף של התשואות היומיות ההיסטוריות (שיטת המומנטים).

    קירוב מוצהר: קנה מידה לאופק T ימים לפי sqrt(T) (לא מדויק סטטיסטית עבור
    סכום משתני t, אך נהוג כקירוב סביר - בדיוק כמו Probability of Touch).
    למניפים ממונפים (SOXL וכו') מומלץ משקל גבוה יותר למודל הזה על פני Normal,
    לפי ההנחיה הקיימת בסקילים.
    """
    n = len(daily_log_returns)
    if n < min_observations:
        return FatTailProbability(
            None, None, None,
            f"אין מספיק תצפיות היסטוריות למודל Fat-tail (יש {n}, נדרשים {min_observations}+)",
        )

    mean = sum(daily_log_returns) / n
    var = sum((r - mean) ** 2 for r in daily_log_returns) / (n - 1)
    if var <= 0:
        return FatTailProbability(None, None, None, "שונות התשואות היומיות אפס - לא ניתן לחשב")

    m4 = sum((r - mean) ** 4 for r in daily_log_returns) / n
    excess_kurtosis = (m4 / (var ** 2)) - 3.0

    if excess_kurtosis <= 0:
        df = 30.0  # אין עודף קורטוזיס מובהק - קרוב לנורמלי, df גבוה
    else:
        df = max(6.0 / excess_kurtosis + 4.0, 2.1)  # df>2 נדרש לשונות סופית

    std = sqrt(var)
    horizon_mean = mean * dte_days
    horizon_std = std * sqrt(dte_days)
    if horizon_std <= 0:
        return FatTailProbability(None, df, excess_kurtosis, "סטיית תקן לאופק אפס")

    log_strike_return = log(K / S)
    t_stat = (log_strike_return - horizon_mean) / horizon_std
    prob_itm = student_t_cdf(t_stat, df)
    prob_otm = 1.0 - prob_itm

    return FatTailProbability(prob_otm, df, excess_kurtosis, "")


# =============================================================================
# 2. היפוך דלתא -> סטרייק
# =============================================================================

def strike_from_delta(
    kind: Kind,
    target_delta: float,
    S: float,
    T: float,
    sigma: float,
    r: float = 0.045,
    q: float = 0.0,
    round_to: float | None = None,
) -> float:
    """
    הסטרייק שנותן את הדלתא המבוקשת.
    מחליף את current_price * (1 - delta) שהיה בפרוטוטייפ.

    target_delta : גודל מוחלט, 0 עד 1. עבור פוט מוחזר סטרייק מתחת ל-S.
    round_to     : עיגול לרשת סטרייקים אמיתית (0.5 / 1.0 / 5.0). None = מדויק.
    """
    d = abs(target_delta)
    if not 0 < d < 1:
        raise ValueError(f"target_delta must be strictly between 0 and 1, got {target_delta}")
    if S <= 0 or T <= 0 or sigma <= 0:
        raise ValueError(f"S, T, sigma must all be > 0 (got S={S}, T={T}, sigma={sigma})")

    adj = d * exp(q * T)  # ניטרול הדיסקאונט של הדיבידנד
    if not 0 < adj < 1:
        raise ValueError(
            f"delta {target_delta} unreachable with q={q}, T={T} (adjusted={adj:.4f})"
        )

    # call : delta = e^-qT * N(d1)   -> d1 =  N^-1(adj)
    # put  : delta = -e^-qT * N(-d1) -> d1 = -N^-1(adj)
    d1 = _N.inv_cdf(adj) * (1 if kind == "call" else -1)

    K = S * exp((r - q + 0.5 * sigma ** 2) * T - d1 * sigma * sqrt(T))
    if not isfinite(K) or K <= 0:
        raise ValueError("strike solution diverged; check inputs")

    return round(K / round_to) * round_to if round_to else K


# =============================================================================
# 3. מודל הרגליים
# =============================================================================

@dataclass(frozen=True)
class Leg:
    """
    רגל בודדת בפוזיציה.

    direction : +1 לונג (קניתי), -1 שורט (כתבתי)
    qty       : מניות עבור stock, חוזים עבור call/put
    entry     : מחיר כניסה למניה אחת. באופציה זו הפרמיה, לא כפול 100.
    """
    kind: Kind
    direction: int
    qty: float
    entry: float
    strike: float | None = None
    label: str = ""

    def __post_init__(self):
        if self.direction not in (1, -1):
            raise ValueError(f"direction must be +1 or -1, got {self.direction}")
        if self.qty <= 0:
            raise ValueError(f"qty must be > 0, got {self.qty}")
        if self.kind == "stock":
            if self.strike is not None:
                raise ValueError("stock leg must not have a strike")
        elif self.kind in ("call", "put"):
            if self.strike is None or self.strike <= 0:
                raise ValueError(f"{self.kind} leg needs a positive strike")
        else:
            raise ValueError(f"unknown kind {self.kind!r}")

    @property
    def multiplier(self) -> float:
        return 1.0 if self.kind == "stock" else CONTRACT_MULTIPLIER

    @property
    def cash_flow(self) -> float:
        """תזרים בפתיחה. שלילי = שילמתי, חיובי = קיבלתי."""
        return -self.direction * self.qty * self.entry * self.multiplier

    def payoff_at(self, spot: float) -> float:
        """רווח/הפסד בדולרים בפקיעה, במחיר spot נתון."""
        if self.kind == "stock":
            intrinsic = spot
        elif self.kind == "call":
            intrinsic = max(spot - self.strike, 0.0)
        else:
            intrinsic = max(self.strike - spot, 0.0)
        return self.direction * self.qty * self.multiplier * (intrinsic - self.entry)


@dataclass
class Position:
    """אוסף רגליים = אסטרטגיה. כל האסטרטגיות עוברות דרך המחלקה הזו."""
    legs: list[Leg] = field(default_factory=list)
    name: str = ""
    underlying: str = ""

    # ---- תזרים ----
    @property
    def net_cash(self) -> float:
        """תזרים נטו בפתיחה. חיובי = עסקת קרדיט."""
        return sum(leg.cash_flow for leg in self.legs)

    @property
    def is_hedge(self) -> bool:
        """פוזיציה שמכילה מניה מוגדרת כהגנה, לא כספקולציה."""
        return any(leg.kind == "stock" for leg in self.legs)

    # ---- עקומת תשלום ----
    def payoff_at(self, spot: float) -> float:
        return sum(leg.payoff_at(spot) for leg in self.legs)

    def payoff_curve(self, lo: float, hi: float, points: int = 400):
        """מחזיר (spots, pnl) לגרף Plotly. נקודות השבירה תמיד נכללות."""
        if hi <= lo:
            raise ValueError("hi must be greater than lo")
        step = (hi - lo) / (points - 1)
        grid = {lo + i * step for i in range(points)}
        grid |= {k for k in self._kinks() if lo <= k <= hi}
        spots = sorted(grid)
        return spots, [self.payoff_at(s) for s in spots]

    def _kinks(self) -> list[float]:
        """נקודות השבירה: כל הסטרייקים ואפס. הפונקציה קווית למקוטעין ביניהן."""
        return [0.0] + sorted({leg.strike for leg in self.legs if leg.strike is not None})

    # ---- שיפועים בקצוות ----
    def _slope_right(self) -> float:
        """שיפור לכל $1 מעל הסטרייק הגבוה ביותר."""
        return sum(
            leg.direction * leg.qty * leg.multiplier
            for leg in self.legs
            if leg.kind in ("stock", "call")
        )

    # ---- סיכון ----
    def max_loss(self) -> float:
        """
        הפסד מקסימלי בדולרים כמספר חיובי.
        float('inf') = סיכון בלתי מוגדר (שורט קול לא מכוסה).
        הפונקציה קווית למקוטעין, לכן המינימום נמצא תמיד בנקודת שבירה.
        """
        if self._slope_right() < 0:
            return float("inf")
        candidates = self._kinks()
        upper = max(candidates) * 3 + 1
        worst = min(self.payoff_at(s) for s in candidates + [upper])
        return max(-worst, 0.0)

    def max_profit(self) -> float:
        if self._slope_right() > 0:
            return float("inf")
        candidates = self._kinks()
        upper = max(candidates) * 3 + 1
        return max(self.payoff_at(s) for s in candidates + [upper])

    def breakevens(self, tol: float = 1e-9) -> list[float]:
        """נקודות איזון. חיפוש ליניארי בין נקודות שבירה סמוכות."""
        pts = sorted(set(self._kinks() + [max(self._kinks()) * 3 + 1]))
        out = []
        for a, b in zip(pts, pts[1:]):
            fa, fb = self.payoff_at(a), self.payoff_at(b)
            if abs(fa) < tol:
                out.append(a)
            elif fa * fb < 0:
                out.append(a + (b - a) * fa / (fa - fb))  # אינטרפולציה ליניארית
        return sorted(set(round(x, 6) for x in out))

    def floor_value(self, shares_price: float) -> float:
        """
        שווי הרצפה של פוזיציה מגודרת: כמה הפוזיציה שווה בקריסה מוחלטת.
        זה המדד הרלוונטי לביטוח, לא max_loss.
        """
        stock_value = sum(
            leg.direction * leg.qty * shares_price
            for leg in self.legs if leg.kind == "stock"
        )
        return stock_value - self.max_loss()


# =============================================================================
# 4. תבניות אסטרטגיה
# =============================================================================

def protective_put(shares: int, stock_entry: float, put_strike: float,
                   put_premium: float, contracts: int | None = None) -> Position:
    """מניה + פוט מגן. ברירת מחדל: חוזה אחד לכל 100 מניות."""
    contracts = contracts if contracts is not None else shares / CONTRACT_MULTIPLIER
    return Position(
        name="Protective Put",
        legs=[
            Leg("stock", +1, shares, stock_entry, label="מניות"),
            Leg("put", +1, contracts, put_premium, put_strike, label="ביטוח"),
        ],
    )


def collar(shares: int, stock_entry: float, put_strike: float, put_premium: float,
           call_strike: float, call_premium: float, contracts: int | None = None) -> Position:
    """מניה + פוט מגן + קול כתוב שמממן אותו."""
    contracts = contracts if contracts is not None else shares / CONTRACT_MULTIPLIER
    return Position(
        name="Collar",
        legs=[
            Leg("stock", +1, shares, stock_entry, label="מניות"),
            Leg("put", +1, contracts, put_premium, put_strike, label="ביטוח"),
            Leg("call", -1, contracts, call_premium, call_strike, label="מימון"),
        ],
    )


def solve_zero_cost_collar(
    shares: int, stock_entry: float, S: float, T: float, sigma: float,
    put_delta: float = 0.25, r: float = 0.045, q: float = 0.0,
    strike_step: float = 5.0, max_search: float = 3.0,
) -> Position:
    """
    סולבר הצווארון. המשתמשת בוחרת רק את הרצפה, המערכת פותרת את התקרה.

    ככל שסטרייק הקול גבוה יותר כך הפרמיה שלו נמוכה יותר, לכן מחפשים את
    הסטרייק הגבוה ביותר שהפרמיה שלו עדיין מכסה את עלות הפוט.
    זו התקרה הכי נדיבה שאפשר לקבל בעלות אפס.
    """
    put_k = strike_from_delta("put", put_delta, S, T, sigma, r, q, round_to=strike_step)
    put_prem = bs_greeks("put", S, put_k, T, sigma, r, q).price

    best_k = best_prem = None
    k = round(S / strike_step) * strike_step
    limit = S * max_search
    while k <= limit:
        prem = bs_greeks("call", S, k, T, sigma, r, q).price
        if prem >= put_prem:
            best_k, best_prem = k, prem   # עדיין מכסה, ננסה גבוה יותר
        else:
            break                          # מכאן והלאה כבר לא יכסה
        k += strike_step

    if best_k is None:
        raise ValueError(
            f"no call strike at or above ${S:,.2f} covers a put costing ${put_prem:,.2f}; "
            f"lower put_delta or shorten T"
        )

    return collar(shares, stock_entry, put_k, put_prem, best_k, best_prem)


def iron_condor(contracts: int,
                short_put: float, short_put_prem: float,
                long_put: float, long_put_prem: float,
                short_call: float, short_call_prem: float,
                long_call: float, long_call_prem: float) -> Position:
    """ארבע רגליים. הלונגים חייבים להיות מחוץ לשורטים."""
    if not (long_put < short_put < short_call < long_call):
        raise ValueError(
            "strikes must satisfy long_put < short_put < short_call < long_call, "
            f"got {long_put}, {short_put}, {short_call}, {long_call}"
        )
    return Position(
        name="Iron Condor",
        legs=[
            Leg("put", +1, contracts, long_put_prem, long_put, label="הגנה תחתונה"),
            Leg("call", +1, contracts, long_call_prem, long_call, label="הגנה עליונה"),
            Leg("put", -1, contracts, short_put_prem, short_put, label="כתיבה תחתונה"),
            Leg("call", -1, contracts, short_call_prem, short_call, label="כתיבה עליונה"),
        ],
    )


def entry_order(position: Position) -> list[Leg]:
    """
    סדר ההזנה הכפוי לברוקר: מניה, אחר כך כל הלונגים, ורק בסוף השורטים.
    קניית ההגנה לפני הכתיבה מונעת דרישת בטוחות מנופחת.
    """
    rank = {("stock", 1): 0, ("stock", -1): 0}
    return sorted(
        position.legs,
        key=lambda l: rank.get((l.kind, l.direction), 1 if l.direction == 1 else 2),
    )


# =============================================================================
# 5. מנוע הסיכון
# =============================================================================

@dataclass(frozen=True)
class RiskVerdict:
    approved: bool
    contracts: int            # כמה חוזים מותרים בפועל. 0 = חסום.
    risk_usd: float           # ההפסד המקסימלי בכמות המאושרת. חסום -> 0.
    risk_pct: float           # אותו סכום כאחוז מהתיק
    budget_usd: float         # תקציב הסיכון
    reason: str
    unit_risk_usd: float = 0.0  # סיכון לחוזה בודד. תמיד מלא, גם כשחסום.


def size_position(
    template: Position,
    portfolio_usd: float,
    max_risk_pct: float = 0.01,
    open_positions: int = 0,
    max_concurrent: int = 5,
    template_contracts: int = 1,
) -> RiskVerdict:
    """
    שומר חוק ה-1% לעסקאות ספקולטיביות.

    template : פוזיציה בנויה עם template_contracts חוזים
    מחזיר את מספר החוזים המרבי שעומד בתקציב. אם אפילו חוזה אחד חורג,
    התוצאה היא 0 חוזים. אין עיגול כלפי מעלה.
    """
    if portfolio_usd <= 0:
        return RiskVerdict(False, 0, 0.0, 0.0, 0.0, "שווי תיק חייב להיות חיובי")

    budget = portfolio_usd * max_risk_pct
    unit_risk = template.max_loss() / template_contracts

    if open_positions >= max_concurrent:
        return RiskVerdict(
            False, 0, 0.0, 0.0, budget,
            f"כבר פתוחות {open_positions} עסקאות. המקסימום הוא {max_concurrent} "
            f"(חשיפה כוללת {max_concurrent * max_risk_pct:.0%})",
            unit_risk,
        )

    if unit_risk == float("inf"):
        return RiskVerdict(False, 0, 0.0, 0.0, budget,
                           "סיכון בלתי מוגדר. האפליקציה מאשרת רק מבנים מוגדרי סיכון",
                           float("inf"))

    if unit_risk <= 0:
        return RiskVerdict(True, template_contracts, 0.0, 0.0, budget,
                           "אין סיכון בפקיעה בפוזיציה הזו", 0.0)

    allowed = int(budget // unit_risk)

    if allowed == 0:
        return RiskVerdict(
            False, 0, 0.0, 0.0, budget,
            f"חוזה בודד מסכן ${unit_risk:,.0f} מול תקציב של ${budget:,.0f}. "
            f"צמצמי את רוחב הכנף, בחרי נכס זול יותר, או שהתיק קטן מדי לעסקה הזו",
            unit_risk,
        )

    risk = allowed * unit_risk
    return RiskVerdict(True, allowed, risk, risk / portfolio_usd, budget,
                       f"מאושר: {allowed} חוזים, סיכון ${risk:,.0f} "
                       f"({risk / portfolio_usd:.2%} מהתיק)",
                       unit_risk)


def portfolio_floor(hedged: Sequence[tuple[Position, float]],
                    unhedged_value: float = 0.0,
                    stress_drawdown: float = 0.20) -> float:
    """
    הדלי השני: רצפת התיק. זה המדד לביטוח, ולא חוק ה-1%.

    hedged          : רשימת (פוזיציה מגודרת, מחיר מניה נוכחי)
    unhedged_value  : שווי מניות ללא הגנה
    stress_drawdown : תרחיש קיצון למניות החשופות
    """
    return (
        sum(pos.floor_value(price) for pos, price in hedged)
        + unhedged_value * (1 - stress_drawdown)
    )


def pop_iron_condor(short_put_delta: float, short_call_delta: float) -> float:
    """
    הסתברות לרווח מלא באיירון קונדור.
    שני סטרייקים קצרים, לכן זו לא 1 מינוס דלתא בודדת.
    בדלתא 0.15 משני הצדדים התוצאה היא כ-70%, לא 85%.
    """
    return max(0.0, 1.0 - abs(short_put_delta) - abs(short_call_delta))
