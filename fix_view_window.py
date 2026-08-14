"""
fix_view_window.py

מחליף את ריפוד ציר ה-X המלאכותי בחלון תצוגה אמיתי, בסגנון TradingView:
מושכים יותר היסטוריה ממה שמציגים, כדי ש-
  * אינדיקטורים (SMA50/200, MACD) יהיו מחוממים כבר מהנר הראשון שנראה
  * זום-אאוט יחשוף היסטוריה אמיתית במקום שוליים ריקים
  * הצפיפות בין הנרות תהיה אחידה בכל הטווחים בלי טריקים

הרצה:
    py fix_view_window.py            # dry-run
    py fix_view_window.py --apply    # מגבה ואז כותב
"""
import sys
import shutil
import difflib
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")

# ── עריכות מבוססות התאמת טקסט מדויקת (כל הבלוקים כאן ASCII בלבד) ──
EDITS = [
    # 1. כמה למשוך, בנפרד מכמה להציג
    (
        'PERIODS = {\n'
        '    "1D":  ("1d",   "5m"),\n'
        '    "5D":  ("5d",   "15m"),\n'
        '    "1M":  ("1mo",  "1d"),\n'
        '    "6M":  ("6mo",  "1d"),\n'
        '    "YTD": ("ytd",  "1d"),\n'
        '    "1Y":  ("1y",   "1d"),\n'
        '    "5Y":  ("5y",   "1wk"),\n'
        '    "MAX": ("max",  "1mo"),\n'
        '}\n',

        'PERIODS = {\n'
        '    "1D":  ("1d",   "5m"),\n'
        '    "5D":  ("5d",   "15m"),\n'
        '    "1M":  ("1mo",  "1d"),\n'
        '    "6M":  ("6mo",  "1d"),\n'
        '    "YTD": ("ytd",  "1d"),\n'
        '    "1Y":  ("1y",   "1d"),\n'
        '    "5Y":  ("5y",   "1wk"),\n'
        '    "MAX": ("max",  "1mo"),\n'
        '}\n'
        '\n'
        '# כמה היסטוריה למשוך בפועל, לעומת כמה מציגים כברירת מחדל.\n'
        '# משיכה רחבה יותר מחממת את האינדיקטורים לפני הנר הראשון שנראה,\n'
        '# ומאפשרת זום-אאוט לתוך היסטוריה אמיתית. MAX כבר מושך הכל.\n'
        'FETCH_PERIODS = {\n'
        '    "1D":  "5d",\n'
        '    "5D":  "1mo",\n'
        '    "1M":  "6mo",\n'
        '    "6M":  "2y",\n'
        '    "YTD": "2y",\n'
        '    "1Y":  "2y",\n'
        '    "5Y":  "10y",\n'
        '    "MAX": "max",\n'
        '}\n',
    ),

    # 2. שימוש במיפוי המשיכה
    (
        'period, interval = PERIODS[st.session_state.period]\n',

        'period, interval = PERIODS[st.session_state.period]\n'
        'period = FETCH_PERIODS.get(st.session_state.period, period)\n',
    ),

    # 3. ל-1D יש עכשיו כמה סשנים בנתונים, אז הוא צריך את אותם rangebreaks כמו 5D
    (
        '    if _cur_period == "1D":\n'
        '        _x_rangebreaks = []\n'
        '    elif _cur_period == "5D":\n'
        '        _x_rangebreaks = [dict(bounds=[16, 9.5], pattern="hour"), dict(bounds=["sat", "mon"])]\n',

        '    if _cur_period in ("1D", "5D"):\n'
        '        _x_rangebreaks = [dict(bounds=[16, 9.5], pattern="hour"), dict(bounds=["sat", "mon"])]\n',
    ),

    # 4. הצבת החלון על הציר
    (
        '        range=_x_padded_range, autorange=(_x_padded_range is None),\n',
        '        range=_x_view_range, autorange=(_x_view_range is None),\n',
    ),
]

