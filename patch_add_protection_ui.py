"""
patch_add_protection_ui.py
=============================
מוסיף לטאב "הסתברות OTM" מקטע נפרד: "צד ההגנה (קניית פוט)" - טבלת הגנה
בדולרים לכל תרחיש, עם כפתור וקלטים משלו (לא תלוי בחישוב ההסתברות למעלה).

דורש: patch_add_protection_table.py כבר רץ על options_engine.py.

שימוש:
    python patch_add_protection_ui.py            # dry-run
    python patch_add_protection_ui.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

IMPORT_OLD = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    "    expected_move, strike_distance_in_expected_moves,\n"
    "    stress_test_table, historical_short_put_pnl_distribution, expected_shortfall,\n"
    ")\n"
)
IMPORT_NEW = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    "    expected_move, strike_distance_in_expected_moves,\n"
    "    stress_test_table, historical_short_put_pnl_distribution, expected_shortfall,\n"
    "    protection_table, insurance_cost,\n"
    ")\n"
)

END_OLD = (
    '                if spread > 0.15:\n'
    '                    st.markdown(\n'
    '                        \'<div class="rs-explain" style="margin-top:8px;">\'\n'
    '                        \'המודלים חלוקים ביותר מ-15 נקודות אחוז - זה סימן לאי-ודאות \'\n'
    '                        \'גבוהה, לא לכך שאחד מהם "נכון" והשאר טועים.\'\n'
    '                        \'</div>\',\n'
    '                        unsafe_allow_html=True,\n'
    '                    )\n'
    '    st.markdown(\'</div>\', unsafe_allow_html=True)\n'
)
END_NEW = (
    '                if spread > 0.15:\n'
    '                    st.markdown(\n'
    '                        \'<div class="rs-explain" style="margin-top:8px;">\'\n'
    '                        \'המודלים חלוקים ביותר מ-15 נקודות אחוז - זה סימן לאי-ודאות \'\n'
    '                        \'גבוהה, לא לכך שאחד מהם "נכון" והשאר טועים.\'\n'
    '                        \'</div>\',\n'
    '                        unsafe_allow_html=True,\n'
    '                    )\n'
    '\n'
    '        st.markdown(\'<hr style="border-color: rgba(255,255,255,.08); margin: 24px 0;">\', unsafe_allow_html=True)\n'
    '        st.markdown(\n'
    '            \'<div class="rs-explain" style="margin-bottom:12px;">\'\n'
    '            \'🛡️ <b>צד ההגנה (קניית פוט)</b>: כמה הגנה בדולרים נותן פוט מגן על מניות '
    '            שכבר מחזיקים, בכל תרחיש ירידה. לא תלוי בחישוב ההסתברות למעלה - קלט נפרד.\'\n'
    '            \'</div>\',\n'
    '            unsafe_allow_html=True,\n'
    '        )\n'
    '        prot_cols = st.columns(4)\n'
    '        with prot_cols[0]:\n'
    '            prot_shares = st.number_input("מניות מוחזקות", min_value=1, value=100,\n'
    '                                           key=f"{key_prefix}_prot_shares")\n'
    '        with prot_cols[1]:\n'
    '            prot_entry = st.number_input("מחיר עלות המניה", min_value=0.01, value=float(round(spot_default, 2)),\n'
    '                                          key=f"{key_prefix}_prot_entry")\n'
    '        with prot_cols[2]:\n'
    '            prot_strike = st.number_input("סטרייק הפוט המגן", min_value=0.01, value=float(round(spot_default * 0.9, 2)),\n'
    '                                           key=f"{key_prefix}_prot_strike")\n'
    '        with prot_cols[3]:\n'
    '            prot_premium = st.number_input("פרמיית הפוט ($)", min_value=0.01, value=5.0,\n'
    '                                            key=f"{key_prefix}_prot_premium")\n'
    '        prot_contracts = st.number_input("מספר חוזי פוט", min_value=1, value=1,\n'
    '                                          key=f"{key_prefix}_prot_contracts")\n'
    '\n'
    '        if st.button("חשב הגנה", key=f"{key_prefix}_prot_calc"):\n'
    '            cost = insurance_cost(prot_premium, prot_contracts)\n'
    '            rows = protection_table(\n'
    '                shares=int(prot_shares), stock_entry=prot_entry, strike=prot_strike,\n'
    '                premium=prot_premium, contracts=int(prot_contracts),\n'
    '            )\n'
    '            grid_prot = [_metric("עלות הביטוח", f"${cost:,.2f}")]\n'
    '            for row in rows:\n'
    '                label = f"{row.pct_move:+.0%} (${row.stressed_price:,.0f})"\n'
    '                if row.protection_pct is not None:\n'
    '                    value = f"${row.protection_amount:,.2f} ({row.protection_pct:+.0%})"\n'
    '                else:\n'
    '                    value = f"${row.protection_amount:,.2f} (אין הפסד ללא הגנה)"\n'
    '                grid_prot.append(_metric(label, value))\n'
    '            prot_explain = (\n'
    '                \'<div class="rs-explain">כל תא: כמה הפוט המגן שיפר את התוצאה לעומת \'\n'
    '                \'מניה בלבד, באותו תרחיש (בסוגריים: % מההפסד הלא-מוגן שקוזז). ליד/מעל \'\n'
    '                \'הסטרייק זה יכול להיות שלילי - שילמת פרמיה לפני שההגנה נכנסה לתוקף, \'\n'
    '                \'זה תקין ולא שגיאה.</div>\'\n'
    '            )\n'
    '            _card("טבלת הגנה", f\'<div class="rs-grid">{"".join(grid_prot)}</div>{prot_explain}\')\n'
    '\n'
    '    st.markdown(\'</div>\', unsafe_allow_html=True)\n'
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
        text = apply_single_anchor(text, IMPORT_OLD, IMPORT_NEW, "import")
        text = apply_single_anchor(text, END_OLD, END_NEW, "protection-section")
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
