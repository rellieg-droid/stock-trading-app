"""
patch_add_protection_table.py
================================
מוסיף ל-options_engine.py: protection_table() - כמה הגנה בדולרים נותן
פוט מגן בכל תרחיש סטרס. משתמש ב-protective_put() ו-Position/Leg הקיימים -
לא נוסחת PnL עצמאית, ולא ציון/דירוג - רק מספרים גולמיים לכל תרחיש.

שימוש:
    python patch_add_protection_table.py            # dry-run
    python patch_add_protection_table.py --apply     # מבצע בפועל
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
    "def protective_put(shares: int, stock_entry: float, put_strike: float,\n"
    "                   put_premium: float, contracts: int | None = None) -> Position:\n"
    "    \"\"\"מניה + פוט מגן. ברירת מחדל: חוזה אחד לכל 100 מניות.\"\"\"\n"
    "    contracts = contracts if contracts is not None else shares / CONTRACT_MULTIPLIER\n"
    "    return Position(\n"
    "        name=\"Protective Put\",\n"
    "        legs=[\n"
    "            Leg(\"stock\", +1, shares, stock_entry, label=\"מניות\"),\n"
    "            Leg(\"put\", +1, contracts, put_premium, put_strike, label=\"ביטוח\"),\n"
    "        ],\n"
    "    )\n"
)

NEW_CODE = '''

# =============================================================================
# 4b. טבלת הגנה - כמה PUT מגן שווה בפועל, בדולרים, בכל תרחיש
# =============================================================================
#
# בונה על protective_put()/Position/Leg הקיימים. אין כאן ציון "הגנה", אין
# "הגנה הכי טובה" - רק המספרים הגולמיים בכל תרחיש, כמו שכל שאר הטבלאות
# בקובץ הזה עובדות.

_DEFAULT_PROTECTION_MOVES = (0.0, -0.10, -0.20, -0.30, -0.40, -0.50, -0.60)


@dataclass(frozen=True)
class ProtectionRow:
    pct_move: float
    stressed_price: float
    unhedged_pnl: float       # P/L של מניה בלבד, בלי ביטוח
    hedged_pnl: float         # P/L של מניה + פוט מגן
    protection_amount: float  # hedged_pnl - unhedged_pnl: כמה ההגנה שיפרה את התוצאה
    protection_pct: float | None  # % מההפסד (הלא-מוגן) שקוזז. None אם לא הייתה הפסד מלכתחילה


def protection_table(
    shares: int,
    stock_entry: float,
    strike: float,
    premium: float,
    contracts: int | None = None,
    pct_moves: Sequence[float] = _DEFAULT_PROTECTION_MOVES,
) -> list[ProtectionRow]:
    """
    משווה P/L של 'מניה בלבד' מול 'מניה + פוט מגן' על פני סדרת תרחישי ירידה.
    protection_pct מחושב רק כשהייתה הפסד ללא הגנה (unhedged_pnl < 0) - אחרת
    השאלה 'כמה % מההפסד קוזז' לא מוגדרת, ומוצג None ולא 0 או ערך שרירותי.
    """
    hedged = protective_put(shares, stock_entry, strike, premium, contracts)
    unhedged = Position(legs=[Leg("stock", +1, shares, stock_entry, label="מניות בלבד")])

    rows = []
    for pct in pct_moves:
        price = stock_entry * (1.0 + pct)
        unhedged_pnl = unhedged.payoff_at(price)
        hedged_pnl = hedged.payoff_at(price)
        protection_amount = hedged_pnl - unhedged_pnl
        protection_pct = (protection_amount / -unhedged_pnl) if unhedged_pnl < 0 else None
        rows.append(ProtectionRow(
            pct_move=pct, stressed_price=price,
            unhedged_pnl=unhedged_pnl, hedged_pnl=hedged_pnl,
            protection_amount=protection_amount, protection_pct=protection_pct,
        ))
    return rows


def insurance_cost(premium: float, contracts: float) -> float:
    """עלות הביטוח בדולרים: פרמיה × 100 × חוזים. לא כולל עמלות (מתווספות בשכבת ה-UI אם רלוונטי)."""
    return premium * CONTRACT_MULTIPLIER * contracts
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
