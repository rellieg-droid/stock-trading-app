"""
פאץ': תיקון באג session_state ב-Streamlit - השדות "סטרייק הגנה" ו"פרמיית
ההגנה" לא התעדכנו מה-fetch החי כי כבר היה להם ערך שמור מקודם, ו-Streamlit
מתעלם מ-value= במצב כזה. הפאץ' הזה מזהה שינוי בטיקר/סטרייק/DTE ומעדכן
בכוח את session_state לפני יצירת השדות - בלי לדרוס עריכה ידנית כל עוד
לא השתנה כלום.

שימוש:
    python patch_fix_protection_defaults.py            # dry-run
    python patch_fix_protection_defaults.py --apply    # מבצע בפועל

דורש ש-patch_fetch_protection_leg.py כבר הוחל.
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "riskshield_tab.py"

ANCHOR = '        # --- רגל הגנה ל-Bull Put Spread - לצורך השוואת הון/ביטחונות למטה --------\n        _protect_live = _try_fetch_otm_put_quote(ticker, below_strike=prob_K, dte_days=int(prob_days))\n        spread_cols = st.columns(2)\n'
INSERTION = '        # --- רגל הגנה ל-Bull Put Spread - לצורך השוואת הון/ביטחונות למטה --------\n        _protect_live = _try_fetch_otm_put_quote(ticker, below_strike=prob_K, dte_days=int(prob_days))\n        # Streamlit מתעלם מ-value= ברגע שלשדה כבר יש ערך שמור ב-session_state -\n        # לכן מעדכנים בכוח רק כשהטיקר/הסטרייק/ה-DTE השתנו מאז השליפה\n        # האחרונה - כדי לא לדרוס עריכה ידנית שעוד רלוונטית.\n        _protect_sig_key = f"{key_prefix}_prob_protect_sig"\n        _protect_sig = (ticker, round(float(prob_K), 2), int(prob_days))\n        if _protect_live and st.session_state.get(_protect_sig_key) != _protect_sig:\n            st.session_state[f"{key_prefix}_prob_protect_K"] = float(round(_protect_live[0], 2))\n            st.session_state[f"{key_prefix}_prob_protect_premium"] = float(round(_protect_live[1], 2))\n            st.session_state[_protect_sig_key] = _protect_sig\n        spread_cols = st.columns(2)\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually write the change (default: dry-run)")
    parser.add_argument("--file", default=TARGET_FILE, help=f"Path to {TARGET_FILE} (default: current directory)")
    args = parser.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"[ERROR] File not found: {target.resolve()}", file=sys.stderr)
        sys.exit(1)

    raw = target.read_bytes()
    is_crlf = raw.count(b"\r\n") > 0
    text = raw.decode("utf-8")
    normalized = text.replace("\r\n", "\n")

    count = normalized.count(ANCHOR)
    if count == 0:
        print("[ERROR] Anchor not found. הקובץ השתנה מאז שנכתב הפאץ' הזה - צריך לעדכן את העוגן.", file=sys.stderr)
        sys.exit(1)
    if count > 1:
        print(f"[ERROR] Anchor found {count} times - צריך עוגן ייחודי יותר.", file=sys.stderr)
        sys.exit(1)

    patched = normalized.replace(ANCHOR, INSERTION, 1)

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[ERROR] Syntax check failed after patch: {e}", file=sys.stderr)
        sys.exit(1)

    print("[OK] Anchor found exactly once, syntax check passed.")
    print("--- Preview ---")
    for line in INSERTION.splitlines():
        print(line)
    print("--- End preview ---")

    if not args.apply:
        print("\nDry-run only. הרצה עם --apply כדי לבצע בפועל.")
        return

    backup_path = target.with_suffix(target.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(target, backup_path)
    print(f"[OK] Backup saved: {backup_path}")

    final_text = patched.replace("\n", "\r\n") if is_crlf else patched
    target.write_bytes(final_text.encode("utf-8"))
    print(f"[OK] Patch applied to {target.resolve()}")


if __name__ == "__main__":
    main()
