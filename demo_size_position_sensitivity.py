"""
דמו עצמאי - לא נוגע באפליקציה, רק מריץ את size_position() הקיים ב-options_engine.py
עם כמה תרחישים, כדי להראות מתי שינוי במגבלת הסיכון (1%-3%) באמת משנה את התוצאה.

שימוש (מתוך C:\\PhyCharm_projects\\Stock_tracking\\):
    C:\\PhyCharm_projects\\Stock_tracking\\.venv\\Scripts\\python.exe demo_size_position_sensitivity.py
"""
from options_engine import size_position, Position, Leg

PORTFOLIO = 25_000.0

# כל תרחיש: (תיאור, סטרייק, פרמיה)
SCENARIOS = [
    ("מניה יקרה - הדוגמה שבתמונה (סטרייק $200, פרמיה $3)", 200.0, 3.0),
    ("מניה זולה יותר (סטרייק $40, פרמיה $1)", 40.0, 1.0),
    ("מניה זולה מאוד, פרמיה נדיבה (סטרייק $25, פרמיה $1.5)", 25.0, 1.5),
    ("סטרייק בינוני (סטרייק $60, פרמיה $1.2)", 60.0, 1.2),
]

RISK_LEVELS = [0.01, 0.02, 0.03]  # 1%, 2%, 3%


def run_csp_scenarios():
    for label, strike, premium in SCENARIOS:
        template = Position(legs=[Leg("put", -1, 1, premium, strike, label="שורט פוט")])
        unit_risk = template.max_loss()
        print(f"\n{label}")
        print(f"  סיכון לחוזה בודד: ${unit_risk:,.2f}  |  תיק: ${PORTFOLIO:,.0f}")
        for pct in RISK_LEVELS:
            v = size_position(template=template, portfolio_usd=PORTFOLIO, max_risk_pct=pct, template_contracts=1)
            budget = PORTFOLIO * pct
            print(
                f"    {pct:.0%}: תקציב ${budget:,.0f} -> "
                f"{v.contracts} חוזים מאושרים, סיכון בפועל ${v.risk_usd:,.2f} ({v.risk_pct:.2%})"
            )


def run_csp_vs_spread_comparison():
    """
    למה CSP רגיל כמעט תמיד יוצא 0 חוזים בכלל ה-1%-3%, ולמה Bull Put Spread
    (אותה מניה, אותו סטרייק כתיבה) כן מגיב לשינוי - כי הסיכון שלו הרבה יותר
    קטן (רוחב המרווח פחות הפרמיה, לא הסטרייק המלא).
    """
    print("\n" + "=" * 70)
    print("השוואה: CSP מלא מול Bull Put Spread על אותה מניה (סטרייק $200)")
    print("=" * 70)

    csp = Position(legs=[Leg("put", -1, 1, 3.0, 200.0, label="שורט פוט")])
    print(f"\nCSP רגיל - סיכון לחוזה: ${csp.max_loss():,.2f}")
    for pct in RISK_LEVELS:
        v = size_position(template=csp, portfolio_usd=PORTFOLIO, max_risk_pct=pct)
        print(f"  {pct:.0%} (תקציב ${PORTFOLIO * pct:,.0f}): {v.contracts} חוזים")

    bps = Position(legs=[
        Leg("put", -1, 1, 3.0, 200.0, label="כתיבה"),
        Leg("put", +1, 1, 1.0, 195.0, label="הגנה"),
    ])
    print(f"\nBull Put Spread (הגנה ב-$195) - סיכון לחוזה: ${bps.max_loss():,.2f} "
          f"(קרדיט נטו: ${bps.net_cash:,.2f})")
    for pct in RISK_LEVELS:
        v = size_position(template=bps, portfolio_usd=PORTFOLIO, max_risk_pct=pct)
        print(f"  {pct:.0%} (תקציב ${PORTFOLIO * pct:,.0f}): {v.contracts} חוזים")


if __name__ == "__main__":
    run_csp_scenarios()
    run_csp_vs_spread_comparison()
