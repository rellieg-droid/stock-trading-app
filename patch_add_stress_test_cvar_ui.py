"""
patch_add_stress_test_cvar_ui.py
===================================
מוסיף לטאב "הסתברות OTM":
1. שדות קלט: פרמיה, מספר חוזים, הון זמין (אופציונלי - להצגת % מההון)
2. כרטיס "סטרס טסט" - טבלת P/L בתרחישי % קבועים, זמין תמיד (לא תלוי בהיסטוריה)
3. כרטיס "CVaR (Expected Shortfall)" - בתוך הענף שדורש היסטוריה, ליד RV Rank

דורש: patch_add_stress_test_cvar.py כבר רץ על options_engine.py.

שימוש:
    python patch_add_stress_test_cvar_ui.py            # dry-run
    python patch_add_stress_test_cvar_ui.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: ייבוא ---------------------------------------------------------
IMPORT_OLD = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    "    expected_move, strike_distance_in_expected_moves,\n"
    ")\n"
)
IMPORT_NEW = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    "    expected_move, strike_distance_in_expected_moves,\n"
    "    stress_test_table, historical_short_put_pnl_distribution, expected_shortfall,\n"
    ")\n"
)

# --- עוגן 2: שדות קלט חדשים לפני הכפתור ------------------------------------
INPUTS_OLD = (
    '        prob_r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,\n'
    '                                      key=f"{key_prefix}_prob_r", help=_HELP["r"])\n'
)
INPUTS_NEW = (
    '        prob_r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,\n'
    '                                      key=f"{key_prefix}_prob_r", help=_HELP["r"])\n'
    '\n'
    '        stress_cols = st.columns(3)\n'
    '        with stress_cols[0]:\n'
    '            prob_premium = st.number_input("פרמיה שהתקבלה ($)", min_value=0.01, value=2.0,\n'
    '                                            key=f"{key_prefix}_prob_premium", help=_HELP["iv_price"])\n'
    '        with stress_cols[1]:\n'
    '            prob_contracts = st.number_input("מספר חוזים", min_value=1, value=1,\n'
    '                                              key=f"{key_prefix}_prob_contracts")\n'
    '        with stress_cols[2]:\n'
    '            prob_capital = st.number_input("הון זמין ($, אופציונלי - להצגת % מההון)", min_value=0.0, value=0.0,\n'
    '                                            key=f"{key_prefix}_prob_capital")\n'
)

# --- עוגן 3: אחרי כרטיס Expected Move - כרטיס סטרס טסט (תמיד זמין) -------
STRESS_CARD_OLD = (
    '            _card("תזוזה צפויה (Expected Move)", f\'<div class="rs-grid">{grid_em}</div>{em_explain}\')\n'
)
STRESS_CARD_NEW = STRESS_CARD_OLD + '''
            # --- סטרס טסט - תרחישי % קבועים, לא תלוי בהיסטוריה --------------
            capital_arg = prob_capital if prob_capital > 0 else None
            stress_rows = stress_test_table(
                S=prob_S, strike=prob_K, premium=prob_premium, contracts=int(prob_contracts),
                available_capital=capital_arg,
            )
            grid_stress = []
            for row in stress_rows:
                label = f"{row.pct_move:+.0%} (${row.stressed_price:,.0f})"
                value = f"${row.pnl:,.2f}"
                if capital_arg:
                    value += f" ({row.pct_of_capital:+.1%})"
                grid_stress.append(_metric(label, value))
            stress_explain = (
                '<div class="rs-explain">P/L של שורט-פוט יחיד בתרחישי % קבועים ביחס למחיר הנוכחי - '
                'משתמש באותו מנוע payoff כמו שאר האסטרטגיות בקובץ, לא נוסחה נפרדת. '
                'בסוגריים: % מההון הזמין, אם הוזן.</div>'
            )
            _card("סטרס טסט", f'<div class="rs-grid">{"".join(grid_stress)}</div>{stress_explain}')
'''

# --- עוגן 4: אחרי כרטיס RV Rank - CVaR היסטורי (דורש closes) --------------
CVAR_CARD_OLD = (
    '                _card("RV Rank (תחליף זמני ל-IV Rank)", f\'<div class="rs-grid">{grid_rv}</div>{rv_explain}\')\n'
)
CVAR_CARD_NEW = CVAR_CARD_OLD + '''
                pnl_dist = historical_short_put_pnl_distribution(
                    closes, strike=prob_K, dte_days=int(prob_days),
                    premium=prob_premium, contracts=int(prob_contracts),
                )
                es = expected_shortfall(pnl_dist, tail_fraction=0.05)
                if es is not None:
                    grid_cvar = [_metric("CVaR (5% הגרועים ביותר)", f"${es:,.2f}")]
                    if capital_arg:
                        grid_cvar.append(_metric("CVaR כ-% מההון", f"{es / capital_arg:+.1%}"))
                    cvar_explain = (
                        '<div class="rs-explain">ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר '
                        f'(מתוך {len(pnl_dist)} תקופות היסטוריות בפועל) - לא תרחיש קיצון בודד ושרירותי, '
                        'אלא ממוצע על פני כל הפעמים שבאמת היה גרוע.</div>'
                    )
                    _card("CVaR (Expected Shortfall)", f'<div class="rs-grid">{"".join(grid_cvar)}</div>{cvar_explain}')
'''


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def apply_single_anchor(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"עוגן '{label}' נמצא {count} פעמים (צריך בדיוק 1)")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    try:
        text = apply_single_anchor(text, IMPORT_OLD, IMPORT_NEW, "import")
        text = apply_single_anchor(text, INPUTS_OLD, INPUTS_NEW, "inputs")
        text = apply_single_anchor(text, STRESS_CARD_OLD, STRESS_CARD_NEW, "stress-test-card")
        text = apply_single_anchor(text, CVAR_CARD_OLD, CVAR_CARD_NEW, "cvar-card")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("ארבעת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

    if not args.apply:
        print("Dry-run בלבד. הרץ עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(f".py.{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נוצר: {backup}")

    out_bytes = text.replace("\n", line_style).encode("utf-8")
    TARGET.write_bytes(out_bytes)
    print(f"נכתב בהצלחה: {TARGET.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
