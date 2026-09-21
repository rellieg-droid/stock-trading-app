"""
patch_fix_ticker_refresh.py
==============================
הבעיה: שדות כמו "מחיר נכס (S)" מקבלים value=spot_default (מהטיקר), אבל
יש להם key קבוע. ב-Streamlit, ברגע שלווידג'ט עם key יש כבר ערך שמור,
ה-value שמועבר בקריאות הבאות מתעלם ממנו - זו לא תקלה, זו התנהגות
מתועדת. זה מה שגורם לשדות "להיתקע" על הטיקר הקודם כשמחליפים טיקר.

הפתרון הנכון ב-Streamlit: לשלב את הטיקר בתוך ה-key עצמו. כשהטיקר
משתנה, זה בעצם ווידג'ט "חדש" מבחינת Streamlit - מקבל את spot_default
העדכני. אם חוזרים לטיקר קודם, גם מה שהוקלד עבורו נשמר (כי ה-key שלו
עדיין קיים ב-session_state).

חל על שמונה שדות: S ו-K בטאבים מחיר-וגריקס/IV/הסתברות, ו-prot_entry/
prot_strike במקטע ההגנה.

שימוש:
    python patch_fix_ticker_refresh.py            # dry-run
    python patch_fix_ticker_refresh.py --apply     # מבצע בפועל
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
        "bs_S",
        '            S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                 key=f"{key_prefix}_bs_S", help=_HELP["S"])\n',
        '            S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                 key=f"{key_prefix}_bs_S_{ticker}", help=_HELP["S"])\n',
    ),
    (
        "bs_K",
        '            K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                 key=f"{key_prefix}_bs_K", help=_HELP["K"])\n',
        '            K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                 key=f"{key_prefix}_bs_K_{ticker}", help=_HELP["K"])\n',
    ),
    (
        "iv_S",
        '            iv_S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                    key=f"{key_prefix}_iv_S", help=_HELP["S"])\n',
        '            iv_S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                    key=f"{key_prefix}_iv_S_{ticker}", help=_HELP["S"])\n',
    ),
    (
        "iv_K",
        '            iv_K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                    key=f"{key_prefix}_iv_K", help=_HELP["K"])\n',
        '            iv_K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                    key=f"{key_prefix}_iv_K_{ticker}", help=_HELP["K"])\n',
    ),
    (
        "prob_S",
        '            prob_S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                      key=f"{key_prefix}_prob_S", help=_HELP["S"])\n',
        '            prob_S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                      key=f"{key_prefix}_prob_S_{ticker}", help=_HELP["S"])\n',
    ),
    (
        "prob_K",
        '            prob_K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default * 0.9, 2)),\n'
        '                                      key=f"{key_prefix}_prob_K", help=_HELP["K"])\n',
        '            prob_K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default * 0.9, 2)),\n'
        '                                      key=f"{key_prefix}_prob_K_{ticker}", help=_HELP["K"])\n',
    ),
    (
        "prot_entry",
        '            prot_entry = st.number_input("מחיר עלות המניה", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                          key=f"{key_prefix}_prot_entry", help=_HELP["prot_entry"])\n',
        '            prot_entry = st.number_input("מחיר עלות המניה", min_value=0.01, value=float(round(spot_default, 2)),\n'
        '                                          key=f"{key_prefix}_prot_entry_{ticker}", help=_HELP["prot_entry"])\n',
    ),
    (
        "prot_strike",
        '            prot_strike = st.number_input("סטרייק הפוט המגן", min_value=0.01, value=float(round(spot_default * 0.9, 2)),\n'
        '                                           key=f"{key_prefix}_prot_strike", help=_HELP["prot_strike"])\n',
        '            prot_strike = st.number_input("סטרייק הפוט המגן", min_value=0.01, value=float(round(spot_default * 0.9, 2)),\n'
        '                                           key=f"{key_prefix}_prot_strike_{ticker}", help=_HELP["prot_strike"])\n',
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

    print("כל שמונת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
