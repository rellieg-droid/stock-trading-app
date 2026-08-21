# -*- coding: utf-8 -*-
"""
patch_iv_badge.py
=================
מוסיף באדג' IV לכרטיס ההירו הגלובלי ב-alpha_paper_trading.py, לצד ה-ATR.

שני שינויים:
    1. הזרקת _iv_stats + _iv_badge_html לפני def _atr_badge_html
    2. הוספת + _iv_badge_html(ticker) אחרי + _atr_badge_html(ticker)

הרצה:
    python patch_iv_badge.py            # dry-run, מציג diff בלבד
    python patch_iv_badge.py --apply    # מגבה ומחיל

מסלול ה-venv המלא:
    C:\\PhyCharm_projects\\Stock_tracking\\.venv\\Scripts\\python.exe patch_iv_badge.py
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path(r"C:\PhyCharm_projects\Stock_tracking\alpha_paper_trading.py")

# ---------------------------------------------------------------------------
# עוגנים. כל אחד חייב להופיע בדיוק פעם אחת.
# ---------------------------------------------------------------------------

ANCHOR_FUNCS = "def _atr_badge_html(symbol: str) -> str:"
ANCHOR_CALL = "    + _atr_badge_html(ticker)\n"

NEW_FUNCS = '''def _iv_finite(x) -> bool:
    """בדיקת מספר תקין בלי תלות ב-math או numpy."""
    if x is None:
        return False
    if x != x:                      # NaN
        return False
    return x not in (float("inf"), float("-inf"))


def _iv_stats(symbol: str):
    """
    IV נוכחי בכסף + HV ממומש + דירוג HV.
    מחזיר None רק כשאין אופציות לסימול (למשל טיקרים בת"א).
    הייבוא עצל בכוונה: מונע ייבוא מעגלי ולא מאט את עליית האפליקציה.
    """
    try:
        from strategy_data import fetch_atm_iv, fetch_history
        from strategy_engine import annualized_vol, hv_rank
    except Exception:
        return None

    try:
        iv = fetch_atm_iv(symbol)
    except Exception:
        return None
    if iv is None or not _iv_finite(iv):
        return None

    out = {"iv": float(iv), "hv": None, "rank": None, "ratio": None}

    # HV הוא תוספת, לא תנאי. אם הוא נופל, IV לבד עדיין שווה משהו.
    try:
        d = fetch_history(symbol, period="2y", interval="1d")
        if d is not None and not d.empty and "Close" in d:
            closes = d["Close"]
            hv = annualized_vol(closes, window=21)
            rk = hv_rank(closes, window=21, lookback=252)
            if _iv_finite(hv) and hv > 0:
                out["hv"] = float(hv)
                out["ratio"] = float(iv) / float(hv)
            if _iv_finite(rk):
                out["rank"] = float(rk)
    except Exception:
        pass

    return out


def _iv_badge_html(symbol: str) -> str:
    """
    באדג' IV לצד באדג' ה-ATR. מחרוזת ריקה אם אין נתון.
    הגוף קצר בכוונה (מובייל). הדירוג והיחס נמצאים ב-tooltip.
    """
    s = _iv_stats(symbol)
    if not s:
        return ""

    iv, hv, rank, ratio = s["iv"], s["hv"], s["rank"], s["ratio"]

    if ratio is None:
        color, label = "#8b949e", "אין השוואה ל-HV"
    elif ratio >= 1.30:
        color, label = "#f0883e", "פרמיה יקרה יחסית לתנועה בפועל"
    elif ratio <= 0.85:
        color, label = "#3fb950", "פרמיה זולה יחסית לתנועה בפועל"
    else:
        color, label = "#8b949e", "פרמיה סבירה"

    tip = f"IV בכסף, תפוגה 20-60 ימים: {iv * 100:.1f}%. "
    if hv is not None:
        tip += f"HV ממומש 21 יום: {hv * 100:.1f}%. "
    if ratio is not None:
        tip += f"IV/HV {ratio:.2f} — {label}. "
    if rank is not None:
        tip += f"HV Rank {rank:.0f}% (פרוקסי ל-IV Rank, לא אותו מדד). "
    tip += "תיאור תמחור בלבד, לא איתות."

    return (
        f'<span title="{tip}" '
        f'style="color:{color};font-size:.78rem;font-weight:600;'
        f'white-space:nowrap;">IV {iv * 100:.1f}%</span>'
    )


'''

NEW_CALL = "    + _atr_badge_html(ticker)\n    + _iv_badge_html(ticker)\n"


# ---------------------------------------------------------------------------
# מנגנון
# ---------------------------------------------------------------------------

def fail(msg: str) -> None:
    print(f"\n[עצירה] {msg}\nלא בוצע שום שינוי.", file=sys.stderr)
    sys.exit(1)


def require_once(text: str, anchor: str, name: str) -> None:
    n = text.count(anchor)
    if n != 1:
        fail(f"העוגן '{name}' הופיע {n} פעמים, נדרש בדיוק 1.")
    print(f"  [OK] עוגן '{name}': הופעה אחת")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="החל את השינוי בפועל")
    ap.add_argument("--path", default=str(TARGET), help="נתיב לקובץ היעד")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        fail(f"הקובץ לא נמצא: {path}")

    # newline="" משמר CRLF כפי שהוא במחרוזת
    original = path.read_text(encoding="utf-8", newline="")

    crlf = original.count("\r\n")
    lf_only = original.count("\n") - crlf
    nl = "\r\n" if crlf > lf_only else "\n"
    print(f"קובץ: {path}")
    print(f"סיומות שורה: CRLF={crlf}, LF={lf_only} -> משתמש ב-{nl!r}")

    work = original.replace("\r\n", "\n")

    print("\nבדיקת עוגנים:")
    if "_iv_badge_html" in work:
        fail("_iv_badge_html כבר קיים בקובץ. הפאץ' כנראה הוחל בעבר.")
    require_once(work, ANCHOR_FUNCS, "def _atr_badge_html")
    require_once(work, ANCHOR_CALL, "+ _atr_badge_html(ticker)")

    patched = work.replace(ANCHOR_FUNCS, NEW_FUNCS + ANCHOR_FUNCS, 1)
    patched = patched.replace(ANCHOR_CALL, NEW_CALL, 1)

    if patched == work:
        fail("ההחלפה לא שינתה דבר. משהו לא צפוי.")

    diff = difflib.unified_diff(
        work.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"{path.name} (לפני)",
        tofile=f"{path.name} (אחרי)",
        n=3,
    )
    print("\n" + "=" * 70)
    sys.stdout.writelines(diff)
    print("=" * 70)

    if not args.apply:
        print("\nDRY-RUN. שום דבר לא נכתב.")
        print("להחלה: הוסף --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".{stamp}.bak")
    shutil.copy2(path, backup)
    print(f"\nגיבוי: {backup.name}")

    out = patched.replace("\n", nl) if nl == "\r\n" else patched
    path.write_text(out, encoding="utf-8", newline="")
    print(f"נכתב: {path.name}")
    print("\nהרץ את האפליקציה ובדוק שהבאדג' מופיע ליד ה-ATR.")
    print("אם משהו נשבר: העתק את קובץ הגיבוי חזרה.")


if __name__ == "__main__":
    main()
