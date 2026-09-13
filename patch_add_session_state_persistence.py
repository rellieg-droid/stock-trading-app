"""
patch_add_session_state_persistence.py
=========================================
מתקן בכל חמשת הכפתורים בקובץ: Streamlit מריץ את כל הסקריפט מחדש בכל
אינטראקציה, ו-st.button() חוזר ל-False בריצה הבאה - זה מה שגורם לתוצאות
"להיעלם" אחרי כמה שניות, גם בלי שהמשתמשת עשתה כלום.

הפתרון: כל כפתור שומר "true" ב-st.session_state ברגע שנלחץ. בריצות הבאות,
התנאי בודק גם את הדגל הזה, לא רק את הלחיצה הרגעית - כך שהתוכן ממשיך
"להיפתח" ולהיות מחושב מחדש (עם הערכים הנוכחיים של השדות) בכל ריצה, במקום
להיעלם. לא נדרש לפרק חישוב מתצוגה - זה שינוי מינימלי בתנאי בלבד.

חמשת המקומות: tab_bs, tab_iv, tab_rv, tab_prob (הסתברות), tab_prob (הגנה).

שימוש:
    python patch_add_session_state_persistence.py            # dry-run
    python patch_add_session_state_persistence.py --apply     # מבצע בפועל
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
        '        if st.button("חשב", key=f"{key_prefix}_bs_calc"):\n',
        '        _bs_flag = f"{key_prefix}_bs_show"\n'
        '        if st.button("חשב", key=f"{key_prefix}_bs_calc") or st.session_state.get(_bs_flag):\n'
        '            st.session_state[_bs_flag] = True\n',
    ),
    (
        "iv",
        '        if st.button("חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc"):\n',
        '        _iv_flag = f"{key_prefix}_iv_show"\n'
        '        if st.button("חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc") or st.session_state.get(_iv_flag):\n'
        '            st.session_state[_iv_flag] = True\n',
    ),
    (
        "rv",
        '            if st.button("חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc"):\n',
        '            _rv_flag = f"{key_prefix}_rv_show"\n'
        '            if st.button("חשב תנודתיות ממומשת", key=f"{key_prefix}_rv_calc") or st.session_state.get(_rv_flag):\n'
        '                st.session_state[_rv_flag] = True\n',
    ),
    (
        "prob",
        '        if st.button("חשב הסתברות OTM", key=f"{key_prefix}_prob_calc"):\n',
        '        _prob_flag = f"{key_prefix}_prob_show"\n'
        '        if st.button("חשב הסתברות OTM", key=f"{key_prefix}_prob_calc") or st.session_state.get(_prob_flag):\n'
        '            st.session_state[_prob_flag] = True\n',
    ),
    (
        "prot",
        '        if st.button("חשב הגנה", key=f"{key_prefix}_prot_calc"):\n',
        '        _prot_flag = f"{key_prefix}_prot_show"\n'
        '        if st.button("חשב הגנה", key=f"{key_prefix}_prot_calc") or st.session_state.get(_prot_flag):\n'
        '            st.session_state[_prot_flag] = True\n',
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
