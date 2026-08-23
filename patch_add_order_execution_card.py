"""
patch_add_order_execution_card.py

מטרה: להוסיף "Order Execution Card" בטאב המסחר (tr_sub1):

1. כרטיס אישור לפני ביצוע -- מחליף את שורת הטקסט הבודדת "עלות: $X"
   בכרטיס מעוצב שמציג פעולה/סימול/כמות/מחיר/עלות כוללת/הערה.

2. כרטיס קבלה אחרי ביצוע -- נשמר ב-st.session_state["last_trade_receipt"]
   מיד לפני כל st.rerun() (גם בקנייה וגם במכירה), ומוצג בעקביות בראש
   הטאב (לא נעלם כמו st.success שרץ), עם כפתור לסגור אותו.

שימוש:
    python patch_add_order_execution_card.py                 # dry-run (ברירת מחדל)
    python patch_add_order_execution_card.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

HEADER_ANCHOR = 'st.markdown(f"### 🛒 Paper Trading — {ticker}")'
COST_LINE_ANCHOR = 'st.markdown(f"**עלות: {sym}{tv_:,.2f}**")'
BUY_SUCCESS_ANCHOR = 'st.success(f"✅ קנית {si_} מניות ב-{sym}{cp_:.2f}"'
SELL_SUCCESS_ANCHOR = "st.success(f\"{'✅' if pnl >= 0 else '❌'} P&L: {sym}{pnl:+.2f}\")"

# כל הבלוקים הבאים הם מחרוזות רגילות (לא f-strings) בכוונה -
# ה-{...} בתוכן נשאר טקסט מילולי, וייכנס כמו שהוא לקובץ היעד,
# שם הוא כבר f-string אמיתי שרץ בתוך האפליקציה.
RECEIPT_RENDER_LINES = [
    'if st.session_state.get("last_trade_receipt"):',
    '    _rc = st.session_state["last_trade_receipt"]',
    '    _rc_clr = "#3fb950" if _rc["action"] == "BUY" else ("#3fb950" if _rc.get("pnl", 0) >= 0 else "#f85149")',
    '    _rc_action_he = "קנייה" if _rc["action"] == "BUY" else "מכירה"',
    '    _rc_pnl_line = (',
    '        f\'<div style="color:#8b949e;font-size:.72rem;">P&L: \'',
    '        f\'<span style="color:{_rc_clr};font-weight:700;">{_rc["pnl"]:+.2f}</span></div>\'',
    '    ) if "pnl" in _rc else ""',
    '    _rc_stop_line = (',
    '        f\'<div style="color:#8b949e;font-size:.72rem;">סטופ: {sym}{_rc["stop_price"]:.2f}</div>\'',
    '    ) if _rc.get("stop_price") else ""',
    '    _rc_col1, _rc_col2 = st.columns([9, 1])',
    '    with _rc_col1:',
    '        st.markdown(',
    '            f\'<div style="background:#161b22;border:1px solid #21262d;\'',
    '            f\'border-top:3px solid {_rc_clr};border-radius:12px;\'',
    '            f\'padding:12px 16px;margin-bottom:10px;direction:rtl;">\'',
    '            f\'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;">בוצע · {_rc["date"]}</div>\'',
    '            f\'<div style="font-weight:700;color:#e6edf3;font-size:.95rem;margin:2px 0;">\'',
    '            f\'{_rc_action_he} {_rc["shares"]} {_rc["symbol"]} @ {sym}{_rc["price"]:.2f} \'',
    '            f\'(סה"כ {sym}{_rc["total"]:,.2f})</div>\'',
    '            f\'{_rc_pnl_line}{_rc_stop_line}\'',
    '            f\'</div>\', unsafe_allow_html=True',
    '        )',
    '    with _rc_col2:',
    '        if st.button("✕", key="dismiss_trade_receipt"):',
    '            del st.session_state["last_trade_receipt"]',
    '            st.rerun()',
]

CONFIRM_CARD_LINES = [
    'st.markdown(',
    '    f\'<div style="background:#161b22;border:1px solid #21262d;\'',
    '    f\'border-radius:12px;padding:12px 16px;margin:6px 0;direction:rtl;">\'',
    '    f\'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;">לאישור</div>\'',
    '    f\'<div style="font-weight:700;color:#e6edf3;font-size:.95rem;margin:2px 0;">\'',
    '    f\'{act.split(" ")[-1]} {si_} {ticker} @ {sym}{cp_:.2f}</div>\'',
    '    f\'<div style="color:#8b949e;font-size:.8rem;">סה"כ: \'',
    '    f\'<span style="color:#e6edf3;font-weight:700;">{sym}{tv_:,.2f}</span></div>\'',
    '    f\'</div>\', unsafe_allow_html=True',
    ')',
]

BUY_RECEIPT_SET_LINES = [
    'st.session_state["last_trade_receipt"] = {',
    '    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "action": "BUY",',
    '    "symbol": ticker, "shares": si_, "price": cp_, "total": tv_,',
    '    "stop_price": pos.get("stop_price"),',
    '}',
]

SELL_RECEIPT_SET_LINES = [
    'st.session_state["last_trade_receipt"] = {',
    '    "date": _sell_date, "action": "SELL",',
    '    "symbol": ticker, "shares": si_, "price": cp_, "total": tv_,',
    '    "pnl": round(pnl, 2),',
    '}',
]


def get_indent(text, anchor):
    idx = text.index(anchor)
    line_start = text.rfind("\n", 0, idx) + 1
    return text[line_start:idx]


def build_block_all_indented(indent, lines):
    """כל השורות (כולל הראשונה) מקבלות את ההזחה - להוספה אחרי שורה חדשה מפורשת."""
    return "\n".join(indent + line for line in lines) + "\n"


def build_block_continue(indent, lines):
    """השורה הראשונה ממשיכה הזחה קיימת (בלי תוספת); שאר השורות מקבלות הזחה חדשה.
    מתאים כשמחליפים עוגן שנמצא באמצע שורה קיימת עם הזחה כבר קודמת לו."""
    first, rest = lines[0], lines[1:]
    parts = [first]
    parts += [indent + line for line in rest]
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

    anchors = {
        "HEADER_ANCHOR": HEADER_ANCHOR,
        "COST_LINE_ANCHOR": COST_LINE_ANCHOR,
        "BUY_SUCCESS_ANCHOR": BUY_SUCCESS_ANCHOR,
        "SELL_SUCCESS_ANCHOR": SELL_SUCCESS_ANCHOR,
    }
    for name, anchor in anchors.items():
        c = text.count(anchor)
        if c != 1:
            print(f"שגיאה: {name} נמצא {c} פעמים (צריך פעם אחת בדיוק). לא בוצע שינוי.")
            sys.exit(1)

    header_indent = get_indent(text, HEADER_ANCHOR)
    cost_indent = get_indent(text, COST_LINE_ANCHOR)
    buy_indent = get_indent(text, BUY_SUCCESS_ANCHOR)
    sell_indent = get_indent(text, SELL_SUCCESS_ANCHOR)

    # HEADER: אחרי החלפת העוגן עצמו, מוסיפים \n משלנו ואז בלוק מוזח במלואו (שורה חדשה אמיתית)
    receipt_render_block = build_block_all_indented(header_indent, RECEIPT_RENDER_LINES)
    new_header_block = HEADER_ANCHOR + "\n" + receipt_render_block.rstrip("\n")

    # COST LINE: מחליפים עוגן שנמצא באמצע שורה עם הזחה קיימת -> שורה ראשונה בלי הזחה נוספת
    new_confirm_block = build_block_continue(cost_indent, CONFIRM_CARD_LINES).rstrip("\n")

    # BUY/SELL: מכניסים בלוק חדש *לפני* העוגן הקיים (שנשאר במקומו, עם ההזחה המקורית שלו) ->
    # השורה הראשונה של הבלוק החדש ממשיכה את ההזחה הקיימת שכבר לפני העוגן (אין להוסיף עוד)
    buy_receipt_block = build_block_continue(buy_indent, BUY_RECEIPT_SET_LINES)
    new_buy_block = buy_receipt_block + buy_indent + BUY_SUCCESS_ANCHOR

    sell_receipt_block = build_block_continue(sell_indent, SELL_RECEIPT_SET_LINES)
    new_sell_block = sell_receipt_block + sell_indent + SELL_SUCCESS_ANCHOR

    new_text = text
    new_text = new_text.replace(HEADER_ANCHOR, new_header_block, 1)
    new_text = new_text.replace(COST_LINE_ANCHOR, new_confirm_block, 1)
    new_text = new_text.replace(BUY_SUCCESS_ANCHOR, new_buy_block, 1)
    new_text = new_text.replace(SELL_SUCCESS_ANCHOR, new_sell_block, 1)

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
    print("לבדוק ידנית: בצעי קנייה ומכירה בטאב מסחר, ותוודאי ש:")
    print("  1. לפני הביצוע מופיע כרטיס אישור מעוצב במקום שורת הטקסט הישנה")
    print("  2. אחרי הביצוע מופיע כרטיס קבלה בראש הטאב, עם כפתור ✕ לסגירה")
    print("  3. הכרטיס נשאר גם אחרי ריענון ידני של הדף, עד שסוגרים אותו")


if __name__ == "__main__":
    main()
