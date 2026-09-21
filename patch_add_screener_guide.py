"""
patch_add_screener_guide.py
=============================
מוסיפה מדריך (expander) בתוך טאב הסורק - מסביר בשפה פשוטה מה מטרת
הטבלה ומאיפה "פרמיה תיאורטית" מגיעה, לאדם שפחות מכיר את המושגים.
אותו דפוס st.expander שכבר קיים בראש הטאב הכללי של RiskShield.

שימוש:
    python patch_add_screener_guide.py                 # dry-run
    python patch_add_screener_guide.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR = (
    "    with tab_screener:\n"
    "        st.markdown(\n"
    "            '<div class=\"rs-explain\" style=\"margin-bottom:12px;\">'\n"
    "            'מריץ את המודל, ההסתברויות, ה-CVaR וה-RV Rank על רשימת טיקרים בבת אחת, '\n"
    "            'בדלתא יעד אחידה לכולם (כך ההשוואה בין מניות שונות הוגנת - אותו \"עומק\" '\n"
    "            'יחסי, לא סטרייק דולרי קבוע). פרמיית הפוט בטבלה תיאורטית (Black-Scholes), '\n"
    "            'לא מחיר שוק בפועל.'\n"
    "            '</div>',\n"
    "            unsafe_allow_html=True,\n"
    "        )\n"
    "\n"
    "        scr_tickers_raw = st.text_area(\n"
)

NEW = '''    with tab_screener:
        st.markdown(
            \'<div class="rs-explain" style="margin-bottom:12px;">\'
            \'מריץ את המודל, ההסתברויות, ה-CVaR וה-RV Rank על רשימת טיקרים בבת אחת, \'
            \'בדלתא יעד אחידה לכולם (כך ההשוואה בין מניות שונות הוגנת - אותו "עומק" \'
            \'יחסי, לא סטרייק דולרי קבוע). פרמיית הפוט בטבלה תיאורטית (Black-Scholes), \'
            \'לא מחיר שוק בפועל.\'
            \'</div>\',
            unsafe_allow_html=True,
        )

        with st.expander("📖 מדריך: מה המטרה של הטבלה, ומאיפה המספרים מגיעים"):
            st.markdown(
                \'<div class="rs-explain">\'
                \'<b>מה זה בכלל עושה?</b><br>\'
                \'לוקח רשימת מניות שאת נותנת, ומריץ על כל אחת את אותה שאלה בדיוק: \'
                \'"אם הייתי כותבת (מוכרת) Put על המניה הזו, בסטרייק שנמצא באותו \'
                \'\\\'מרחק יחסי\\\' מהמחיר הנוכחי (נקבע לפי הדלתא שבחרת), מה היו \'
                \'המספרים?" המטרה היא להשוות הרבה מניות זו לזו במבט אחד - לא לומר \'
                \'איזו לבחור.<br><br>\'
                \'<b>מאיפה מגיעה "פרמיה תיאורטית"?</b><br>\'
                \'מנוסחה מתמטית ידועה (Black-Scholes) - אותה נוסחה שגם עושי-שוק \'
                \'משתמשים בה כנקודת פתיחה לתמחור אופציות. היא מקבלת 5 מספרים: מחיר \'
                \'המניה כרגע, הסטרייק, כמה ימים נשארו לפקיעה, כמה תנועה השוק מצפה \'
                \'מהמניה (IV, נשלף מהשוק האמיתי), וריבית חסרת סיכון - ומחשבת מהם \'
                \'"מחיר הוגן" תיאורטי.<br><br>\'
                \'<b>למה זה "עקבי להשוואה" אם זה לא המחיר האמיתי?</b><br>\'
                \'כמו למדוד כמה חדרים באותו סרגל בדיוק - ההשוואה ביניהם אמינה, גם \'
                \'אם הסרגל עצמו סוטה קצת מהמטר האמיתי. אותה נוסחה, באותה לוגיקה, \'
                \'מופעלת על כל מניה בטבלה בלי יוצא מן הכלל - אז השוואה יחסית \'
                \'ביניהן הגיונית, גם אם המספר המוחלט של כל אחת עלול להיות שונה \'
                \'ממה שהברוקר יציע בפועל. מחיר שוק אמיתי מושפע גם מדברים שהמודל \'
                \'לא רואה - כמה קונים/מוכרים יש כרגע על החוזה הספציפי, וכמה \'
                \'"עמלת תיווך" (bid-ask spread) השוק גובה.<br><br>\'
                \'<b>המסקנה המעשית:</b> אפשר לסמוך על הטבלה כדי לצמצם רשימה ארוכה \'
                \'למועמדות שכדאי לבדוק לעומק - אבל לפני שסוגרים עסקה בפועל, תמיד \'
                \'פותחים את שרשרת האופציות האמיתית אצל הברוקר ובודקים את המחיר \'
                \'בפועל.\'
                \'</div>\',
                unsafe_allow_html=True,
            )

        scr_tickers_raw = st.text_area(
'''


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
