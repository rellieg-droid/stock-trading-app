"""
patch_add_stress_test_cvar.py
================================
מוסיף ל-options_engine.py:

1. stress_test_table() - טבלת P/L לפוזיציית שורט-פוט בתרחישי % שינוי קבועים
   (+20/+10/0/-10/-20/-30/-40/-50). משתמש ב-Leg/Position הקיימים - לא כותב
   נוסחת PnL חדשה, רק בונה Position("put", direction=-1, ...) וקורא ל-payoff_at.

2. historical_short_put_pnl_distribution() - פילוג P/L אמפירי מהיסטוריית
   מחירים בפועל (אותה שיטת "מחיר עתידי בעוד DTE ימים" כמו במודל ההיסטורי
   שכבר קיים - לא נוסחה חדשה).

3. expected_shortfall() - CVaR: ממוצע ה-X% הגרועים בפילוג נתון. פונקציה
   גנרית טהורה, לא תלויה בסוג הפוזיציה.

שימוש:
    python patch_add_stress_test_cvar.py            # dry-run
    python patch_add_stress_test_cvar.py --apply     # מבצע בפועל
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
    "def pop_iron_condor(short_put_delta: float, short_call_delta: float) -> float:\n"
    "    \"\"\"\n"
    "    הסתברות לרווח מלא באיירון קונדור.\n"
    "    שני סטרייקים קצרים, לכן זו לא 1 מינוס דלתא בודדת.\n"
    "    בדלתא 0.15 משני הצדדים התוצאה היא כ-70%, לא 85%.\n"
    "    \"\"\"\n"
    "    return max(0.0, 1.0 - abs(short_put_delta) - abs(short_call_delta))\n"
)

NEW_CODE = '''

# =============================================================================
# 6. סטרס טסט ו-CVaR לשורט-פוט - בונה על Leg/Position הקיימים, לא מכפיל נוסחה
# =============================================================================

_DEFAULT_STRESS_MOVES = (0.20, 0.10, 0.0, -0.10, -0.20, -0.30, -0.40, -0.50)


@dataclass(frozen=True)
class StressTestRow:
    pct_move: float                  # לדוגמה -0.30 = ירידה של 30%
    stressed_price: float
    pnl: float
    pct_of_capital: float | None      # None אם לא סופק הון זמין


def stress_test_table(
    S: float,
    strike: float,
    premium: float,
    contracts: int,
    available_capital: float | None = None,
    pct_moves: Sequence[float] = _DEFAULT_STRESS_MOVES,
) -> list[StressTestRow]:
    """
    P/L לפוזיציית שורט-פוט יחיד (cash-secured/naked) על פני תרחישי % קבועים.
    משתמש ב-Position/Leg הקיים - לא נוסחת PnL עצמאית.
    """
    position = Position(legs=[Leg("put", -1, contracts, premium, strike, label="שורט פוט")])
    rows = []
    for pct in pct_moves:
        stressed_price = S * (1.0 + pct)
        pnl = position.payoff_at(stressed_price)
        pct_of_capital = (pnl / available_capital) if available_capital else None
        rows.append(StressTestRow(pct_move=pct, stressed_price=stressed_price, pnl=pnl, pct_of_capital=pct_of_capital))
    return rows


def historical_short_put_pnl_distribution(
    closes: Sequence[float],
    strike: float,
    dte_days: int,
    premium: float,
    contracts: int,
) -> list[float]:
    """
    פילוג P/L אמפירי: לכל יום מסחר היסטורי, מה היה ה-P/L של שורט-פוט הזה
    אילו נפתח אז ופג dte_days ימים קדימה, לפי המחיר שבאמת קרה. אותה שיטת
    'מחיר עתידי' כמו historical_put_otm_probability - לא נוסחה חדשה.
    """
    n = len(closes)
    total = n - dte_days
    if total <= 0:
        return []
    position = Position(legs=[Leg("put", -1, contracts, premium, strike, label="שורט פוט")])
    return [position.payoff_at(closes[i + dte_days]) for i in range(total)]


def expected_shortfall(pnl_distribution: Sequence[float], tail_fraction: float = 0.05) -> float | None:
    """
    CVaR: ממוצע ה-tail_fraction (ברירת מחדל 5%) הגרועים בפילוג. None אם
    הפילוג ריק. פונקציה גנרית - לא תלויה בסוג הפוזיציה שהפיקה את הפילוג.
    """
    if not pnl_distribution:
        return None
    ordered = sorted(pnl_distribution)
    n_tail = max(1, int(len(ordered) * tail_fraction))
    worst = ordered[:n_tail]
    return sum(worst) / len(worst)
'''


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
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

    print("עוגן נמצא פעם אחת. ast.parse עבר בהצלחה.")

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
