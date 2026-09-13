"""
patch_add_expected_move.py
============================
מוסיף ל-options_engine.py:
1. expected_move() - תזוזה צפויה, מהנוסחה S*IV*sqrt(T) (קירוב סטנדרטי;
   ATM straddle מדויק יותר אך דורש מחירי אופציות בפועל שלא תמיד זמינים -
   לא ממומש בשלב הזה, מתועד כמגבלה מוצהרת).
2. strike_distance_in_expected_moves() - כמה "תזוזות צפויות" הסטרייק
   מרוחק מהמחיר הנוכחי. מדד תיאורי טהור, לא שיפוט.

שימוש:
    python patch_add_expected_move.py            # dry-run
    python patch_add_expected_move.py --apply     # מבצע בפועל
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
    "def rv_percentile(\n"
    "    closes: Sequence[float],\n"
    "    vol_window: int = 20,\n"
    "    lookback_days: int = 252,\n"
    ") -> float | None:\n"
    "    \"\"\"אחוז הימים בטווח שבהם ה-RV היה נמוך או שווה ל-RV הנוכחי. None אם אין מספיק נתונים.\"\"\"\n"
    "    series = _rolling_rv_series(closes, vol_window, lookback_days)\n"
    "    if len(series) < 2:\n"
    "        return None\n"
    "    current = series[-1]\n"
    "    count_leq = sum(1 for v in series if v <= current)\n"
    "    return count_leq / len(series) * 100.0\n"
)

NEW_CODE = '''

# =============================================================================
# 1e. תזוזה צפויה (Expected Move) ומרחק הסטרייק ממנה
# =============================================================================
#
# קירוב מהנוסחה הסטנדרטית S*IV*sqrt(T), לא מ-ATM straddle (מדויק יותר אבל
# דורש מחירי אופציות בפועל - לא זמין כאן כרגע). מתויג ככזה בפלט.


@dataclass(frozen=True)
class ExpectedMove:
    move: float          # תזוזה צפויה בדולרים (סטיית תקן אחת, לא טווח מובטח)
    low: float           # S - move
    high: float          # S + move
    method: str = "formula"  # "formula" (S*IV*sqrt(T)) לעומת "straddle" (לא ממומש עדיין)


def expected_move(S: float, sigma: float, T_days: float) -> ExpectedMove:
    """
    תזוזה צפויה = S * sigma * sqrt(T בשנים). זו סטיית תקן אחת - כ-68% מהמקרים
    (בהנחת התפלגות נורמלית, שכבר ידוע לנו שלא תמיד מחזיקה - ראו מודל Fat-tail).
    """
    if S <= 0:
        raise ValueError("S must be positive")
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if T_days < 0:
        raise ValueError("T_days must be non-negative")
    move = S * sigma * sqrt(T_days / 365.0)
    return ExpectedMove(move=move, low=S - move, high=S + move, method="formula")


def strike_distance_in_expected_moves(S: float, K: float, move: float) -> float | None:
    """
    כמה 'תזוזות צפויות' מרוחק הסטרייק מהמחיר הנוכחי. חיובי = הסטרייק מתחת
    למחיר (רלוונטי לפוט). None אם move==0 (למשל IV=0 או T=0) - לא חלוקה באפס.
    """
    if move == 0:
        return None
    return (S - K) / move
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
