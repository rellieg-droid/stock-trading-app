"""
rr_engine.py
============
מנוע חישוב אסטרטגיית סיכון-סיכוי (Risk / Reward) + ניהול פוזיציה סביב דוחות כספיים.

מודול טהור: ללא Streamlit, ללא רשת, ללא I/O. כל פונקציה ניתנת לבדיקה ב-pytest.
כל המחירים במטבע אחד. כל ה"רווח" נמדד ביחידות R (R = הסיכון למניה).

מבנה:
    1. יסודות R          – risk_per_share, target_price, build_plan
    2. גודל פוזיציה      – position_size, size_for_gap_budget
    3. מתמטיקת רווחיות   – breakeven_win_rate, expectancy_r, blended_r
    4. דוחות כספיים      – days_to_earnings, earnings_risk_tier, earnings_action
    5. סימולציית פערים   – simulate_gap, gap_scenario_table
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Optional, Sequence

Direction = Literal["long", "short"]

# ---------------------------------------------------------------------------
# קבועים ניתנים לשינוי
# ---------------------------------------------------------------------------

DEFAULT_R_MULTIPLES: tuple[float, ...] = (1.0, 2.0, 3.0)
DEFAULT_SCALE_OUT: tuple[float, ...] = (0.50, 0.30, 0.20)  # כמה מהפוזיציה לממש בכל יעד
DEFAULT_GAP_GRID: tuple[float, ...] = (-0.20, -0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20)

TARGET_LABELS = {1.0: "יעד 1 (1:1)", 2.0: "יעד 2 (1:2)", 3.0: "יעד 3 (1:3)"}


# ---------------------------------------------------------------------------
# 1. יסודות R
# ---------------------------------------------------------------------------

def direction_sign(direction: Direction) -> int:
    """+1 עבור לונג, -1 עבור שורט."""
    if direction == "long":
        return 1
    if direction == "short":
        return -1
    raise ValueError(f"כיוון לא חוקי: {direction!r} (מותר: 'long' / 'short')")


def risk_per_share(entry: float, stop: float, direction: Direction = "long") -> float:
    """
    R ליחידה אחת = המרחק בין הכניסה לסטופ.
    מחזיר תמיד ערך חיובי, ומכשיל סטופ שנמצא בצד הלא נכון של הכניסה.
    """
    if entry <= 0 or stop <= 0:
        raise ValueError("מחירי כניסה וסטופ חייבים להיות גדולים מאפס.")
    sign = direction_sign(direction)
    r = (entry - stop) * sign
    if r <= 0:
        side = "מתחת" if direction == "long" else "מעל"
        raise ValueError(f"בעסקת {direction} הסטופ חייב להיות {side} למחיר הכניסה.")
    return r


def target_price(entry: float, r_unit: float, r_multiple: float,
                 direction: Direction = "long") -> float:
    """מחיר יעד עבור כפולת R נתונה."""
    return entry + direction_sign(direction) * r_unit * r_multiple


def stop_from_atr(entry: float, atr: float, atr_mult: float = 2.0,
                  direction: Direction = "long") -> float:
    """
    סטופ מבוסס תנודתיות במקום אחוז שרירותי.
    entry ± (ATR × מכפיל). דורש ATR חיובי.
    """
    if atr <= 0:
        raise ValueError("ATR חייב להיות גדול מאפס.")
    if atr_mult <= 0:
        raise ValueError("מכפיל ATR חייב להיות גדול מאפס.")
    return entry - direction_sign(direction) * atr * atr_mult


def r_multiple_of_price(price: float, entry: float, r_unit: float,
                        direction: Direction = "long") -> float:
    """כמה R שווה מחיר נתון ביחס לכניסה. שלילי = הפסד."""
    return direction_sign(direction) * (price - entry) / r_unit


# ---------------------------------------------------------------------------
# 2. גודל פוזיציה
# ---------------------------------------------------------------------------

def position_size(account_value: float, risk_pct: float, entry: float, stop: float,
                  direction: Direction = "long",
                  max_position_pct: Optional[float] = None) -> dict:
    """
    גודל פוזיציה לפי כלל סיכון קבוע (ברירת מחדל בפועל: 1% מהתיק).

    risk_pct        – שבר עשרוני (0.01 = 1%), לא אחוזים שלמים.
    max_position_pct – תקרת חשיפה אופציונלית לפוזיציה בודדת (שבר עשרוני).

    מחזיר dict עם shares, risk_amount, notional, ודגל capped.
    """
    if account_value <= 0:
        raise ValueError("שווי התיק חייב להיות גדול מאפס.")
    if not 0 < risk_pct < 1:
        raise ValueError("risk_pct חייב להיות שבר עשרוני בין 0 ל-1 (למשל 0.01).")

    r_unit = risk_per_share(entry, stop, direction)
    risk_budget = account_value * risk_pct
    shares = math.floor(risk_budget / r_unit)
    capped = False

    if max_position_pct is not None:
        if not 0 < max_position_pct <= 1:
            raise ValueError("max_position_pct חייב להיות שבר עשרוני בין 0 ל-1.")
        max_shares = math.floor((account_value * max_position_pct) / entry)
        if max_shares < shares:
            shares, capped = max_shares, True

    return {
        "shares": max(shares, 0),
        "r_unit": r_unit,
        "risk_budget": risk_budget,
        "risk_amount": max(shares, 0) * r_unit,       # הסיכון בפועל אחרי עיגול מניות
        "notional": max(shares, 0) * entry,
        "notional_pct": (max(shares, 0) * entry) / account_value,
        "capped_by_exposure": capped,
    }


def size_for_gap_budget(account_value: float, max_gap_loss_pct: float, entry: float,
                        assumed_gap_pct: float, direction: Direction = "long") -> dict:
    """
    גודל פוזיציה שנגזר מתרחיש הפער, לא מהסטופ.

    הרעיון: לפני דוח, הסטופ לא מגן. לכן שואלים "כמה אני מוכן להפסיד אם המניה
    תיפתח 12% נגדי" ומגזרים מכך את מספר המניות.

    max_gap_loss_pct – שבר עשרוני מהתיק (0.02 = 2%).
    assumed_gap_pct  – גודל הפער בהנחה, כערך מוחלט (0.12 = 12%).
    """
    if assumed_gap_pct <= 0:
        raise ValueError("assumed_gap_pct חייב להיות ערך מוחלט חיובי (למשל 0.12).")
    if not 0 < max_gap_loss_pct < 1:
        raise ValueError("max_gap_loss_pct חייב להיות שבר עשרוני בין 0 ל-1.")

    loss_per_share = entry * assumed_gap_pct
    budget = account_value * max_gap_loss_pct
    shares = math.floor(budget / loss_per_share)
    return {
        "shares": max(shares, 0),
        "loss_per_share": loss_per_share,
        "gap_loss": max(shares, 0) * loss_per_share,
        "notional": max(shares, 0) * entry,
        "direction": direction,
    }


# ---------------------------------------------------------------------------
# 3. מתמטיקת רווחיות
# ---------------------------------------------------------------------------

def breakeven_win_rate(rr: float) -> float:
    """אחוז ההצלחה המינימלי הדרוש כדי לא להפסיד ביחס סיכון-סיכוי נתון."""
    if rr <= 0:
        raise ValueError("יחס סיכון-סיכוי חייב להיות חיובי.")
    return 1.0 / (1.0 + rr)


def expectancy_r(win_rate: float, rr: float) -> float:
    """תוחלת ביחידות R לעסקה. חיובי = אסטרטגיה רווחית לאורך זמן."""
    if not 0 <= win_rate <= 1:
        raise ValueError("win_rate חייב להיות בין 0 ל-1.")
    return win_rate * rr - (1.0 - win_rate)


def blended_r(r_multiples: Sequence[float] = DEFAULT_R_MULTIPLES,
              weights: Sequence[float] = DEFAULT_SCALE_OUT) -> float:
    """
    ה-R המשוקלל של יציאה מדורגת (למשל 50% ב-1R, 30% ב-2R, 20% ב-3R).
    הנחה: כל היעדים נפגעים. זהו התרחיש הטוב, לא הממוצע.
    """
    if len(r_multiples) != len(weights):
        raise ValueError("אורך רשימת היעדים ורשימת המשקלים חייב להיות זהה.")
    total = sum(weights)
    if not math.isclose(total, 1.0, abs_tol=1e-6):
        raise ValueError(f"סכום המשקלים חייב להיות 1.0 (התקבל {total}).")
    return sum(r * w for r, w in zip(r_multiples, weights))


# ---------------------------------------------------------------------------
# תוכנית עסקה
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Target:
    r_multiple: float
    price: float
    weight: float          # חלק הפוזיציה שמיועד ליציאה כאן
    label: str = ""
    shares: int = 0
    profit: float = 0.0    # רווח כספי מהמנה הזו בלבד

    @property
    def rr_text(self) -> str:
        return f"1:{self.r_multiple:g}"


@dataclass
class TradePlan:
    ticker: str
    direction: Direction
    entry: float
    stop: float
    r_unit: float
    shares: int
    targets: list[Target] = field(default_factory=list)
    account_value: Optional[float] = None
    risk_pct: Optional[float] = None
    earnings_date: Optional[date] = None
    notes: str = ""

    # --- נגזרות ---
    @property
    def risk_amount(self) -> float:
        return self.shares * self.r_unit

    @property
    def notional(self) -> float:
        return self.shares * self.entry

    @property
    def stop_distance_pct(self) -> float:
        return self.r_unit / self.entry

    @property
    def blended_r(self) -> float:
        if not self.targets:
            return 0.0
        return sum(t.r_multiple * t.weight for t in self.targets)

    @property
    def max_profit(self) -> float:
        return sum(t.profit for t in self.targets)

    def target_by_r(self, r_multiple: float) -> Optional[Target]:
        for t in self.targets:
            if math.isclose(t.r_multiple, r_multiple):
                return t
        return None

    def to_rows(self) -> list[dict]:
        """שורות מוכנות לטבלת ריכוז האסטרטגיה בממשק."""
        rows = [
            {
                "שלב": "מחיר קנייה (כניסה)" if self.direction == "long" else "מחיר מכירה (כניסה)",
                "יחס": "—",
                "מחיר": self.entry,
                "מרחק %": 0.0,
                "מניות": self.shares,
                "רווח/הפסד": 0.0,
                "R": 0.0,
            },
            {
                "שלב": "פקודת הגנה (Stop Loss)",
                "יחס": "—",
                "מחיר": self.stop,
                "מרחק %": -self.stop_distance_pct,
                "מניות": self.shares,
                "רווח/הפסד": -self.risk_amount,
                "R": -1.0,
            },
        ]
        for t in self.targets:
            rows.append({
                "שלב": t.label,
                "יחס": t.rr_text,
                "מחיר": t.price,
                "מרחק %": direction_sign(self.direction) * (t.price - self.entry) / self.entry,
                "מניות": t.shares,
                "רווח/הפסד": t.profit,
                "R": t.r_multiple,
            })
        return rows


def build_plan(ticker: str, entry: float, stop: float, shares: int = 0,
               direction: Direction = "long",
               r_multiples: Sequence[float] = DEFAULT_R_MULTIPLES,
               weights: Optional[Sequence[float]] = None,
               account_value: Optional[float] = None,
               risk_pct: Optional[float] = None,
               earnings_date: Optional[date] = None,
               notes: str = "") -> TradePlan:
    """
    בונה תוכנית עסקה מלאה. זו נקודת הכניסה היחידה שהממשק צריך להכיר.

    אם account_value ו-risk_pct סופקו ו-shares=0, גודל הפוזיציה יחושב אוטומטית
    לפי כלל הסיכון.
    """
    r_unit = risk_per_share(entry, stop, direction)

    if shares <= 0 and account_value and risk_pct:
        shares = position_size(account_value, risk_pct, entry, stop, direction)["shares"]
    shares = max(int(shares), 0)

    if weights is None:
        weights = DEFAULT_SCALE_OUT[:len(r_multiples)]
    if len(weights) != len(r_multiples):
        raise ValueError("אורך רשימת המשקלים חייב להתאים למספר היעדים.")
    if not math.isclose(sum(weights), 1.0, abs_tol=1e-6):
        raise ValueError(f"סכום המשקלים חייב להיות 1.0 (התקבל {sum(weights)}).")

    # חלוקת מניות ליעדים ללא איבוד שברים: השארית נופלת ליעד האחרון
    allocated, targets = 0, []
    for i, (rm, w) in enumerate(zip(r_multiples, weights)):
        is_last = i == len(r_multiples) - 1
        t_shares = shares - allocated if is_last else math.floor(shares * w)
        allocated += t_shares
        price = target_price(entry, r_unit, rm, direction)
        targets.append(Target(
            r_multiple=rm,
            price=price,
            weight=w,
            label=TARGET_LABELS.get(rm, f"יעד {rm:g}R"),
            shares=t_shares,
            profit=t_shares * r_unit * rm,
        ))

    return TradePlan(
        ticker=ticker.upper().strip(),
        direction=direction,
        entry=entry,
        stop=stop,
        r_unit=r_unit,
        shares=shares,
        targets=targets,
        account_value=account_value,
        risk_pct=risk_pct,
        earnings_date=earnings_date,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# 4. דוחות כספיים
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EarningsAssessment:
    days: Optional[int]
    tier: str                 # מזהה פנימי
    label: str                # טקסט לתצוגה
    color: str                # מפתח צבע לממשק
    recommended_size_pct: float   # איזה חלק מהפוזיציה המקורית להשאיר
    action: str               # המלצה מנוסחת
    hard_rule: bool           # האם זו הנחיה קשיחה ולא רק תזכורת


def days_to_earnings(earnings_date: Optional[date],
                     today: Optional[date] = None) -> Optional[int]:
    """מספר ימי לוח עד לדוח. שלילי = הדוח כבר פורסם. None = אין תאריך."""
    if earnings_date is None:
        return None
    if isinstance(earnings_date, datetime):
        earnings_date = earnings_date.date()
    today = today or date.today()
    if isinstance(today, datetime):
        today = today.date()
    return (earnings_date - today).days


def earnings_risk_tier(days: Optional[int]) -> str:
    """סיווג רמת הסיכון לפי הקרבה לדוח."""
    if days is None:
        return "unknown"
    if days < 0:
        return "passed"
    if days == 0:
        return "today"
    if days <= 2:
        return "critical"
    if days <= 5:
        return "high"
    if days <= 10:
        return "elevated"
    return "clear"


_TIER_SPEC = {
    "clear":    ("מרחק בטוח מהדוח", "green",  1.00, "גודל פוזיציה מלא. הסטופ עדיין רלוונטי.", False),
    "elevated": ("הדוח מתקרב",      "yellow", 1.00, "אין להגדיל פוזיציה. לוודא שהסטופ מעודכן.", False),
    "high":     ("אזור חימום",      "orange", 0.75, "לצמצם ל-75%. אין כניסות חדשות בטיקר הזה.", False),
    "critical": ("אזור אסור",       "red",    0.50, "לממש לפחות מחצית. הסטופ לא מגן מפני פער.", True),
    "today":    ("דוח היום",        "red",    0.00, "לסגור לפני הפרסום, או להגדיר תקציב פער מפורש.", True),
    "passed":   ("הדוח פורסם",      "gray",   1.00, "התנודתיות מתכווצת. אפשר לחזור לניהול רגיל.", False),
    "unknown":  ("אין תאריך דוח",   "gray",   1.00, "לאמת ידנית מול לוח הדוחות לפני הגדלת חשיפה.", False),
}


def earnings_action(days: Optional[int], has_1r_locked: bool = False) -> EarningsAssessment:
    """
    המלצת חשיפה לקראת דוח.

    has_1r_locked – האם כבר מומש יעד 1 (1:1). אם כן, חלק מהסיכון כבר הוסר
    ולכן מותר להחזיק חשיפה גדולה יותר לתוך הדוח.
    """
    tier = earnings_risk_tier(days)
    label, color, size_pct, action, hard = _TIER_SPEC[tier]

    if has_1r_locked and tier in ("high", "critical"):
        size_pct = min(1.0, size_pct + 0.25)
        action += " (יעד 1 כבר מומש — הסיכון הנותר מופחת)."

    return EarningsAssessment(
        days=days, tier=tier, label=label, color=color,
        recommended_size_pct=size_pct, action=action, hard_rule=hard,
    )


def trim_plan(plan: TradePlan, keep_pct: float) -> dict:
    """כמה מניות למכור / להשאיר כדי להגיע לחשיפה מומלצת."""
    if not 0 <= keep_pct <= 1:
        raise ValueError("keep_pct חייב להיות בין 0 ל-1.")
    keep = math.floor(plan.shares * keep_pct)
    trim = plan.shares - keep
    return {
        "keep_shares": keep,
        "trim_shares": trim,
        "keep_notional": keep * plan.entry,
        "residual_risk": keep * plan.r_unit,
    }


# ---------------------------------------------------------------------------
# 5. סימולציית פערים (Gap Up / Gap Down)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GapOutcome:
    gap_pct: float
    open_price: float
    outcome: str           # מזהה: stop_breached / target_3 / target_2 / target_1 / open
    label: str             # טקסט לתצוגה
    fill_price: float      # המחיר בו העסקה בפועל נסגרת (או המחיר הנוכחי אם פתוחה)
    realized_r: float      # תוצאה ביחידות R
    pnl: float             # רווח/הפסד כספי
    slippage_r: float      # כמה R מעבר לתכנון (רלוונטי רק בפריצת סטופ)
    closed: bool


def simulate_gap(plan: TradePlan, gap_pct: float,
                 ref_price: Optional[float] = None) -> GapOutcome:
    """
    מדמה פתיחת מסחר אחרי דוח.

    ref_price – מחיר הסגירה לפני הדוח. ברירת מחדל: מחיר הכניסה.
    הפער מחושב ממנו, לא מהכניסה, כדי לאפשר סימולציה על פוזיציה שכבר ברווח.

    נקודה קריטית: פער מתחת לסטופ אינו מתמלא בסטופ. הפוזיציה נסגרת במחיר
    הפתיחה, ולכן ההפסד בפועל יכול להיות 2R או 3R ולא 1R. זה בדיוק הסיכון
    שסטופ רגיל אינו מכסה סביב דוחות.
    """
    ref = ref_price if ref_price is not None else plan.entry
    open_price = ref * (1.0 + gap_pct)
    sign = direction_sign(plan.direction)
    raw_r = sign * (open_price - plan.entry) / plan.r_unit

    stop_breached = (open_price <= plan.stop) if plan.direction == "long" \
        else (open_price >= plan.stop)

    if stop_breached:
        return GapOutcome(
            gap_pct=gap_pct, open_price=open_price, outcome="stop_breached",
            label="פריצת סטופ בפער — מילוי במחיר הפתיחה",
            fill_price=open_price, realized_r=raw_r,
            pnl=raw_r * plan.r_unit * plan.shares,
            slippage_r=abs(raw_r + 1.0) if raw_r < -1.0 else 0.0,
            closed=True,
        )

    # איזה יעד נפגע בפתיחה (פקודת לימיט מתמלאת במחיר הפתיחה, שהוא טוב יותר)
    hit = None
    for t in sorted(plan.targets, key=lambda x: x.r_multiple, reverse=True):
        reached = (open_price >= t.price) if plan.direction == "long" \
            else (open_price <= t.price)
        if reached:
            hit = t
            break

    if hit is None:
        return GapOutcome(
            gap_pct=gap_pct, open_price=open_price, outcome="open",
            label="הפוזיציה נשארת פתוחה — לא נפגע אף יעד",
            fill_price=open_price, realized_r=raw_r,
            pnl=raw_r * plan.r_unit * plan.shares,
            slippage_r=0.0, closed=False,
        )

    # כל המנות עד ליעד שנפגע מתמלאות במחיר הפתיחה
    filled = [t for t in plan.targets if t.r_multiple <= hit.r_multiple]
    filled_shares = sum(t.shares for t in filled)
    remaining = plan.shares - filled_shares
    pnl = raw_r * plan.r_unit * filled_shares + raw_r * plan.r_unit * remaining
    idx = plan.targets.index(hit) + 1

    return GapOutcome(
        gap_pct=gap_pct, open_price=open_price, outcome=f"target_{idx}",
        label=f"{hit.label} נפגע בפתיחה" + ("" if remaining == 0 else " — יתרה נשארת פתוחה"),
        fill_price=open_price, realized_r=raw_r, pnl=pnl,
        slippage_r=0.0, closed=(remaining == 0),
    )


def gap_scenario_table(plan: TradePlan,
                       gaps: Sequence[float] = DEFAULT_GAP_GRID,
                       ref_price: Optional[float] = None) -> list[GapOutcome]:
    """טבלת תרחישים מלאה, ממוינת מהפער השלילי לחיובי."""
    return [simulate_gap(plan, g, ref_price) for g in sorted(gaps)]


def worst_case_gap_loss(plan: TradePlan, gap_pct: float = -0.15,
                        ref_price: Optional[float] = None) -> dict:
    """כמה באמת עולה תרחיש הרע. משמש להצגת הפער בין הסיכון המתוכנן למציאות."""
    out = simulate_gap(plan, -abs(gap_pct) * direction_sign(plan.direction), ref_price)
    planned = -plan.risk_amount
    return {
        "planned_loss": planned,
        "actual_loss": out.pnl,
        "extra_loss": out.pnl - planned,
        "multiple_of_plan": abs(out.realized_r),
        "open_price": out.open_price,
    }


# ---------------------------------------------------------------------------
# 6. מצב פוזיציה קיימת ביחס למפת היעדים
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionStatus:
    current_price: float
    current_r: float              # איפה המחיר עכשיו, ביחידות R
    unrealized_pnl: float
    stop_breached: bool
    targets_hit: list             # רשימת כפולות R שכבר נפגעו
    next_target: Optional[Target]
    distance_to_next_pct: Optional[float]
    distance_to_stop_pct: float
    label: str
    color: str                    # מפתח צבע לממשק


def position_status(plan: TradePlan, current_price: float) -> PositionStatus:
    """
    ממקם פוזיציה פתוחה על מפת ה-R.

    שונה מ-simulate_gap: כאן המחיר כבר ידוע ואין הנחת פער. זו תמונת מצב,
    לא תרחיש.
    """
    if current_price <= 0:
        raise ValueError("מחיר נוכחי חייב להיות גדול מאפס.")

    sign = direction_sign(plan.direction)
    cur_r = r_multiple_of_price(current_price, plan.entry, plan.r_unit, plan.direction)
    breached = (current_price <= plan.stop) if plan.direction == "long" \
        else (current_price >= plan.stop)

    hit = [t.r_multiple for t in plan.targets
           if (current_price >= t.price if plan.direction == "long"
               else current_price <= t.price)]

    nxt = next((t for t in sorted(plan.targets, key=lambda x: x.r_multiple)
                if t.r_multiple not in hit), None)
    dist_next = (sign * (nxt.price - current_price) / current_price) if nxt else None
    dist_stop = sign * (current_price - plan.stop) / current_price

    if breached:
        label, color = "הסטופ נפרץ — הפוזיציה אמורה להיות סגורה", "red"
    elif len(hit) == len(plan.targets):
        label, color = "כל היעדים נפגעו", "green"
    elif hit:
        label, color = f"יעד {len(hit)} נפגע — הסיכון הופחת", "green"
    elif cur_r >= 0:
        label, color = "ברווח, טרם נפגע יעד", "yellow"
    else:
        label, color = "בהפסד, מעל הסטופ", "orange"

    return PositionStatus(
        current_price=current_price,
        current_r=cur_r,
        unrealized_pnl=cur_r * plan.r_unit * plan.shares,
        stop_breached=breached,
        targets_hit=hit,
        next_target=nxt,
        distance_to_next_pct=dist_next,
        distance_to_stop_pct=dist_stop,
        label=label,
        color=color,
    )


def breakeven_stop_after_target(plan: TradePlan, r_multiple: float = 1.0) -> float:
    """
    לאן להזיז את הסטופ אחרי שיעד מסוים נפגע.
    ברירת מחדל: אחרי יעד 1 מעבירים לנקודת האיזון.
    """
    if r_multiple <= 0:
        return plan.stop
    return plan.entry
