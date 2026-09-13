"""
patch_add_fattail_rvrank_to_compare_and_guide.py
====================================================
שלושה שינויים:

1. שורת "➕ הוסף שורה" רק מסמנת "ממתין להוספה" - הבנייה בפועל של השורה
   קורית בסוף הבלוק (אחרי ש-Fat-tail ו-RV Rank כבר חושבו), כדי שהם
   ייכללו בטבלה. לפני זה הם היו מחושבים אחרי מקום הכפתור, אז לא היו
   זמינים.
2. שתי עמודות/שורות חדשות בטבלת ההשוואה: הסתברות Fat-tail ו-RV Rank.
3. המדריך המתקפל (📖) מקבל פסקה שמסבירה מה כל אחד מהמודלים/הכלים
   בטאב "הסתברות OTM" בודק בפועל.

שימוש:
    python patch_add_fattail_rvrank_to_compare_and_guide.py            # dry-run
    python patch_add_fattail_rvrank_to_compare_and_guide.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: הכפתור מסמן "ממתין" במקום לבנות את השורה מיד -----------------
ADD_BUTTON_OLD = (
    '            add_col, export_col = st.columns([1, 1])\n'
    '            with add_col:\n'
    '                add_clicked = st.button("➕ הוסף שורה", key=f"{key_prefix}_compare_add")\n'
    '            if add_clicked:\n'
    '                new_row = {\n'
    '                    "טיקר": ticker, "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,\n'
    '                    "נפח": prob_volume, "עניין פתוח": prob_oi,\n'
    '                    "Breakeven": round(breakeven, 2),\n'
    '                    "הסתברות מודל (%)": round(normal_prob * 100, 1) if normal_prob is not None else None,\n'
    '                    "מרחק (xEM)": round(em_distance, 2) if em_distance is not None else None,\n'
    '                    "נזילות": "⚠️ נמוכה" if (0 < prob_volume < 50 or 0 < prob_oi < 50) else "תקינה",\n'
    '                }\n'
    '                existing = next(\n'
    '                    (r for r in st.session_state[_compare_key]\n'
    '                     if r["טיקר"] == ticker and r["סטרייק"] == prob_K),\n'
    '                    None,\n'
    '                )\n'
    '                if existing is not None:\n'
    '                    existing.update(new_row)\n'
    '                else:\n'
    '                    st.session_state[_compare_key].append(new_row)\n'
)
ADD_BUTTON_NEW = (
    '            _fat_for_row = None\n'
    '            _rv_rank_for_row = None\n'
    '            add_col, export_col = st.columns([1, 1])\n'
    '            with add_col:\n'
    '                if st.button("➕ הוסף שורה", key=f"{key_prefix}_compare_add"):\n'
    '                    st.session_state[f"{key_prefix}_compare_pending"] = True\n'
)

# --- עוגן 2: קליטת Fat-tail בזמן שהוא מחושב ---------------------------------
FAT_CAPTURE_OLD = (
    '                    _card("Fat-tail", f\'<div class="rs-grid">{grid_fat}</div>{fat_explain}\')\n'
    '                    available_for_diff["Fat-tail"] = fat.otm_probability\n'
)
FAT_CAPTURE_NEW = (
    '                    _card("Fat-tail", f\'<div class="rs-grid">{grid_fat}</div>{fat_explain}\')\n'
    '                    available_for_diff["Fat-tail"] = fat.otm_probability\n'
    '                    _fat_for_row = fat.otm_probability\n'
)

# --- עוגן 3: קליטת RV Rank בזמן שהוא מחושב ----------------------------------
RV_CAPTURE_OLD = (
    '                _card("RV Rank (תחליף זמני ל-IV Rank)", f\'<div class="rs-grid">{grid_rv}</div>{rv_explain}\')\n'
)
RV_CAPTURE_NEW = (
    '                _card("RV Rank (תחליף זמני ל-IV Rank)", f\'<div class="rs-grid">{grid_rv}</div>{rv_explain}\')\n'
    '                _rv_rank_for_row = rank\n'
)

# --- עוגן 4: בניית השורה בפועל, בסוף הבלוק (אחרי CVaR, לפני פערי מודלים) --
BUILD_ROW_OLD = (
    '            # --- פערי מודלים - עובדה, לא ציון ------------------------------\n'
)
BUILD_ROW_NEW = (
    '            if st.session_state.get(f"{key_prefix}_compare_pending"):\n'
    '                new_row = {\n'
    '                    "טיקר": ticker, "סטרייק": prob_K, "פרמיה": prob_premium, "IV (%)": prob_sigma_pct,\n'
    '                    "נפח": prob_volume, "עניין פתוח": prob_oi,\n'
    '                    "Breakeven": round(breakeven, 2),\n'
    '                    "הסתברות מודל (%)": round(normal_prob * 100, 1) if normal_prob is not None else None,\n'
    '                    "Fat-tail (%)": round(_fat_for_row * 100, 1) if _fat_for_row is not None else None,\n'
    '                    "RV Rank": round(_rv_rank_for_row, 0) if _rv_rank_for_row is not None else None,\n'
    '                    "מרחק (xEM)": round(em_distance, 2) if em_distance is not None else None,\n'
    '                    "נזילות": "⚠️ נמוכה" if (0 < prob_volume < 50 or 0 < prob_oi < 50) else "תקינה",\n'
    '                }\n'
    '                existing = next(\n'
    '                    (r for r in st.session_state[_compare_key]\n'
    '                     if r["טיקר"] == ticker and r["סטרייק"] == prob_K),\n'
    '                    None,\n'
    '                )\n'
    '                if existing is not None:\n'
    '                    existing.update(new_row)\n'
    '                else:\n'
    '                    st.session_state[_compare_key].append(new_row)\n'
    '                st.session_state[f"{key_prefix}_compare_pending"] = False\n'
    '\n'
    '            # --- פערי מודלים - עובדה, לא ציון ------------------------------\n'
)

# --- עוגן 5: הוספת Fat-tail ו-RV Rank לשורות התצוגה בטבלה -------------------
TABLE_ROWS_OLD = (
    '                    ("הסתברות מודל OTM", lambda r: (\n'
    '                        f"{r[\'הסתברות מודל (%)\']:.1f}%" if r["הסתברות מודל (%)"] is not None else "—"\n'
    '                    )),\n'
    '                    ("Breakeven", lambda r: f"${r[\'Breakeven\']:.2f}"),\n'
)
TABLE_ROWS_NEW = (
    '                    ("הסתברות מודל OTM", lambda r: (\n'
    '                        f"{r[\'הסתברות מודל (%)\']:.1f}%" if r["הסתברות מודל (%)"] is not None else "—"\n'
    '                    )),\n'
    '                    ("הסתברות Fat-tail OTM", lambda r: (\n'
    '                        f"{r.get(\'Fat-tail (%)\'):.1f}%" if r.get("Fat-tail (%)") is not None else "—"\n'
    '                    )),\n'
    '                    ("RV Rank", lambda r: (\n'
    '                        f"{r.get(\'RV Rank\'):.0f}" if r.get("RV Rank") is not None else "—"\n'
    '                    )),\n'
    '                    ("Breakeven", lambda r: f"${r[\'Breakeven\']:.2f}"),\n'
)

# --- עוגן 6: הוספת הסבר מודלים למדריך ---------------------------------------
GUIDE_OLD = (
    '            \'<b>Expected Move</b>: טווח מחירים סביר עד הפקיעה, לפי ה-IV.<br>\'\n'
    '            \'<b>CVaR</b>: ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר - לא תרחיש קיצון בודד.\'\n'
    '            \'</div>\',\n'
)
GUIDE_NEW = (
    '            \'<b>Expected Move</b>: טווח מחירים סביר עד הפקיעה, לפי ה-IV (בהנחת התפלגות נורמלית).<br>\'\n'
    '            \'<b>Fat-tail</b>: הסתברות OTM לפי התפלגות t-Student במקום נורמלית - \'\n'
    '            \'"זנבות שמנים" יותר, בדיוק התיקון להנחה של Expected Move שלא תמיד מחזיקה.<br>\'\n'
    '            \'<b>CVaR</b>: ממוצע ה-P/L ב-5% התרחישים ההיסטוריים הגרועים ביותר בפועל - \'\n'
    '            \'לא מניח שום התפלגות בכלל, פשוט לוקח מה שקרה.<br>\'\n'
    '            \'<b>סטרס טסט</b>: תרחישי ירידה קבועים (עד 50%-) - גם הם לא תלויים בשום הנחת התפלגות.\'\n'
    '            \'</div>\',\n'
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
        text = apply_single_anchor(text, ADD_BUTTON_OLD, ADD_BUTTON_NEW, "add-button")
        text = apply_single_anchor(text, FAT_CAPTURE_OLD, FAT_CAPTURE_NEW, "fat-capture")
        text = apply_single_anchor(text, RV_CAPTURE_OLD, RV_CAPTURE_NEW, "rv-capture")
        text = apply_single_anchor(text, BUILD_ROW_OLD, BUILD_ROW_NEW, "build-row")
        text = apply_single_anchor(text, TABLE_ROWS_OLD, TABLE_ROWS_NEW, "table-rows")
        text = apply_single_anchor(text, GUIDE_OLD, GUIDE_NEW, "guide-text")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("כל ששת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
