"""
patch_add_button_tooltips.py
==============================
מוסיף help= (סימון ❓ בריחוף) לחמשת כפתורי "חשב" - אותו דפוס שכבר קיים
בכל שדות הקלט בקובץ, פשוט לא הוחל על הכפתורים עצמם.

דורש: patch_add_session_state_persistence.py כבר רץ (העוגנים כאן כוללים
את התוספת _flag שהוא הוסיף).

שימוש:
    python patch_add_button_tooltips.py            # dry-run
    python patch_add_button_tooltips.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

REPLACEMENTS = [
    (
        "bs",
        '        if st.button("חשב", key=f"{key_prefix}_bs_calc") or st.session_state.get(_bs_flag):\n',
        '        if st.button(\n'
        '            "חשב", key=f"{key_prefix}_bs_calc",\n'
        '            help="מחשב מחיר ואת כל הגריקס (Delta/Gamma/Vega/Theta) והסתברות OTM לפי המודל, "\n'
        '                 "מהערכים שהוזנו למעלה.",\n'
        '        ) or st.session_state.get(_bs_flag):\n',
    ),
    (
        "iv",
        '        if st.button("חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc") or st.session_state.get(_iv_flag):\n',
        '        if st.button(\n'
        '            "חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc",\n'
        '            help="פותר אחורה איזו IV מסבירה את מחיר השוק שהוזן, ושומר את התצפית "\n'
        '                 "לאיסוף היסטוריית IV (לצורך IV Rank אמיתי בעתיד).",\n'
        '        ) or st.session_state.get(_iv_flag):\n',
    ),
    (
        "rv",
        '            if st.button("חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc") or st.session_state.get(_rv_flag):\n',
        '            if st.button(\n'
        '                "חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc",\n'
        '                help="מחשב RV מהיסטוריית המחירים בפועל (לא ממה שהשוק מצפה), "\n'
        '                     "ומשווה אותו ל-IV שתזיני.",\n'
        '            ) or st.session_state.get(_rv_flag):\n',
    ),
    (
        "prob",
        '        if st.button("חשב הסתברות OTM", key=f"{key_prefix}_prob_calc") or st.session_state.get(_prob_flag):\n',
        '        if st.button(\n'
        '            "חשב הסתברות OTM", key=f"{key_prefix}_prob_calc",\n'
        '            help="מריץ בבת אחת: הסתברות לפי שלושה מודלים נפרדים, תזוזה צפויה, "\n'
        '                 "סטרס טסט ו-CVaR. חלק מהתוצאות דורשות היסטוריית מחירים (yfinance).",\n'
        '        ) or st.session_state.get(_prob_flag):\n',
    ),
    (
        "prot",
        '        if st.button("חשב הגנה", key=f"{key_prefix}_prot_calc") or st.session_state.get(_prot_flag):\n',
        '        if st.button(\n'
        '            "חשב הגנה", key=f"{key_prefix}_prot_calc",\n'
        '            help="משווה מניה בלבד מול מניה+פוט מגן בכל תרחיש ירידה, "\n'
        '                 "ומראה כמה דולרים ואיזה אחוז מההפסד הלא-מוגן ההגנה קיזזה.",\n'
        '        ) or st.session_state.get(_prot_flag):\n',
    ),
]


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    for label, old, new in REPLACEMENTS:
        count = text.count(old)
        if count != 1:
            print(f"עוגן '{label}' נמצא {count} פעמים (צריך בדיוק 1). לא בוצע שום שינוי.")
            return 1

    for label, old, new in REPLACEMENTS:
        text = text.replace(old, new, 1)

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("כל חמשת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
