"""
patch_add_rv_rank.py
=====================
מוסיף ל-options_engine.py שתי פונקציות טהורות: rv_rank ו-rv_percentile.

הקשר: IV Rank אמיתי דורש היסטוריית IV (לא קיימת ב-yfinance/Yahoo - הם
נותנים רק תמונת מצב נוכחית של שרשרת אופציות, לא ארכיון). RV Rank הוא
תחליף מוצהר שמבוסס על תנודתיות ממומשת (יש לה היסטוריה מלאה כבר, כי היא
נגזרת ממחיר המניה). זה לא אותו דבר - RV מתאר מה קרה, IV מתאר מה מתומחר -
ולכן זה חייב תמיד להיות מתויג "RV Rank", לא "IV Rank", בממשק.

שימוש:
    python patch_add_rv_rank.py            # dry-run
    python patch_add_rv_rank.py --apply     # מבצע בפועל
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
