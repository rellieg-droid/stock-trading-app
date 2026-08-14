"""
fix_cmp_period.py
מתקן את הבאג בטאב "השוואה": תוויות ה-selectbox ("1M","3M"...) נשלחו ישירות
כ-period ל-yfinance, שדוחה אותן בשקט ומחזיר None — כלומר הטאב לא עבד בכלל.

הרצה:
    py fix_cmp_period.py            # dry-run — רק מציג diff
    py fix_cmp_period.py --apply    # מגבה ואז כותב
"""
import sys
import shutil
import difflib
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")

EDITS = [
    # ── 1. מוסיפים מיפוי period ליד מיפוי ה-interval הקיים ──
    (
        '            INTERVAL_MAP = {"1M":"1d","3M":"1d","6M":"1d","1Y":"1d","3Y":"1wk","5Y":"1wk"}\n'
        '            interval_cmp = INTERVAL_MAP.get(cmp_period, "1d")\n',

        '            INTERVAL_MAP = {"1M":"1d","3M":"1d","6M":"1d","1Y":"1d","3Y":"1wk","5Y":"1wk"}\n'
        '            interval_cmp = INTERVAL_MAP.get(cmp_period, "1d")\n'
        '            # תוויות ה-UI אינן מחרוזות period חוקיות של yfinance — חובה למפות.\n'
        '            # ל-3Y אין period מקביל, לכן מושכים 5y וחותכים בהמשך.\n'
        '            CMP_PERIOD_MAP = {"1M":"1mo","3M":"3mo","6M":"6mo",\n'
        '                              "1Y":"1y","3Y":"5y","5Y":"5y"}\n'
        '            period_cmp = CMP_PERIOD_MAP.get(cmp_period, "1y")\n',
    ),

    # ── 2. הקריאה עצמה + חיתוך ל-3 שנים ──
    (
        '                        df_c = load_ohlcv(sym_c, cmp_period, interval_cmp)\n'
        '                        if df_c is not None and len(df_c) > 0:\n',

        '                        df_c = load_ohlcv(sym_c, period_cmp, interval_cmp)\n'
        '                        if df_c is not None and len(df_c) > 0 and cmp_period == "3Y":\n'
        '                            _cut3 = df_c.index[-1] - pd.DateOffset(years=3)\n'
        '                            df_c = df_c[df_c.index >= _cut3]\n'
        '                        if df_c is not None and len(df_c) > 0:\n',
    ),
]


def main() -> int:
    apply = "--apply" in sys.argv

    if not TARGET.exists():
        print(f"לא נמצא {TARGET} — הריצי מתוך תיקיית הפרויקט.")
        return 1

    original = TARGET.read_text(encoding="utf-8")
    patched = original

    for idx, (old, new) in enumerate(EDITS, start=1):
        count = patched.count(old)
        if count == 0:
            print(f"עריכה {idx}: הבלוק לא נמצא. ייתכן שהקוד כבר תוקן או השתנה. מפסיק.")
            return 1
        if count > 1:
            print(f"עריכה {idx}: הבלוק מופיע {count} פעמים — לא חד-משמעי. מפסיק.")
            return 1
        patched = patched.replace(old, new)
        print(f"עריכה {idx}: התאמה אחת נמצאה.")

    if patched == original:
        print("אין שינוי.")
        return 0

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"{TARGET} (לפני)",
        tofile=f"{TARGET} (אחרי)",
        n=3,
    )
    print("\n" + "".join(diff))

    if not apply:
        print("\n[DRY-RUN] לא נכתב כלום. להחלה:  py fix_cmp_period.py --apply")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}.{stamp}.bak")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(patched, encoding="utf-8")
    print(f"\nגיבוי נשמר: {backup}")
    print(f"נכתב: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
