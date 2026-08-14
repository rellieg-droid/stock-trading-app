"""
fix_input_css.py

מתקן שדות טקסט שנראים לבנים עם טקסט בלתי נראה.
הסיבה: הסלקטור הקיים ".stTextInput > div > div" לא תופס את ה-DOM של
Streamlit 1.55, שעבר למאפייני data-baseweb. העטיפה נשארת בהירה, והטקסט
הבהיר שמוגדר עליה נעלם.

הפתרון: כלל CSS ממוקד יותר שמכוון ישירות לעטיפות baseweb, עם ספציפיות
גבוהה מספיק כדי לנצח בלי תלות בסדר הכללים.

הרצה:
    py fix_input_css.py            # dry-run
    py fix_input_css.py --apply    # מגבה ואז כותב
"""
import sys
import shutil
import difflib
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")

ANCHOR = (
    '.stTextInput > div > div,\n'
    '.stTextInput input,\n'
    '.stNumberInput input {\n'
)

NEW_CSS = '''/* Streamlit 1.55 baseweb DOM — העטיפות שצריך לצבוע בפועל.
   ספציפיות גבוהה מהכלל הישן, לכן מנצח בלי קשר לסדר. */
[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stTextInput"] div[data-baseweb="base-input"],
[data-testid="stNumberInput"] div[data-baseweb="input"],
[data-testid="stNumberInput"] div[data-baseweb="base-input"] {
  background: var(--c-surface-2) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: 6px !important;
}
/* ה-input עצמו שקוף, כדי שצבע העטיפה יראה דרכו */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
  background: transparent !important;
  color: var(--c-text-1) !important;
  -webkit-text-fill-color: var(--c-text-1) !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder {
  color: var(--c-text-3, #8b949e) !important;
  opacity: 1 !important;
}
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within {
  border-color: var(--c-blue) !important;
  box-shadow: 0 0 0 1px rgba(31,111,235,0.3) !important;
}

'''


def main() -> int:
    apply = "--apply" in sys.argv

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} — הריצי מתוך תיקיית הפרויקט.")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if '[data-testid="stTextInput"] div[data-baseweb="input"]' in original:
        print("נראה שהתיקון כבר הוחל. לא נכתב כלום.")
        return 0

    count = original.count(ANCHOR)
    if count != 1:
        print(f"נמצאו {count} עוגנים במקום אחד. מפסיק, לא נכתב כלום.")
        return 1

    patched = original.replace(ANCHOR, NEW_CSS + ANCHOR)

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile="לפני", tofile="אחרי", n=3,
    )
    print("".join(diff))

    if not apply:
        print("\n[DRY-RUN] לא נכתב כלום. להחלה:  py fix_input_css.py --apply")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}.{stamp}.bak")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(patched, encoding="utf-8")
    print(f"\nגיבוי: {backup}")
    print(f"נכתב:  {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
