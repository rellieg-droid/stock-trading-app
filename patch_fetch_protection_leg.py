"""
פאץ': משיכה חיה (yfinance) של סטרייק ופרמיית הגנה אמיתיים ל-Bull Put
Spread, במקום ברירת המחדל המשוערת (95% מהסטרייק / 40% מהפרמיה) שהיתה
עד עכשיו בשדות "סטרייק הגנה" ו"פרמיית ההגנה" בטאב "הסתברות OTM".

שימוש:
    python patch_fetch_protection_leg.py            # dry-run
    python patch_fetch_protection_leg.py --apply    # מבצע בפועל

מה זה עושה (שלושה עוגנים, כולם ב-riskshield_tab.py):
    1. מוסיף timedelta לייבוא הקיים מ-datetime
    2. מוסיף פונקציה חדשה _try_fetch_otm_put_quote(ticker, below_strike,
       dte_days, target_delta=0.15) - שולפת שרשרת אופציות אמיתית
       מ-yfinance, מוצאת את הפקיעה הכי קרובה ל-dte_days, ומחפשת בין
       הפוטים מתחת ל-below_strike עם bid/ask תקינים את זה שהדלתא שלו
       (מחושבת עם bs_greeks הקיים, מה-IV הגלום בציטוט עצמו) הכי קרובה
       ל-0.15. מחזירה (סטרייק, Ask) או None אם נכשל בכל שלב - נכשלת
       בשקט כמו כל שאר ה-_try_fetch_* בקובץ
    3. מחליף את חישוב ברירת המחדל הסטטית של prob_protect_K/premium
       בניסיון fetch חי קודם, עם נפילה חזרה לברירת המחדל המשוערת אם
       אין ציטוט - ומוסיף caption שאומר בפירוש איזה משני המקרים קרה

    שים לב: זה פאץ' היחיד עד כה שנוגע ברשת (yfinance option_chain).
    בדקתי את הלוגיקה מול נתוני אופציות מדומים (synthetic) - לא ניתן
    לבדוק כאן מול Yahoo Finance אמיתי. מומלץ לבדוק על טיקר נזיל (כמו
    AAPL/SPY) בשעות מסחר לפני הסתמכות מלאה.

    שלושת העוגנים נבדקים בנפרד, כל אחד בקול אם לא ייחודי.
    גיבוי עם timestamp, בדיקת ast.parse על הקובץ המלא לפני כתיבה,
    שימור סגנון שבירת השורות המקורי (LF/CRLF, מזוהה אוטומטית).
"""
import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = "riskshield_tab.py"

ANCHOR_1 = 'from datetime import date as _date\n'
INSERTION_1 = 'from datetime import date as _date, timedelta as _timedelta\n'

