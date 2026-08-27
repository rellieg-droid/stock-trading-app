"""
patch_sliders_to_number_input.py

מטרה: להחליף את 5 הסליידרים בטאב האסטרטגיה (rel_max, hv_max, vix_max,
atr_mult, blackout) ב-st.number_input עם min_value/max_value/step
מתאימים -- עוקף לגמרי את באג ה-value-label של Streamlit/BaseWeb
(GitHub #3555) שהתגלה בסליידרים בתוך st.expander, ונותן שליטה
מדויקת יותר בערכים כבונוס.

טווחים (זהים למה שהיה בסליידרים):
    rel_max:  10-95, step 1
    hv_max:   10-95, step 1
    vix_max:  10-40, step 1
    atr_mult: 1.0-4.0, step 0.5
    blackout: 0-21, step 1

שימוש:
    python patch_sliders_to_number_input.py                 # dry-run (ברירת מחדל)
    python patch_sliders_to_number_input.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "strategy_tab.py"

OLD_LINES = [
    '# כל הסליידרים ברוחב מלא, בלי st.columns() -- תבנית מוכחת (rr_tab.py)',
    'rel_max = st.slider("סף אחוזון תנודתיות יחסית", 10, 95,',
    '                    int(cfg.rel_vol_rank_pass_max), key="strat_rel_max")',
    'hv_max = st.slider("סף אחוזון HV", 10, 95,',
    '                   int(cfg.hv_rank_pass_max), key="strat_hv_max")',
    'vix_max = st.slider("סף VIX", 10, 40, int(cfg.vix_max), key="strat_vix_max")',
    'atr_mult = st.slider("מכפיל ATR ל-Stop", 1.0, 4.0,',
    '                     float(cfg.atr_stop_multiplier), 0.5, key="strat_atr_mult")',
    'blackout = st.slider("חלון חסימה לפני דוח (ימים)", 0, 21,',
    '                     int(cfg.earnings_blackout_days), key="strat_blackout")',
    'e6 = st',
]

NEW_LINES = [
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

    anchor = OLD_LINES[0]
    if text.count(anchor) != 1:
        print(f"שגיאה: העוגן {anchor!r} נמצא {text.count(anchor)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    indent = get_indent(text, anchor)
    eol = "\r\n" if uses_crlf else "\n"

    old_full_block = eol.join(indent + l for l in OLD_LINES)
    if old_full_block not in text:
        print("שגיאה: הבלוק המלא לא נמצא ברצף מדויק כמו שציפינו.")
        print("ייתכן שהפאץ' הקודם (patch_sliders_full_width_stacked.py) עוד לא הוחל, או שהקוד שונה.")
        sys.exit(1)
    if text.count(old_full_block) != 1:
        print(f"שגיאה: הבלוק נמצא {text.count(old_full_block)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    new_full_block = "\n".join(indent + l for l in NEW_LINES)

    new_text = text.replace(old_full_block, new_full_block, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        diff = difflib.unified_diff(
            old_full_block.splitlines(keepends=True),
            new_full_block.splitlines(keepends=True),
            fromfile="לפני", tofile="אחרי", lineterm=""
        )
        print("".join(diff))
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
    print("לבדוק: 5 שדות מספריים עם חצים +/- במקום סליידרים, כל אחד עם")
    print("הערך הנוכחי ברור לגמרי בלי שום חפיפה/היעלמות.")


if __name__ == "__main__":
    main()
