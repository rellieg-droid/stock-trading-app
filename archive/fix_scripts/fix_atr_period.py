"""
fix_atr_period.py — Alpha Charts Pro

מתקן שימוש בערך period לא חוקי בקריאות ל-load_ohlcv.

load_ohlcv מעביר את ה-period ישירות ל-yf.Ticker.history(), שמקבל
רק את הערכים של yfinance: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max.
"3M" אינו חוקי והשליפה מחזירה None בשקט.

שני מקומות:
ארבעה מקומות, שלושה מהם באגים קיימים מלפני עבודת ה-ATR.

שימוש:
    py fix_atr_period.py            <- תצוגה מקדימה
    py fix_atr_period.py --apply    <- ביצוע + גיבוי
"""

import re
import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

VALID = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}

# מיפוי מהערך השגוי לערך שיאהו מקבלת
FIXES = {"3M": "3mo", "5D": "5d", "1M": "1mo", "6M": "6mo", "1D": "1d", "1Y": "1y"}


def main():
    try:
        with open(TARGET, "r", encoding="utf-8", newline="") as fh:
            src = fh.read()
    except FileNotFoundError:
        print(f"[עצירה] {TARGET} לא נמצא. מריצים מתיקיית הפרויקט.")
        return 1

    # ── סריקה: כל קריאה ל-load_ohlcv עם period מילולי ────────────────
    pattern = re.compile(r'load_ohlcv\(\s*([^,]+?)\s*,\s*"([^"]+)"')
    findings = []
    for m in pattern.finditer(src):
        period = m.group(2)
        line_no = src[:m.start()].count("\n") + 1
        findings.append((line_no, m.group(1).strip(), period, period in VALID))

    print("=" * 62)
    print("בדיקת period בקריאות ל-load_ohlcv"
          + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print()
    bad = [f for f in findings if not f[3]]
    for line_no, sym, period, ok in findings:
        mark = "תקין" if ok else "לא חוקי"
        print(f'  שורה {line_no:>5}  load_ohlcv({sym}, "{period}", ...)   {mark}')

    if not bad:
        print("\n  כל הקריאות תקינות. אין מה לתקן.")
        return 0

    print(f"\n  ערכים לא חוקיים: {len(bad)}")
    print(f"  yfinance מקבל רק: {', '.join(sorted(VALID))}")
    unknown = {f[2] for f in bad} - set(FIXES)
    if unknown:
        print(f"\n[עצירה] ערכים שאין להם תיקון מוגדר: {unknown}")
        return 1
    print("\n  התיקונים:")
    for w, r in FIXES.items():
        print(f'    "{w}" -> "{r}"')

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_atr_period.py --apply")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)

    n_before = src.count('load_ohlcv')
    out, n_fixed = src, 0
    for wrong, right in FIXES.items():
        pat = r'(load_ohlcv\(\s*[^,]+?\s*,\s*)"' + wrong + '"'
        n_fixed += len(re.findall(pat, out))
        out = re.sub(pat, r'\1"' + right + '"', out)

    if out.count('load_ohlcv') != n_before:
        print("[עצירה] מספר הקריאות השתנה. לא נכתב כלום.")
        return 1

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print("\n" + "-" * 62)
    print(f"תוקנו {n_fixed} קריאות. גיבוי: {backup}")
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    print("  ואז Ctrl+F5. שווה לבדוק גם את טאב Watchlist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
