#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_add_combo_strategy_tab.py

Adds the "🧩 אסטרטגיות משולבות" (Combo Strategies) sub-tab as a SECOND pill
under the existing RiskShield nav group in alpha_paper_trading.py — it does
not touch or merge into the RiskShield tab's own content.

What it does, in order:
  1. Adds `from combo_strategy_tab import render_combo_strategy_tab`
     right under the existing riskshield_tab import.
  2. Adds "🧩 אסטרטגיות משולבות" as a second sub under NAV_GROUPS["RiskShield"].
  3. Updates the RiskShield group tooltip to mention the new sub.
  4. Extends _TAB_KEYS with "tabbody_combo".
  5. Extends _active_map with the new sub -> tabbody_combo mapping.
  6. Appends a new `with st.container(key="tabbody_combo"): render_combo_strategy_tab()`
     block at the end of the file, matching the existing TAB block style.

Usage:
    python patch_add_combo_strategy_tab.py            # dry run — shows what would change
    python patch_add_combo_strategy_tab.py --apply     # writes the changes for real

Requires combo_strategy_engine.py and combo_strategy_tab.py to already sit
next to alpha_paper_trading.py (this script does not create or check them).
"""

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")

# (name, old, new) — each `old` must appear in the file EXACTLY once.
ANCHORS = [
    (
        "import riskshield_tab -> also import combo_strategy_tab",
        'from riskshield_tab import render_riskshield_tab',
        'from riskshield_tab import render_riskshield_tab\n'
        'from combo_strategy_tab import render_combo_strategy_tab',
    ),
    (
        "NAV_GROUPS['RiskShield']['subs'] gains a second pill",
        '"RiskShield": {"icon": "shield-check", "subs": ["🛡️ RiskShield"]},',
        '"RiskShield": {"icon": "shield-check", "subs": ["🛡️ RiskShield", "🧩 אסטרטגיות משולבות"]},',
    ),
    (
        "GROUP_TOOLTIPS['RiskShield'] mentions the new sub",
        '"RiskShield": "RiskShield — מחשבון Black-Scholes ותנודתיות, בלי המלצות קנייה/מכירה",',
        '"RiskShield": "RiskShield — מחשבון Black-Scholes ותנודתיות, בלי המלצות קנייה/מכירה. '
        'כולל גם סורק אסטרטגיות משולבות (ריסק ריברסל)",',
    ),
    (
        "_TAB_KEYS gains tabbody_combo",
        '_TAB_KEYS = ["tabbody_home", "tabbody_chart", "tabbody_analysis", "tabbody_backtest",\n'
        '             "tabbody_trade", "tabbody_guide", "tabbody_compare", "tabbody_portfolio",\n'
        '             "tabbody_alerts", "tabbody_reports", "tabbody_watchlist", "tabbody_strategy",\n'
        '             "tabbody_riskshield"]',
        '_TAB_KEYS = ["tabbody_home", "tabbody_chart", "tabbody_analysis", "tabbody_backtest",\n'
        '             "tabbody_trade", "tabbody_guide", "tabbody_compare", "tabbody_portfolio",\n'
        '             "tabbody_alerts", "tabbody_reports", "tabbody_watchlist", "tabbody_strategy",\n'
        '             "tabbody_riskshield", "tabbody_combo"]',
    ),
    (
        "_active_map gains the new sub mapping",
        '"🧭 אסטרטגיה": "tabbody_strategy", "🛡️ RiskShield": "tabbody_riskshield"}',
        '"🧭 אסטרטגיה": "tabbody_strategy", "🛡️ RiskShield": "tabbody_riskshield",\n'
        '               "🧩 אסטרטגיות משולבות": "tabbody_combo"}',
    ),
]

# Leading "\n\n" ends the file's current last line and adds the one blank
# line the existing TAB blocks use before their comment header.
APPEND_BLOCK = (
    '\n\n'
    '# ════════════════════════════════════════\n'
    '# TAB 15 — 🧩 אסטרטגיות משולבות\n'
    '# ════════════════════════════════════════\n'
    'with st.container(key="tabbody_combo"):\n'
    '    render_combo_strategy_tab()\n'
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes for real")
    args = parser.parse_args()

    if not TARGET.exists():
        sys.exit(f"לא נמצא {TARGET} בתיקייה הנוכחית.")

    raw = TARGET.read_bytes()
    text = raw.decode("utf-8").replace("\r\n", "\n")

    for name, old, new in ANCHORS:
        count = text.count(old)
        if count == 0:
            sys.exit(f"❌ עוגן לא נמצא: {name}\n--- מחפש: ---\n{old}")
        if count > 1:
            sys.exit(f"❌ עוגן מופיע {count} פעמים (צריך בדיוק פעם אחת): {name}")
        text = text.replace(old, new)
        print(f"✅ {name}")

    if APPEND_BLOCK.strip() in text:
        sys.exit("❌ נראה שהבלוק כבר קיים בקובץ — הפאץ' כבר הורץ?")
    text = text + APPEND_BLOCK
    print("✅ בלוק tabbody_combo נוסף בסוף הקובץ")

    try:
        ast.parse(text)
    except SyntaxError as e:
        sys.exit(f"❌ שגיאת syntax אחרי הפאץ': {e}")
    print("✅ ast.parse עבר בהצלחה")

    final_bytes = text.replace("\n", "\r\n").encode("utf-8")

    if not args.apply:
        print("\n--- DRY RUN — לא נשמר כלום. הריצי עם --apply כדי לכתוב בפועל. ---")
        return

    backup_path = TARGET.with_name(
        TARGET.stem + f".py.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(TARGET, backup_path)
    print(f"📦 גיבוי נשמר ב: {backup_path}")

    TARGET.write_bytes(final_bytes)
    print(f"✅ {TARGET} נשמר עם השינויים.")


if __name__ == "__main__":
    main()
