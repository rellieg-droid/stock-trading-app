"""
patch_add_button_help_icon.py
================================
Streamlit's st.button(help=...) מציג טולטיפ רק כשמרחפים בדיוק מעל הכפתור
עצמו, בלי סימן ❓ נפרד ליד השם - שונה מאיך שזה נראה בשדות הקלט. הפאץ' הזה
מוסיף שורה קטנה עם ❓ אמיתי (native HTML title attribute - עובד בכל דפדפן,
לא תלוי ברינדור הפנימי של Streamlit) מיד מעל כל אחד מחמשת הכפתורים,
באותה שפה חזותית כמו שאר האפליקציה.

דורש: patch_add_button_tooltips.py כבר רץ (העוגנים כאן כוללים את הגרסה
המורחבת של st.button עם help=).

שימוש:
    python patch_add_button_help_icon.py            # dry-run
    python patch_add_button_help_icon.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: CSS לסגנון ה-❓ החדש -------------------------------------------
CSS_OLD = (
    '.rs-badge.gray   { background: rgba(139,147,161,.14);color: var(--c-text-2, #8B93A7); }\n'
)
CSS_NEW = CSS_OLD + (
    '.rs-btn-help {\n'
    '  display: inline-block; cursor: help; font-size: 0.78rem;\n'
    '  color: var(--c-text-2, #8B93A7); margin-bottom: 6px;\n'
    '}\n'
)

REPLACEMENTS = [
    (
        "bs",
        '        _bs_flag = f"{key_prefix}_bs_show"\n'
        '        if st.button(\n'
        '            "חשב", key=f"{key_prefix}_bs_calc",\n',
        '        _bs_flag = f"{key_prefix}_bs_show"\n'
        '        st.markdown(\n'
        '            \'<span class="rs-btn-help" title="מחשב מחיר ואת כל הגריקס '
        '(Delta/Gamma/Vega/Theta) והסתברות OTM לפי המודל, מהערכים שהוזנו למעלה.">'
        '❓ מה הכפתור עושה</span>\',\n'
        '            unsafe_allow_html=True,\n'
        '        )\n'
        '        if st.button(\n'
        '            "חשב", key=f"{key_prefix}_bs_calc",\n',
    ),
    (
        "iv",
        '        _iv_flag = f"{key_prefix}_iv_show"\n'
        '        if st.button(\n'
        '            "חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc",\n',
        '        _iv_flag = f"{key_prefix}_iv_show"\n'
        '        st.markdown(\n'
        '            \'<span class="rs-btn-help" title="פותר אחורה איזו IV מסבירה '
        'את מחיר השוק שהוזן, ושומר את התצפית לאיסוף היסטוריית IV (לצורך IV Rank '
        'אמיתי בעתיד).">❓ מה הכפתור עושה</span>\',\n'
        '            unsafe_allow_html=True,\n'
        '        )\n'
        '        if st.button(\n'
        '            "חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc",\n',
    ),
    (
        "rv",
        '            _rv_flag = f"{key_prefix}_rv_show"\n'
        '            if st.button(\n'
        '                "חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc",\n',
        '            _rv_flag = f"{key_prefix}_rv_show"\n'
        '            st.markdown(\n'
        '                \'<span class="rs-btn-help" title="מחשב RV מהיסטוריית '
        'המחירים בפועל (לא ממה שהשוק מצפה), ומשווה אותו ל-IV שתזיני.">'
        '❓ מה הכפתור עושה</span>\',\n'
        '                unsafe_allow_html=True,\n'
        '            )\n'
        '            if st.button(\n'
        '                "חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc",\n',
    ),
    (
        "prob",
        '        _prob_flag = f"{key_prefix}_prob_show"\n'
        '        if st.button(\n'
        '            "חשב הסתברות OTM", key=f"{key_prefix}_prob_calc",\n',
        '        _prob_flag = f"{key_prefix}_prob_show"\n'
        '        st.markdown(\n'
        '            \'<span class="rs-btn-help" title="מריץ בבת אחת: הסתברות לפי '
        'שלושה מודלים נפרדים, תזוזה צפויה, סטרס טסט ו-CVaR. חלק מהתוצאות דורשות '
        'היסטוריית מחירים (yfinance).">❓ מה הכפתור עושה</span>\',\n'
        '            unsafe_allow_html=True,\n'
        '        )\n'
        '        if st.button(\n'
        '            "חשב הסתברות OTM", key=f"{key_prefix}_prob_calc",\n',
    ),
    (
        "prot",
        '        _prot_flag = f"{key_prefix}_prot_show"\n'
        '        if st.button(\n'
        '            "חשב הגנה", key=f"{key_prefix}_prot_calc",\n',
        '        _prot_flag = f"{key_prefix}_prot_show"\n'
        '        st.markdown(\n'
        '            \'<span class="rs-btn-help" title="משווה מניה בלבד מול '
        'מניה+פוט מגן בכל תרחיש ירידה, ומראה כמה דולרים ואיזה אחוז מההפסד '
        'הלא-מוגן ההגנה קיזזה.">❓ מה הכפתור עושה</span>\',\n'
        '            unsafe_allow_html=True,\n'
        '        )\n'
        '        if st.button(\n'
        '            "חשב הגנה", key=f"{key_prefix}_prot_calc",\n',
    ),
]


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
        text = apply_single_anchor(text, CSS_OLD, CSS_NEW, "css")
        for label, old, new in REPLACEMENTS:
            text = apply_single_anchor(text, old, new, label)
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("כל ששת העוגנים (CSS + 5 כפתורים) נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
