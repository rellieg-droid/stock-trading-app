"""
patch_sliders_full_width_stacked.py

מטרה: אחרי שני ניסיונות שלא פתרו לגמרי (columns(5) עדיין הראה חפיפה),
עוברים לגישה שונה: כל 5 הסליידרים בשורות נפרדות, ברוחב מלא, בלי שום
st.columns() ביניהם -- בדיוק התבנית שכבר הוכחה כעובדת ב-rr_tab.py
(patch_fix_gap_slider_overlap.py). הפעם מיושם על כל 5 הסליידרים
יחד (לא רק על שניים), כדי להיות עקבי ולמנוע ערבוב סגנונות.

שימוש:
    python patch_sliders_full_width_stacked.py                 # dry-run (ברירת מחדל)
    python patch_sliders_full_width_stacked.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "strategy_tab.py"

OLD_LINES = [
    'e1, e2, e3, e4, e5 = st.columns(5)',
    'rel_max = e1.slider("סף אחוזון תנודתיות יחסית", 10, 95,',
    '                    int(cfg.rel_vol_rank_pass_max), key="strat_rel_max")',
    'hv_max = e2.slider("סף אחוזון HV", 10, 95,',
    '                   int(cfg.hv_rank_pass_max), key="strat_hv_max")',
    'vix_max = e3.slider("סף VIX", 10, 40, int(cfg.vix_max), key="strat_vix_max")',
    'atr_mult = e4.slider("מכפיל ATR ל-Stop", 1.0, 4.0,',
    '                     float(cfg.atr_stop_multiplier), 0.5, key="strat_atr_mult")',
    'blackout = e5.slider("חלון חסימה לפני דוח (ימים)", 0, 21,',
    '                     int(cfg.earnings_blackout_days), key="strat_blackout")',
    '# e6 נשאר st ישירות -- שדה הטקסט לא חולק שורה עם הסליידרים',
    'e6 = st',
]

NEW_LINES = [
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
        print("ייתכן שהפאץ' הקודם (patch_merge_slider_columns.py) עוד לא הוחל, או שהקוד שונה.")
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
    print("לבדוק: כל 5 הסליידרים בשורות נפרדות, ברוחב מלא, עם נקודה ומספר תקינים.")


if __name__ == "__main__":
    main()
