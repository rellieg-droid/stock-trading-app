"""
patch_add_breakeven_liquidity_compare.py
===========================================
שלושה שיפורים לטאב "הסתברות OTM", כולם עובדתיים - בלי ציון, בלי מיון
לפי "כדאיות", בלי המלצה:

1. שדות "נפח" ו"עניין פתוח" (הזנה ידנית - עדיין אין שליפה אוטומטית של
   שרשרת אופציות) + תג אזהרה עובדתי אם שניהם נמוכים מסף.
2. Breakeven מחושב, מוצג בכרטיס "מודל".
3. טבלת השוואה: מוסיפים שורה (סטרייק/פרמיה/IV/נפח/עניין פתוח) לכל
   מועמד שבודקים, והטבלה מציגה לכל שורה Breakeven, הסתברות מודל, מרחק
   ב-Expected Move, ותג נזילות - ממוינת לפי סטרייק, לא לפי "כמה טוב".

דורש: patch_add_breakeven.py כבר רץ על options_engine.py.

שימוש:
    python patch_add_breakeven_liquidity_compare.py            # dry-run
    python patch_add_breakeven_liquidity_compare.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: ייבוא ---------------------------------------------------------
IMPORT_OLD = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    "    expected_move, strike_distance_in_expected_moves,\n"
    "    stress_test_table, historical_short_put_pnl_distribution, expected_shortfall,\n"
    "    protection_table, insurance_cost,\n"
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
    "    short_put_breakeven,\n"
    ")\n"
)

# --- עוגן 2: שדות נפח/עניין פתוח, אחרי שורת פרמיה/חוזים/הון ---------------
CAPITAL_OLD = (
    '        with stress_cols[2]:\n'
    '            prob_capital = st.number_input("הון זמין ($, אופציונלי - להצגת % מההון)", min_value=0.0, value=0.0,\n'
    '                                            key=f"{key_prefix}_prob_capital", help=_HELP["capital"])\n'
)
CAPITAL_NEW = CAPITAL_OLD + (
    '        liq_cols = st.columns(2)\n'
    '        with liq_cols[0]:\n'
    '            prob_volume = st.number_input("נפח (מ-Yahoo/הברוקר, אופציונלי)", min_value=0, value=0,\n'
    '                                           key=f"{key_prefix}_prob_volume")\n'
    '        with liq_cols[1]:\n'
    '            prob_oi = st.number_input("עניין פתוח (מ-Yahoo/הברוקר, אופציונלי)", min_value=0, value=0,\n'
    '                                       key=f"{key_prefix}_prob_oi")\n'
)

# --- עוגן 3: כרטיס מודל - הוספת Breakeven + תג נזילות ----------------------
MODEL_CARD_OLD = (
    '            grid_normal = _metric("הסתברות OTM - מודל", f"{normal_prob:.1%}" if normal_prob is not None else "—")\n'
    '            _card("מודל (Black-Scholes)", f\'<div class="rs-grid">{grid_normal}</div>\')\n'
)
MODEL_CARD_NEW = (
    '            breakeven = short_put_breakeven(strike=prob_K, premium=prob_premium)\n'
    '            grid_normal = "".join([\n'
    '                _metric("הסתברות OTM - מודל", f"{normal_prob:.1%}" if normal_prob is not None else "—"),\n'
    '                _metric("Breakeven", f"${breakeven:,.2f}"),\n'
    '            ])\n'
    '            model_extra = ""\n'
    '            LIQUIDITY_THRESHOLD = 50\n'
    '            if 0 < prob_volume < LIQUIDITY_THRESHOLD or 0 < prob_oi < LIQUIDITY_THRESHOLD:\n'
    '                model_extra = (\n'
    '                    \'<span class="rs-badge red" style="margin-top:8px; display:inline-block;">\'\n'
    '                    f\'נפח/עניין פתוח נמוכים ({int(prob_volume)}/{int(prob_oi)}) - המחיר עלול \'\n'
    '                    \'לא לשקף מסחר אמיתי</span>\'\n'
    '                )\n'
    '            _card("מודל (Black-Scholes)", f\'<div class="rs-grid">{grid_normal}</div>{model_extra}\')\n'
)

# --- עוגן 4: טבלת השוואה, בסוף הבלוק (אחרי badge פערי המודלים) -----------
COMPARE_ANCHOR_OLD = (
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
)
COMPARE_ANCHOR_NEW = (
    '                if spread > 0.15:\n'
    '                    st.markdown(\n'
    '                        \'<div class="rs-explain" style="margin-top:8px;">\'\n'
    '                        \'המודלים חלוקים ביותר מ-15 נקודות אחוז - זה סימן לאי-ודאות \'\n'
    '                        \'גבוהה, לא לכך שאחד מהם "נכון" והשאר טועים.\'\n'
    '                        \'</div>\',\n'
    '                        unsafe_allow_html=True,\n'
    '                    )\n'
    '\n'
    '            _compare_key = f"{key_prefix}_compare_rows"\n'
    '            if _compare_key not in st.session_state:\n'
    '                st.session_state[_compare_key] = []\n'
    '            if st.button("➕ הוסף שורה לטבלת ההשוואה", key=f"{key_prefix}_compare_add"):\n'
    '                st.session_state[_compare_key].append({\n'
    '                    "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,\n'
    '                    "נפח": prob_volume, "עניין פתוח": prob_oi,\n'
    '                    "Breakeven": breakeven,\n'
    '                    "הסתברות מודל": normal_prob,\n'
    '                    "מרחק (Expected Moves)": em_distance,\n'
    '                })\n'
    '\n'
    '        st.markdown(\'<hr style="border-color: rgba(255,255,255,.08); margin: 24px 0;">\', unsafe_allow_html=True)\n'
    '        if st.session_state.get(f"{key_prefix}_compare_rows"):\n'
    '            st.markdown(\'<div class="rs-title" style="margin-bottom:8px;">טבלת השוואה (לפי סטרייק, לא לפי \\"כדאיות\\")</div>\', unsafe_allow_html=True)\n'
    '            import pandas as pd\n'
    '            rows = st.session_state[f"{key_prefix}_compare_rows"]\n'
    '            df = pd.DataFrame(rows).sort_values("סטרייק").reset_index(drop=True)\n'
    '            df["הסתברות מודל"] = df["הסתברות מודל"].map(lambda v: f"{v:.1%}" if v is not None else "—")\n'
    '            df["מרחק (Expected Moves)"] = df["מרחק (Expected Moves)"].map(lambda v: f"{v:.2f}x" if v is not None else "—")\n'
    '            df["נזילות"] = [\n'
    '                "⚠️ נמוכה" if (0 < r["נפח"] < 50 or 0 < r["עניין פתוח"] < 50) else "—"\n'
    '                for _, r in df.iterrows()\n'
    '            ]\n'
    '            st.dataframe(df, use_container_width=True, hide_index=True)\n'
    '            if st.button("🗑️ נקה טבלה", key=f"{key_prefix}_compare_clear"):\n'
    '                st.session_state[f"{key_prefix}_compare_rows"] = []\n'
    '                st.rerun()\n'
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
        text = apply_single_anchor(text, CAPITAL_OLD, CAPITAL_NEW, "liquidity-inputs")
        text = apply_single_anchor(text, MODEL_CARD_OLD, MODEL_CARD_NEW, "model-card-breakeven")
        text = apply_single_anchor(text, COMPARE_ANCHOR_OLD, COMPARE_ANCHOR_NEW, "compare-table")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("כל ארבעת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
