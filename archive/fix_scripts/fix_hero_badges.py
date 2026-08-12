"""
fix_hero_badges.py — Alpha Charts Pro
מוסיף שני באדג'ים לכרטיס הכותרת (Premium glass hero card):

  1. תאריך הדוח הבא + אזהרה אם הוא בתוך 14 יום
  2. מדד VIX עם סימון סנטימנט שוק בשלוש רמות

הכרטיס יושב מעל הניווט, כלומר הבאדג'ים גלויים בכל 11 העמודים.

שימוש:
    py fix_hero_badges.py            <- תצוגה מקדימה
    py fix_hero_badges.py --apply    <- ביצוע + גיבוי
"""

import sys
import shutil
import datetime

TARGET = "alpha_paper_trading.py"
APPLY = "--apply" in sys.argv

# ── עוגן 1: אחרי load_info, שם נכנסות הפונקציות החדשות ──────────────
ANCHOR_FUNCS = '''@st.cache_data(ttl=3600)
def load_quarterly(symbol: str) -> list | None:'''

NEW_FUNCS = '''@st.cache_data(ttl=3600)
def next_earnings(symbol: str) -> tuple[str, int] | None:
    """
    מחזיר (תאריך בפורמט dd/mm/yyyy, ימים עד הדוח) או None אם אין נתון.
    ימים שליליים = הדוח כבר היה ויאהו טרם עדכנה.
    """
    try:
        inf = load_info(symbol)
        ned = inf.get("earningsDate") or inf.get("earningsTimestamp")
        if isinstance(ned, (list, tuple)):
            ned = ned[0] if ned else None
        if not ned:
            return None
        if isinstance(ned, (int, float)):
            ned_dt = datetime.fromtimestamp(ned)
        else:
            ned_dt = pd.Timestamp(ned).to_pydatetime()
        days = (ned_dt.date() - datetime.now().date()).days
        return ned_dt.strftime("%d/%m/%Y"), days
    except Exception:
        return None


@st.cache_data(ttl=300)
def load_vix() -> float | None:
    """ערך VIX הנוכחי. None אם השליפה נכשלה."""
    try:
        h = yf.Ticker("^VIX").history(period="5d", interval="1d")
        if h is None or h.empty:
            return None
        return float(h["Close"].iloc[-1])
    except Exception:
        return None


def _earnings_badge_html(symbol: str) -> str:
    """באדג' דוח הבא. מחרוזת ריקה אם אין נתון — עדיף כלום מ'לא ידוע'."""
    res = next_earnings(symbol)
    if not res:
        return ""
    date_str, days = res
    if days < 0:
        return ""
    if days <= 14:
        clr, icon, label = "#F5454F", "⚠️", f"דוח בעוד {days} ימים"
    elif days <= 30:
        clr, icon, label = "#E8B84B", "📅", f"דוח בעוד {days} ימים"
    else:
        clr, icon, label = "#8B93A7", "📅", f"דוח: {date_str}"
    return (
        f'<span title="תאריך הדוח הבא: {date_str}" '
        f'style="background:{clr}1f;color:{clr};border:1px solid {clr}44;'
        f'border-radius:10px;padding:4px 10px;font-size:.72rem;font-weight:600;'
        f'white-space:nowrap;">{icon} {label}</span>'
    )


def _vix_badge_html() -> str:
    """באדג' VIX בשלוש רמות. מחרוזת ריקה אם השליפה נכשלה."""
    v = load_vix()
    if v is None:
        return ""
    if v < 20:
        clr, label = "#2BD46B", "שוק רגוע"
    elif v <= 25:
        clr, label = "#E8B84B", "תנודתיות בינונית"
    else:
        clr, label = "#F5454F", "שוק תנודתי"
    return (
        f'<span title="מדד התנודתיות VIX. מתחת ל-20 רגוע, מעל 25 תנודתי." '
        f'style="background:{clr}1f;color:{clr};border:1px solid {clr}44;'
        f'border-radius:10px;padding:4px 10px;font-size:.72rem;font-weight:600;'
        f'white-space:nowrap;">VIX {v:.1f} · {label}</span>'
    )


@st.cache_data(ttl=3600)
def load_quarterly(symbol: str) -> list | None:'''

# ── עוגן 2: נקודת ההזרקה בכרטיס הכותרת ──────────────────────────────
# הבאדג'ים נכנסים אחרי "היום" ולפני טווח 52 שבועות, כי לאחרון
# יש margin-right:auto שדוחף אותו ואת מה שאחריו לצד השני.
ANCHOR_CARD = '''    f'<span style="color:var(--c-text-3);font-size:.75rem;">היום</span>'
    + (f'<span style="color:var(--c-text-3);font-size:.72rem;margin-right:auto;">52ש׳:'''

NEW_CARD = '''    f'<span style="color:var(--c-text-3);font-size:.75rem;">היום</span>'
    + _earnings_badge_html(ticker)
    + _vix_badge_html()
    + (f'<span style="color:var(--c-text-3);font-size:.72rem;margin-right:auto;">52ש׳:'''


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

    edits = [
        ("פונקציות חדשות (next_earnings, load_vix, באדג'ים)",
         norm(ANCHOR_FUNCS), norm(NEW_FUNCS)),
        ("הזרקת הבאדג'ים לכרטיס הכותרת",
         norm(ANCHOR_CARD), norm(NEW_CARD)),
    ]

    # ── בדיקות שפיות לפני נגיעה בקובץ ────────────────────────────────
    if "def next_earnings" in src or "def load_vix" in src:
        print("[עצירה] הפונקציות כבר קיימות. הסקריפט כבר רץ פעם אחת.")
        return 1

    for label, anchor, _ in edits:
        n = src.count(anchor)
        if n == 0:
            print(f"[עצירה] לא נמצא עוגן עבור: {label}")
            print("        הקובץ השתנה מאז הבדיקה. אל תריצי --apply.")
            return 1
        if n > 1:
            print(f"[עצירה] העוגן עבור '{label}' מופיע {n} פעמים. "
                  "צריך עוגן ייחודי יותר.")
            return 1

    print("=" * 62)
    print("באדג'ים בכרטיס הכותרת" + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)
    print("\nשני עוגנים נמצאו, כל אחד פעם אחת בדיוק.\n")
    print("  1. next_earnings(symbol) -> (תאריך, ימים) | None   [cache 1h]")
    print("  2. load_vix()            -> float | None           [cache 5m]")
    print("  3. שני באדג'ים נכנסים לכרטיס אחרי 'היום'\n")
    print("  רמות דוח:  <=14 יום אדום | <=30 כתום | מעבר לזה אפור")
    print("  רמות VIX:  <20 ירוק | 20-25 כתום | >25 אדום")
    print("  אין נתון -> לא מוצג באדג' בכלל (לא 'לא ידוע')")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא שונה כלום. לביצוע:  py fix_hero_badges.py --apply")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
