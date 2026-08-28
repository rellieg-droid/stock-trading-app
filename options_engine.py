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
