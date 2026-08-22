# -*- coding: utf-8 -*-
"""
test_psych_journal.py

בדיקות ל-psych_journal.py. כל טסט משתמש ב-DB זמני נפרד (tmp_path),
כדי לא לגעת ב-trading_journal.db האמיתי.

הרצה: pytest test_psych_journal.py -v
"""

import sqlite3

import pytest

import psych_journal as pj


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_journal.db"


def test_initialize_creates_table(db_path):
    pj.initialize_application_database(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    assert ("trade_emotions",) in tables


def test_initialize_is_idempotent(db_path):
    pj.initialize_application_database(db_path)
    pj.initialize_application_database(db_path)  # לא אמור להתפוצץ
    pj.log_trade_psychology("2026-08-22 10:00", "AAPL", 50.0, True, "Calm", db_path)
    metrics = pj.calculate_trader_discipline_metrics(db_path)
    assert metrics.total_trades == 1


def test_log_trade_psychology_rejects_invalid_emotion(db_path):
    with pytest.raises(ValueError):
        pj.log_trade_psychology(
            "2026-08-22 10:00", "AAPL", -30.0, False, "Boredom", db_path
        )


def test_log_trade_psychology_rejects_empty_symbol(db_path):
    with pytest.raises(ValueError):
        pj.log_trade_psychology("2026-08-22 10:00", "  ", -30.0, False, "Fear", db_path)


def test_metrics_empty_db_returns_none_score(db_path):
    pj.initialize_application_database(db_path)
    metrics = pj.calculate_trader_discipline_metrics(db_path)
    assert metrics.total_trades == 0
    assert metrics.discipline_score_pct is None
    assert metrics.total_emotional_loss_cost == 0.0


def test_discipline_score_all_followed(db_path):
    pj.log_trade_psychology("2026-08-20 10:00", "AAPL", 100.0, True, "Calm", db_path)
    pj.log_trade_psychology("2026-08-21 10:00", "NVDA", -20.0, True, "Calm", db_path)
    metrics = pj.calculate_trader_discipline_metrics(db_path)
    assert metrics.total_trades == 2
    assert metrics.discipline_score_pct == 100.0
    # שני הפוזיציות עקבו אחרי התוכנית וברוגע — אין הפסד "רגשי"
    assert metrics.total_emotional_loss_cost == 0.0


def test_discipline_score_mixed(db_path):
    pj.log_trade_psychology("2026-08-20 10:00", "AAPL", 100.0, True, "Calm", db_path)
    pj.log_trade_psychology("2026-08-21 10:00", "NVDA", -50.0, False, "FOMO", db_path)
    pj.log_trade_psychology("2026-08-22 10:00", "TSLA", -30.0, False, "Revenge Trading", db_path)
    metrics = pj.calculate_trader_discipline_metrics(db_path)
    assert metrics.total_trades == 3
    assert metrics.discipline_score_pct == pytest.approx(33.3, abs=0.1)
    # שתי עסקאות מפסידות + לא עקבו אחרי התוכנית -> שתיהן "הפסד רגשי"
    assert metrics.total_emotional_loss_cost == 80.0
    assert metrics.emotional_loss_trade_count == 2


def test_winning_trade_with_bad_emotion_not_counted_as_loss(db_path):
    # עקבו אחרי התוכנית אבל היו ב-FOMO, ובכל זאת הרוויחו -> לא נכנס
    # ל"הפסד רגשי" כי pnl לא שלילי, גם אם ההתנהגות לא הייתה אידיאלית
    pj.log_trade_psychology("2026-08-20 10:00", "AAPL", 40.0, True, "FOMO", db_path)
    metrics = pj.calculate_trader_discipline_metrics(db_path)
    assert metrics.total_emotional_loss_cost == 0.0


def test_followed_plan_but_calm_loss_not_counted_as_emotional(db_path):
    # עקבו אחרי התוכנית, רוגעים, אבל עדיין הפסידו (סטופ נורמלי) ->
    # זה הפסד "מתוכנן", לא רגשי
    pj.log_trade_psychology("2026-08-20 10:00", "AAPL", -25.0, True, "Calm", db_path)
    metrics = pj.calculate_trader_discipline_metrics(db_path)
    assert metrics.total_emotional_loss_cost == 0.0
    assert metrics.emotional_loss_trade_count == 0


def test_emotion_breakdown_counts_all_emotions(db_path):
    pj.log_trade_psychology("2026-08-20 10:00", "AAPL", 10.0, True, "Calm", db_path)
    pj.log_trade_psychology("2026-08-21 10:00", "NVDA", -10.0, False, "Fear", db_path)
    pj.log_trade_psychology("2026-08-22 10:00", "TSLA", -10.0, False, "Fear", db_path)
    metrics = pj.calculate_trader_discipline_metrics(db_path)
    assert metrics.emotion_breakdown["Calm"] == 1
    assert metrics.emotion_breakdown["Fear"] == 2
    assert metrics.emotion_breakdown["FOMO"] == 0


def test_symbol_is_normalized_uppercase(db_path):
    pj.log_trade_psychology("2026-08-20 10:00", "aapl", 10.0, True, "Calm", db_path)
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT symbol FROM trade_emotions").fetchone()
    assert row[0] == "AAPL"
