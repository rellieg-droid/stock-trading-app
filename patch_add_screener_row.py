"""
patch_add_screener_row.py
==========================
מוסיף ל-options_engine.py: ScreenerRow dataclass + build_screener_row().
שכבת ריכוז מעל פונקציות קיימות בלבד - לא נוסחה חדשה, לא מיזוג לציון יחיד.

שימוש:
    python patch_add_screener_row.py                 # dry-run, רק מציג
    python patch_add_screener_row.py --apply          # מבצע בפועל
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("options_engine.py")

ANCHOR = (
    "def expected_shortfall(pnl_distribution: Sequence[float], tail_fraction: float = 0.05) -> float | None:\n"
    "    \"\"\"\n"
    "    CVaR: ממוצע ה-tail_fraction (ברירת מחדל 5%) הגרועים בפילוג. None אם\n"
    "    הפילוג ריק. פונקציה גנרית - לא תלויה בסוג הפוזיציה שהפיקה את הפילוג.\n"
    "    \"\"\"\n"
    "    if not pnl_distribution:\n"
    "        return None\n"
    "    ordered = sorted(pnl_distribution)\n"
    "    n_tail = max(1, int(len(ordered) * tail_fraction))\n"
    "    worst = ordered[:n_tail]\n"
    "    return sum(worst) / len(worst)\n"
)

NEW_CODE = '''

# =============================================================================
# 7. סורק רב-מניות - שכבת ריכוז מעל הפונקציות הקיימות, לא נוסחה חדשה
# =============================================================================
#
# דלתא יעד אחידה לכל הטיקרים (למשל 0.20 לכולם), לא סטרייק דולרי קבוע -
# כך ההשוואה בין מניות שונות הוגנת (אותו "עומק" יחסי מהמחיר הנוכחי).
# put_premium כאן תיאורטי (Black-Scholes לפי ה-IV שנמסר) - לא מחיר שוק
# בפועל. שליפת bid/ask אמיתי דורשת קריאת options chain נפרדת לכל טיקר,
# שכבה נוספת ויקרה יותר מעל זה - מוצהר כאן ב-note, לא מוסתר.

@dataclass(frozen=True)
class ScreenerRow:
    """שורה אחת בטבלת הסריקה. כל שדה מגיע מפונקציה קיימת - אין חישוב חדש כאן."""
    ticker: str
    spot: float
    strike: float | None
    dte_days: int
    iv: float | None
    rv_rank: float | None
    rv_percentile: float | None
    iv_rv_spread: float | None
    expected_move_pct: float | None
    put_premium: float | None
    put_delta: float | None
    breakeven: float | None
    prob_otm_model: float | None
    prob_otm_fat_tail: float | None
    prob_otm_historical: float | None
    xem_distance: float | None
    cvar_5pct: float | None
    max_loss: float | None
    note: str = ""


def build_screener_row(
    ticker: str,
    S: float,
    closes: Sequence[float] | None,
    iv: float | None,
    target_put_delta: float,
    dte_days: int,
    r: float = 0.045,
    strike_round_to: float | None = None,
) -> ScreenerRow:
    """
    בונה שורת סריקה אחת. S / closes / iv כבר שאובים מבחוץ (yfinance
    וכו') - אותה הפרדת I/O-מול-חישוב שכבר קיימת ברמת הקובץ הזה.
    """

    def _empty(note: str) -> ScreenerRow:
        return ScreenerRow(
            ticker=ticker, spot=S, strike=None, dte_days=dte_days, iv=iv,
            rv_rank=None, rv_percentile=None, iv_rv_spread=None,
            expected_move_pct=None, put_premium=None, put_delta=None,
            breakeven=None, prob_otm_model=None, prob_otm_fat_tail=None,
            prob_otm_historical=None, xem_distance=None, cvar_5pct=None,
            max_loss=None, note=note,
        )

    if iv is None or S <= 0:
        return _empty("אין IV זמין - טיקר דולג")

    T = dte_days / 365.0
    try:
        strike = strike_from_delta("put", target_put_delta, S, T, iv, r, round_to=strike_round_to)
        g = bs_greeks("put", S, strike, T, iv, r)
    except ValueError as e:
        return _empty(f"לא נמצא סטרייק לדלתא {target_put_delta}: {e}")

    premium = g.price
    rv = realized_vol(closes) if closes else None
    rank = rv_rank(closes) if closes else None
    pct = rv_percentile(closes) if closes else None
    iv_rv_spread = (iv - rv) if rv is not None else None
    breakeven = short_put_breakeven(strike, premium)

    em = expected_move(S, iv, dte_days)
    em_pct = em.move / S
    xem = strike_distance_in_expected_moves(S, strike, em.move)

    prob_hist = fat = cvar = None
    if closes:
        hist = historical_put_otm_probability(closes, strike, dte_days)
        prob_hist = hist.weighted_otm
        log_returns = [log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
        fat_result = fat_tail_otm_probability(log_returns, S, strike, dte_days)
        fat = fat_result.otm_probability
        pnl_dist = historical_short_put_pnl_distribution(closes, strike, dte_days, premium, contracts=1)
        cvar = expected_shortfall(pnl_dist, tail_fraction=0.05)

    max_loss = Position(legs=[Leg("put", -1, 1, premium, strike)]).max_loss()
    note = "פרמיה תיאורטית (BS), לא מחיר שוק" if closes else "אין היסטוריית מחירים - חלק מהמדדים לא זמינים"

    return ScreenerRow(
        ticker=ticker, spot=S, strike=strike, dte_days=dte_days, iv=iv,
        rv_rank=rank, rv_percentile=pct, iv_rv_spread=iv_rv_spread,
        expected_move_pct=em_pct, put_premium=premium, put_delta=g.delta,
        breakeven=breakeven, prob_otm_model=g.prob_otm, prob_otm_fat_tail=fat,
        prob_otm_historical=prob_hist, xem_distance=xem, cvar_5pct=cvar,
        max_loss=max_loss, note=note,
    )
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
        print("האנקור לא נמצא. ייתכן שהקובץ השתנה מאז שהפאץ' נכתב - יש לעדכן ידנית.", file=sys.stderr)
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

    print("--- תצוגה מקדימה: הקוד שיתווסף (סוף הקובץ) ---")
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
