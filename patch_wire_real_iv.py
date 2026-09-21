"""
patch_wire_real_iv.py
========================
מחבר את RiskShield לפונקציה שכבר קיימת אצלך - fetch_atm_iv() ב-
strategy_data.py - בדיוק אותה פונקציה שמייצרת את באדג' "IV 32.3%" בכותרת
הראשית של האפליקציה. עכשיו שדות ה-IV בטאבים "מחיר וגריקס" ו-"הסתברות OTM"
יתמלאו עם IV אמיתי מהשוק במקום ברירת מחדל קבועה של 30%.

ייבוא עצל (lazy import) בתוך try/except, באותו דפדוק בדיוק כמו ב-
alpha_paper_trading.py._iv_stats - נכשל בשקט אם strategy_data לא נגיש
מהתיקייה הזו, בלי לשבור שום דבר.

שימוש:
    python patch_wire_real_iv.py            # dry-run
    python patch_wire_real_iv.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: הוספת helper אחרי _try_fetch_spot ----------------------------
HELPER_ANCHOR = (
    "def _try_fetch_spot(ticker: str) -> Optional[float]:\n"
    "    \"\"\"שולף מחיר אחרון דרך yfinance. נכשל בשקט - בלי badge, בלי crash.\"\"\"\n"
    "    if not ticker:\n"
    "        return None\n"
    "    try:\n"
    "        import yfinance as yf\n"
    "        hist = yf.Ticker(ticker).history(period=\"5d\")\n"
    "        if hist.empty:\n"
    "            return None\n"
    "        return float(hist[\"Close\"].iloc[-1])\n"
    "    except Exception:\n"
    "        return None\n"
)
HELPER_NEW = HELPER_ANCHOR + '''

def _try_fetch_atm_iv(ticker: str) -> Optional[float]:
    """
    IV אמיתי מהשוק (ATM, תפוגה 20-60 יום) - אותה fetch_atm_iv() מ-strategy_data.py
    שכבר מייצרת את באדג' ה-IV בכותרת הראשית. מחזיר אחוזים (32.3, לא 0.323).
    נכשל בשקט (None) אם strategy_data לא נגיש או שאין אופציות לטיקר.
    """
    if not ticker:
        return None
    try:
        from strategy_data import fetch_atm_iv
        iv = fetch_atm_iv(ticker)
        if iv is None:
            return None
        return float(iv) * 100.0
    except Exception:
        return None
'''

# --- עוגן 2: sigma_pct בטאב מחיר וגריקס ------------------------------------
BS_SIGMA_OLD = (
    '            sigma_pct = st.number_input("IV (%)", min_value=0.1, value=30.0,\n'
    '                                         key=f"{key_prefix}_bs_sigma", help=_HELP["sigma"])\n'
)
BS_SIGMA_NEW = (
    '            _bs_iv_live = _try_fetch_atm_iv(ticker)\n'
    '            sigma_pct = st.number_input(\n'
    '                "IV (%)", min_value=0.1,\n'
    '                value=float(round(_bs_iv_live, 1)) if _bs_iv_live else 30.0,\n'
    '                key=f"{key_prefix}_bs_sigma_{ticker}", help=_HELP["sigma"],\n'
    '            )\n'
    '            if _bs_iv_live:\n'
    '                st.caption(f"נמשך אוטומטית משוק אמיתי: {_bs_iv_live:.1f}%")\n'
)

# --- עוגן 3: prob_sigma_pct בטאב הסתברות OTM -------------------------------
PROB_SIGMA_OLD = (
    '            prob_sigma_pct = st.number_input("IV למודל (%)", min_value=0.1, value=30.0,\n'
    '                                              key=f"{key_prefix}_prob_sigma", help=_HELP["sigma"])\n'
)
PROB_SIGMA_NEW = (
    '            _prob_iv_live = _try_fetch_atm_iv(ticker)\n'
    '            prob_sigma_pct = st.number_input(\n'
    '                "IV למודל (%)", min_value=0.1,\n'
    '                value=float(round(_prob_iv_live, 1)) if _prob_iv_live else 30.0,\n'
    '                key=f"{key_prefix}_prob_sigma_{ticker}", help=_HELP["sigma"],\n'
    '            )\n'
    '            if _prob_iv_live:\n'
    '                st.caption(f"נמשך אוטומטית משוק אמיתי: {_prob_iv_live:.1f}%")\n'
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
        text = apply_single_anchor(text, HELPER_ANCHOR, HELPER_NEW, "helper")
        text = apply_single_anchor(text, BS_SIGMA_OLD, BS_SIGMA_NEW, "bs-sigma")
        text = apply_single_anchor(text, PROB_SIGMA_OLD, PROB_SIGMA_NEW, "prob-sigma")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("שלושת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
