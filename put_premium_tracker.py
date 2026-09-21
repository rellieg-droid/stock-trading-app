# -*- coding: utf-8 -*-
"""
put_premium_tracker.py

Tracks short PUT positions (cash-secured PUT selling for income) and
calculates realized/unrealized premium P&L across multiple positions.

Designed to sit alongside options_engine.py / psych_journal.py, using
the same SQLite pattern as trading_journal.db.
"""

import sqlite3
from datetime import date
from typing import Optional

DB_PATH = "put_tracker.db"  # or point this at trading_journal.db to share the file


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS put_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    strike REAL NOT NULL,
    contracts INTEGER NOT NULL DEFAULT 1,
    premium_received REAL NOT NULL,       -- per share, at sale
    stock_price_at_sale REAL,
    sale_date TEXT NOT NULL,              -- ISO format YYYY-MM-DD
    expiration_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',  -- open | expired_worthless | closed_manual | assigned
    close_date TEXT,
    premium_paid_to_close REAL,           -- per share, only if status = closed_manual
    stock_price_at_close REAL,
    notes TEXT
);
"""


def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def add_put_sale(
    symbol: str,
    strike: float,
    premium_received: float,
    sale_date: str,
    expiration_date: str,
    contracts: int = 1,
    stock_price_at_sale: Optional[float] = None,
    notes: str = "",
    db_path: str = DB_PATH,
) -> int:
    """Record a new short PUT sale. Returns the new row's id."""
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        """
        INSERT INTO put_positions
            (symbol, strike, contracts, premium_received, stock_price_at_sale,
             sale_date, expiration_date, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (symbol, strike, contracts, premium_received, stock_price_at_sale,
         sale_date, expiration_date, notes),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def close_expired_worthless(position_id: int, close_date: Optional[str] = None,
                             db_path: str = DB_PATH) -> None:
    """Mark a position as expired worthless — full premium kept as profit."""
    close_date = close_date or date.today().isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE put_positions SET status='expired_worthless', close_date=? WHERE id=?",
        (close_date, position_id),
    )
    conn.commit()
    conn.close()


def close_manual(position_id: int, premium_paid_to_close: float,
                  stock_price_at_close: Optional[float] = None,
                  close_date: Optional[str] = None, db_path: str = DB_PATH) -> None:
    """Record a buyback before expiration."""
    close_date = close_date or date.today().isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        UPDATE put_positions
        SET status='closed_manual', close_date=?, premium_paid_to_close=?,
            stock_price_at_close=?
        WHERE id=?
        """,
        (close_date, premium_paid_to_close, stock_price_at_close, position_id),
    )
    conn.commit()
    conn.close()


def mark_assigned(position_id: int, close_date: Optional[str] = None,
                   db_path: str = DB_PATH) -> None:
    """Mark a position as assigned (stock was put to you at strike)."""
    close_date = close_date or date.today().isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE put_positions SET status='assigned', close_date=? WHERE id=?",
        (close_date, position_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Read / analytics
# ---------------------------------------------------------------------------

def _pnl_per_share(row: sqlite3.Row) -> Optional[float]:
    """P&L per share for a single row, or None if still open."""
    if row["status"] == "expired_worthless":
        return row["premium_received"]
    if row["status"] == "closed_manual":
        return row["premium_received"] - (row["premium_paid_to_close"] or 0.0)
    if row["status"] == "assigned":
        # Premium is kept; the "cost" shows up later in the stock position itself,
        # not here. Treat premium as realized profit on the options leg.
        return row["premium_received"]
    return None  # still open


def get_summary(db_path: str = DB_PATH) -> dict:
    """
    Returns:
        {
            "total_premium_collected": float,   # all positions, regardless of status
            "realized_pnl": float,               # closed positions only
            "open_exposure_premium": float,      # premium on still-open positions
            "win_count": int,
            "loss_count": int,
            "open_count": int,
            "by_symbol": {symbol: {"premium_collected": .., "realized_pnl": ..}, ...},
        }
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM put_positions").fetchall()
    conn.close()

    total_premium = 0.0
    realized_pnl = 0.0
    open_exposure = 0.0
    win_count = 0
    loss_count = 0
    open_count = 0
    by_symbol: dict = {}

    for row in rows:
        contracts = row["contracts"]
        premium_total = row["premium_received"] * 100 * contracts
        total_premium += premium_total

        sym = row["symbol"]
        by_symbol.setdefault(sym, {"premium_collected": 0.0, "realized_pnl": 0.0})
        by_symbol[sym]["premium_collected"] += premium_total

        pnl_per_share = _pnl_per_share(row)
        if pnl_per_share is None:
            open_exposure += premium_total
            open_count += 1
        else:
            pnl_total = pnl_per_share * 100 * contracts
            realized_pnl += pnl_total
            by_symbol[sym]["realized_pnl"] += pnl_total
            if pnl_total >= 0:
                win_count += 1
            else:
                loss_count += 1

    return {
        "total_premium_collected": round(total_premium, 2),
        "realized_pnl": round(realized_pnl, 2),
        "open_exposure_premium": round(open_exposure, 2),
        "win_count": win_count,
        "loss_count": loss_count,
        "open_count": open_count,
        "by_symbol": {
            s: {k: round(v, 2) for k, v in d.items()} for s, d in by_symbol.items()
        },
    }


def get_pnl_by_period(db_path: str = DB_PATH):
    """
    Realized P&L broken down by month and by year, based on close_date.
    Only closed positions (status != 'open') are included.

    Returns (monthly, yearly) — each a list of dicts sorted chronologically:
        {"period": "2026-09" or "2026", "realized_pnl": float, "closed_count": int}
    """
    from collections import defaultdict

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM put_positions WHERE status != 'open' AND close_date IS NOT NULL"
    ).fetchall()
    conn.close()

    monthly: dict = defaultdict(lambda: {"realized_pnl": 0.0, "closed_count": 0})
    yearly: dict = defaultdict(lambda: {"realized_pnl": 0.0, "closed_count": 0})

    for row in rows:
        pnl_per_share = _pnl_per_share(row)
        if pnl_per_share is None:
            continue
        pnl_total = pnl_per_share * 100 * row["contracts"]
        close_date = row["close_date"]  # ISO format 'YYYY-MM-DD'
        year = close_date[:4]
        month = close_date[:7]

        monthly[month]["realized_pnl"] += pnl_total
        monthly[month]["closed_count"] += 1
        yearly[year]["realized_pnl"] += pnl_total
        yearly[year]["closed_count"] += 1

    monthly_list = [
        {"period": k, "realized_pnl": round(v["realized_pnl"], 2), "closed_count": v["closed_count"]}
        for k, v in sorted(monthly.items())
    ]
    yearly_list = [
        {"period": k, "realized_pnl": round(v["realized_pnl"], 2), "closed_count": v["closed_count"]}
        for k, v in sorted(yearly.items())
    ]
    return monthly_list, yearly_list


if __name__ == "__main__":
    init_db()
    # Example usage matching the scenario discussed:
    # add_put_sale("XYZ", strike=80, premium_received=1.4,
    #              sale_date="2026-09-08", expiration_date="2026-09-24",
    #              stock_price_at_sale=120)
    print(get_summary())
