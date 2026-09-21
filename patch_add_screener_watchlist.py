"""
patch_add_screener_watchlist.py
=================================
מוסיפה רשימת מעקב אישית לסורק - שמורה בקובץ JSON, לא תלויה ב-Watchlist
הראשי של Alpha Charts Pro (זה נפרד בכוונה, ראו הערה למטה). שלושה
כפתורים: שמירה, טעינה, ניקוי.

שני אנקורים:
1. import json ליד ה-imports הקיימים.
2. פונקציות load/save + שורת כפתורים בתוך tab_screener, מיד אחרי
   ה-text_area של הטיקרים.

שימוש:
    python patch_add_screener_watchlist.py                 # dry-run
    python patch_add_screener_watchlist.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR_1 = (
    'import sqlite3\n'
    'from datetime import date as _date\n'
)
NEW_1 = (
    'import sqlite3\n'
    'import json\n'
    'from datetime import date as _date\n'
)

ANCHOR_2 = (
    '        scr_tickers_raw = st.text_area(\n'
    '            "טיקרים (מופרדים בפסיק או בשורות נפרדות)",\n'
    '            value="AAPL, MSFT, NVDA",\n'
    '            key=f"{key_prefix}_scr_tickers",\n'
    '        )\n'
    '        scr_cols = st.columns(3)\n'
)

NEW_2 = '''        scr_tickers_raw = st.text_area(
            "טיקרים (מופרדים בפסיק או בשורות נפרדות)",
            value="AAPL, MSFT, NVDA",
            key=f"{key_prefix}_scr_tickers",
        )

        wl_cols = st.columns(3)
        with wl_cols[0]:
            if st.button("\U0001F4BE שמרי לרשימת המעקב שלי", key=f"{key_prefix}_scr_wl_save"):
                current = [
                    t.strip().upper()
                    for chunk in scr_tickers_raw.split("\\n")
                    for t in chunk.split(",") if t.strip()
                ]
                merged = sorted(set(_load_screener_watchlist()) | set(current))
                _save_screener_watchlist(merged)
                st.success(f"נשמרו. סה\\"כ ברשימת המעקב: {len(merged)} טיקרים.")
        with wl_cols[1]:
            if st.button("\U0001F4CB טעני מרשימת המעקב שלי", key=f"{key_prefix}_scr_wl_load"):
                saved = _load_screener_watchlist()
                if saved:
                    st.session_state[f"{key_prefix}_scr_tickers"] = ", ".join(saved)
                    st.rerun()
                else:
                    st.info("רשימת המעקב ריקה עדיין.")
        with wl_cols[2]:
            if st.button("\U0001F5D1\uFE0F נקי את רשימת המעקב", key=f"{key_prefix}_scr_wl_clear"):
                _save_screener_watchlist([])
                st.success("רשימת המעקב נוקתה.")

        _current_wl = _load_screener_watchlist()
        if _current_wl:
            st.caption(f"ברשימת המעקב שלך כרגע: {', '.join(_current_wl)}")

        scr_cols = st.columns(3)
'''

ANCHOR_3 = (
    '# ---------------------------------------------------------------------------\n'
    '# סורק רב-מניות - שכבת ריכוז בלבד. שואבת עם אותם _try_fetch_* שכבר בקובץ,\n'
    '# מחשבת עם build_screener_row (options_engine.py) - אין כאן נוסחה חדשה.\n'
    '# ---------------------------------------------------------------------------\n'
    '\n'
    'def _run_screener(\n'
)

NEW_3 = '''# ---------------------------------------------------------------------------
# רשימת מעקב אישית לסורק - קובץ JSON נפרד מ-Watchlist הראשי של האפליקציה
# בכוונה: זו רשימת "מניות שכדאי לבדוק" לצורך הסורק, לא רשימת ההחזקות/
# מעקב הכללית. שילוב עם ה-Watchlist הראשי (אם רוצים גם את זה) דורש
# לראות איפה הוא ממומש - זה קובץ אחר.
# ---------------------------------------------------------------------------
_SCREENER_WATCHLIST_FILE = "riskshield_watchlist.json"


def _load_screener_watchlist() -> list[str]:
    """טוענת את רשימת המעקב האישית של הסורק. נכשלת בשקט לרשימה ריקה."""
    try:
        with open(_SCREENER_WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [t for t in data if isinstance(t, str)]
    except Exception:
        return []


def _save_screener_watchlist(tickers: list[str]) -> None:
    """שומרת את רשימת המעקב. נכשלת בשקט (דיסק/הרשאות) - לא שוברת את הטאב."""
    try:
        with open(_SCREENER_WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(set(tickers)), f, ensure_ascii=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# סורק רב-מניות - שכבת ריכוז בלבד. שואבת עם אותם _try_fetch_* שכבר בקובץ,
# מחשבת עם build_screener_row (options_engine.py) - אין כאן נוסחה חדשה.
# ---------------------------------------------------------------------------

def _run_screener(
'''


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

    text = _apply_edit(text, ANCHOR_1.replace("\r\n", "\n"), NEW_1.replace("\r\n", "\n"), "1/3 - import json")
    text = _apply_edit(text, ANCHOR_2.replace("\r\n", "\n"), NEW_2.replace("\r\n", "\n"), "2/3 - כפתורי רשימת מעקב")
    text = _apply_edit(text, ANCHOR_3.replace("\r\n", "\n"), NEW_3.replace("\r\n", "\n"), "3/3 - פונקציות load/save")

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
