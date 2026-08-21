# -*- coding: utf-8 -*-
"""
patch_iv_badge_style.py
=======================
משדרג את הבאדג' של _iv_badge_html לגלולה זהה ל-VIX ול-ATR.

שינויים:
    * גופן .78rem -> .92rem
    * תוספת רקע, מסגרת, padding ו-border-radius (אותם ערכים כמו שאר הבאדג'ים)
    * תווית קצרה בגוף ("פרמיה זולה"), הניסוח המלא נשאר ב-tooltip

דורש שהרצת קודם את patch_iv_badge.py --apply

הרצה:
    python patch_iv_badge_style.py            # dry-run
    python patch_iv_badge_style.py --apply    # מגבה ומחיל
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
# עוגן 1 — בלוק הצבע והתווית
# ---------------------------------------------------------------------------

OLD_LABELS = '''    if ratio is None:
        color, label = "#8b949e", "אין השוואה ל-HV"
    elif ratio >= 1.30:
        color, label = "#f0883e", "פרמיה יקרה יחסית לתנועה בפועל"
    elif ratio <= 0.85:
        color, label = "#3fb950", "פרמיה זולה יחסית לתנועה בפועל"
    else:
        color, label = "#8b949e", "פרמיה סבירה"
'''

NEW_LABELS = '''    if ratio is None:
        color, short, label = "#8b949e", "אין HV", "אין השוואה ל-HV"
    elif ratio >= 1.30:
        color, short, label = "#f0883e", "פרמיה יקרה", "פרמיה יקרה יחסית לתנועה בפועל"
    elif ratio <= 0.85:
        color, short, label = "#3fb950", "פרמיה זולה", "פרמיה זולה יחסית לתנועה בפועל"
    else:
        color, short, label = "#8b949e", "פרמיה סבירה", "פרמיה סבירה"
'''

# ---------------------------------------------------------------------------
# עוגן 2 — ה-return
# ---------------------------------------------------------------------------

OLD_RETURN = '''    return (
        f'<span title="{tip}" '
        f'style="color:{color};font-size:.78rem;font-weight:600;'
        f'white-space:nowrap;">IV {iv * 100:.1f}%</span>'
    )
'''

NEW_RETURN = '''    return (
        f'<span title="{tip}" '
        f'style="background:{color}1f;color:{color};border:1px solid {color}44;'
        f'border-radius:10px;padding:4px 12px;font-size:.92rem;font-weight:700;'
        f'white-space:nowrap;">IV {iv * 100:.1f}% · {short}</span>'
    )
'''


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

    original = path.read_text(encoding="utf-8", newline="")
    crlf = original.count("\r\n")
    lf_only = original.count("\n") - crlf
    nl = "\r\n" if crlf > lf_only else "\n"
    print(f"קובץ: {path}")
    print(f"סיומות שורה: CRLF={crlf}, LF={lf_only} -> משתמש ב-{nl!r}")

    work = original.replace("\r\n", "\n")

    print("\nבדיקת עוגנים:")
    if "_iv_badge_html" not in work:
        fail("_iv_badge_html לא נמצא. הרץ קודם את patch_iv_badge.py --apply")
    if "color, short, label" in work:
        fail("פאץ' העיצוב כבר הוחל בעבר.")
    require_once(work, OLD_LABELS, "בלוק צבע ותווית")
    require_once(work, OLD_RETURN, "return של הבאדג'")

    patched = work.replace(OLD_LABELS, NEW_LABELS, 1)
    patched = patched.replace(OLD_RETURN, NEW_RETURN, 1)

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


if __name__ == "__main__":
    main()
