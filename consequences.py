"""
consequences.py - "מה יקרה אם אלחץ"

שכבת הסבר בשפה פשוטה לכרטיס האישור בטאב Paper Trading.
פונקציות טהורות בלבד: בלי Streamlit, בלי רשת. נבדק ב-test_consequences.py.

build_consequences()      -> מחשב מספרים ומשפטים
render_consequences_html() -> הופך אותם ל-HTML בעיצוב הכהה של האפליקציה

מספרים מוצגים LTR בשלוש שכבות (Streamlit מסיר את dir="ltr"):
CSS direction/unicode-bidi + תווי בידוד יוניקוד LRI/PDI (U+2066/U+2069).
"""
from dataclasses import dataclass, field
from html import escape

DEFAULT_SCENARIO_PCT = 0.10

_TONE_COLORS = {
    "pos": "#3fb950",
    "neg": "#f85149",
    "warn": "#d29922",
    "neutral": "#e6edf3",
}


@dataclass
class Consequences:
    action: str                      # "BUY" / "SELL"
    headline: str                    # משפט פתיחה
    lines: list = field(default_factory=list)  # [(label, value_str, tone)]


def _amount(x, cur):
    """סכום ללא סימן: $1,234.56"""
    return f"{cur}{abs(x):,.2f}"


def _signed(x, cur):
    """סכום עם סימן: +$1,234.56 / -$1,234.56"""
    return f"{'+' if x >= 0 else '-'}{cur}{abs(x):,.2f}"


def _shares_he(n):
    """1 -> 'מניה אחת', אחרת '{n} מניות'"""
    return "מניה אחת" if n == 1 else f"{n} מניות"


def build_consequences(action, symbol, shares, price,
                       held_shares=0, avg_price=None,
                       currency="$", scenario_pct=DEFAULT_SCENARIO_PCT):
    if action not in ("BUY", "SELL"):
        raise ValueError(f"action must be BUY or SELL, got {action!r}")
    if not shares or shares <= 0:
        raise ValueError("shares must be > 0")
    if price is None or price <= 0:
        raise ValueError("price must be > 0")

    pct_label = f"{round(scenario_pct * 100):g}%"
    cur = currency

    if action == "BUY":
        total = shares * price
        headline = (f"קונים {_shares_he(shares)} של {symbol} ב-{_amount(price, cur)}. "
                    f"יוצאים מהחשבון {_amount(total, cur)}.")
        lines = [
            (f"אם המניה עולה {pct_label}", _signed(total * scenario_pct, cur), "pos"),
            (f"אם המניה יורדת {pct_label}", _signed(-total * scenario_pct, cur), "neg"),
        ]
        return Consequences("BUY", headline, lines)

    # SELL
    held = held_shares or 0
    if held <= 0:
        return Consequences("SELL", f"אין אחזקה ב-{symbol}, אין מה למכור.",
                            [("שימו לב", "אין מניות למכירה", "warn")])

    lines = []
    qty = shares
    if shares > held:
        qty = held
        lines.append(("שימו לב",
                      f"ניסיון למכור {shares}, אבל יש רק {held}", "warn"))

    proceeds = qty * price
    headline = (f"מוכרים {_shares_he(qty)} של {symbol} ב-{_amount(price, cur)}. "
                f"נכנסים לחשבון {_amount(proceeds, cur)}.")

    if avg_price:
        realized = (price - avg_price) * qty
        lines.append(("רווח/הפסד ממומש", _signed(realized, cur),
                      "pos" if realized >= 0 else "neg"))

    move = proceeds * scenario_pct
    lines.append((f"אם תעלה עוד {pct_label} אחרי המכירה, רווח שלא יתקבל",
                  _amount(move, cur), "neutral"))
    lines.append((f"אם תרד {pct_label} אחרי המכירה, הפסד שנחסך",
                  _amount(move, cur), "neutral"))
    return Consequences("SELL", headline, lines)


def render_consequences_html(c):
    rows = "".join(
        f'<div style="display:flex;justify-content:space-between;gap:12px;'
        f'padding:3px 0;font-size:.8rem;">'
        f'<span style="color:#8b949e;">{escape(label)}</span>'
        f'<span dir="ltr" style="direction:ltr;unicode-bidi:isolate;'
        f'color:{_TONE_COLORS.get(tone, "#e6edf3")};'
        f'font-weight:700;font-family:\'JetBrains Mono\',monospace;">'
        f'\u2066{escape(value)}\u2069</span>'
        f'</div>'
        for label, value, tone in c.lines
    )
    return (
        f'<div style="background:#0d1117;border:1px dashed #30363d;border-radius:12px;'
        f'padding:10px 16px;margin:6px 0;direction:rtl;">'
        f'<div style="color:#8b949e;font-size:.62rem;text-transform:uppercase;">'
        f'מה יקרה אם אלחץ</div>'
        f'<div style="color:#e6edf3;font-size:.85rem;margin:4px 0 6px;">'
        f'{escape(c.headline)}</div>'
        f'{rows}'
        f'</div>'
    )
