"""
פאץ': חיבור size_position() הקיים (options_engine.py) למסך "הסתברות OTM"
ב-riskshield_tab.py - מגבלת סיכון לעסקה (1%-3% מהתיק) + התראת ריכוז יתר (>5%).

שימוש:
    python patch_wire_size_position.py            # dry-run
    python patch_wire_size_position.py --apply    # מבצע בפועל

מה זה עושה (שני עוגנים, שניהם באותו קובץ):
    1. מוסיף size_position, Position, Leg לייבוא הקיים מ-options_engine
    2. מוסיף כרטיס "גודל פוזיציה מומלץ" מיד אחרי כרטיס הסטרס טסט הקיים
       בטאב "הסתברות OTM" - פעיל רק כש"הון זמין" (prob_capital) מוזן,
       בדיוק כמו התנאי הקיים ל-% מההון בסטרס טסט. מציג: חוזים מאושרים,
       סיכון לחוזה, סיכון כולל, והתראה אדומה אם סיכון > 5% מהתיק.
    - אין נוסחה חדשה - size_position() כבר קיים ובדוק (יש לו pytest ייעודי
      לפי היסטוריית הפרויקט), רק לא היה מחובר לשום מסך
    - שני עוגנים נבדקים בנפרד, כל אחד בקול אם לא ייחודי
    - גיבוי עם timestamp, בדיקת ast.parse על הקובץ המלא לפני כתיבה
    - שומר על סגנון שבירת השורות המקורי (LF/CRLF, מזוהה אוטומטית)
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "riskshield_tab.py"

ANCHOR_1 = '    protection_table, insurance_cost,\n    short_put_breakeven,\n)\n'
INSERTION_1 = '    protection_table, insurance_cost,\n    short_put_breakeven,\n    size_position, Position, Leg,\n)\n'

ANCHOR_2 = '            _card("סטרס טסט", f\'<div class="rs-grid">{"".join(grid_stress)}</div>{stress_explain}\')\n\n            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------\n'
INSERTION_2 = '            _card("סטרס טסט", f\'<div class="rs-grid">{"".join(grid_stress)}</div>{stress_explain}\')\n\n            # --- גודל פוזיציה מומלץ - חוק הסיכון (1%-3% מהתיק) --------------\n            if capital_arg:\n                _size_template = Position(legs=[Leg("put", -1, 1, prob_premium, prob_K, label="שורט פוט")])\n                prob_max_risk_pct = st.number_input(\n                    "מגבלת סיכון לעסקה (% מהתיק)", min_value=0.5, max_value=10.0, value=1.0, step=0.5,\n                    key=f"{key_prefix}_prob_max_risk_pct",\n                    help="ההפסד המרבי המותר בעסקה בודדת, כאחוז מהתיק. מקובל למסחר ספקולטיבי: 1%-3%.",\n                )\n                verdict = size_position(\n                    template=_size_template, portfolio_usd=capital_arg,\n                    max_risk_pct=prob_max_risk_pct / 100.0, template_contracts=1,\n                )\n                grid_size = "".join([\n                    _metric("חוזים מאושרים", str(verdict.contracts)),\n                    _metric("סיכון לחוזה", f"${verdict.unit_risk_usd:,.2f}"),\n                    _metric("סיכון כולל מאושר", f"${verdict.risk_usd:,.2f} ({verdict.risk_pct:.2%})"),\n                ])\n                size_extra = f\'<div class="rs-explain">{verdict.reason}</div>\'\n                if verdict.risk_pct > 0.05:\n                    size_extra += (\n                        \'<span class="rs-badge red" style="margin-top:8px; display:inline-block;">\'\n                        \'⚠️ ריכוז יתר - הפוזיציה מסכנת מעל 5% מהתיק. שקלי להקטין חוזים או לבחור סטרייק רחוק יותר\'\n                        \'</span>\'\n                    )\n                _card("גודל פוזיציה מומלץ (חוק הסיכון)", f\'<div class="rs-grid">{grid_size}</div>{size_extra}\')\n            else:\n                st.caption(\n                    "💡 הזיני \\"הון זמין\\" למעלה (בשורת הפרמיה/חוזים) כדי לראות כמה חוזים "\n                    "מותרים לפי חוק הסיכון (1%-3% מהתיק), וקבלת התראה על ריכוז יתר."\n                )\n\n            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------\n'


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
    patched = apply_single_anchor(patched, ANCHOR_2, INSERTION_2, "risk-sizing card")

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[ERROR] Syntax check failed after patch: {e}", file=sys.stderr)
        sys.exit(1)

    print("[OK] Both anchors found exactly once, syntax check passed.")
    print("--- Preview of inserted risk-sizing block ---")
    for line in INSERTION_2.splitlines():
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
