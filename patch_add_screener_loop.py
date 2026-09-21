"""
patch_add_screener_loop.py
===========================
מוסיפה ל-riskshield_tab.py: _run_screener() - לולאה שרצה על רשימת
טיקרים, שואבת לכל אחד S / closes / IV דרך אותם _try_fetch_* הקיימים,
מריצה build_screener_row() (options_engine.py) ומרכזת הכל ל-DataFrame
אחד. שכבת אוסף בלבד - אין כאן חישוב חדש, רק ריכוז.

שימוש:
    python patch_add_screener_loop.py                 # dry-run
    python patch_add_screener_loop.py --apply          # מבצע בפועל
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR = (
    "def _try_fetch_closes(ticker: str, period: str = \"1y\") -> Optional[list]:\n"
    "    \"\"\"שולף סדרת סגירות יומית להיסטוריה. נכשל בשקט.\"\"\"\n"
    "    if not ticker:\n"
    "        return None\n"
    "    try:\n"
    "        import yfinance as yf\n"
    "        hist = yf.Ticker(ticker).history(period=period)\n"
    "        if hist.empty or len(hist) < 3:\n"
    "            return None\n"
    "        return hist[\"Close\"].tolist()\n"
    "    except Exception:\n"
    "        return None\n"
)

NEW_CODE = '''

# ---------------------------------------------------------------------------
# סורק רב-מניות - שכבת ריכוז בלבד. שואבת עם אותם _try_fetch_* שכבר בקובץ,
# מחשבת עם build_screener_row (options_engine.py) - אין כאן נוסחה חדשה.
# ---------------------------------------------------------------------------

def _run_screener(
    tickers,
    target_put_delta: float = 0.20,
    dte_days: int = 30,
    closes_period: str = "10y",
):
    """
    מריצה build_screener_row על כל טיקר ברשימה, טיקר אחרי טיקר (לא
    במקביל - yfinance לא אוהב הצפה של בקשות). טיקר שנכשל בשליפת מחיר
    (סימבול שגוי / בעיית רשת) לא מפיל את כל הסריקה - הוא מקבל שורה עם
    note בלבד, שאר העמודות NaN, בדיוק כמו שאר ה-_try_fetch_* בקובץ
    שנכשלים בשקט. מחזירה pandas.DataFrame, שורה אחת לטיקר.
    """
    import pandas as pd
    from dataclasses import asdict
    from options_engine import build_screener_row

    rows = []
    for raw_ticker in tickers:
        ticker = raw_ticker.strip().upper()
        if not ticker:
            continue

        spot = _try_fetch_spot(ticker)
        if spot is None:
            rows.append({"ticker": ticker, "spot": None,
                        "note": "לא נמצא מחיר - טיקר שגוי או בעיית רשת"})
            continue

        closes = _try_fetch_closes(ticker, period=closes_period)
        iv_pct = _try_fetch_atm_iv(ticker)
        iv = (iv_pct / 100.0) if iv_pct is not None else None

        row = build_screener_row(
            ticker=ticker, S=spot, closes=closes, iv=iv,
            target_put_delta=target_put_delta, dte_days=dte_days,
        )
        rows.append(asdict(row))

    return pd.DataFrame(rows)
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="מבצע בפועל. בלי הדגל הזה - dry-run בלבד.")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} בתיקייה הנוכחית.", file=sys.stderr)
        return 1

    raw = TARGET.read_bytes()
    used_crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")

    anchor_normalized = ANCHOR.replace("\r\n", "\n")
    count = text.count(anchor_normalized)
    if count == 0:
        print("האנקור לא נמצא. ייתכן שהקובץ השתנה - יש לעדכן ידנית.", file=sys.stderr)
        return 1
    if count > 1:
        print(f"האנקור נמצא {count} פעמים - לא ייחודי, עוצר.", file=sys.stderr)
        return 1

    new_text = text.replace(anchor_normalized, anchor_normalized + NEW_CODE, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת תחביר בקוד החדש: {e}", file=sys.stderr)
        return 1

    print("--- תצוגה מקדימה: הקוד שיתווסף ---")
    print(NEW_CODE)
    print("--- סוף תצוגה מקדימה ---")

    if not args.apply:
        print("\nDry-run בלבד. הריצי עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(TARGET.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נשמר: {backup}")

    out_text = new_text.replace("\n", "\r\n") if used_crlf else new_text
    TARGET.write_bytes(out_text.encode("utf-8"))
    print(f"בוצע. {TARGET} עודכן.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
