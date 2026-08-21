# -*- coding: utf-8 -*-
"""
patch_entry_stop.py
===================
Step 2, שלב א: שמירת מחיר סטופ ברגע הקנייה.

מדיניות שנבחרה (אופציה א):
    הסטופ נקבע פעם אחת, בכניסה הראשונה לפוזיציה, ולא זז בקנייה חוזרת.
    מכירה חלקית לא נוגעת בו. סגירת פוזיציה מוחקת אותו יחד איתה.

שני שינויים ב-alpha_paper_trading.py:
    1. אחרי עדכון הכמות בקנייה — קביעת stop_price מ-ATR, רק אם עוד לא קיים
    2. הודעת ההצלחה מציגה את הסטופ

מה הפאץ' לא עושה:
    לא נוגע ב-render_position_manager ולא ב-5%/12% הקשיחים.
    זה שלב ב', אחרי שנוודא שהשדה באמת נשמר לקובץ.

הרצה:
    python patch_entry_stop.py            # dry-run
    python patch_entry_stop.py --apply    # מגבה ומחיל
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path(r"C:\PhyCharm_projects\Stock_tracking\alpha_paper_trading.py")

ATR_STOP_MULTIPLIER = 2.0   # תואם ל-StrategyConfig.atr_stop_multiplier

# ---------------------------------------------------------------------------
# עוגנים — התאמה לפי תוכן השורה אחרי strip, כדי לא לנחש הזחה
# ---------------------------------------------------------------------------

ANCHOR_SHARES = "pos['shares']    = ts"

ANCHOR_SUCCESS = 'st.success(f"✅ קנית {si_} מניות ב-{sym}{cp_:.2f}")'

# הבלוק שיוזרק. ההזחה נלקחת מהשורה של העוגן.
STOP_BLOCK = [
    "",
    "# ── סטופ בכניסה ──────────────────────────────────────────",
    "# נקבע פעם אחת בלבד. קנייה חוזרת לא מזיזה אותו (מדיניות א).",
    'if pos.get("stop_price") is None:',
    "    try:",
    "        _entry_atr = _rr_atr(ticker)",
    "    except Exception:",
    "        _entry_atr = None",
    "    if _entry_atr:",
    f'        pos["stop_price"] = round(cp_ - {ATR_STOP_MULTIPLIER} * _entry_atr, 2)',
    '        pos["entry_price"] = round(cp_, 2)',
    f'        pos["entry_atr"] = round(_entry_atr, 4)',
    f'        pos["stop_atr_mult"] = {ATR_STOP_MULTIPLIER}',
    '        pos["entry_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")',
]

NEW_SUCCESS = (
    'st.success(f"✅ קנית {si_} מניות ב-{sym}{cp_:.2f}"'
    ' + (f" · סטופ {sym}{pos[\'stop_price\']:.2f}" if pos.get("stop_price") else ""))'
)


def fail(msg: str) -> None:
    print(f"\n[עצירה] {msg}\nלא בוצע שום שינוי.", file=sys.stderr)
    sys.exit(1)


def find_unique(lines: list[str], stripped: str, name: str) -> int:
    hits = [i for i, ln in enumerate(lines) if ln.strip() == stripped]
    if len(hits) != 1:
        fail(f"העוגן '{name}' נמצא {len(hits)} פעמים, נדרש בדיוק 1.")
    print(f"  [OK] עוגן '{name}': שורה {hits[0] + 1}")
    return hits[0]


def indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


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
    lines = work.split("\n")

    print("\nבדיקת עוגנים:")
    if "stop_price" in work:
        fail("stop_price כבר קיים בקובץ. הפאץ' כנראה הוחל בעבר.")

    i_shares = find_unique(lines, ANCHOR_SHARES, "עדכון כמות בקנייה")
    i_success = find_unique(lines, ANCHOR_SUCCESS, "הודעת הצלחה")

    if i_success <= i_shares:
        fail("הודעת ההצלחה מופיעה לפני עדכון הכמות. מבנה לא צפוי.")

    # 1. החלפת הודעת ההצלחה (קודם, כדי לא להזיז אינדקסים)
    lines[i_success] = indent_of(lines[i_success]) + NEW_SUCCESS

    # 2. הזרקת בלוק הסטופ אחרי עדכון הכמות
    ind = indent_of(lines[i_shares])
    block = [(ind + ln) if ln else "" for ln in STOP_BLOCK]
    lines[i_shares + 1: i_shares + 1] = block

    patched = "\n".join(lines)
    if patched == work:
        fail("ההחלפה לא שינתה דבר. משהו לא צפוי.")

    diff = difflib.unified_diff(
        work.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"{path.name} (לפני)",
        tofile=f"{path.name} (אחרי)",
        n=4,
    )
    print("\n" + "=" * 70)
    sys.stdout.writelines(diff)
    print("=" * 70)

    if not args.apply:
        print("\nDRY-RUN. שום דבר לא נכתב.")
        print("להחלה: הוסיפי --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".{stamp}.bak")
    shutil.copy2(path, backup)
    print(f"\nגיבוי: {backup.name}")

    out = patched.replace("\n", nl) if nl == "\r\n" else patched
    path.write_text(out, encoding="utf-8", newline="")
    print(f"נכתב: {path.name}")
    print("\nבדיקה: קני מניה אחת בטאב מסחר. הודעת ההצלחה צריכה להציג סטופ.")
    print("ואז פתחי את קובץ התיק וודאי ש-stop_price נשמר.")


if __name__ == "__main__":
    main()
