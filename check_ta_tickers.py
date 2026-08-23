"""
check_ta_tickers.py

בדיקה ישירה מול yfinance של הטיקרים הבעייתיים ברשימת ה-backlog,
כולל אלטרנטיבות שנמצאו בחיפוש (שם נכון אפשרי לפי מחקר).

שימוש:
    python check_ta_tickers.py
"""

import yfinance as yf

CANDIDATES = {
    "CHKP.TA": ["CHKP.TA", "CHKP"],
    "SANO.TA": ["SANO.TA", "SANO1.TA"],
    "HAPO.TA": ["HAPO.TA", "POLI.TA"],
    "MIZR.TA": ["MIZR.TA", "MZTF.TA"],
    "EMCO.TA": ["EMCO.TA"],
    "SPNS.TA": ["SPNS.TA", "SPNS"],
}

for original, options in CANDIDATES.items():
    print(f"\n=== {original} ===")
    for sym in options:
        try:
            h = yf.Ticker(sym).history(period="5d")
            if h.empty:
                print(f"  {sym}: ריק (אין נתונים)")
            else:
                last_close = h["Close"].iloc[-1]
                print(f"  {sym}: OK - מחיר אחרון {last_close:.2f} ({len(h)} שורות)")
        except Exception as e:
            print(f"  {sym}: שגיאה - {e}")
