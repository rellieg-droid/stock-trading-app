"""
patch_finalize_strategy_inputs.py

מטרה: שני שיפורים נוספים אחרי המעבר ל-number_input:
1. להמיר גם את "% מהתיק" (position_pct) מ-slider ל-number_input,
   מאותה סיבה (עוקף את באג הסליידר-בתוך-columns).
2. לסדר את 5 שדות הספים (rel_max/hv_max/vix_max/atr_mult/blackout)
   בשורה אחת (st.columns(5)) במקום מוערמים אנכית -- number_input
   לא סובל מבאג הרוחב של סליידרים, אז זה בטוח.

שימוש:
    python patch_finalize_strategy_inputs.py                 # dry-run (ברירת מחדל)
    python patch_finalize_strategy_inputs.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "strategy_tab.py"

# ── חלק 1: position_pct ──
POS_PCT_OLD = 'position_pct = c3.slider("% מהתיק", 1, 50, 5, key="strat_pos_pct") / 100.0'
POS_PCT_NEW = 'position_pct = c3.number_input("% מהתיק", min_value=1, max_value=50, value=5, step=1, key="strat_pos_pct") / 100.0'

# ── חלק 2: 5 שדות הספים לשורה אחת ──
THRESH_OLD_LINES = [
    '# number_input במקום slider -- עוקף באג ידוע ב-Streamlit (GitHub #3555)',
    '# שבו תווית הערך של סליידר בתוך st.expander נחתכת/נעלמת.',
    'rel_max = st.number_input("סף אחוזון תנודתיות יחסית", min_value=10, max_value=95,',
    '                          value=int(cfg.rel_vol_rank_pass_max), step=1, key="strat_rel_max")',
    'hv_max = st.number_input("סף אחוזון HV", min_value=10, max_value=95,',
    '                         value=int(cfg.hv_rank_pass_max), step=1, key="strat_hv_max")',
    'vix_max = st.number_input("סף VIX", min_value=10, max_value=40,',
    '                          value=int(cfg.vix_max), step=1, key="strat_vix_max")',
    'atr_mult = st.number_input("מכפיל ATR ל-Stop", min_value=1.0, max_value=4.0,',
    '                           value=float(cfg.atr_stop_multiplier), step=0.5, key="strat_atr_mult")',
    'blackout = st.number_input("חלון חסימה לפני דוח (ימים)", min_value=0, max_value=21,',
    '                           value=int(cfg.earnings_blackout_days), step=1, key="strat_blackout")',
    'e6 = st',
]

THRESH_NEW_LINES = [
    '# number_input בשורה אחת (st.columns(5)) -- עוקף באג ידוע ב-Streamlit',
    '# (GitHub #3555) של תווית ערך סליידר בתוך st.expander שנחתכת/נעלמת.',
    'e1, e2, e3, e4, e5 = st.columns(5)',
    'rel_max = e1.number_input("סף אחוזון תנודתיות יחסית", min_value=10, max_value=95,',
    '                          value=int(cfg.rel_vol_rank_pass_max), step=1, key="strat_rel_max")',
    'hv_max = e2.number_input("סף אחוזון HV", min_value=10, max_value=95,',
    '                         value=int(cfg.hv_rank_pass_max), step=1, key="strat_hv_max")',
    'vix_max = e3.number_input("סף VIX", min_value=10, max_value=40,',
    '                          value=int(cfg.vix_max), step=1, key="strat_vix_max")',
    'atr_mult = e4.number_input("מכפיל ATR ל-Stop", min_value=1.0, max_value=4.0,',
    '                           value=float(cfg.atr_stop_multiplier), step=0.5, key="strat_atr_mult")',
    'blackout = e5.number_input("חלון חסימה לפני דוח (ימים)", min_value=0, max_value=21,',
    '                           value=int(cfg.earnings_blackout_days), step=1, key="strat_blackout")',
    'e6 = st',
]


def get_indent(text, anchor):
    idx = text.index(anchor)
    line_start = text.rfind("\n", 0, idx) + 1
    return text[line_start:idx]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="בצע בפועל (במקום dry-run)")
    args = parser.parse_args()

    target = Path(TARGET_FILE)
    if not target.exists():
        print(f"שגיאה: לא נמצא הקובץ {TARGET_FILE} בתיקייה הנוכחית.")
        sys.exit(1)

    raw_bytes = target.read_bytes()
    uses_crlf = b"\r\n" in raw_bytes
    text = raw_bytes.decode("utf-8")
    eol = "\r\n" if uses_crlf else "\n"

    # אימות עוגן חלק 1
    if text.count(POS_PCT_OLD) != 1:
        print(f"שגיאה: עוגן % מהתיק נמצא {text.count(POS_PCT_OLD)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    # אימות עוגן חלק 2
    thresh_anchor = THRESH_OLD_LINES[0]
    if text.count(thresh_anchor) != 1:
        print(f"שגיאה: עוגן שדות הספים נמצא {text.count(thresh_anchor)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    thresh_indent = get_indent(text, thresh_anchor)
    thresh_old_full = eol.join(thresh_indent + l for l in THRESH_OLD_LINES)
    if thresh_old_full not in text:
        print("שגיאה: בלוק שדות הספים לא נמצא ברצף מדויק. לא בוצע שינוי.")
        sys.exit(1)
    if text.count(thresh_old_full) != 1:
        print(f"שגיאה: בלוק שדות הספים נמצא {text.count(thresh_old_full)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)
    thresh_new_full = "\n".join(thresh_indent + l for l in THRESH_NEW_LINES)

    new_text = text
    new_text = new_text.replace(POS_PCT_OLD, POS_PCT_NEW, 1)
    new_text = new_text.replace(thresh_old_full, thresh_new_full, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        old_lines = text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="לפני", tofile="אחרי", lineterm="")
        for line in diff:
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                print(line)
        print("\nלביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"גיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן.")
    print("לבדוק: '% מהתיק' עכשיו שדה מספרי עם חצים, ו-5 שדות הספים בשורה אחת.")


if __name__ == "__main__":
    main()