ANCHOR_2 = 'def _try_fetch_closes(ticker: str, period: str = "1y") -> Optional[list]:\n    """שולף סדרת סגירות יומית להיסטוריה. נכשל בשקט."""\n    if not ticker:\n        return None\n    try:\n        import yfinance as yf\n        hist = yf.Ticker(ticker).history(period=period)\n        if hist.empty or len(hist) < 3:\n            return None\n        return hist["Close"].tolist()\n    except Exception:\n        return None\n\n\n# ---------------------------------------------------------------------------\n# רשימת מעקב אישית לסורק - קובץ JSON נפרד מ-Watchlist הראשי של האפליקציה\n# בכוונה: זו רשימת "מניות שכדאי לבדוק" לצורך הסורק, לא רשימת ההחזקות/\n# מעקב הכללית. שילוב עם ה-Watchlist הראשי (אם רוצים גם את זה) דורש\n# לראות איפה הוא ממומש - זה קובץ אחר.\n# ---------------------------------------------------------------------------\n_SCREENER_WATCHLIST_FILE = "riskshield_watchlist.json"\n'
INSERTION_2 = 'def _try_fetch_closes(ticker: str, period: str = "1y") -> Optional[list]:\n    """שולף סדרת סגירות יומית להיסטוריה. נכשל בשקט."""\n    if not ticker:\n        return None\n    try:\n        import yfinance as yf\n        hist = yf.Ticker(ticker).history(period=period)\n        if hist.empty or len(hist) < 3:\n            return None\n        return hist["Close"].tolist()\n    except Exception:\n        return None\n\n\ndef _try_fetch_otm_put_quote(\n    ticker: str, below_strike: float, dte_days: int = 30, target_delta: float = 0.15,\n) -> Optional[tuple[float, float]]:\n    """\n    שולפת מ-yfinance סטרייק ופרמיה אמיתיים (Ask) לפוט הגנה מחוץ לכסף,\n    מתחת ל-below_strike - הסטרייק שהדלתא שלו (מחושבת מה-IV הגלום בציטוט\n    עצמו, לא IV חיצוני) הכי קרובה ל-target_delta. משתמשת ב-bs_greeks הקיים -\n    לא נוסחת דלתא נפרדת. נכשלת בשקט (None) אם אין רשת, אין תפוגות\n    זמינות, או אין ציטוטי bid/ask תקינים מתחת לסטרייק המבוקש.\n    """\n    if not ticker or not below_strike or below_strike <= 0:\n        return None\n    try:\n        import yfinance as yf\n        tk = yf.Ticker(ticker)\n        expirations = tk.options\n        if not expirations:\n            return None\n\n        target_date = _date.today() + _timedelta(days=dte_days)\n        best_exp = min(expirations, key=lambda e: abs((_date.fromisoformat(e) - target_date).days))\n        actual_dte = (_date.fromisoformat(best_exp) - _date.today()).days\n        if actual_dte <= 0:\n            return None\n\n        puts = tk.option_chain(best_exp).puts\n        if puts is None or puts.empty:\n            return None\n\n        spot = _try_fetch_spot(ticker)\n        if spot is None:\n            return None\n\n        candidates = puts[\n            (puts["strike"] < below_strike) & (puts["bid"] > 0) & (puts["ask"] > 0)\n        ].copy()\n        if candidates.empty:\n            return None\n\n        T = actual_dte / 365.0\n\n        def _row_delta(row):\n            iv = row.get("impliedVolatility")\n            if iv is None or iv <= 0:\n                return None\n            try:\n                return abs(bs_greeks("put", spot, float(row["strike"]), T, float(iv)).delta)\n            except Exception:\n                return None\n\n        candidates["_delta"] = candidates.apply(_row_delta, axis=1)\n        candidates = candidates.dropna(subset=["_delta"])\n        if candidates.empty:\n            return None\n\n        best_idx = (candidates["_delta"] - target_delta).abs().idxmin()\n        best_row = candidates.loc[best_idx]\n        return float(best_row["strike"]), float(best_row["ask"])\n    except Exception:\n        return None\n\n\n# ---------------------------------------------------------------------------\n# רשימת מעקב אישית לסורק - קובץ JSON נפרד מ-Watchlist הראשי של האפליקציה\n# בכוונה: זו רשימת "מניות שכדאי לבדוק" לצורך הסורק, לא רשימת ההחזקות/\n# מעקב הכללית. שילוב עם ה-Watchlist הראשי (אם רוצים גם את זה) דורש\n# לראות איפה הוא ממומש - זה קובץ אחר.\n# ---------------------------------------------------------------------------\n_SCREENER_WATCHLIST_FILE = "riskshield_watchlist.json"\n'

