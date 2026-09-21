"""
פאץ': טבלת השוואת הון/ביטחונות ו-ROC - CSP (חוזה 1), CSP (3 חוזים), ו-
Bull Put Spread (חוזה 1) - בטאב "הסתברות OTM" ב-riskshield_tab.py.

דורש שהפאץ' patch_add_bull_put_spread.py כבר הוחל על options_engine.py.

שימוש:
    python patch_capital_comparison_table.py            # dry-run
    python patch_capital_comparison_table.py --apply    # מבצע בפועל

מה זה עושה (שלושה עוגנים, כולם ב-riskshield_tab.py):
    1. מוסיף bull_put_spread, CONTRACT_MULTIPLIER לייבוא הקיים מ-options_engine
    2. מוסיף שני שדות קלט חדשים (סטרייק הגנה + פרמיית הגנה) לצורך בניית
       ה-Bull Put Spread להשוואה - מיד אחרי שדה "עניין פתוח" הקיים
    3. מוסיף כרטיס טבלה - "השוואת הון וביטחונות" - מיד אחרי כרטיס
       "גודל פוזיציה מומלץ" (מהפאץ' הקודם) ולפני "מודלים 2+3"

    חשוב: ביטחונות ל-CSP מחושבים כ-Strike x 100 (הסכום המלא שברוקר קאש
    נועל) - לא כ-max_loss (שהוא (Strike-Premium) x 100, מספר קטן יותר).
    ל-Bull Put Spread, ביטחונות = max_loss (רוחב המרווח x 100 פחות
    הקרדיט) - כי כלל Reg-T הרגיל מזהה שהסיכון כבר מוגדר מראש. ROC בשתי
    השורות מחושב כקרדיט חלקי הביטחונות (לא חלקי max_loss).

    שלושת העוגנים נבדקים בנפרד, כל אחד בקול אם לא ייחודי.
    גיבוי עם timestamp, בדיקת ast.parse על הקובץ המלא לפני כתיבה,
    שימור סגנון שבירת השורות המקורי (LF/CRLF, מזוהה אוטומטית).
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "riskshield_tab.py"

ANCHOR_1 = '    size_position, Position, Leg,\n)\n'
INSERTION_1 = '    size_position, Position, Leg,\n    bull_put_spread, CONTRACT_MULTIPLIER,\n)\n'

ANCHOR_2 = '        with liq_cols[1]:\n            prob_oi = st.number_input("עניין פתוח (מ-Yahoo/הברוקר, אופציונלי)", min_value=0, value=0,\n                                       key=f"{key_prefix}_prob_oi")\n\n        _prob_flag = f"{key_prefix}_prob_show"\n'
INSERTION_2 = '        with liq_cols[1]:\n            prob_oi = st.number_input("עניין פתוח (מ-Yahoo/הברוקר, אופציונלי)", min_value=0, value=0,\n                                       key=f"{key_prefix}_prob_oi")\n\n        # --- רגל הגנה ל-Bull Put Spread - לצורך השוואת הון/ביטחונות למטה --------\n        spread_cols = st.columns(2)\n        with spread_cols[0]:\n            prob_protect_K = st.number_input(\n                "סטרייק הגנה ל-Bull Put Spread", min_value=0.01,\n                value=float(round(prob_K * 0.95, 2)),\n                key=f"{key_prefix}_prob_protect_K",\n                help="הסטרייק שבו קונים פוט הגנה, מתחת לסטרייק הכתיבה - קובע את רוחב המרווח.",\n            )\n        with spread_cols[1]:\n            prob_protect_premium = st.number_input(\n                "פרמיית ההגנה ($)", min_value=0.01, value=float(round(prob_premium * 0.4, 2)),\n                key=f"{key_prefix}_prob_protect_premium",\n                help="הפרמיה ששולמת עבור פוט ההגנה. כלל אצבע גס: פוט רחוק יותר מהכסף עולה פחות.",\n            )\n\n        _prob_flag = f"{key_prefix}_prob_show"\n'

ANCHOR_3 = '                _card("גודל פוזיציה מומלץ (חוק הסיכון)", f\'<div class="rs-grid">{grid_size}</div>{size_extra}\')\n            else:\n                st.caption(\n                    "💡 הזיני \\"הון זמין\\" למעלה (בשורת הפרמיה/חוזים) כדי לראות כמה חוזים "\n                    "מותרים לפי חוק הסיכון (1%-3% מהתיק), וקבלת התראה על ריכוז יתר."\n                )\n\n            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------\n'
INSERTION_3 = '                _card("גודל פוזיציה מומלץ (חוק הסיכון)", f\'<div class="rs-grid">{grid_size}</div>{size_extra}\')\n            else:\n                st.caption(\n                    "💡 הזיני \\"הון זמין\\" למעלה (בשורת הפרמיה/חוזים) כדי לראות כמה חוזים "\n                    "מותרים לפי חוק הסיכון (1%-3% מהתיק), וקבלת התראה על ריכוז יתר."\n                )\n\n            # --- השוואת הון/ביטחונות ו-ROC: CSP מול Bull Put Spread -----------\n            _csp1_collateral = prob_K * CONTRACT_MULTIPLIER * 1\n            _csp1_credit = prob_premium * CONTRACT_MULTIPLIER * 1\n            _csp1_max_loss = Position(legs=[Leg("put", -1, 1, prob_premium, prob_K)]).max_loss()\n            _csp1_roc = (_csp1_credit / _csp1_collateral) if _csp1_collateral else None\n\n            _csp3_collateral = _csp1_collateral * 3\n            _csp3_credit = _csp1_credit * 3\n            _csp3_max_loss = _csp1_max_loss * 3\n            _csp3_roc = _csp1_roc\n\n            _bps = bull_put_spread(\n                1, short_put=prob_K, short_put_prem=prob_premium,\n                long_put=prob_protect_K, long_put_prem=prob_protect_premium,\n            )\n            _bps_credit = _bps.net_cash\n            _bps_max_loss = _bps.max_loss()\n            _bps_collateral = _bps_max_loss  # Reg-T: ביטחונות = הפסד מרבי בסיכון מוגדר\n            _bps_roc = (_bps_credit / _bps_collateral) if _bps_collateral else None\n\n            def _roc_str(r):\n                return f"{r:.1%}" if r is not None else "—"\n\n            _cmp_headers = ["", "CSP (חוזה 1)", "CSP (3 חוזים)", "Bull Put Spread (חוזה 1)"]\n            _cmp_rows = [\n                ("ביטחונות נדרשים", f"${_csp1_collateral:,.0f}", f"${_csp3_collateral:,.0f}", f"${_bps_collateral:,.0f}"),\n                ("קרדיט נטו", f"${_csp1_credit:,.0f}", f"${_csp3_credit:,.0f}", f"${_bps_credit:,.0f}"),\n                ("הפסד מרבי", f"${_csp1_max_loss:,.0f}", f"${_csp3_max_loss:,.0f}", f"${_bps_max_loss:,.0f}"),\n                ("ROC (קרדיט/ביטחונות)", _roc_str(_csp1_roc), _roc_str(_csp3_roc), _roc_str(_bps_roc)),\n            ]\n            _cmp_thead = "".join(f"<th>{h}</th>" for h in _cmp_headers)\n            _cmp_trs = "".join(\n                "<tr>" + f"<td>{row[0]}</td>" + "".join(f"<td>{v}</td>" for v in row[1:]) + "</tr>"\n                for row in _cmp_rows\n            )\n            _cmp_table_html = (\n                f\'<div style="overflow-x:auto;"><table class="rs-table">\'\n                f\'<thead><tr>{_cmp_thead}</tr></thead><tbody>{_cmp_trs}</tbody></table></div>\'\n            )\n            _cmp_explain = (\n                \'<div class="rs-explain">\'\n                \'ביטחונות ב-CSP הם הסטרייק המלא × 100 (הסכום שנועל הברוקר בחשבון קאש), \'\n                \'לא ההפסד המרבי התיאורטי - שני מספרים שונים בכוונה. ב-Bull Put Spread, \'\n                \'הביטחונות (לפי כלל Reg-T הרגיל) שווים בדיוק להפסד המרבי, כי ההגנה כבר \'\n                \'מגבילה את הסיכון. ROC כאן הוא קרדיט חלקי ביטחונות, לא קרדיט חלקי הפסד מרבי - \'\n                \'ל-CSP השניים שונים.\'\n                \'</div>\'\n            )\n            _card(\n                "השוואת הון וביטחונות - CSP מול Bull Put Spread",\n                f"{_cmp_table_html}{_cmp_explain}",\n            )\n\n            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------\n'


def apply_single_anchor(text: str, anchor: str, insertion: str, label: str) -> str:
    count = text.count(anchor)
    if count == 0:
        print(f"[ERROR] Anchor '{label}' not found. הקובץ השתנה מאז שנכתב הפאץ' הזה - צריך לעדכן את העוגן.", file=sys.stderr)
        sys.exit(1)
    if count > 1:
        print(f"[ERROR] Anchor '{label}' found {count} times - צריך עוגן ייחודי יותר.", file=sys.stderr)
        sys.exit(1)
    return text.replace(anchor, insertion, 1)


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

    patched = apply_single_anchor(normalized, ANCHOR_1, INSERTION_1, "imports")
    patched = apply_single_anchor(patched, ANCHOR_2, INSERTION_2, "spread protection inputs")
    patched = apply_single_anchor(patched, ANCHOR_3, INSERTION_3, "capital comparison table")

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[ERROR] Syntax check failed after patch: {e}", file=sys.stderr)
        sys.exit(1)

    print("[OK] All 3 anchors found exactly once, syntax check passed.")
    print("--- Preview of new comparison-table block ---")
    for line in INSERTION_3.splitlines():
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
