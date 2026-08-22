# -*- coding: utf-8 -*-
"""
psych_journal.py

מודול היומן הפסיכולוגי — עוקב אחרי משמעת מסחר (האם עקבת אחרי תוכנית ה-ATR)
ורגש בזמן סגירת עסקה, ומחשב מדדי משמעת.

שימוש עצמאי (SQLite), לא נוגע ב-paper_portfolio.json הקיים — טבלה חדשה
לחלוטין, לפי ההחלטה שהתקבלה: JSON נשאר לפורטפוליו, SQLite רק למודולים
חדשים (פסיכולוגי, בעתיד גם התראות).

טבלה: trade_emotions
    id              INTEGER PRIMARY KEY AUTOINCREMENT
    trade_date      TEXT      (תואם לפורמט "%Y-%m-%d %H:%M" של trades ב-JSON)
    symbol          TEXT
    pnl             REAL      (רווח/הפסד בעסקת המכירה, $)
    followed_plan   INTEGER   (0/1)
    emotion         TEXT      (Calm / FOMO / Revenge Trading / Fear / Greed)
    logged_at       TEXT      (מתי נרשמה השורה, ISO timestamp)
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DB_FILE = "trading_journal.db"

# רגשות חוקיים — נשמרים באנגלית ב-DB (יציב, לא תלוי שפת UI),
# מוצגים בעברית בשכבת התצוגה (ב-alpha_paper_trading.py / rr_tab.py).
VALID_EMOTIONS = ("Calm", "FOMO", "Revenge Trading", "Fear", "Greed")

# רגשות ש"לא רגועים" — עסקה שנסגרה בהפסד תחת אחד מהם, או בלי לעקוב
# אחרי התוכנית, נספרת כ"הפסד רגשי" בחישוב המצטבר.
_NON_CALM_EMOTIONS = tuple(e for e in VALID_EMOTIONS if e != "Calm")


@dataclass
class DisciplineMetrics:
    total_trades: int
    discipline_score_pct: float | None  # None אם אין עדיין עסקאות
    total_emotional_loss_cost: float
    emotional_loss_trade_count: int
    emotion_breakdown: dict[str, int]


def initialize_application_database(db_path: str | Path = DB_FILE) -> None:
    """
    יוצר את קובץ ה-DB והטבלה אם עדיין לא קיימים. אידמפוטנטי — בטוח
    להריץ בכל עליית אפליקציה.
    """
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_emotions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date    TEXT NOT NULL,
                symbol        TEXT NOT NULL,
                pnl           REAL NOT NULL,
                followed_plan INTEGER NOT NULL CHECK (followed_plan IN (0, 1)),
                emotion       TEXT NOT NULL,
                logged_at     TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trade_emotions_date "
            "ON trade_emotions (trade_date, symbol)"
        )
        conn.commit()


def log_trade_psychology(
    trade_date: str,
    symbol: str,
    pnl: float,
    followed_plan: bool,
    emotion: str,
    db_path: str | Path = DB_FILE,
) -> None:
    """
    רושם שורה אחת ליומן הפסיכולוגי, בהתאמה לעסקת SELL שנסגרה זה עתה.
    קוראים לזה בדיוק פעם אחת לכל עסקת סגירה, מיד אחרי שהיא נשמרת
    ב-pf['trades'] (paper_portfolio.json).
    """
    if emotion not in VALID_EMOTIONS:
        raise ValueError(
            f"רגש לא חוקי: {emotion!r}. חוקיים: {', '.join(VALID_EMOTIONS)}"
        )
    if not symbol or not str(symbol).strip():
        raise ValueError("symbol לא יכול להיות ריק")

    initialize_application_database(db_path)  # הגנה: אם מישהו קורא לפני init
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO trade_emotions
                (trade_date, symbol, pnl, followed_plan, emotion, logged_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                trade_date,
                symbol.strip().upper(),
                float(pnl),
                1 if followed_plan else 0,
                emotion,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def calculate_trader_discipline_metrics(
    db_path: str | Path = DB_FILE,
) -> DisciplineMetrics:
    """
    מחשב את מדדי המשמעת המצטברים על כל ההיסטוריה ביומן הפסיכולוגי.

    discipline_score_pct = אחוז העסקאות שבהן followed_plan=1
    total_emotional_loss_cost = סכום ה-|הפסד| בעסקאות מפסידות שבהן
        לא עקבו אחרי התוכנית, או שהרגש לא היה "רוגע" — ההנחה היא
        שהפסדים בתנאים האלה "ניתנים למניעה" ברמה גבוהה יותר מהפסד
        רגיל שהתוכנית עצמה חזתה.
    """
    initialize_application_database(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT pnl, followed_plan, emotion FROM trade_emotions"
        ).fetchall()

    total = len(rows)
    if total == 0:
        return DisciplineMetrics(
            total_trades=0,
            discipline_score_pct=None,
            total_emotional_loss_cost=0.0,
            emotional_loss_trade_count=0,
            emotion_breakdown={e: 0 for e in VALID_EMOTIONS},
        )

    followed_count = sum(1 for r in rows if r["followed_plan"] == 1)
    discipline_pct = round(followed_count / total * 100, 1)

    emotional_loss_total = 0.0
    emotional_loss_trades = 0
    breakdown = {e: 0 for e in VALID_EMOTIONS}
    for r in rows:
        breakdown[r["emotion"]] = breakdown.get(r["emotion"], 0) + 1
        is_undisciplined = (r["followed_plan"] == 0) or (r["emotion"] in _NON_CALM_EMOTIONS)
        if is_undisciplined and r["pnl"] < 0:
            emotional_loss_total += abs(r["pnl"])
            emotional_loss_trades += 1

    return DisciplineMetrics(
        total_trades=total,
        discipline_score_pct=discipline_pct,
        total_emotional_loss_cost=round(emotional_loss_total, 2),
        emotional_loss_trade_count=emotional_loss_trades,
        emotion_breakdown=breakdown,
    )


@contextmanager
def _connect(db_path: str | Path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
