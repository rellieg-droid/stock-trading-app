"""
patch_fix_widget_session_state_error.py
==========================================
מתקנת StreamlitAPIException: "cannot be modified after the widget with
key ... is instantiated". הבאג: הכפתורים "טעני..." ניסו לכתוב ישירות
ל-st.session_state[key] של תיבת הטיקרים אחרי שה-widget הזה כבר נוצר
באותה הרצה (text_area מוגדר למעלה, הכפתורים למטה) - Streamlit אוסר
את זה בכל מקרה, גם עם st.rerun() אחריו.

התיקון: דפוס "ערך ממתין" (pending) - הכפתור כותב למפתח session_state
נפרד, לא למפתח של ה-widget עצמו, וקורא ל-st.rerun(). בתחילת ההרצה
הבאה, *לפני* שה-widget נוצר, בודקים אם יש ערך ממתין ומעתיקים אותו
למפתח של ה-widget - זה מותר, כי זה קורה לפני היצירה, לא אחריה.

שלושה אנקורים:
1. הוספת הבדיקה/העתקה של ה-pending, ממש לפני st.text_area.
2. שינוי כפתור "טעני מרשימת המעקב שלי" לכתוב ל-pending במקום ישירות.
3. שינוי כפתור "טעני מה-Watchlist הראשי" לכתוב ל-pending במקום ישירות.

שימוש:
    python patch_fix_widget_session_state_error.py                 # dry-run
    python patch_fix_widget_session_state_error.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR_1 = '        scr_tickers_raw = st.text_area(\n'
NEW_1 = (
    '        _scr_pending_key = f"{key_prefix}_scr_tickers_pending"\n'
    '        if _scr_pending_key in st.session_state:\n'
    '            # מותר לכתוב ל-session_state של ה-widget רק *לפני* שהוא נוצר -\n'
    '            # זו בדיוק הנקודה הזו, עוד לפני קריאת st.text_area שמתחת.\n'
    '            st.session_state[f"{key_prefix}_scr_tickers"] = st.session_state.pop(_scr_pending_key)\n'
    '\n'
    '        scr_tickers_raw = st.text_area(\n'
)

ANCHOR_2 = '                    st.session_state[f"{key_prefix}_scr_tickers"] = ", ".join(saved)\n'
NEW_2 = '                    st.session_state[_scr_pending_key] = ", ".join(saved)\n'

ANCHOR_3 = '                    st.session_state[f"{key_prefix}_scr_tickers"] = ", ".join(main_wl)\n'
NEW_3 = '                    st.session_state[_scr_pending_key] = ", ".join(main_wl)\n'


def _apply_edit(text: str, anchor: str, new_block: str, label: str) -> str:
    count = text.count(anchor)
    if count == 0:
        print(f"[{label}] האנקור לא נמצא. עוצר בלי לגעת בקובץ.", file=sys.stderr)
        sys.exit(1)
    if count > 1:
        print(f"[{label}] האנקור נמצא {count} פעמים - לא ייחודי, עוצר.", file=sys.stderr)
        sys.exit(1)
    return text.replace(anchor, new_block, 1)


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

    text = _apply_edit(text, ANCHOR_1.replace("\r\n", "\n"), NEW_1.replace("\r\n", "\n"), "1/3 - בדיקת pending לפני ה-widget")
    text = _apply_edit(text, ANCHOR_2.replace("\r\n", "\n"), NEW_2.replace("\r\n", "\n"), "2/3 - כפתור רשימה אישית")
    text = _apply_edit(text, ANCHOR_3.replace("\r\n", "\n"), NEW_3.replace("\r\n", "\n"), "3/3 - כפתור Watchlist ראשי")

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת תחביר בקוד החדש: {e}", file=sys.stderr)
        return 1

    print("שלושת האנקורים נמצאו ותוקנו בהצלחה. ast.parse עבר.")

    if not args.apply:
        print("\nDry-run בלבד. הריצי עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(TARGET.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נשמר: {backup}")

    out_text = text.replace("\n", "\r\n") if used_crlf else text
    TARGET.write_bytes(out_text.encode("utf-8"))
    print(f"בוצע. {TARGET} עודכן.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