ANCHOR_3 = '        # --- רגל הגנה ל-Bull Put Spread - לצורך השוואת הון/ביטחונות למטה --------\n        spread_cols = st.columns(2)\n        with spread_cols[0]:\n            prob_protect_K = st.number_input(\n                "סטרייק הגנה ל-Bull Put Spread", min_value=0.01,\n                value=float(round(prob_K * 0.95, 2)),\n                key=f"{key_prefix}_prob_protect_K",\n                help="הסטרייק שבו קונים פוט הגנה, מתחת לסטרייק הכתיבה - קובע את רוחב המרווח.",\n            )\n        with spread_cols[1]:\n            prob_protect_premium = st.number_input(\n                "פרמיית ההגנה ($)", min_value=0.01, value=float(round(prob_premium * 0.4, 2)),\n                key=f"{key_prefix}_prob_protect_premium",\n                help="הפרמיה ששולמת עבור פוט ההגנה. כלל אצבע גס: פוט רחוק יותר מהכסף עולה פחות.",\n            )\n\n        _prob_flag = f"{key_prefix}_prob_show"\n'
INSERTION_3 = '        # --- רגל הגנה ל-Bull Put Spread - לצורך השוואת הון/ביטחונות למטה --------\n        _protect_live = _try_fetch_otm_put_quote(ticker, below_strike=prob_K, dte_days=int(prob_days))\n        spread_cols = st.columns(2)\n        with spread_cols[0]:\n            prob_protect_K = st.number_input(\n                "סטרייק הגנה ל-Bull Put Spread", min_value=0.01,\n                value=float(round(_protect_live[0], 2)) if _protect_live else float(round(prob_K * 0.95, 2)),\n                key=f"{key_prefix}_prob_protect_K",\n                help="הסטרייק שבו קונים פוט הגנה, מתחת לסטרייק הכתיבה - קובע את רוחב המרווח. נמשך אוטומטית משוק אמיתי כשזמין, אחרת דלתא ~0.15.",\n            )\n        with spread_cols[1]:\n            prob_protect_premium = st.number_input(\n                "פרמיית ההגנה ($)", min_value=0.01,\n                value=float(round(_protect_live[1], 2)) if _protect_live else float(round(prob_premium * 0.4, 2)),\n                key=f"{key_prefix}_prob_protect_premium",\n                help="הפרמיה ששולמת עבור פוט ההגנה. נמשך אוטומטית (Ask אמיתי) כשזמין.",\n            )\n        if _protect_live:\n            st.caption(\n                f"נמשך אוטומטית משוק אמיתי (דלתא יעד ~0.15): "\n                f"סטרייק ${_protect_live[0]:,.2f}, Ask ${_protect_live[1]:,.2f}"\n            )\n        else:\n            st.caption(\n                "לא נמצא ציטוט הגנה חי - הוזנו ערכי ברירת מחדל משוערים בלבד. "\n                "לפני החלטה אמיתית, כדאי לבדוק בשרשרת האופציות אצל הברוקר."\n            )\n\n        _prob_flag = f"{key_prefix}_prob_show"\n'


def apply_single_anchor(text: str, anchor: str, insertion: str, label: str) -> str:
    count = text.count(anchor)
    if count == 0:
        print(f"[ERROR] Anchor '{label}' not found. הקובץ השתנה מאז שנכתב הפאץ' הזה - צריך לעדכן את העוגן.", file=sys.stderr)
        sys.exit(1)
    if count > 1:
        print(f"[ERROR] Anchor '{label}' found {count} times - צריך עוגן ייחודי יותר.", file=sys.stderr)
        sys.exit(1)
    return text.replace(anchor, insertion, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually write the change (default: dry-run)")
    parser.add_argument("--file", default=TARGET_FILE, help=f"Path to {TARGET_FILE} (default: current directory)")
    args = parser.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"[ERROR] File not found: {target.resolve()}", file=sys.stderr)
        sys.exit(1)

    raw = target.read_bytes()
    is_crlf = raw.count(b"\r\n") > 0
    text = raw.decode("utf-8")
    normalized = text.replace("\r\n", "\n")

    patched = apply_single_anchor(normalized, ANCHOR_1, INSERTION_1, "datetime import")
    patched = apply_single_anchor(patched, ANCHOR_2, INSERTION_2, "fetch function")
    patched = apply_single_anchor(patched, ANCHOR_3, INSERTION_3, "UI wiring")

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[ERROR] Syntax check failed after patch: {e}", file=sys.stderr)
        sys.exit(1)

    print("[OK] All 3 anchors found exactly once, syntax check passed.")
    print("--- Preview of UI wiring change ---")
    for line in INSERTION_3.splitlines():
        print(line)
    print("--- End preview ---")

    if not args.apply:
        print("\nDry-run only. הרצה עם --apply כדי לבצע בפועל.")
        return

    backup_path = target.with_suffix(target.suffix + f".{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(target, backup_path)
    print(f"[OK] Backup saved: {backup_path}")

    final_text = patched.replace("\n", "\r\n") if is_crlf else patched
    target.write_bytes(final_text.encode("utf-8"))
    print(f"[OK] Patch applied to {target.resolve()}")


if __name__ == "__main__":
    main()
