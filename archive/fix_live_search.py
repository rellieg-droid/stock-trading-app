"""
fix_live_search.py

מחליף את חיפוש ההידר בחיפוש חי בסגנון אתרי מסחר מקצועיים:
מקלידים, הרשימה נפתחת מעצמה, בוחרים, המניה נטענת מיד.

מה יוצא:
  * שדה טקסט שמגיב רק ב-Enter
  * שני כפתורים "חפשי" / "ישירות"
  * רשימת תוצאות שמצוירת ידנית עם כפתור לכל שורה
  * כפתור "סגור"

מה נכנס:
  * st_searchbox עם debounce, שקורא ל-Yahoo תוך כדי הקלדה
  * resolve() נשמר — חיפוש בעברית עדיין עובד, והתוצאה שלו ראשונה ברשימה

הגנה מפני לולאה: st_searchbox מחזיר את הבחירה שוב בכל ריצה מחדש,
ו-_set_ticker קורא ל-st.rerun(). לכן פועלים רק אם הסימול שנבחר שונה
מהסימול הנוכחי.

הרצה:
    py fix_live_search.py            # dry-run
    py fix_live_search.py --apply    # מגבה ואז כותב
"""
import sys
import shutil
import difflib
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")

IMPORT_ANCHOR = "from streamlit_option_menu import option_menu\n"
IMPORT_NEW = (
    "from streamlit_option_menu import option_menu\n"
    "from streamlit_searchbox import st_searchbox\n"
)

NEW_SEARCH_BLOCK = '''    def _set_ticker(sym_found):
        st.session_state.ticker         = sym_found
        st.session_state.err            = ""
        st.session_state.ai_res         = None
        st.session_state.search_results = []
        st.session_state.search_query   = ""
        if sym_found not in st.session_state.recent:
            st.session_state.recent.insert(0, sym_found)
            st.session_state.recent = st.session_state.recent[:8]
        save_user_data()
        st.rerun()

    def _header_search(term: str):
        """
        מוחזר (תווית להצגה, סימול). מתחת ל-2 תווים לא פונים ל-API בכלל,
        אחרת כל הקשה בודדת מייצרת בקשה מיותרת.
        """
        term = (term or "").strip()
        if len(term) < 2:
            return []

        opts, seen = [], set()

        # הצעה ישירה: resolve מטפל גם בשמות בעברית וגם בסימולים ישראליים
        try:
            _direct = resolve(term)
        except Exception:
            _direct = None
        if _direct:
            opts.append((f"▶  {_direct}", _direct))
            seen.add(_direct.upper())

        for _r in yahoo_search(term):
            _sy = _r["sym"]
            if _sy.upper() in seen:
                continue
            seen.add(_sy.upper())
            _nm = _r["name"][:34]
            opts.append((f'{_sy}  ·  {_nm}  ·  {_r["exch"]}', _sy))

        return opts

    _picked = st_searchbox(
        _header_search,
        placeholder="🔍  סימול או שם חברה — AAPL, Tesla, טבע...",
        key="header_sb",
        debounce=250,
        clear_on_submit=False,
    )

    # ההשוואה לטיקר הנוכחי היא מה שמונע לולאת rerun אינסופית
    if _picked and _picked != st.session_state.ticker:
        _set_ticker(_picked)
'''


def replace_block(lines: list[str]) -> list[str] | None:
    """מאתר את הבלוק הישן לפי שורות עוגן, ומחליף אותו בשלמותו."""
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("_s_in = st.text_input("):
            start = i
            break
    if start is None:
        print("לא נמצאה שורת הפתיחה (_s_in = st.text_input). ייתכן שכבר תוקן.")
        return None

    close_idx = None
    for i in range(start, min(start + 140, len(lines))):
        if "close_results" in lines[i]:
            close_idx = i
            break
    if close_idx is None:
        print("לא נמצא סוף הבלוק (close_results). מפסיק.")
        return None

    # אחרי שורת ה-if של close_results יש שתי שורות גוף
    end = close_idx + 2
    if "st.rerun()" not in lines[end]:
        print(f"מבנה בלתי צפוי בסוף הבלוק (שורה {end + 1}). מפסיק.")
        return None

    return lines[:start] + NEW_SEARCH_BLOCK.splitlines(keepends=True) + lines[end + 1:]


def main() -> int:
    apply = "--apply" in sys.argv

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} — הריצי מתוך תיקיית הפרויקט.")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if "st_searchbox" in original:
        print("נראה שהתיקון כבר הוחל. לא נכתב כלום.")
        return 0

    if original.count(IMPORT_ANCHOR) != 1:
        print("עוגן הייבוא לא נמצא בדיוק פעם אחת. מפסיק.")
        return 1
    patched = original.replace(IMPORT_ANCHOR, IMPORT_NEW)
    print("ייבוא: OK")

    new_lines = replace_block(patched.splitlines(keepends=True))
    if new_lines is None:
        return 1
    patched = "".join(new_lines)
    print("בלוק החיפוש: OK")

    for leftover in ("header_search_btn", "header_go", "close_results"):
        if leftover in patched:
            print(f"אזהרה: נשארה התייחסות ל-{leftover}. מפסיק.")
            return 1

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile="לפני", tofile="אחרי", n=3,
    )
    print("\n" + "".join(diff))

    if not apply:
        print("\n[DRY-RUN] לא נכתב כלום. להחלה:  py fix_live_search.py --apply")
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
