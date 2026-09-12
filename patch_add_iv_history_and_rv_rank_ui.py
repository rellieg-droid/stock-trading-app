"""
patch_add_iv_history_and_rv_rank_ui.py
========================================
שני שינויים ב-riskshield_tab.py, יחד בפאץ' אחד כי הם תלויים זה בזה
(ה-UI מציג את מה שהאיסוף שומר), אבל כל אחד עוגן נפרד ומאומת בנפרד:

1. כל חישוב IV בטאב "תנודתיות גלומה" נשמר ל-SQLite מקומי (iv_history.db) -
   תשתית לאיסוף היסטוריית IV אמיתית קדימה מעכשיו. options_engine.py נשאר
   טהור לגמרי - כל ה-I/O כאן, בשכבת ה-UI שכבר "מלוכלכת" ממילא (yfinance).
2. טאב "הסתברות OTM" מציג RV Rank / RV Percentile - תחליף זמני ומתויג
   בבירור, עד שיש מספיק תצפיות IV שנאספו כדי לחשב IV Rank אמיתי.

שימוש:
    python patch_add_iv_history_and_rv_rank_ui.py            # dry-run
    python patch_add_iv_history_and_rv_rank_ui.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

# --- עוגן 1: שורת הייבוא -------------------------------------------------
IMPORT_OLD = (
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    ")\n"
)
IMPORT_NEW = (
    "import sqlite3\n"
    "from datetime import date as _date\n\n"
    "from options_engine import (\n"
    "    bs_greeks, norm_cdf, realized_vol, implied_vol, iv_rv_ratio, Greeks,\n"
    "    historical_put_otm_probability, fat_tail_otm_probability,\n"
    "    rv_rank, rv_percentile,\n"
    ")\n"
)

# --- עוגן 2: אחרי _try_fetch_closes - מוסיפים helpers ל-SQLite ----------
HELPERS_OLD = (
    "def _try_fetch_closes(ticker: str, period: str = \"1y\") -> Optional[list]:\n"
    "    \"\"\"שולף סדרת סגירות יומית להיסטוריה. נכשל בשקט.\"\"\"\n"
    "    if not ticker:\n"
    "        return None\n"
    "    try:\n"
    "        import yfinance as yf\n"
    "        hist = yf.Ticker(ticker).history(period=period)\n"
    "        if hist.empty or len(hist) < 3:\n"
    "            return None\n"
    "        return hist[\"Close\"].tolist()\n"
    "    except Exception:\n"
    "        return None\n"
)
HELPERS_NEW = HELPERS_OLD + '''

# ---------------------------------------------------------------------------
# איסוף היסטוריית IV - תשתית ל-IV Rank אמיתי בעתיד. options_engine.py
# נשאר טהור בכוונה; כל ה-I/O כאן, ליד ה-yfinance שכבר בקובץ הזה.
# ---------------------------------------------------------------------------
_IV_HISTORY_DB = "iv_history.db"


def _iv_history_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_IV_HISTORY_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS iv_observations ("
        "ticker TEXT NOT NULL, observed_at TEXT NOT NULL, "
        "dte INTEGER NOT NULL, iv REAL NOT NULL)"
    )
    return conn


def _record_iv_observation(ticker: str, dte: int, iv: float) -> None:
    """שומרת תצפית IV יומית. נכשלת בשקט אם אי אפשר לכתוב (דיסק/הרשאות) -
    זו תשתית עזר, לא אמורה לשבור את הטאב אם היא נכשלת."""
    if not ticker:
        return
    try:
        with _iv_history_conn() as conn:
            conn.execute(
                "INSERT INTO iv_observations (ticker, observed_at, dte, iv) VALUES (?, ?, ?, ?)",
                (ticker.upper(), _date.today().isoformat(), int(dte), float(iv)),
            )
    except Exception:
        pass


def _iv_observation_count(ticker: str) -> int:
    """כמה תצפיות IV נאספו עד כה לטיקר הזה. 0 אם אין/נכשל - לא קורס."""
    if not ticker:
        return 0
    try:
        with _iv_history_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM iv_observations WHERE ticker = ?", (ticker.upper(),)
            ).fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0
'''

# --- עוגן 3: בתוך tab_iv - שמירת התצפית אחרי חישוב מוצלח ----------------
TAB_IV_OLD = (
    '        if st.button("חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc"):\n'
    '            try:\n'
    '                iv_result = implied_vol(\n'
    '                    kind=iv_kind, market_price=iv_price, S=iv_S, K=iv_K,\n'
    '                    T=iv_days / 365.0, r=iv_r_pct / 100.0,\n'
    '                )\n'
    '                _card("תוצאה", _metric("IV גלום מהשוק", f"{iv_result:.1%}") + _IV_EXPLAIN)\n'
    '            except ValueError as e:\n'
    '                st.error(f"לא ניתן לפתור: {e}")\n'
)
TAB_IV_NEW = (
    '        if st.button("חשב תנודתיות גלומה", key=f"{key_prefix}_iv_calc"):\n'
    '            try:\n'
    '                iv_result = implied_vol(\n'
    '                    kind=iv_kind, market_price=iv_price, S=iv_S, K=iv_K,\n'
    '                    T=iv_days / 365.0, r=iv_r_pct / 100.0,\n'
    '                )\n'
    '                _card("תוצאה", _metric("IV גלום מהשוק", f"{iv_result:.1%}") + _IV_EXPLAIN)\n'
    '                _record_iv_observation(ticker, int(iv_days), iv_result)\n'
    '                n_obs = _iv_observation_count(ticker)\n'
    '                st.caption(\n'
    '                    f"נשמר לאיסוף היסטוריית IV. {n_obs} תצפיות עד כה עבור {ticker or \'טיקר לא צוין\'} "\n'
    '                    "(IV Rank אמיתי דורש היסטוריה - עד אז, טאב \'הסתברות OTM\' מציג RV Rank כתחליף)."\n'
    '                )\n'
    '            except ValueError as e:\n'
    '                st.error(f"לא ניתן לפתור: {e}")\n'
)

# --- עוגן 4: בתוך tab_prob - אחרי כרטיס ה-Fat-tail, לפני פערי המודלים ---
PROB_OLD = (
    '                    _card("Fat-tail", f\'<div class="rs-grid">{grid_fat}</div>{fat_explain}\')\n'
    '                    available_for_diff["Fat-tail"] = fat.otm_probability\n'
    '                else:\n'
    '                    st.info(f"Fat-tail: {fat.note}")\n'
)
PROB_NEW = (
    '                    _card("Fat-tail", f\'<div class="rs-grid">{grid_fat}</div>{fat_explain}\')\n'
    '                    available_for_diff["Fat-tail"] = fat.otm_probability\n'
    '                else:\n'
    '                    st.info(f"Fat-tail: {fat.note}")\n'
    '\n'
    '                rank = rv_rank(closes)\n'
    '                pct = rv_percentile(closes)\n'
    '                n_obs = _iv_observation_count(ticker)\n'
    '                grid_rv = "".join([\n'
    '                    _metric("RV Rank", f"{rank:.0f}" if rank is not None else "אין מספיק היסטוריה"),\n'
    '                    _metric("RV Percentile", f"{pct:.0f}%" if pct is not None else "אין מספיק היסטוריה"),\n'
    '                ])\n'
    '                rv_explain = (\n'
    '                    \'<div class="rs-explain">תחליף זמני ל-IV Rank: yfinance/Yahoo לא שומרים \'\n'
    '                    \'ארכיון היסטוריית IV (רק שרשרת אופציות נוכחית), אז מוצג כאן דירוג של \'\n'
    '                    \'התנודתיות הממומשת (RV) - מה שקרה בפועל, לא מה שהשוק מתמחר. \'\n'
    '                    f\'נאספו {n_obs} תצפיות IV אמיתיות לטיקר הזה בטאב "תנודתיות גלומה" - \'\n'
    '                    \'ברגע שיצטבר מספיק, ניתן יהיה לחשב IV Rank אמיתי.\'\n'
    '                    \'</div>\'\n'
    '                )\n'
    '                _card("RV Rank (תחליף זמני ל-IV Rank)", f\'<div class="rs-grid">{grid_rv}</div>{rv_explain}\')\n'
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
        text = apply_single_anchor(text, HELPERS_OLD, HELPERS_NEW, "sqlite-helpers")
        text = apply_single_anchor(text, TAB_IV_OLD, TAB_IV_NEW, "tab-iv-record")
        text = apply_single_anchor(text, PROB_OLD, PROB_NEW, "tab-prob-rv-rank")
    except RuntimeError as e:
        print(str(e))
        return 1

    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("ארבעת העוגנים נמצאו פעם אחת כל אחד. ast.parse עבר בהצלחה.")

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
