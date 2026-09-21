"""
פאץ': שלוש בדיקות מול ספים נפוצים - DTE (30-45 יום), יחס קרדיט/רוחב
(20%-30%) ל-Bull Put Spread, ונזילות (כמה % מהתיק כל אסטרטגיה נועלת,
מול סף נפוץ של 50%). כרטיס חדש "בדיקות מול ספים נפוצים", מיד אחרי
כרטיס "השוואת הון וביטחונות" בטאב "הסתברות OTM".

חשוב: בכוונה לא "עבר/נכשל" - RiskShield נמנע במפורש מקביעות טוב/רע
(ראו _ratio_badge הקיים). כל בדיקה מוצגת כעובדה + צבע + הפניה לסף
הנפוץ, בלי שהאפליקציה קובעת בעצמה אם זה מתאים לעסקה הספציפית.

שימוש:
    python patch_add_threshold_checks.py            # dry-run
    python patch_add_threshold_checks.py --apply    # מבצע בפועל

דורש ש-patch_capital_comparison_table.py כבר הוחל (משתמש באותם
משתנים: _bps_credit, _csp1_collateral וכו').
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "riskshield_tab.py"

ANCHOR = '            _card(\n                "השוואת הון וביטחונות - CSP מול Bull Put Spread",\n                f"{_cmp_table_html}{_cmp_explain}",\n            )\n\n            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------\n'
INSERTION = '            _card(\n                "השוואת הון וביטחונות - CSP מול Bull Put Spread",\n                f"{_cmp_table_html}{_cmp_explain}",\n            )\n\n            # --- בדיקות מול ספים נפוצים: DTE, יחס קרדיט/רוחב, נזילות -------\n            _dte_badge_cls = "green" if 30 <= int(prob_days) <= 45 else "gray"\n            _dte_badge = (\n                f\'<span class="rs-badge {_dte_badge_cls}">DTE: {int(prob_days)} ימים \'\n                f\'(טווח 30-45 נפוץ לשחיקת תטא)</span>\'\n            )\n\n            _width = prob_K - prob_protect_K\n            if _width > 0:\n                _cw_ratio = _bps_credit / (_width * CONTRACT_MULTIPLIER)\n                _cw_cls = "green" if _cw_ratio >= 0.20 else "yellow" if _cw_ratio >= 0.10 else "red"\n                _cw_badge = (\n                    f\'<span class="rs-badge {_cw_cls}">יחס קרדיט/רוחב (Bull Put Spread): \'\n                    f\'{_cw_ratio:.0%} (סף נפוץ: 20%-30%)</span>\'\n                )\n            else:\n                _cw_badge = (\n                    \'<span class="rs-badge gray">יחס קרדיט/רוחב: לא ניתן לחשב - \'\n                    \'רוחב מרווח 0 או שלילי</span>\'\n                )\n\n            _threshold_badges = [_dte_badge, _cw_badge]\n            if prob_capital:\n                for _label, _coll in [\n                    ("CSP (חוזה 1)", _csp1_collateral),\n                    ("CSP (3 חוזים)", _csp3_collateral),\n                    ("Bull Put Spread (חוזה 1)", _bps_collateral),\n                ]:\n                    _pct_locked = _coll / prob_capital\n                    _liq_cls = "green" if _pct_locked <= 0.5 else "yellow" if _pct_locked <= 0.75 else "red"\n                    _threshold_badges.append(\n                        f\'<span class="rs-badge {_liq_cls}">{_label}: {_pct_locked:.0%} מהתיק נעול \'\n                        f\'(סף נזילות נפוץ: עד 50%)</span>\'\n                    )\n\n            _thresholds_html = (\n                \'<div style="display:flex; flex-direction:column; gap:8px; align-items:flex-start;">\'\n                + "".join(_threshold_badges) + "</div>"\n            )\n            if not prob_capital:\n                _thresholds_html += (\n                    \'<div class="rs-explain" style="margin-top:8px;">\'\n                    \'הזיני "הון זמין" למעלה כדי לראות איזה אחוז מהתיק כל אסטרטגיה \'\n                    \'נועלת כביטחונות.\'\n                    \'</div>\'\n                )\n            _card("בדיקות מול ספים נפוצים", _thresholds_html)\n\n            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------\n'


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