# ── הבלוק שמוחלף בשלמותו (כולל שורות ההערה שמעליו) ──
OLD_PAD_BLOCK = (
    '    _n_bars = len(idx)\n'
    '    _min_visible_slots = 100\n'
    '    _x_padded_range = None\n'
    '    if 2 <= _n_bars < _min_visible_slots and _cur_period != "1D":\n'
    '        _missing = _min_visible_slots - _n_bars\n'
    '        _pad_each_side = _missing // 2\n'
    '        if _pad_each_side >= 1:\n'
    '            _bday = pd.tseries.offsets.BDay(_pad_each_side)\n'
    '            _idx_dt = pd.to_datetime(pd.Series(idx))\n'
    '            _x_padded_range = [_idx_dt.iloc[0] - _bday, _idx_dt.iloc[-1] + _bday]\n'
)

NEW_VIEW_BLOCK = '''    # ── חלון תצוגה ──
    # הנתונים שנמשכו רחבים מהחלון המוצג (ראי FETCH_PERIODS). כאן קובעים
    # כמה מתוכם נראה כברירת מחדל. השאר קיים ברקע וזום-אאוט חושף אותו.
    _n_bars = len(idx)
    _x_view_range = None
    if _n_bars >= 2:
        _idx_dt = pd.to_datetime(pd.Series(idx))
        _first, _last = _idx_dt.iloc[0], _idx_dt.iloc[-1]
        _start = None
        if _cur_period in ("1D", "5D"):
            # תוך-יומי: סופרים ימי מסחר בפועל, לא ימי לוח
            _sessions = _idx_dt.dt.normalize().unique()
            _n_sess = 1 if _cur_period == "1D" else 5
            _start = _sessions[max(0, len(_sessions) - _n_sess)]
        elif _cur_period == "YTD":
            _start = pd.Timestamp(year=_last.year, month=1, day=1, tz=_last.tz)
        else:
            _spans = {
                "1M": pd.DateOffset(months=1),
                "6M": pd.DateOffset(months=6),
                "1Y": pd.DateOffset(years=1),
                "5Y": pd.DateOffset(years=5),
            }
            if _cur_period in _spans:
                _start = _last - _spans[_cur_period]
        # MAX, או טווח שכבר מכסה את כל מה שנמשך -> autorange
        if _start is not None and _start > _first:
            _x_view_range = [_start, _last]
'''


def apply_block_replacement(text: str) -> str | None:
    """מחליף את בלוק הריפוד, ומוחק גם את שורות ההערה שמעליו."""
    if text.count(OLD_PAD_BLOCK) != 1:
        return None
    head, tail = text.split(OLD_PAD_BLOCK)
    # גלילה אחורה מעל שורות ההערה שמתארות את הריפוד
    head_lines = head.split("\n")
    while len(head_lines) >= 2 and head_lines[-2].strip().startswith("#"):
        head_lines.pop(-2)
    return "\n".join(head_lines) + NEW_VIEW_BLOCK + tail


def main() -> int:
    apply = "--apply" in sys.argv

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} — הריצי מתוך תיקיית הפרויקט.")
        return 1

    original = TARGET.read_text(encoding="utf-8")
    patched = original

    for idx_e, (old, new) in enumerate(EDITS, start=1):
        count = patched.count(old)
        if count != 1:
            print(f"עריכה {idx_e}: נמצאו {count} התאמות במקום אחת. מפסיק, לא נכתב כלום.")
            return 1
        patched = patched.replace(old, new)
        print(f"עריכה {idx_e}: OK")

    result = apply_block_replacement(patched)
    if result is None:
        print("עריכה 5: בלוק הריפוד לא נמצא (או מופיע יותר מפעם אחת). מפסיק.")
        return 1
    patched = result
    print("עריכה 5: OK (בלוק הריפוד + ההערות שלו הוחלפו)")

    if "_x_padded_range" in patched:
        print("אזהרה: נשארו התייחסויות ל-_x_padded_range. מפסיק.")
        return 1

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile="לפני", tofile="אחרי", n=3,
    )
    print("\n" + "".join(diff))

    if not apply:
        print("\n[DRY-RUN] לא נכתב כלום. להחלה:  py fix_view_window.py --apply")
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
