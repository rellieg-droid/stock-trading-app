"""
patch_add_expected_move_ui.py
===============================
מוסיף כרטיס "תזוזה צפויה (Expected Move)" לטאב "הסתברות OTM", מייד אחרי
כרטיס המודל (Black-Scholes) - לא תלוי בהיסטוריית מחירים, אז מוצג תמיד.

דורש: patch_add_expected_move.py כבר רץ על options_engine.py.

שימוש:
    python patch_add_expected_move_ui.py            # dry-run
    python patch_add_expected_move_ui.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

IMPORT_OLD = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    ")\n"
)
IMPORT_NEW = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    "    expected_move, strike_distance_in_expected_moves,\n"
    ")\n"
)

CARD_OLD = (
    '            grid_normal = _metric("הסתברות OTM - מודל", f"{normal_prob:.1%}" if normal_prob is not None else "—")\n'
    '            _card("מודל (Black-Scholes)", f\'<div class="rs-grid">{grid_normal}</div>\')\n'
)
CARD_NEW = (
    '            grid_normal = _metric("הסתברות OTM - מודל", f"{normal_prob:.1%}" if normal_prob is not None else "—")\n'
    '            _card("מודל (Black-Scholes)", f\'<div class="rs-grid">{grid_normal}</div>\')\n'
    '\n'
    '            # --- תזוזה צפויה - לא תלוי בהיסטוריה, זמין תמיד ------------------\n'
    '            em = expected_move(S=prob_S, sigma=prob_sigma_pct / 100.0, T_days=prob_days)\n'
    '            em_distance = strike_distance_in_expected_moves(S=prob_S, K=prob_K, move=em.move)\n'
    '            grid_em = "".join([\n'
    '                _metric("תזוזה צפויה", f"±${em.move:,.2f}"),\n'
    '                _metric("טווח צפוי", f"${em.low:,.2f} - ${em.high:,.2f}"),\n'
    '                _metric("מרחק הסטרייק", f"{em_distance:.2f}x תזוזה צפויה" if em_distance is not None else "—"),\n'
    '            ])\n'
    '            em_explain = (\n'
    '                \'<div class="rs-explain">קירוב מהנוסחה S×IV×√T (סטיית תקן אחת, לא טווח \'\n'
    '                \'מובטח - בהנחת התפלגות נורמלית, שראינו שלא תמיד מחזיקה). מרחק הסטרייק \'\n'
    '                \'חיובי אומר שהוא מתחת למחיר הנוכחי; ככל שהמספר גבוה יותר, הסטרייק רחוק \'\n'
    '                \'יותר ביחס לתזוזה הצפויה.\'\n'
    '                \'</div>\'\n'
    '            )\n'
    '            _card("תזוזה צפויה (Expected Move)", f\'<div class="rs-grid">{grid_em}</div>{em_explain}\')\n'
)


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
        text = apply_single_anchor(text, CARD_OLD, CARD_NEW, "expected-move-card")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("שני העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
