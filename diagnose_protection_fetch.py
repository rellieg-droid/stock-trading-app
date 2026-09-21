"""
דיאגנוסטיקה - לא נוגע באפליקציה. מריץ את אותה לוגיקה כמו
_try_fetch_otm_put_quote() אבל בלי ה-try/except השקט, כדי לראות
בדיוק באיזה שלב זה נכשל ולמה.

שימוש (מתוך C:\\PhyCharm_projects\\Stock_tracking\\):
    C:\\PhyCharm_projects\\Stock_tracking\\.venv\\Scripts\\python.exe diagnose_protection_fetch.py AAPL 90 30
    (טיקר, סטרייק כתיבה, ימים לפקיעה - כולם אופציונליים, ברירת מחדל AAPL/90/30)
"""
import sys
from datetime import date, timedelta

ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
below_strike = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
dte_days = int(sys.argv[3]) if len(sys.argv) > 3 else 30

import yfinance as yf

print(f"בודקת: {ticker}, סטרייק כתיבה {below_strike}, {dte_days} ימים לפקיעה\n")

tk = yf.Ticker(ticker)
expirations = tk.options
print(f"תפוגות זמינות: {len(expirations)}")
if not expirations:
    print("STOP: אין תפוגות בכלל לטיקר הזה - יתכן שאין לו אופציות נסחרות, או בעיית רשת.")
    sys.exit(1)

target_date = date.today() + timedelta(days=dte_days)
best_exp = min(expirations, key=lambda e: abs((date.fromisoformat(e) - target_date).days))
actual_dte = (date.fromisoformat(best_exp) - date.today()).days
print(f"תפוגה שנבחרה: {best_exp} ({actual_dte} ימים בפועל)")

puts = tk.option_chain(best_exp).puts
print(f"שורות פוט בשרשרת: {len(puts)}")
if puts.empty:
    print("STOP: השרשרת ריקה עבור התפוגה הזו.")
    sys.exit(1)

spot = float(tk.history(period="5d")["Close"].iloc[-1])
print(f"מחיר נכס נוכחי: ${spot:,.2f}")

below = puts[puts["strike"] < below_strike]
print(f"שורות עם סטרייק מתחת ל-{below_strike}: {len(below)}")

valid_bid_ask = below[(below["bid"] > 0) & (below["ask"] > 0)]
print(f"מתוכן, עם bid>0 וגם ask>0: {len(valid_bid_ask)}")

if valid_bid_ask.empty:
    n_zero_bid = (below["bid"] <= 0).sum()
    n_zero_ask = (below["ask"] <= 0).sum()
    print(f"\nSTOP: אין אף שורה עם ציטוט חי. {n_zero_bid} מתוך {len(below)} עם bid=0, {n_zero_ask} עם ask=0.")
    print("זה כמעט תמיד אומר שהשוק האמריקאי סגור כרגע - אין market makers מצטטים.")
    print(f"\nלדוגמה, שלוש השורות הראשונות (עמודות strike/bid/ask/impliedVolatility):")
    print(below[["strike", "bid", "ask", "impliedVolatility"]].head(3).to_string(index=False))
else:
    print("\nיש ציטוטים חיים - הפונקציה הראשית הייתה צריכה למצוא תוצאה. יתכן שהבעיה במקום אחר.")
    print(valid_bid_ask[["strike", "bid", "ask", "impliedVolatility"]].to_string(index=False))
