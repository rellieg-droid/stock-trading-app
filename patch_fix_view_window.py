"""
patch_fix_view_window.py

מטרה: להפריד בין חלון השליפה (FETCH_PERIODS, רחב בכוונה כדי שיהיה
באפר לאינדיקטורים וזום-אאוט בלי שליפה חוזרת) לבין חלון התצוגה
הראשוני בגרף (PERIODS, הקצר שהמשתמשת בפועל בחרה - למשל "1D").

היום ה-DataFrame הרחב מוצג במלואו בגרף בלי שום קיצוץ/הגבלת טווח --
בחירת "1D" בפועל מציגה את כל 5 הימים שנשלפו, לא רק את היום האחרון.

התיקון (גישה ב', בלי לקצץ את ה-DataFrame עצמו):
1. שומרים את חלון התצוגה המקורי (הצר) לפני שהוא נדרס בערך הרחב.
2. אחרי בניית הגרף, קובעים את טווח ציר ה-X ההתחלתי (xaxis range)
   לחלון הצר -- הגרף "נפתח" מזוזם לטווח המבוקש, אבל כל הנתונים
   הרחבים עדיין קיימים בפועל, כך שזום-אאוט ידני עדיין עובד בלי
   שליפה נוספת, בדיוק כמו שתוכנן במקור.

שימוש:
    python patch_fix_view_window.py                 # dry-run (ברירת מחדל)
    python patch_fix_view_window.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

HELPER_ANCHOR = "COMPANY_MAP = {"

PERIOD_CAPTURE_ANCHOR_LINES = [
    "period, interval = PERIODS[st.session_state.period]",
    "period = FETCH_PERIODS.get(st.session_state.period, period)",
]

CHART_RANGE_ANCHOR = 'st.plotly_chart(fig, width="stretch",'

HELPER_FUNC_LINES = [
    "def _view_window_start(period_str, last_ts):",
    '    """',
    "    מחשבת נקודת התחלה לחלון התצוגה הראשוני בגרף, לפי מחרוזת period",
    '    מ-PERIODS (למשל "1d", "5d", "1mo", "ytd", "max"), ביחס לנר האחרון.',
    "    מחזירה None כשאין צורך בהגבלה (max).",
    '    """',
    "    if not period_str or period_str == \"max\":",
    "        return None",
    "    if period_str == \"ytd\":",
    "        try:",
    "            return pd.Timestamp(year=last_ts.year, month=1, day=1, tz=getattr(last_ts, 'tz', None))",
    "        except Exception:",
    "            return None",
    "    m = re.match(r\"(\\d+)(d|mo|y)$\", period_str)",
    "    if not m:",
    "        return None",
    "    n, unit = int(m.group(1)), m.group(2)",
    "    try:",
    "        if unit == \"d\":",
    "            return last_ts - pd.Timedelta(days=n)",
    "        if unit == \"mo\":",
    "            return last_ts - pd.DateOffset(months=n)",
    "        if unit == \"y\":",
    "            return last_ts - pd.DateOffset(years=n)",
    "    except Exception:",
    "        return None",
    "    return None",
    "",
    "",
]

CHART_RANGE_SET_LINES = [
    "_view_start = _view_window_start(_view_period_raw, idx[-1])",
    "if _view_start is not None:",
    "    fig.update_xaxes(range=[_view_start, idx[-1]])",
]


def get_indent(text, anchor):
    idx = text.index(anchor)
    line_start = text.rfind("\n", 0, idx) + 1
    return text[line_start:idx]


def build_block_all_indented(indent, lines):
    return "\n".join((indent + line if line else "") for line in lines) + "\n"


def build_block_continue(indent, lines):
    """השורה הראשונה ממשיכה הזחה קיימת (בלי תוספת); שאר השורות מקבלות הזחה חדשה.
    מתאים כשמחליפים עוגן שנמצא באמצע שורה קיימת עם הזחה כבר קודמת לו."""
    first, rest = lines[0], lines[1:]
    parts = [first] + [indent + line for line in rest]
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="בצע בפועל (במקום dry-run)")
    args = parser.parse_args()

    target = Path(TARGET_FILE)
    if not target.exists():
        print(f"שגיאה: לא נמצא הקובץ {TARGET_FILE} בתיקייה הנוכחית.")
        sys.exit(1)

    raw_bytes = target.read_bytes()
    uses_crlf = b"\r\n" in raw_bytes
    text = raw_bytes.decode("utf-8")

    # ── אימות עוגנים ──
    if text.count(HELPER_ANCHOR) != 1:
        print(f"שגיאה: HELPER_ANCHOR נמצא {text.count(HELPER_ANCHOR)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)
    if text.count(CHART_RANGE_ANCHOR) != 1:
        print(f"שגיאה: CHART_RANGE_ANCHOR נמצא {text.count(CHART_RANGE_ANCHOR)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    period_indent = get_indent(text, PERIOD_CAPTURE_ANCHOR_LINES[0])
    eol = "\r\n" if uses_crlf else "\n"
    period_block_old = eol.join(period_indent + l for l in PERIOD_CAPTURE_ANCHOR_LINES)
    if period_block_old not in text:
        print("שגיאה: בלוק שורות ה-period לא נמצא ברצף מדויק. לא בוצע שינוי.")
        sys.exit(1)
    if text.count(period_block_old) != 1:
        print(f"שגיאה: בלוק שורות ה-period נמצא {text.count(period_block_old)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    if "import re" not in text.split(HELPER_ANCHOR)[0]:
        needs_re_import = True
    else:
        needs_re_import = False

    # ── בניית הבלוקים ──
    helper_indent = get_indent(text, HELPER_ANCHOR)  # ברמת המודול, אמור להיות ""
    helper_block = build_block_all_indented(helper_indent, HELPER_FUNC_LINES)
    new_helper_and_anchor = helper_block + helper_indent + HELPER_ANCHOR

    period_block_new = (
        period_indent + PERIOD_CAPTURE_ANCHOR_LINES[0] + "\n"
        + period_indent + "_view_period_raw = period\n"
        + period_indent + PERIOD_CAPTURE_ANCHOR_LINES[1]
    )

    chart_indent = get_indent(text, CHART_RANGE_ANCHOR)
    chart_range_block = build_block_continue(chart_indent, CHART_RANGE_SET_LINES)
    new_chart_block = chart_range_block + chart_indent + CHART_RANGE_ANCHOR

    new_text = text
    if needs_re_import:
        # מוסיפים import re מיד לפני ההגדרה של הפונקציה, בטוח יותר מלגעת בראש הקובץ
        new_helper_and_anchor = "import re\n" + helper_indent + new_helper_and_anchor
        # (מונע כפילות אם 're' כבר מיובא במקום אחר -- import re כפול ב-Python אינו שגיאה, רק redundant)

    new_text = new_text.replace(HELPER_ANCHOR, new_helper_and_anchor, 1)
    new_text = new_text.replace(period_block_old, period_block_new, 1)
    new_text = new_text.replace(CHART_RANGE_ANCHOR, new_chart_block, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        old_lines = text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="לפני", tofile="אחרי", lineterm="")
        print("".join(diff))
        print("\nלביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"גיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן.")
    print("לבדוק ידנית: בחרי '1D' ותוודאי שהגרף נפתח מזוזם ליום האחרון בלבד,")
    print("ושעדיין ניתן לגלול/לזום-אאוט ולראות ימים קודמים בלי הודעת שגיאה.")
    print("כדאי לבדוק גם '5D', '1M' ו-'MAX' לוודא שכולם מתנהגים כמצופה.")


if __name__ == "__main__":
    main()
