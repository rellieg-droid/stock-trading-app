# -*- coding: utf-8 -*-
"""
patch_unify_atr_position_sizing.py
===================================
מאחד את שני מחשבוני ה-Position Sizing (render_position_module +
תת-הטאב הנפרד "⚠️ Position Sizing") לשימוש באותו מקור חישוב ATR,
דרך position_sizing.atr_position_defaults (שעוטף את
strategy_engine.build_position_plan).

לפני ההרצה: ודאי ש-position_sizing.py קיים באותה תיקייה כמו
alpha_paper_trading.py.

הרצה (ברירת מחדל = dry-run, מציג diff בלי לגעת בקובץ):
    python patch_unify_atr_position_sizing.py

הרצה בפועל:
    python patch_unify_atr_position_sizing.py --apply
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = Path("alpha_paper_trading.py")

# ── עוגן 1: ייבוא position_sizing אחרי ייבוא strategy_guide ──
ANCHOR_1 = 'from strategy_guide import render_strategy_guide\r\n'
REPLACEMENT_1 = (
    'from strategy_guide import render_strategy_guide\r\n'
    'from position_sizing import atr_position_defaults\r\n'
)

# ── עוגן 2: מחשבון ה-Position Sizing בתוך render_position_module ──
ANCHOR_2 = (
    '    ps1, ps2, ps3 = st.columns(3)\r\n'
    '    with ps1:\r\n'
    '        account_val = st.number_input("גודל תיק ($):", value=10000, min_value=100, step=500, key="ps_acc")\r\n'
    '        risk_pct    = st.slider("סיכון לעסקה (%):", 0.5, 5.0, 1.0, 0.5, key="ps_risk")\r\n'
    '    with ps2:\r\n'
    '        entry_p = st.number_input("מחיר כניסה:", value=float(cur_price), min_value=0.01, key="ps_entry")\r\n'
    '        stop_p  = st.number_input("Stop Loss:", value=round(float(cur_price) * 0.95, 2), min_value=0.01, key="ps_stop")\r\n'
    '    with ps3:\r\n'
    '        target_p = st.number_input("מחיר יעד:", value=round(float(cur_price) * 1.12, 2), min_value=0.01, key="ps_tgt")\r\n'
    '        st.markdown(f\'<div style="color:#8b949e;font-size:.72rem;margin-top:8px;">מחיר נוכחי: <b style="color:#e6edf3;">{ccy_s}{cur_price:.2f}</b></div>\', unsafe_allow_html=True)\r\n'
)
REPLACEMENT_2 = (
    '    ps1, ps2, ps3 = st.columns(3)\r\n'
    '    with ps1:\r\n'
    '        account_val = st.number_input("גודל תיק ($):", value=10000, min_value=100, step=500, key="ps_acc")\r\n'
    '        risk_pct    = st.slider("סיכון לעסקה (%):", 0.5, 5.0, 1.0, 0.5, key="ps_risk")\r\n'
    '\r\n'
    '    # ATR מבוסס strategy_engine.build_position_plan, מקור יחיד לשני מחשבוני ה-Position Sizing\r\n'
    '    _atr_plan = atr_position_defaults(df, cur_price, account_val, risk_pct)\r\n'
    '    _default_stop   = _atr_plan.stop_price        if _atr_plan else round(float(cur_price) * 0.95, 2)\r\n'
    '    _default_target = _atr_plan.take_profit_price if _atr_plan else round(float(cur_price) * 1.12, 2)\r\n'
    '\r\n'
    '    with ps2:\r\n'
    '        entry_p = st.number_input("מחיר כניסה:", value=float(cur_price), min_value=0.01, key="ps_entry")\r\n'
    '        stop_p  = st.number_input("Stop Loss:", value=round(float(_default_stop), 2), min_value=0.01, key="ps_stop")\r\n'
    '    with ps3:\r\n'
    '        target_p = st.number_input("מחיר יעד:", value=round(float(_default_target), 2), min_value=0.01, key="ps_tgt")\r\n'
    '        _atr_note = \'<div style="color:#8b949e;font-size:.66rem;margin-top:2px;">ברירת מחדל: ATR</div>\' if _atr_plan else \'<div style="color:#8b949e;font-size:.66rem;margin-top:2px;">ATR לא זמין — ברירת מחדל אחוזית</div>\'\r\n'
    '        st.markdown(f\'<div style="color:#8b949e;font-size:.72rem;margin-top:8px;">מחיר נוכחי: <b style="color:#e6edf3;">{ccy_s}{cur_price:.2f}</b></div>\' + _atr_note, unsafe_allow_html=True)\r\n'
)

# ── עוגן 3: מחשבון Position Sizing בתת-הטאב העצמאי (an_sub4) ──
ANCHOR_3 = (
    '            enp = st.number_input("מחיר כניסה:", value=float(cp_) if cp_ else 100., min_value=.01)\r\n'
    '            slp = st.number_input("Stop Loss:",  value=float(enp * .95), min_value=.01)\r\n'
    '            tgp = st.number_input("יעד:",        value=float(enp * 1.10), min_value=.01)\r\n'
)
REPLACEMENT_3 = (
    '            enp = st.number_input("מחיר כניסה:", value=float(cp_) if cp_ else 100., min_value=.01)\r\n'
    '            _atr_plan2 = atr_position_defaults(df, enp, acc, rsk)\r\n'
    '            _def_stop2 = _atr_plan2.stop_price        if _atr_plan2 else float(enp * .95)\r\n'
    '            _def_tgt2  = _atr_plan2.take_profit_price if _atr_plan2 else float(enp * 1.10)\r\n'
    '            slp = st.number_input("Stop Loss:",  value=float(_def_stop2), min_value=.01)\r\n'
    '            tgp = st.number_input("יעד:",        value=float(_def_tgt2), min_value=.01)\r\n'
)

PATCHES = [
    ("ייבוא position_sizing", ANCHOR_1, REPLACEMENT_1),
    ("מחשבון Position Sizing בתוך סיכום והחלטה", ANCHOR_2, REPLACEMENT_2),
    ("מחשבון Position Sizing בתת-הטאב העצמאי", ANCHOR_3, REPLACEMENT_3),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="לבצע בפועל, לא רק dry-run")
    args = parser.parse_args()

    if not TARGET_FILE.exists():
        print(f"❌ לא נמצא {TARGET_FILE} בתיקייה הנוכחית.")
        return 1

    with open(TARGET_FILE, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    for name, anchor, _ in PATCHES:
        count = content.count(anchor)
        if count == 0:
            print(f"❌ עוגן לא נמצא: {name}. ייתכן שהקוד השתנה מאז שנכתב הפאץ'. עוצר בלי לגעת בקובץ.")
            return 1
        if count > 1:
            print(f"❌ עוגן מופיע {count} פעמים: {name}. צריך עוגן ייחודי יותר. עוצר בלי לגעת בקובץ.")
            return 1

    new_content = content
    for name, anchor, replacement in PATCHES:
        new_content = new_content.replace(anchor, replacement, 1)

    print("=== תצוגה מקדימה (unified diff) ===")
    diff = difflib.unified_diff(
        content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=str(TARGET_FILE),
        tofile=f"{TARGET_FILE} (אחרי הפאץ')",
    )
    sys.stdout.writelines(diff)
    print(f"\n{len(PATCHES)} עוגנים נמצאו ותוקנו בהצלחה (dry-run).")

    if not args.apply:
        print("\nזה היה dry-run בלבד. שום דבר לא נכתב. הריצי עם --apply כדי לבצע בפועל.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = TARGET_FILE.with_suffix(f".py.bak_{ts}")
    with open(backup_path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print(f"✅ גיבוי נשמר: {backup_path}")

    with open(TARGET_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    print(f"✅ {TARGET_FILE} עודכן.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
