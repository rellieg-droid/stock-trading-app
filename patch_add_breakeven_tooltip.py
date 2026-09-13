"""
patch_add_breakeven_tooltip.py
=================================
מוסיף פרמטר tooltip אופציונלי ל-_metric() (לא שובר אף קריאה קיימת - ברירת
מחדל None), ומשתמש בו כדי להוסיף ❓ עם הסבר ל-Breakeven בכרטיס "מודל".

שימוש:
    python patch_add_breakeven_tooltip.py            # dry-run
    python patch_add_breakeven_tooltip.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: הרחבת _metric() עם tooltip אופציונלי --------------------------
METRIC_OLD = (
    "def _metric(label: str, value: str) -> str:\n"
    "    return f'<div class=\"rs-metric\"><div class=\"rs-metric-label\">{label}</div><div class=\"rs-metric-value\">{value}</div></div>'\n"
)
METRIC_NEW = (
    "def _metric(label: str, value: str, tooltip: Optional[str] = None) -> str:\n"
    "    help_html = f' <span class=\"rs-btn-help\" title=\"{tooltip}\">❓</span>' if tooltip else \"\"\n"
    "    return (\n"
    "        f'<div class=\"rs-metric\"><div class=\"rs-metric-label\">{label}{help_html}</div>'\n"
    "        f'<div class=\"rs-metric-value\">{value}</div></div>'\n"
    "    )\n"
)

# --- עוגן 2: שימוש ב-tooltip עבור Breakeven ---------------------------------
BREAKEVEN_OLD = (
    '                _metric("Breakeven", f"${breakeven:,.2f}"),\n'
)
BREAKEVEN_NEW = (
    '                _metric(\n'
    '                    "Breakeven", f"${breakeven:,.2f}",\n'
    '                    tooltip="הסטרייק פחות הפרמיה שקיבלת. זה המחיר שמתחתיו העסקה מתחילה "\n'
    '                            "להפסיד בפועל - מעליו, הפרמיה מכסה את ההפסד המהותי במלואו.",\n'
    '                ),\n'
)


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def apply_single_anchor(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"עוגן '{label}' נמצא {count} פעמים (צריך בדיוק 1)")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    try:
        text = apply_single_anchor(text, METRIC_OLD, METRIC_NEW, "metric-function")
        text = apply_single_anchor(text, BREAKEVEN_OLD, BREAKEVEN_NEW, "breakeven-call")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("שני העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

    if not args.apply:
        print("Dry-run בלבד. הרץ עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(f".py.{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נוצר: {backup}")

    out_bytes = text.replace("\n", line_style).encode("utf-8")
    TARGET.write_bytes(out_bytes)
    print(f"נכתב בהצלחה: {TARGET.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
