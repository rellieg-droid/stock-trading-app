"""
patch_add_probability_models.py
================================
מוסיף ל-options_engine.py שני מודלי הסתברות חדשים ל-OTM (Slice 1, שלב 1):

1. historical_put_otm_probability() - הסתברות היסטורית לפי חלונות 1/3/5/10 שנים,
   כל תקופה מוצגת בנפרד + ממוצע משוקלל. אין ניקוד, אין מיזוג להחלטה.
2. student_t_cdf() + fat_tail_otm_probability() - מודל Fat-tail (Student-t) המחושב
   ישירות עם פונקציית הבטא הבלתי-שלמה, בלי scipy - תואם את דרישת "ספריית התקן בלבד"
   שכתובה בראש הקובץ המקורי.

מודל ה-Normal כבר קיים (bs_greeks().prob_otm) - לא נבנה מחדש.

שימוש:
    python patch_add_probability_models.py                 # dry-run, רק מציג מה ישתנה
    python patch_add_probability_models.py --apply          # מבצע בפועל, יוצר .bak

הערות:
- קורא בייטים גולמיים, מזהה CRLF/LF, מנרמל ל-\\n לצורך התאמת העוגן, וכותב חזרה
  באותו סגנון שורות שהיה בקובץ המקורי (שומר CRLF אם היה, לא כופה שינוי).
- בדיקת עוגן יחיד: נכשל בקול אם העוגן מופיע 0 או יותר מפעם אחת.
- בדיקת ast.parse לפני כתיבה בפועל.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("options_engine.py")

ANCHOR = (
    "def iv_rv_ratio(iv: float, rv: float) -> float:\n"
    "    \"\"\"\n"
    "    יחס IV/RV. מעל 1 אומר שהשוק מתמחר יותר תנודתיות ממה שהמניה עשתה בפועל,\n"
    "    וזה מה שמצדיק מכירת תנודתיות. rv אפס מחזיר אינסוף.\n"
    "    \"\"\"\n"
    "    return float(\"inf\") if rv <= 0 else iv / rv\n"
)

NEW_CODE = '''

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
'''


def normalize(text_bytes: bytes) -> tuple[str, str]:
    """מזהה CRLF מול LF, מחזיר (טקסט מנורמל ל-\\n, סגנון שורה מקורי)."""
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="מבצע בפועל (ברירת מחדל: dry-run)")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    count = text.count(ANCHOR)
    if count != 1:
        print(f"עוגן נמצא {count} פעמים (צריך בדיוק 1). לא בוצע שינוי.")
        return 1

    new_text = text.replace(ANCHOR, ANCHOR + NEW_CODE, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    added_lines = new_text.count("\n") - text.count("\n")
    print(f"עוגן נמצא פעם אחת. ast.parse עבר בהצלחה. יתווספו כ-{added_lines} שורות.")

    if not args.apply:
        print("Dry-run בלבד. הרץ עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(f".py.{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נוצר: {backup}")

    out_bytes = new_text.replace("\n", line_style).encode("utf-8")
    TARGET.write_bytes(out_bytes)
    print(f"נכתב בהצלחה: {TARGET.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
