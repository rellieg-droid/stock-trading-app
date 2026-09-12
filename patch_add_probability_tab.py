"""
patch_add_probability_tab.py
=============================
מוסיף טאב-משנה רביעי ל-RiskShield: "הסתברות OTM (Put)".
מציג את שלושת מודלי ההסתברות (Normal / היסטורי / Fat-tail) בנפרד לגמרי -
בלי מיזוג למספר אחד, בלי המלצה. תואם ל-riskshield_tab.py הקיים באותה
מוסכמת עיצוב (rs-card, rs-metric, rs-explain, badges תיאוריים בלבד).

דורש: patch_add_probability_models.py כבר הורץ על options_engine.py
(מוסיף historical_put_otm_probability + fat_tail_otm_probability).

שימוש:
    python patch_add_probability_tab.py            # dry-run
    python patch_add_probability_tab.py --apply     # מבצע בפועל

הערה: הטאב הזה ממוקד ב-Put בלבד (זה הכיוון שנבנה ונבדק ב-options_engine.py
כרגע - הרחבה ל-Call תדרוש נוסחאות סימטריות נפרדות שעוד לא נכתבו/נבדקו).
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: שורת הייבוא -----------------------------------------------
IMPORT_OLD = (
    "from options_engine import bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks\n"
)
IMPORT_NEW = (
    "from math import log as _log\n\n"
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    ")\n"
)

# --- עוגן 2: הגדרת שלושת הטאבים ----------------------------------------
TABS_OLD = (
    '    tab_bs, tab_iv, tab_rv = st.tabs(["מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)"])\n'
)
TABS_NEW = (
    '    tab_bs, tab_iv, tab_rv, tab_prob = st.tabs(\n'
    '        ["מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)", "הסתברות OTM (Put)"]\n'
    '    )\n'
)

# --- עוגן 3: סוף הפונקציה (לפני סגירת ה-wrap) --------------------------
END_OLD = (
    '    st.markdown(\'</div>\', unsafe_allow_html=True)\n'
)
NEW_TAB_BLOCK = '''
    # -------------------------------------------------------------------
    # טאב 4: הסתברות OTM - שלושה מודלים נפרדים, בלי מיזוג ובלי המלצה
    # -------------------------------------------------------------------
    with tab_prob:
        st.markdown(
            \'<div class="rs-explain" style="margin-bottom:12px;">\'
            \'שלושה מודלים נפרדים להערכת הסתברות OTM לפוט: מודל (Black-Scholes), \'
            \'היסטורי (לפי מה שקרה בפועל בעבר), ו-Fat-tail (מתחשב בזנבות שמנים \'
            \'מעבר להתפלגות נורמלית). המודלים מוצגים כל אחד בנפרד - אין כאן ציון \'
            \'מאוחד, דירוג, או "המלצה". אם המודלים חלוקים ביניהם באופן משמעותי, \'
            \'זה מוצג במפורש, לא מוסתר.\'
            \'</div>\',
            unsafe_allow_html=True,
        )

        spot_default = _try_fetch_spot(ticker) or 100.0
        cols = st.columns(4)
        with cols[0]:
            prob_S = st.number_input("מחיר נכס (S)", min_value=0.01, value=float(round(spot_default, 2)),
                                      key=f"{key_prefix}_prob_S", help=_HELP["S"])
        with cols[1]:
            prob_K = st.number_input("סטרייק (K)", min_value=0.01, value=float(round(spot_default * 0.9, 2)),
                                      key=f"{key_prefix}_prob_K", help=_HELP["K"])
        with cols[2]:
            prob_days = st.number_input("ימים לפקיעה", min_value=1, value=30,
                                         key=f"{key_prefix}_prob_days", help=_HELP["days"])
        with cols[3]:
            prob_sigma_pct = st.number_input("IV למודל (%)", min_value=0.1, value=30.0,
                                              key=f"{key_prefix}_prob_sigma", help=_HELP["sigma"])

        prob_r_pct = st.number_input("ריבית חסרת סיכון (%)", value=4.5,
                                      key=f"{key_prefix}_prob_r", help=_HELP["r"])

        if st.button("חשב הסתברות OTM", key=f"{key_prefix}_prob_calc"):
            # --- מודל 1: Normal (Black-Scholes) - קיים כבר, רק נחשף כאן ---
            try:
                normal_prob = bs_greeks(
                    kind="put", S=prob_S, K=prob_K, T=prob_days / 365.0,
                    sigma=prob_sigma_pct / 100.0, r=prob_r_pct / 100.0,
                ).prob_otm
            except ValueError as e:
                st.error(f"קלט לא תקין למודל: {e}")
                normal_prob = None

            available_for_diff = {}
            if normal_prob is not None:
                available_for_diff["מודל"] = normal_prob

            grid_normal = _metric("הסתברות OTM - מודל", f"{normal_prob:.1%}" if normal_prob is not None else "—")
            _card("מודל (Black-Scholes)", f'<div class="rs-grid">{grid_normal}</div>')

            # --- מודלים 2+3 דורשים היסטוריית מחירים -----------------------
            closes = _try_fetch_closes(ticker, period="10y")
            if closes is None:
                st.info(
                    f"לא נמצאה היסטוריית מחירים עבור \\"{ticker}\\" - מוצג רק מודל "
                    "ה-Black-Scholes. היסטורי ו-Fat-tail דורשים סדרת מחירים."
                )
            else:
                hist = historical_put_otm_probability(closes, strike=prob_K, dte_days=int(prob_days))
                period_metrics = "".join(
                    _metric(f"{years} שנים", f"{p:.1%}" if p is not None else "אין מספיק היסטוריה")
                    for years, p in sorted(hist.by_period.items())
                )
                weighted_html = (
                    _metric("ממוצע משוקלל", f"{hist.weighted_otm:.1%}")
                    if hist.weighted_otm is not None else ""
                )
                hist_explain = (
                    '<div class="rs-explain">כל תקופה (1/3/5/10 שנים) מחושבת בנפרד לפי '
                    'כמה פעמים בעבר המחיר, בהינתן אותו מרחק זמן לפקיעה, נשאר מעל הסטרייק. '
                    'הממוצע המשוקלל (40/30/20/10) מוצג לצד הפירוט המלא, לא במקומו.'
                    + (f'<br><b>{hist.note}</b>' if hist.note else '')
                    + '</div>'
                )
                _card("היסטורי", f'<div class="rs-grid">{period_metrics}{weighted_html}</div>{hist_explain}')
                if hist.weighted_otm is not None:
                    available_for_diff["היסטורי"] = hist.weighted_otm

                log_returns = [_log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
                fat = fat_tail_otm_probability(log_returns, S=prob_S, K=prob_K, dte_days=int(prob_days))
                if fat.otm_probability is not None:
                    grid_fat = "".join([
                        _metric("הסתברות OTM - Fat-tail", f"{fat.otm_probability:.1%}"),
                        _metric("דרגות חופש (df)", f"{fat.degrees_of_freedom:.1f}"),
                        _metric("קורטוזיס עודף", f"{fat.excess_kurtosis:.2f}"),
                    ])
                    fat_explain = (
                        '<div class="rs-explain">קירוב מוצהר: מעריך דרגות חופש של התפלגות '
                        't-Student מהקורטוזיס העודף בתשואות ההיסטוריות, ומתאים לאופק הזמן '
                        'לפי שורש-זמן. df נמוך = זנבות שמנים משמעותיים ביחס להתפלגות נורמלית.'
                        '</div>'
                    )
                    _card("Fat-tail", f'<div class="rs-grid">{grid_fat}</div>{fat_explain}')
                    available_for_diff["Fat-tail"] = fat.otm_probability
                else:
                    st.info(f"Fat-tail: {fat.note}")

            # --- פערי מודלים - עובדה, לא ציון ------------------------------
            if len(available_for_diff) >= 2:
                spread = max(available_for_diff.values()) - min(available_for_diff.values())
                cls = "red" if spread > 0.15 else ("yellow" if spread > 0.05 else "gray")
                txt = f"פער בין המודלים: {spread:.1%}"
                st.markdown(f'<span class="rs-badge {cls}">{txt}</span>', unsafe_allow_html=True)
                if spread > 0.15:
                    st.markdown(
                        \'<div class="rs-explain" style="margin-top:8px;">\'
                        \'המודלים חלוקים ביותר מ-15 נקודות אחוז - זה סימן לאי-ודאות \'
                        \'גבוהה, לא לכך שאחד מהם "נכון" והשאר טועים.\'
                        \'</div>\',
                        unsafe_allow_html=True,
                    )
'''


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
        text = apply_single_anchor(text, TABS_OLD, TABS_NEW, "tabs")
        text = apply_single_anchor(text, END_OLD, NEW_TAB_BLOCK + END_OLD, "end-of-function")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("שלושת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
