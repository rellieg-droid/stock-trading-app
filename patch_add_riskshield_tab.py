"""
patch_add_riskshield_tab.py
============================
מוסיף את RiskShield כקבוצת ניווט ראשית חדשה (לא תת-טאב) ב-alpha_paper_trading.py.

שימוש:
    python patch_add_riskshield_tab.py             # dry-run - רק בודק ומדפיס
    python patch_add_riskshield_tab.py --apply      # מבצע בפועל, עם גיבוי

לפני הרצה: וודאי ש-riskshield_tab.py ו-options_engine.py כבר נמצאים
באותה תיקייה כמו alpha_paper_trading.py.

הערה: הוספת קבוצה שישית ל-GROUP_ORDER הופכת את כל 6 כפתורי ה-nav
הראשי לצרים יותר (st.columns(len(GROUP_ORDER)) הוא דינמי, אז אין צורך
בשינוי קוד בשביל זה - אבל כדאי לבדוק ויזואלית אחרי ההרצה).
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("alpha_paper_trading.py")

# כל שינוי: (תיאור, טקסט מקור ייחודי, טקסט חדש)
EDITS = [
    (
        "import של render_riskshield_tab",
        "from strategy_tab import render_strategy_tab",
        "from strategy_tab import render_strategy_tab\nfrom riskshield_tab import render_riskshield_tab",
    ),
    (
        "הוספת קבוצת RiskShield ל-NAV_GROUPS",
        '"מסחר":  {"icon": "cart",       "subs": ["🛒 מסחר", "💼 תיק", "👁️ Watchlist"]},',
        '"מסחר":  {"icon": "cart",       "subs": ["🛒 מסחר", "💼 תיק", "👁️ Watchlist"]},\n'
        '    "RiskShield": {"icon": "shield-check", "subs": ["🛡️ RiskShield"]},',
    ),
    (
        "הוספת RiskShield ל-GROUP_ORDER",
        'GROUP_ORDER = ["בית", "גרף", "ניתוח", "מסחר", "עוד"]',
        'GROUP_ORDER = ["בית", "גרף", "ניתוח", "מסחר", "RiskShield", "עוד"]',
    ),
    (
        "הוספת אייקון תחתון עבור RiskShield",
        'GROUP_BOTTOM_ICONS = {"בית": "🏠", "גרף": "📈", "ניתוח": "🎯", "מסחר": "🛒", "עוד": "☰"}',
        'GROUP_BOTTOM_ICONS = {"בית": "🏠", "גרף": "📈", "ניתוח": "🎯", "מסחר": "🛒", "RiskShield": "🛡️", "עוד": "☰"}',
    ),
    (
        "הוספת tooltip עבור RiskShield",
        '"מסחר":  "מסחר — קנייה ומכירה, תיק אחזקות, Watchlist וניהול יעדים",',
        '"מסחר":  "מסחר — קנייה ומכירה, תיק אחזקות, Watchlist וניהול יעדים",\n'
        '    "RiskShield": "RiskShield — מחשבון Black-Scholes ותנודתיות, בלי המלצות קנייה/מכירה",',
    ),
    (
        "הוספת tabbody_riskshield ל-_TAB_KEYS",
        '_TAB_KEYS = ["tabbody_home", "tabbody_chart", "tabbody_analysis", "tabbody_backtest",\n'
        '             "tabbody_trade", "tabbody_guide", "tabbody_compare", "tabbody_portfolio",\n'
        '             "tabbody_alerts", "tabbody_reports", "tabbody_watchlist", "tabbody_strategy"]',
        '_TAB_KEYS = ["tabbody_home", "tabbody_chart", "tabbody_analysis", "tabbody_backtest",\n'
        '             "tabbody_trade", "tabbody_guide", "tabbody_compare", "tabbody_portfolio",\n'
        '             "tabbody_alerts", "tabbody_reports", "tabbody_watchlist", "tabbody_strategy",\n'
        '             "tabbody_riskshield"]',
    ),
    (
        "הוספת ערך RiskShield ל-_active_map",
        '"🧭 אסטרטגיה": "tabbody_strategy"}',
        '"🧭 אסטרטגיה": "tabbody_strategy", "🛡️ RiskShield": "tabbody_riskshield"}',
    ),
    (
        "בלוק container חדש לטאב RiskShield",
        'with st.container(key="tabbody_strategy"):\n'
        '    render_strategy_tab(default_ticker=st.session_state.get("ticker", "NVDA"))',
        'with st.container(key="tabbody_strategy"):\n'
        '    render_strategy_tab(default_ticker=st.session_state.get("ticker", "NVDA"))\n\n'
        'with st.container(key="tabbody_riskshield"):\n'
        '    render_riskshield_tab(default_ticker=st.session_state.get("ticker", "NVDA"))',
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="בצע בפועל (ברירת מחדל: dry-run בלבד)")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"שגיאה: {TARGET} לא נמצא. הריצי מהתיקייה שבה נמצא alpha_paper_trading.py.")
        return 1

    raw_bytes = TARGET.read_bytes()
    has_crlf = b"\r\n" in raw_bytes
    # מנרמלים ל-\n לצורך ההשוואה/החלפה (אחרת עוגנים רב-שורתיים לא יתאימו
    # מול \r\n גולמי). הופכים בחזרה ל-\r\n רק בכתיבה הסופית, למטה.
    text = raw_bytes.decode("utf-8").replace("\r\n", "\n")

    for desc, old, _new in EDITS:
        count = text.count(old)
        if count == 0:
            print(f"❌ עצירה: לא נמצא anchor עבור \"{desc}\".")
            print("   ייתכן שהטקסט בקובץ שונה מעט ממה שהפאץ' מצפה לו (רווחים/שינוי קודם).")
            return 1
        if count > 1:
            print(f"❌ עצירה: anchor עבור \"{desc}\" נמצא {count} פעמים (צריך בדיוק פעם אחת).")
            return 1

    print(f"✅ כל {len(EDITS)} העוגנים נמצאו בדיוק פעם אחת. הפאץ' תקין לביצוע.\n")
    for desc, _old, _new in EDITS:
        print(f"   - {desc}")

    if not args.apply:
        print("\n(dry-run בלבד — שום קובץ לא שונה. הריצי עם --apply כדי לבצע בפועל.)")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = TARGET.with_suffix(TARGET.suffix + f".bak_{stamp}")
    shutil.copy2(TARGET, backup_path)
    print(f"\n📦 גיבוי נשמר: {backup_path}")

    new_text = text
    for _desc, old, new in EDITS:
        new_text = new_text.replace(old, new, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"❌ עצירה: הקוד אחרי הפאץ' לא עובר ast.parse ({e}). לא נכתב כלום.")
        return 1

    final_text = new_text.replace("\n", "\r\n") if has_crlf else new_text
    TARGET.write_bytes(final_text.encode("utf-8"))
    print(f"✅ נכתב בהצלחה ל-{TARGET}. {len(EDITS)} שינויים בוצעו.")
    print("   מומלץ להריץ עכשיו: streamlit run alpha_paper_trading.py, ולבדוק:")
    print("   1. שקבוצת ניווט חדשה '🛡️' מופיעה בשורת ה-nav הראשית (6 כפתורים)")
    print("   2. שלחיצה עליה פותחת את טאב RiskShield")
    print("   3. שרוחב שאר 5 הכפתורים עדיין נראה טוב עם 6 עמודות")
    return 0


if __name__ == "__main__":
    sys.exit(main())
