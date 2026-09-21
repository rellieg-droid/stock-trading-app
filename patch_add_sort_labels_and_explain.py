"""
patch_add_sort_labels_and_explain.py
=======================================
מתקנת את תיבת "מיין לפי" בטאב הסורק: במקום להציג שמות שדה גולמיים
(rv_rank, iv_rv_spread וכו') היא מציגה עכשיו תוויות בעברית, ומוסיפה
הסבר קצר שמתעדכן לפי הפרמטר שנבחר - כדי שברור מה כל מדד אומר בלי
לפתוח תיעוד חיצוני.

שימוש:
    python patch_add_sort_labels_and_explain.py                 # dry-run
    python patch_add_sort_labels_and_explain.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR = (
    '                _sortable = [c for c in [\n'
    '                    "ticker", "spot", "strike", "iv", "rv_rank", "rv_percentile",\n'
    '                    "iv_rv_spread", "expected_move_pct", "put_premium", "put_delta",\n'
    '                    "breakeven", "prob_otm_model", "prob_otm_fat_tail",\n'
    '                    "prob_otm_historical", "xem_distance", "cvar_5pct", "max_loss",\n'
    '                ] if c in scr_view.columns]\n'
    '                sort_ui = st.columns([2, 1])\n'
    '                with sort_ui[0]:\n'
    '                    sort_by = st.selectbox("מיין לפי", _sortable, index=0, key=f"{key_prefix}_scr_sort_by")\n'
    '                with sort_ui[1]:\n'
    '                    sort_desc = st.checkbox("יורד", value=False, key=f"{key_prefix}_scr_sort_desc")\n'
    '                scr_view = scr_view.sort_values(sort_by, ascending=not sort_desc, na_position="last")\n'
)

NEW = '''                _sortable = [c for c in [
                    "ticker", "spot", "strike", "iv", "rv_rank", "rv_percentile",
                    "iv_rv_spread", "expected_move_pct", "put_premium", "put_delta",
                    "breakeven", "prob_otm_model", "prob_otm_fat_tail",
                    "prob_otm_historical", "xem_distance", "cvar_5pct", "max_loss",
                ] if c in scr_view.columns]

                _scr_metric_labels = {
                    "ticker": "טיקר", "spot": "מחיר", "strike": "סטרייק", "iv": "IV",
                    "rv_rank": "RV Rank", "rv_percentile": "RV Percentile",
                    "iv_rv_spread": "IV-RV (הפרש)", "expected_move_pct": "תזוזה צפויה (%)",
                    "put_premium": "פרמיית הפוט", "put_delta": "דלתא בפועל",
                    "breakeven": "Breakeven", "prob_otm_model": "הסתברות OTM - מודל",
                    "prob_otm_fat_tail": "הסתברות OTM - Fat-tail",
                    "prob_otm_historical": "הסתברות OTM - היסטורי", "xem_distance": "מרחק (xEM)",
                    "cvar_5pct": "CVaR (5% הגרועים)", "max_loss": "הפסד מקסימלי",
                }
                _scr_metric_explain = {
                    "ticker": "סימול המניה.",
                    "spot": "מחיר המניה הנוכחי בשוק.",
                    "strike": "מחיר המימוש שנבחר לפי הדלתא היעד שהוגדרה למעלה.",
                    "iv": "תנודתיות גלומה - כמה תנועה השוק מצפה, לפי מחיר האופציה בפועל.",
                    "rv_rank": "דירוג התנודתיות שהמניה הראתה בפועל (0-100) ביחס לטווח שלה. תחליף זמני ל-IV Rank.",
                    "rv_percentile": "אחוז הימים בהיסטוריה שבהם ה-RV היה נמוך מהערך הנוכחי.",
                    "iv_rv_spread": "ההפרש בין IV ל-RV. חיובי = השוק מתמחר יותר תנודתיות ממה שקרה בפועל.",
                    "expected_move_pct": "התזוזה הצפויה עד הפקיעה, כאחוז מהמחיר הנוכחי (סטיית תקן אחת).",
                    "put_premium": "פרמיית הפוט התיאורטית (Black-Scholes) - לא מחיר שוק בפועל.",
                    "put_delta": "הדלתא בפועל של הסטרייק שנבחר - אמורה להיות קרובה לדלתא היעד שהוגדרה.",
                    "breakeven": "המחיר שמתחתיו מוכר הפוט מתחיל להפסיד בפועל (סטרייק פחות פרמיה).",
                    "prob_otm_model": "הסתברות (Black-Scholes) שהאופציה תפקע מחוץ לכסף.",
                    "prob_otm_fat_tail": "אותה הסתברות OTM, לפי מודל עם \\'זנבות שמנים\\' (t-Student) במקום נורמלית.",
                    "prob_otm_historical": "הסתברות OTM לפי מה שקרה בפועל בהיסטוריה, לא לפי מודל תיאורטי.",
                    "xem_distance": "כמה \\'תזוזות צפויות\\' רחוק הסטרייק מהמחיר הנוכחי.",
                    "cvar_5pct": "ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר, לתקופה של dte_days ימים.",
                    "max_loss": "ההפסד המקסימלי התיאורטי בפוזיציה (סטרייק פחות פרמיה, כפול 100 כפול חוזים).",
                }

                sort_ui = st.columns([2, 1])
                with sort_ui[0]:
                    sort_by = st.selectbox(
                        "מיין לפי", _sortable, index=0, key=f"{key_prefix}_scr_sort_by",
                        format_func=lambda c: _scr_metric_labels.get(c, c),
                    )
                with sort_ui[1]:
                    sort_desc = st.checkbox("יורד", value=False, key=f"{key_prefix}_scr_sort_desc")
                st.caption(_scr_metric_explain.get(sort_by, ""))
                scr_view = scr_view.sort_values(sort_by, ascending=not sort_desc, na_position="last")
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
