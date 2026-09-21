"""
patch_add_help_texts_and_guide.py
====================================
שני שיפורים:
1. משלים help= (סימון ❓) לכל שדה שעדיין חסר לו הסבר - מספר חוזים, הון
   זמין, ושדות מקטע ההגנה (מניות מוחזקות, מחיר עלות, סטרייק, פרמיה,
   מספר חוזי פוט).
2. מוסיף expander "📖 מדריך" בראש הטאב, מיד אחרי שדה הטיקר - מסביר מה
   ההבדל בין ארבעת הטאבים, ומילון מונחים קצר (IV/RV/OTM/Strike/CVaR/
   Expected Move) - כדי שההדרכה תהיה בתוך האפליקציה עצמה, לא רק בצ'אט.

שימוש:
    python patch_add_help_texts_and_guide.py            # dry-run
    python patch_add_help_texts_and_guide.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: הוספת מונחים חדשים ל-_HELP -----------------------------------
HELP_DICT_OLD = (
    '    "rv_iv_compare": "ה-IV שאיתו משווים את ה-RV שחושב. אפשר להזין ידנית, או להשתמש בערך שיצא בטאב \'תנודתיות גלומה\'.",\n'
    "}\n"
)
HELP_DICT_NEW = (
    '    "rv_iv_compare": "ה-IV שאיתו משווים את ה-RV שחושב. אפשר להזין ידנית, או להשתמש בערך שיצא בטאב \'תנודתיות גלומה\'.",\n'
    '    "contracts": "כמה חוזי אופציה. כל חוזה מייצג 100 מניות - זה מה שהופך פרמיה קטנה למספרים גדולים.",\n'
    '    "capital": "ההון שהוקצה לעסקה הזו. משמש רק כדי להציג את הסיכון כאחוז מההון שלך - לא משפיע על שום חישוב אחר.",\n'
    '    "prot_shares": "כמה מניות בפועל מוחזקות ורוצים להגן עליהן.",\n'
    '    "prot_entry": "המחיר שבו נקנתה המניה (עלות הבסיס) - קובע את הרווח/הפסד היחסי בכל תרחיש סטרס.",\n'
    '    "prot_strike": "מחיר המימוש של הפוט המגן. מתחתיו הוא מתחיל לקזז הפסדים דולר-לדולר.",\n'
    '}\n'
)

# --- עוגן 2: מדריך בראש הטאב, אחרי שדה הטיקר -----------------------------
GUIDE_OLD = (
    '    ticker = st.text_input("טיקר (לצורך מילוי ראשוני בלבד)", value=default_ticker, key=f"{key_prefix}_ticker")\n'
)
GUIDE_NEW = GUIDE_OLD + '''
    with st.expander("📖 מדריך: מה ההבדל בין הטאבים, ומה זה אומר"):
        st.markdown(
            \'<div class="rs-explain">\'
            \'<b>מחיר וגריקס</b>: תיאורטי לגמרי - מזינים IV משוערת, מקבלים מחיר \'
            \'תיאורטי לאופציה ואת הרגישויות שלה (גריקס). שאלה שהוא עונה עליה: \'
            \'"אם התנודתיות היא X, כמה האופציה אמורה לעלות?"<br><br>\'
            \'<b>תנודתיות גלומה (IV)</b>: ההפך - מזינים את המחיר האמיתי בשוק, \'
            \'והמערכת פותרת אחורה איזו תנודתיות "מוסתרת" בתוכו. שאלה: \'
            \'"השוק מתמחר את זה ב-$X - כלומר כמה תנועה הוא בעצם מצפה?"<br><br>\'
            \'<b>תנודתיות ממומשת (RV)</b>: לא תיאורטי בכלל - מודד כמה המניה \'
            \'באמת זזה בעבר, מהיסטוריית המחירים. משווים ל-IV כדי לראות אם \'
            \'האופציה "יקרה" או "זולה" ביחס למה שקרה בפועל.<br><br>\'
            \'<b>הסתברות OTM (Put)</b>: הטאב המורכב - לוקח את כל הכלים \'
            \'הקודמים ומיישם על שאלה ספציפית: "מה הסיכוי שהמניה תישאר מעל \'
            \'סטרייק מסוים עד הפקיעה?" לפי שלוש שיטות נפרדות, פלוס תזוזה \'
            \'צפויה, סטרס טסט, CVaR, וטבלת הגנה (לצד קניית פוט).\'
            \'</div>\',
            unsafe_allow_html=True,
        )
        st.markdown(
            \'<div class="rs-explain" style="margin-top:10px;">\'
            \'<b>מילון מונחים קצר:</b><br>\'
            \'<b>Strike (סטרייק)</b>: המחיר שנקבע מראש באופציה.<br>\'
            \'<b>OTM</b>: "מחוץ לכסף" - האופציה פוקעת חסרת ערך (טוב למוכר פוט, רע לקונה).<br>\'
            \'<b>IV</b>: מה השוק מצפה שהמניה תזוז (מהמחיר של האופציה עצמה).<br>\'
            \'<b>RV</b>: מה המניה באמת זזה בעבר (מהמחיר ההיסטורי).<br>\'
            \'<b>Expected Move</b>: טווח מחירים סביר עד הפקיעה, לפי ה-IV.<br>\'
            \'<b>CVaR</b>: ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר - לא תרחיש קיצון בודד.\'
            \'</div>\',
            unsafe_allow_html=True,
        )
'''

# --- עוגן 3: prob_contracts + prob_capital ---------------------------------
PROB_INPUTS_OLD = (
    '            prob_contracts = st.number_input("מספר חוזים", min_value=1, value=1,\n'
    '                                              key=f"{key_prefix}_prob_contracts")\n'
    '        with stress_cols[2]:\n'
    '            prob_capital = st.number_input("הון זמין ($, אופציונלי - להצגת % מההון)", min_value=0.0, value=0.0,\n'
    '                                            key=f"{key_prefix}_prob_capital")\n'
)
PROB_INPUTS_NEW = (
    '            prob_contracts = st.number_input("מספר חוזים", min_value=1, value=1,\n'
    '                                              key=f"{key_prefix}_prob_contracts", help=_HELP["contracts"])\n'
    '        with stress_cols[2]:\n'
    '            prob_capital = st.number_input("הון זמין ($, אופציונלי - להצגת % מההון)", min_value=0.0, value=0.0,\n'
    '                                            key=f"{key_prefix}_prob_capital", help=_HELP["capital"])\n'
)

# --- עוגן 4: שדות מקטע ההגנה ------------------------------------------------
PROT_INPUTS_OLD = (
    '            prot_shares = st.number_input("מניות מוחזקות", min_value=1, value=100,\n'
    '                                           key=f"{key_prefix}_prot_shares")\n'
    '        with prot_cols[1]:\n'
    '            prot_entry = st.number_input("מחיר עלות המניה", min_value=0.01, value=float(round(spot_default, 2)),\n'
    '                                          key=f"{key_prefix}_prot_entry")\n'
    '        with prot_cols[2]:\n'
    '            prot_strike = st.number_input("סטרייק הפוט המגן", min_value=0.01, value=float(round(spot_default * 0.9, 2)),\n'
    '                                           key=f"{key_prefix}_prot_strike")\n'
    '        with prot_cols[3]:\n'
    '            prot_premium = st.number_input("פרמיית הפוט ($)", min_value=0.01, value=5.0,\n'
    '                                            key=f"{key_prefix}_prot_premium")\n'
    '        prot_contracts = st.number_input("מספר חוזי פוט", min_value=1, value=1,\n'
    '                                          key=f"{key_prefix}_prot_contracts")\n'
)
PROT_INPUTS_NEW = (
    '            prot_shares = st.number_input("מניות מוחזקות", min_value=1, value=100,\n'
    '                                           key=f"{key_prefix}_prot_shares", help=_HELP["prot_shares"])\n'
    '        with prot_cols[1]:\n'
    '            prot_entry = st.number_input("מחיר עלות המניה", min_value=0.01, value=float(round(spot_default, 2)),\n'
    '                                          key=f"{key_prefix}_prot_entry", help=_HELP["prot_entry"])\n'
    '        with prot_cols[2]:\n'
    '            prot_strike = st.number_input("סטרייק הפוט המגן", min_value=0.01, value=float(round(spot_default * 0.9, 2)),\n'
    '                                           key=f"{key_prefix}_prot_strike", help=_HELP["prot_strike"])\n'
    '        with prot_cols[3]:\n'
    '            prot_premium = st.number_input("פרמיית הפוט ($)", min_value=0.01, value=5.0,\n'
    '                                            key=f"{key_prefix}_prot_premium", help=_HELP["iv_price"])\n'
    '        prot_contracts = st.number_input("מספר חוזי פוט", min_value=1, value=1,\n'
    '                                          key=f"{key_prefix}_prot_contracts", help=_HELP["contracts"])\n'
)


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
        text = apply_single_anchor(text, HELP_DICT_OLD, HELP_DICT_NEW, "help-dict")
        text = apply_single_anchor(text, GUIDE_OLD, GUIDE_NEW, "guide-expander")
        text = apply_single_anchor(text, PROB_INPUTS_OLD, PROB_INPUTS_NEW, "prob-inputs-help")
        text = apply_single_anchor(text, PROT_INPUTS_OLD, PROT_INPUTS_NEW, "prot-inputs-help")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("ארבעת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
