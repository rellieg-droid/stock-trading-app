"""
fix_atr.py — Alpha Charts Pro

שני שינויים:

  1. תיקון חישוב ה-ATR ב-calc_risk_level.
     הקוד הנוכחי מחשב (High - Low).rolling(14).mean() — זה ממוצע טווח
     יומי, לא ATR. הוא מתעלם מגאפים בין סגירה לפתיחה, ולכן מזלזל
     בתנודתיות בדיוק במניות שקופצות אחרי דוחות.
     ההחלפה: True Range אמיתי + החלקת Wilder.

  2. באדג' ATR% בכרטיס הכותרת, ליד VIX.
     VIX = תנודתיות השוק. ATR% = תנודתיות המניה. יחד הם עונים על
     השאלה אם התנודתיות מגיעה מהשוק או מהמניה עצמה.

הבאדג' מחושב תמיד על נתונים יומיים (3M/1d) ולא על טווח הזמן
שנבחר בגרף, אחרת המספר היה משתנה בכל החלפת טיימפריים. הקריאה
הזו כבר מקושטת ב-cache הקיים של load_ohlcv ומשותפת עם Watchlist.

שימוש:
    py fix_atr.py            <- תצוגה מקדימה
    py fix_atr.py --apply    <- ביצוע + גיבוי
"""

import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

# ── עוגן 1: הפונקציות החדשות נכנסות לפני load_quarterly ─────────────
ANCHOR_FUNCS = '''@st.cache_data(ttl=3600)
def load_quarterly(symbol: str) -> list | None:'''

NEW_FUNCS = '''def true_atr(df, period: int = 14) -> float | None:
    """
    ATR אמיתי בשיטת Wilder.
    True Range = המקסימום מבין:
        High - Low
        |High - Close הקודם|
        |Low  - Close הקודם|
    בניגוד ל-(High-Low) בלבד, זה תופס גאפים בין סגירה לפתיחה.
    """
    try:
        if df is None or len(df) < period + 1:
            return None
        h = df["High"].astype(float)
        l = df["Low"].astype(float)
        c = df["Close"].astype(float)
        pc = c.shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        # החלקת Wilder = ewm עם alpha=1/period
        atr = tr.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
        if pd.isna(atr):
            return None
        return float(atr)
    except Exception:
        return None


def atr_percent(symbol: str) -> float | None:
    """
    ATR באחוזים מהמחיר, על נתונים יומיים.
    מכוון תמיד ל-3M/1d כדי שהמספר לא ישתנה בכל החלפת טיימפריים בגרף.
    """
    try:
        d = load_ohlcv(symbol, "3M", "1d")
        if d is None or d.empty:
            return None
        a = true_atr(d)
        if a is None:
            return None
        last = float(d["Close"].iloc[-1])
        if last <= 0:
            return None
        return a / last * 100
    except Exception:
        return None


def _atr_badge_html(symbol: str) -> str:
    """באדג' ATR%. מחרוזת ריקה אם אין נתון."""
    p = atr_percent(symbol)
    if p is None:
        return ""
    if p > 4:
        clr, label = "#F5454F", "תנודתיות גבוהה"
    elif p > 2:
        clr, label = "#E8B84B", "תנודתיות בינונית"
    else:
        clr, label = "#2BD46B", "תנודתיות נמוכה"
    return (
        f'<span title="ATR יומי כאחוז מהמחיר. התנועה היומית הטיפוסית של המניה." '
        f'style="background:{clr}1f;color:{clr};border:1px solid {clr}44;'
        f'border-radius:10px;padding:4px 10px;font-size:.72rem;font-weight:600;'
        f'white-space:nowrap;">ATR {p:.1f}% · {label}</span>'
    )


@st.cache_data(ttl=3600)
def load_quarterly(symbol: str) -> list | None:'''

# ── עוגן 2: הבאדג' נכנס אחרי VIX ────────────────────────────────────
ANCHOR_CARD = '''    + _vix_badge_html()'''
NEW_CARD = '''    + _vix_badge_html()
    + _atr_badge_html(ticker)'''

# ── עוגן 3: החלפת ה-proxy השגוי ב-calc_risk_level ───────────────────
ANCHOR_RISK = '''            hi = df['High'].astype(float); lo = df['Low'].astype(float)
            cl = df['Close'].astype(float)
            atr = (hi - lo).rolling(14).mean().iloc[-1]
            atr_pct = atr / cl.iloc[-1] * 100'''

NEW_RISK = '''            cl = df['Close'].astype(float)
            _a = true_atr(df)
            atr_pct = (_a / cl.iloc[-1] * 100) if _a else 0.0'''


def main():
    try:
        with open(TARGET, "r", encoding="utf-8", newline="") as fh:
            src = fh.read()
    except FileNotFoundError:
        print(f"[עצירה] {TARGET} לא נמצא. מריצים מתיקיית הפרויקט.")
        return 1

    newline = "\r\n" if "\r\n" in src else "\n"

    def norm(s):
        return s.replace("\n", newline)

    # ── בדיקות שפיות ──────────────────────────────────────────────────
    if "def true_atr" in src:
        print("[עצירה] true_atr כבר קיימת. הסקריפט כבר רץ.")
        return 1

    if "_vix_badge_html" not in src:
        print("[עצירה] _vix_badge_html לא נמצאה.")
        print("        צריך להריץ קודם את fix_hero_badges.py --apply")
        return 1

    edits = [
        ("פונקציות ATR (true_atr, atr_percent, באדג')",
         norm(ANCHOR_FUNCS), norm(NEW_FUNCS)),
        ("באדג' ATR בכרטיס הכותרת",
         norm(ANCHOR_CARD), norm(NEW_CARD)),
        ("החלפת ה-ATR proxy ב-calc_risk_level",
         norm(ANCHOR_RISK), norm(NEW_RISK)),
    ]

    for label, anchor, _ in edits:
        n = src.count(anchor)
        if n == 0:
            print(f"[עצירה] לא נמצא עוגן עבור: {label}")
            return 1
        if n > 1:
            print(f"[עצירה] העוגן עבור '{label}' מופיע {n} פעמים.")
            return 1

    print("=" * 62)
    print("ATR" + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print("\nשלושה עוגנים נמצאו, כל אחד פעם אחת בדיוק.\n")
    print("  לפני:  atr = (High - Low).rolling(14).mean()")
    print("         ממוצע טווח יומי. מתעלם מגאפים.\n")
    print("  אחרי:  TR = max(H-L, |H-C_prev|, |L-C_prev|)")
    print("         ATR = TR.ewm(alpha=1/14)   [החלקת Wilder]\n")
    print("  באדג': ATR% על 3M/1d, לא על הטיימפריים שנבחר בגרף")
    print("  רמות:  >4% אדום | 2-4% כתום | <2% ירוק")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_atr.py --apply")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{TARGET}.bak_{stamp}"
    shutil.copy2(TARGET, backup)

    out = src
    for label, anchor, replacement in edits:
        out = out.replace(anchor, replacement, 1)
        print(f"  [בוצע] {label}")

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    print("\n" + "-" * 62)
    print(f"עודכן. גיבוי: {backup}")
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    print("  ואז Ctrl+F5 בדפדפן.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
