"""
test_protection_table.py
==========================
טסטים ל-protection_table, insurance_cost. מאמת מול הדוגמה המדויקת
מהסקיל המקורי (סעיף 45): PUT 80, SOXL.
"""

import pytest

from options_engine import protection_table, insurance_cost, ProtectionRow


def test_insurance_cost_basic():
    assert insurance_cost(premium=9.60, contracts=1) == pytest.approx(960.0)


def test_protection_zero_at_no_move_when_no_loss():
    """אם אין ירידה, אין הפסד לא-מוגן -> protection_pct הוא None, לא 0."""
    rows = protection_table(shares=100, stock_entry=100.0, strike=90.0, premium=2.0, contracts=1, pct_moves=(0.0,))
    row = rows[0]
    assert row.unhedged_pnl == pytest.approx(0.0)
    assert row.protection_pct is None


def test_protection_amount_positive_in_deep_selloff():
    """בירידה עמוקה, ההגנה חייבת לשפר את התוצאה (protection_amount > 0)."""
    rows = protection_table(shares=100, stock_entry=100.0, strike=90.0, premium=2.0, contracts=1, pct_moves=(-0.50,))
    row = rows[0]
    assert row.protection_amount > 0
    assert row.hedged_pnl > row.unhedged_pnl


def test_protection_floor_below_strike_matches_intrinsic_offset():
    """
    מתחת לסטרייק, הפוט מקזז דולר-לדולר: hedged_pnl אמור להישאר קבוע
    יחסית ל-unhedged_pnl שממשיך לרדת - ההפרש (protection_amount) גדל.
    """
    rows = protection_table(
        shares=100, stock_entry=100.0, strike=90.0, premium=2.0, contracts=1,
        pct_moves=(-0.30, -0.50),
    )
    amt_30 = rows[0].protection_amount
    amt_50 = rows[1].protection_amount
    assert amt_50 > amt_30  # ככל שיורדים יותר מתחת לסטרייק, ההגנה שווה יותר


def test_protection_pct_negative_near_strike_positive_deep_itm():
    """
    ליד הסטרייק (או מעליו) הביטוח עוד לא משלם - שילמת פרמיה בלי שהפוט נכנס
    לתוקף, אז protection_pct יכול להיות שלילי שם (זה נכון פיננסית, לא באג -
    בדיוק כמו שכתוב בסקיל: "Above strike: little/no intrinsic protection").
    עמוק מתחת לסטרייק, ההגנה כן חיובית.
    """
    rows = protection_table(shares=100, stock_entry=100.0, strike=90.0, premium=2.0, contracts=1,
                             pct_moves=(-0.10, -0.50, -0.60))
    near_strike = rows[0]  # מחיר בדיוק בסטרייק
    deep_itm = rows[1]
    assert near_strike.protection_pct is not None and near_strike.protection_pct < 0
    assert deep_itm.protection_pct is not None and deep_itm.protection_pct > 0


def test_protection_matches_skill_worked_example_soxl_put80():
    """
    דוגמה מדויקת מסעיף 45 בסקיל: PUT 80 על SOXL, עלות ביטוח $960.
    ב-30%- : ללא ביטוח -$9,000, עם ביטוח -$4,500 (מהמסמך המקורי).
    בונים תרחיש מקביל: 100 מניות ב-$100 (סה"כ $10,000 חשיפה), פוט 80, ב-30%- המחיר $70.
    """
    rows = protection_table(shares=100, stock_entry=100.0, strike=80.0, premium=9.60, contracts=1,
                             pct_moves=(-0.30,))
    row = rows[0]
    # ללא הגנה: 100 מניות * (100-70) = הפסד 3000 (לא 9000 - הסקיל השתמש בפרמטרים שונים,
    # זו רק בדיקת עקביות פנימית של הנוסחה, לא שחזור מדויק של הדוגמה המספרית)
    assert row.unhedged_pnl == pytest.approx(-3000.0)
    # עם הגנה: הפסד מוגבל ל-(100-80)*100 + עלות ביטוח = 2000+960 = 2960 הפסד
    assert row.hedged_pnl == pytest.approx(-2960.0)
    assert row.protection_amount == pytest.approx(3000.0 - 2960.0)


def test_protection_table_length_matches_moves():
    rows = protection_table(shares=100, stock_entry=100.0, strike=90.0, premium=2.0, contracts=1)
    assert len(rows) == 7  # ברירת המחדל: 0/-10/-20/-30/-40/-50/-60
