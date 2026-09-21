"""
patch_add_load_from_main_watchlist.py
=======================================
מוסיפה כפתור רביעי לשורת רשימת המעקב בסורק: טעינה מה-Watchlist הראשי
של האפליקציה (alpha_paper_trading.py, st.session_state["watchlist"]).
לא נוגעת בקובץ alpha_paper_trading.py בכלל - רק קוראת מאותו session_state
משותף, כי שני הקבצים רצים באותה סשן Streamlit אחת.

שימוש:
    python patch_add_load_from_main_watchlist.py                 # dry-run
    python patch_add_load_from_main_watchlist.py --apply
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

ANCHOR_1 = '        wl_cols = st.columns(3)\n'
NEW_1 = '        wl_cols = st.columns(4)\n'

ANCHOR_2 = (
    '        with wl_cols[2]:\n'
    '            if st.button("\U0001F5D1\uFE0F נקי את רשימת המעקב", key=f"{key_prefix}_scr_wl_clear"):\n'
    '                _save_screener_watchlist([])\n'
    '                st.success("רשימת המעקב נוקתה.")\n'
    '\n'
    '        _current_wl = _load_screener_watchlist()\n'
)

NEW_2 = '''        with wl_cols[2]:
            if st.button("\U0001F5D1\uFE0F נקי את רשימת המעקב", key=f"{key_prefix}_scr_wl_clear"):
                _save_screener_watchlist([])
                st.success("רשימת המעקב נוקתה.")
        with wl_cols[3]:
            if st.button("\U0001F4E5 טעני מה-Watchlist הראשי", key=f"{key_prefix}_scr_wl_main"):
                main_wl = st.session_state.get("watchlist", [])
                if main_wl:
                    st.session_state[f"{key_prefix}_scr_tickers"] = ", ".join(main_wl)
                    st.rerun()
                else:
                    st.info("ה-Watchlist הראשי ריק.")

        _current_wl = _load_screener_watchlist()
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

    text = _apply_edit(text, ANCHOR_1.replace("\r\n", "\n"), NEW_1.replace("\r\n", "\n"), "1/2 - עמודות")
    text = _apply_edit(text, ANCHOR_2.replace("\r\n", "\n"), NEW_2.replace("\r\n", "\n"), "2/2 - כפתור")

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת תחביר בקוד החדש: {e}", file=sys.stderr)
        return 1

    print("שני האנקורים נמצאו ותוקנו בהצלחה. ast.parse עבר.")

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
