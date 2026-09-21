"""
patch_add_full_metric_legend.py
==================================
מוסיפה expander עם רשימת הסבר לכל המדדים בבת אחת (לא רק זה שנבחר
כרגע ב"מיין לפי") - בנוי דינמית מאותם _scr_metric_labels /
_scr_metric_explain שכבר קיימים, בלי לשכפל טקסט.

שימוש:
    python patch_add_full_metric_legend.py                 # dry-run
    python patch_add_full_metric_legend.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR = (
    '                    "max_loss": "ההפסד המקסימלי התיאורטי בפוזיציה (סטרייק פחות פרמיה, כפול 100 כפול חוזים).",\n'
    '                }\n'
    '\n'
    '                sort_ui = st.columns([2, 1])\n'
)

NEW = (
    '                    "max_loss": "ההפסד המקסימלי התיאורטי בפוזיציה (סטרייק פחות פרמיה, כפול 100 כפול חוזים).",\n'
    '                }\n'
    '\n'
    '                with st.expander("📖 הסבר לכל המדדים ברשימה"):\n'
    '                    _legend_html = "".join(\n'
    '                        f\'<div class="rs-explain" style="margin-bottom:6px;">\'\n'
    '                        f\'<b>{_scr_metric_labels.get(c, c)}</b>: {_scr_metric_explain.get(c, "")}\'\n'
    '                        f\'</div>\'\n'
    '                        for c in _sortable\n'
    '                    )\n'
    '                    st.markdown(_legend_html, unsafe_allow_html=True)\n'
    '\n'
    '                sort_ui = st.columns([2, 1])\n'
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="מבצע בפועל. בלי הדגל הזה - dry-run בלבד.")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} בתיקייה הנוכחית.", file=sys.stderr)
        return 1

    raw = TARGET.read_bytes()
    used_crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")

    anchor_normalized = ANCHOR.replace("\r\n", "\n")
    count = text.count(anchor_normalized)
    if count == 0:
        print("האנקור לא נמצא. ייתכן שהקובץ השתנה - יש לעדכן ידנית.", file=sys.stderr)
        return 1
    if count > 1:
        print(f"האנקור נמצא {count} פעמים - לא ייחודי, עוצר.", file=sys.stderr)
        return 1

    new_text = text.replace(anchor_normalized, NEW.replace("\r\n", "\n"), 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת תחביר בקוד החדש: {e}", file=sys.stderr)
        return 1

    print("האנקור נמצא ותוקן בהצלחה. ast.parse עבר.")

    if not args.apply:
        print("\nDry-run בלבד. הריצי עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(TARGET.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נשמר: {backup}")

    out_text = new_text.replace("\n", "\r\n") if used_crlf else new_text
    TARGET.write_bytes(out_text.encode("utf-8"))
    print(f"בוצע. {TARGET} עודכן.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
