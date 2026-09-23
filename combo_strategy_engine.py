"""
combo_strategy_engine.py

Core calculation engine for the "Combo Strategies" tab (אסטרטגיות משולבות).

Implements the risk-reversal / financed bull-call-spread strategy discussed
for SOXL:
    - Buy 1x CALL near the money (the "anchor")
    - Sell 1x CALL further out-of-the-money, ideally at ~half the anchor's
      premium
    - Sell N puts (default 2) below the market, chosen so that
      N * put_premium is close to the net cost of the call spread

This module has no Streamlit dependency so it can be unit tested and
reused independently of the UI. See test_combo_strategy_engine.py.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional

import pandas as pd
import yfinance as yf

# Leg/Position/entry_order כבר בנויים ונבדקים ב-RiskShield — לא משוכפלים כאן.
# ראו options_engine.py: "3. מודל הרגליים" ו-entry_order().
from options_engine import Leg, Position, entry_order


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def get_current_price(ticker: str) -> float:
    """Return the latest available price for a ticker via yfinance."""
    t = yf.Ticker(ticker)
    price = None
    try:
        price = t.fast_info.get("last_price")
    except Exception:
        pass
    if price:
        return float(price)
    hist = t.history(period="1d")
    if hist.empty:
        raise ValueError(f"לא נמצא מחיר עבור {ticker}")
    return float(hist["Close"].iloc[-1])


_TICKER_NAME_CACHE: dict[str, str] = {}  # TICKER_NAME_FALLBACK_V1 - רק הצלחות נשמרות


def _ticker_name_via_search(ticker: str) -> Optional[str]:
    """גיבוי: API החיפוש של Yahoo, לא דורש crumb. מחזיר שם רק להתאמה מדויקת של הסימבול."""
    try:
        import requests
        r = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": ticker, "quotesCount": 6, "newsCount": 0, "listsCount": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=6,
        )
        if r.status_code != 200:
            return None
        for q in r.json().get("quotes", []):
            if str(q.get("symbol", "")).upper() == ticker.upper():
                return q.get("shortname") or q.get("longname")
    except Exception:
        return None
    return None


def get_ticker_name(ticker: str) -> Optional[str]:
    """Best-effort company/fund name for a ticker, so the UI can confirm the symbol is right."""
    key = (ticker or "").upper().strip()
    if not key:
        return None
    if key in _TICKER_NAME_CACHE:
        return _TICKER_NAME_CACHE[key]
    name = None
    try:
        info = yf.Ticker(key).info
        name = info.get("shortName") or info.get("longName")
    except Exception:
        name = None
    if not name:
        name = _ticker_name_via_search(key)
    if name:
        _TICKER_NAME_CACHE[key] = name
    return name


def list_available_expirations(ticker: str) -> list[str]:
    return list(yf.Ticker(ticker).options)


def fetch_option_chain(ticker: str, expiration: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch the calls and puts chain for one expiration date.
    expiration format: 'YYYY-MM-DD', must be one of ticker.options.
    """
    t = yf.Ticker(ticker)
    if expiration not in t.options:
        raise ValueError(
            f"{expiration} אינו תאריך פקיעה זמין. תאריכים זמינים: {t.options}"
        )
    chain = t.option_chain(expiration)
    return chain.calls, chain.puts


# ---------------------------------------------------------------------------
# Strategy detection
# ---------------------------------------------------------------------------

@dataclass
class ComboCandidate:
    ticker: str
    expiration: str
    spot_price: float
    anchor_call_strike: float
    anchor_call_premium: float
    second_call_strike: float
    second_call_premium: float
    put_strike: float
    put_premium: float
    num_puts: int
    net_cost: float          # per-share equivalent; positive = net debit, negative = net credit
    call_spread_width: float

    def to_position(self) -> Position:
        """Build the options_engine.Position for this candidate (3 legs)."""
        return bull_call_spread_financed_by_puts(
            contracts=1,
            long_call=self.anchor_call_strike, long_call_prem=self.anchor_call_premium,
            short_call=self.second_call_strike, short_call_prem=self.second_call_premium,
            put_strike=self.put_strike, put_prem=self.put_premium,
            put_contracts=self.num_puts,
        )


def bull_call_spread_financed_by_puts(
    contracts: int,
    long_call: float, long_call_prem: float,
    short_call: float, short_call_prem: float,
    put_strike: float, put_prem: float,
    put_contracts: int,
) -> Position:
    """
    מרווח קולים בחיוב (קנייה בסטרייק נמוך, כתיבה בסטרייק גבוה), ממומן חלקית
    או במלואו ע"י כתיבת פוטים נוספים בסטרייק נמוך יותר.

    בשונה מ-bull_put_spread או iron_condor שב-options_engine.py, כאן הסיכון
    כלפי מטה אינו מוגדר-מראש: הפוטים חשופים עד למחיר 0, לא רק עד לרוחב
    מרווח קבוע. Position.max_loss() עדיין מחזיר מספר סופי (לא inf) כי המניה
    לא יכולה לרדת מתחת ל-0, אבל המספר הזה יכול להיות גדול משמעותית מהפרמיה
    שהתקבלה.
    """
    if not (long_call < short_call):
        raise ValueError(f"long_call must be below short_call, got {long_call}, {short_call}")
    if not (put_strike < long_call):
        raise ValueError(f"put_strike should sit below long_call, got {put_strike}, {long_call}")
    return Position(
        name="Bull Call Spread Financed by Puts",
        legs=[
            Leg("call", +1, contracts, long_call_prem, long_call, label="לונג"),
            Leg("call", -1, contracts, short_call_prem, short_call, label="מימון חלקי"),
            Leg("put", -1, put_contracts, put_prem, put_strike, label="מימון עיקרי"),
        ],
    )


def suggested_entry_order(candidate: ComboCandidate) -> list[Leg]:
    """Broker-safe entry order (longs before shorts) via options_engine.entry_order."""
    return entry_order(candidate.to_position())


def _premium_mid(row: pd.Series) -> float:
    """Prefer the mid of bid/ask; fall back to lastPrice if bid/ask are missing or zero."""
    bid = row.get("bid", 0) or 0
    ask = row.get("ask", 0) or 0
    if bid > 0 and ask > 0:
        return round((bid + ask) / 2, 4)
    return float(row.get("lastPrice", 0) or 0)


def find_candidates(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot_price: float,
    ticker: str,
    expiration: str,
    ratio_target: float = 0.5,
    ratio_tolerance: float = 0.20,
    num_puts: int = 2,
    top_n: int = 3,
) -> list[ComboCandidate]:
    """
    Scan the chain for combos matching the pattern:
      anchor call (closest strike to spot) -> second call whose premium is
      close to ratio_target of the anchor's premium -> put whose
      (num_puts * premium) is closest to the resulting call-spread net debit.

    Returns up to top_n candidates, ranked by |net_cost| ascending
    (closest to a net-zero entry first).
    """
    calls = calls.copy()
    puts = puts.copy()
    calls["mid"] = calls.apply(_premium_mid, axis=1)
    puts["mid"] = puts.apply(_premium_mid, axis=1)
    calls = calls[calls["mid"] > 0].sort_values("strike")
    puts = puts[puts["mid"] > 0].sort_values("strike")

    if calls.empty or puts.empty:
        return []

    calls["dist_to_spot"] = (calls["strike"] - spot_price).abs()
    anchor_row = calls.loc[calls["dist_to_spot"].idxmin()]
    anchor_strike = float(anchor_row["strike"])
    anchor_premium = float(anchor_row["mid"])

    higher_calls = calls[calls["strike"] > anchor_strike].copy()
    if higher_calls.empty:
        return []

    target_premium = anchor_premium * ratio_target
    higher_calls["ratio_diff"] = (higher_calls["mid"] - target_premium).abs()
    in_tolerance = higher_calls[
        higher_calls["mid"].between(
            target_premium * (1 - ratio_tolerance), target_premium * (1 + ratio_tolerance)
        )
    ]
    # if nothing falls inside the tolerance band, fall back to the closest few
    # rather than returning an empty scan
    candidates_calls = in_tolerance if not in_tolerance.empty else higher_calls.nsmallest(3, "ratio_diff")

    lower_puts_base = puts[puts["strike"] < spot_price].copy()

    candidates: list[ComboCandidate] = []
    for _, call2_row in candidates_calls.iterrows():
        second_strike = float(call2_row["strike"])
        second_premium = float(call2_row["mid"])
        net_call_debit = anchor_premium - second_premium
        if net_call_debit <= 0:
            continue  # not a genuine debit spread, skip

        if lower_puts_base.empty:
            continue
        lower_puts = lower_puts_base.copy()
        lower_puts["total_credit"] = lower_puts["mid"] * num_puts
        lower_puts["net_diff"] = (lower_puts["total_credit"] - net_call_debit).abs()
        best_put = lower_puts.loc[lower_puts["net_diff"].idxmin()]

        put_strike = float(best_put["strike"])
        put_premium = float(best_put["mid"])
        net_cost = net_call_debit - (put_premium * num_puts)

        candidates.append(
            ComboCandidate(
                ticker=ticker,
                expiration=expiration,
                spot_price=spot_price,
                anchor_call_strike=anchor_strike,
                anchor_call_premium=anchor_premium,
                second_call_strike=second_strike,
                second_call_premium=second_premium,
                put_strike=put_strike,
                put_premium=put_premium,
                num_puts=num_puts,
                net_cost=round(net_cost, 4),
                call_spread_width=second_strike - anchor_strike,
            )
        )

    candidates.sort(key=lambda c: abs(c.net_cost))
    return candidates[:top_n]


# ---------------------------------------------------------------------------
# Payoff calculations
# ---------------------------------------------------------------------------

def compute_payoff_table(candidate: ComboCandidate, price_points: Optional[list[float]] = None) -> pd.DataFrame:
    """Return a DataFrame of price -> P&L ($) at expiration, via Position.payoff_curve()."""
    position = candidate.to_position()

    if price_points is None:
        lo = max(0.0, candidate.put_strike * 0.3)
        hi = candidate.second_call_strike * 1.3
        spots, pnls = position.payoff_curve(lo, hi, points=80)
        return pd.DataFrame({"price": spots, "pnl": pnls})

    rows = [{"price": s, "pnl": position.payoff_at(s)} for s in price_points]
    return pd.DataFrame(rows)


def key_figures(candidate: ComboCandidate) -> dict:
    """Headline numbers via Position: net cost, max profit, max loss at 0, breakeven(s)."""
    position = candidate.to_position()
    breakevens = position.breakevens()
    return {
        "net_cost_dollars": round(-position.net_cash, 2),  # net_cash: +credit/-debit; net_cost is the mirror
        "max_profit": round(position.max_profit(), 2),
        "max_loss_at_zero": round(-position.max_loss(), 2),
        "breakeven_low": round(min(breakevens), 2) if breakevens else None,
        "breakevens": [round(b, 2) for b in breakevens],
    }


# ---------------------------------------------------------------------------
# Margin estimates (rough — actual figures depend on the broker)
# ---------------------------------------------------------------------------

def margin_estimates(candidate: ComboCandidate) -> dict:
    """
    cash_secured: cash needed to fully guarantee the put obligation on its own.
    reg_t_estimate: standard US Reg-T naked-put formula (greater of the two
                     legs), times num_puts. Brokers differ — treat as a
                     starting point, not a quote.
    """
    strike = candidate.put_strike
    premium = candidate.put_premium
    spot = candidate.spot_price
    num_puts = candidate.num_puts

    cash_secured = strike * 100 * num_puts - premium * 100 * num_puts

    otm_amount = max(0.0, spot - strike)
    formula_a = (0.20 * spot * 100) - (otm_amount * 100) + (premium * 100)
    formula_b = (0.10 * strike * 100) + (premium * 100)
    per_contract = max(formula_a, formula_b, 0.0)
    reg_t_estimate = per_contract * num_puts

    return {
        "cash_secured": round(cash_secured, 2),
        "reg_t_estimate": round(reg_t_estimate, 2),
    }


def get_entry_margins(entry: dict) -> dict:
    """
    Margin figures for a saved watchlist entry: {'cash_secured', 'reg_t_estimate'}.

    Uses the stored values when present (fast path, set by add_position()).
    Entries saved before margin storage was added lack those fields — for
    those, rebuild the ComboCandidate from the entry's own strikes/premiums
    (always present since the first version) and recompute on the fly, so
    old watchlist entries show correct numbers without needing to be
    deleted and re-added.
    """
    if entry.get("margin_reg_t") is not None and entry.get("margin_cash_secured") is not None:
        return {"cash_secured": entry["margin_cash_secured"], "reg_t_estimate": entry["margin_reg_t"]}
    candidate = ComboCandidate(
        ticker=entry["ticker"], expiration=entry["expiration"], spot_price=entry["spot_price"],
        anchor_call_strike=entry["anchor_call_strike"], anchor_call_premium=entry["anchor_call_premium"],
        second_call_strike=entry["second_call_strike"], second_call_premium=entry["second_call_premium"],
        put_strike=entry["put_strike"], put_premium=entry["put_premium"], num_puts=entry["num_puts"],
        net_cost=entry["net_cost"], call_spread_width=entry["call_spread_width"],
    )
    return margin_estimates(candidate)


# ---------------------------------------------------------------------------
# Watchlist persistence
# ---------------------------------------------------------------------------

WATCHLIST_PATH = "combo_strategies.json"


def load_watchlist(path: str = WATCHLIST_PATH) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_watchlist(data: list[dict], path: str = WATCHLIST_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def price_for_pnl_threshold(candidate: ComboCandidate, threshold_dollars: float) -> Optional[float]:
    """
    Reference price (AT EXPIRATION) where this position's payoff first crosses
    threshold_dollars, scanning from high price down to 0.

    This is informational only — it's read off the same expiration payoff curve
    as key_figures()/compute_payoff_table(), so it does NOT account for time
    value. If you plan to close before expiration (as opposed to holding to
    assignment), the real trigger price will typically arrive sooner than this,
    especially with elevated IV. Use the live mtm_pnl_dollars from
    refresh_position() as the accurate, real-time check — this is just a
    ballpark you can watch without opening the app.
    """
    kinks = sorted({0.0, candidate.put_strike, candidate.anchor_call_strike, candidate.second_call_strike})
    points = kinks + [kinks[-1] * 3 + 1]
    position = candidate.to_position()
    for a, b in zip(points, points[1:]):
        fa, fb = position.payoff_at(a), position.payoff_at(b)
        if fa == threshold_dollars:
            return round(a, 2)
        if (fa - threshold_dollars) * (fb - threshold_dollars) < 0:
            return round(a + (b - a) * (threshold_dollars - fa) / (fb - fa), 2)
    return None


def add_position(
    candidate: ComboCandidate, note: str = "", alert_threshold: Optional[float] = None,
    available_capital: Optional[float] = None, path: str = WATCHLIST_PATH,
) -> None:
    data = load_watchlist(path)
    entry = asdict(candidate)
    entry["entry_date"] = date.today().isoformat()
    entry["note"] = note
    entry["alert_threshold"] = alert_threshold
    if alert_threshold is not None:
        entry["alert_reference_price"] = price_for_pnl_threshold(candidate, alert_threshold)

    margins = margin_estimates(candidate)
    entry["margin_cash_secured"] = margins["cash_secured"]
    entry["margin_reg_t"] = margins["reg_t_estimate"]
    entry["available_capital"] = available_capital
    if available_capital:
        entry["margin_pct_cash_secured"] = round(margins["cash_secured"] / available_capital * 100, 1)
        entry["margin_pct_reg_t"] = round(margins["reg_t_estimate"] / available_capital * 100, 1)

    data.append(entry)
    save_watchlist(data, path)


def remove_position(index: int, path: str = WATCHLIST_PATH) -> None:
    data = load_watchlist(path)
    if 0 <= index < len(data):
        data.pop(index)
        save_watchlist(data, path)


def premium_for_strike(chain: pd.DataFrame, strike: float) -> Optional[float]:
    """Public helper: mid-price premium for one exact strike in a calls or puts chain."""
    df = chain.copy()
    df["mid"] = df.apply(_premium_mid, axis=1)
    match = df[df["strike"] == strike]
    return float(match["mid"].iloc[0]) if not match.empty else None


def build_manual_candidate(
    ticker: str, expiration: str, spot_price: float,
    calls: pd.DataFrame, puts: pd.DataFrame,
    anchor_call_strike: float, second_call_strike: float,
    put_strike: float, num_puts: int,
) -> ComboCandidate:
    """Build a ComboCandidate from strikes chosen manually (not by the scanner)."""
    anchor_premium = premium_for_strike(calls, anchor_call_strike)
    second_premium = premium_for_strike(calls, second_call_strike)
    put_premium = premium_for_strike(puts, put_strike)
    if None in (anchor_premium, second_premium, put_premium):
        raise ValueError("לא נמצא מחיר עבור אחד הסטרייקים שנבחרו")

    net_call_debit = anchor_premium - second_premium
    net_cost = net_call_debit - (put_premium * num_puts)
    return ComboCandidate(
        ticker=ticker, expiration=expiration, spot_price=spot_price,
        anchor_call_strike=anchor_call_strike, anchor_call_premium=anchor_premium,
        second_call_strike=second_call_strike, second_call_premium=second_premium,
        put_strike=put_strike, put_premium=put_premium, num_puts=num_puts,
        net_cost=round(net_cost, 4), call_spread_width=second_call_strike - anchor_call_strike,
    )


def refresh_position(entry: dict) -> dict:
    """
    Re-fetch live prices for a saved position and compute mark-to-market P&L
    if it were closed right now. Does not mutate the saved file.
    """
    ticker = entry["ticker"]
    expiration = entry["expiration"]
    spot = get_current_price(ticker)
    calls, puts = fetch_option_chain(ticker, expiration)
    calls = calls.copy()
    puts = puts.copy()

    current_anchor = premium_for_strike(calls, entry["anchor_call_strike"])
    current_second = premium_for_strike(calls, entry["second_call_strike"])
    current_put = premium_for_strike(puts, entry["put_strike"])

    enriched = dict(entry)
    enriched["current_spot"] = spot
    enriched["current_anchor_call_premium"] = current_anchor
    enriched["current_second_call_premium"] = current_second
    enriched["current_put_premium"] = current_put

    if None not in (current_anchor, current_second, current_put):
        current_net_cost = (current_anchor - current_second) - current_put * entry["num_puts"]
        enriched["current_net_cost"] = round(current_net_cost, 4)
        # P&L if closed now = (current_net_cost - entry_net_cost) * 100
        # see test_combo_strategy_engine.py for the derivation
        enriched["mtm_pnl_dollars"] = round((current_net_cost - entry["net_cost"]) * 100, 2)
        threshold = entry.get("alert_threshold")
        enriched["alert_triggered"] = (
            threshold is not None and enriched["mtm_pnl_dollars"] <= threshold
        )
    else:
        enriched["mtm_pnl_dollars"] = None
        enriched["alert_triggered"] = None

    exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
    enriched["days_to_expiry"] = (exp_date - date.today()).days

    return enriched


# ---------------------------------------------------------------------------
# Position lifecycle — open vs closed
# ---------------------------------------------------------------------------
# Existing watchlist entries have no "status" field; treat missing as "open"
# so nothing already saved breaks.

def compute_net_realized(gross_pnl: float, commission: float = 15.0, tax_rate: float = 0.25) -> dict:
    """
    gross_pnl: raw P&L before costs (e.g. the mid-price mtm_pnl_dollars at close).
    commission: flat round-trip commission — buy + sell together (default 7.5$+7.5$=15$).
    tax_rate: applied only to a positive pre-tax net; a loss isn't taxed here.
    """
    pre_tax_net = round(gross_pnl - commission, 2)
    tax = round(pre_tax_net * tax_rate, 2) if pre_tax_net > 0 else 0.0
    net_pnl = round(pre_tax_net - tax, 2)
    return {
        "gross_pnl": round(gross_pnl, 2),
        "commission": round(commission, 2),
        "pre_tax_net": pre_tax_net,
        "tax": tax,
        "net_pnl": net_pnl,
    }


def close_position(
    index: int, gross_pnl: float, commission: float = 15.0, tax_rate: float = 0.25,
    path: str = WATCHLIST_PATH,
) -> None:
    """
    Mark a watchlist entry closed. Stores the full breakdown (gross P&L,
    commission, tax, net P&L) — "realized_pnl" is always the NET figure,
    so it's what feeds the ledger/summary and other callers unchanged.
    """
    data = load_watchlist(path)
    if 0 <= index < len(data):
        breakdown = compute_net_realized(gross_pnl, commission, tax_rate)
        data[index]["status"] = "closed"
        data[index]["close_date"] = date.today().isoformat()
        data[index]["realized_pnl_gross"] = breakdown["gross_pnl"]
        data[index]["commission"] = breakdown["commission"]
        data[index]["tax"] = breakdown["tax"]
        data[index]["realized_pnl"] = breakdown["net_pnl"]
        save_watchlist(data, path)


def reopen_position(index: int, path: str = WATCHLIST_PATH) -> None:
    """Undo close_position — for correcting a mistaken close."""
    data = load_watchlist(path)
    if 0 <= index < len(data):
        data[index]["status"] = "open"
        data[index].pop("close_date", None)
        data[index].pop("realized_pnl", None)
        save_watchlist(data, path)


# ---------------------------------------------------------------------------
# Capital ledger — deposits/withdrawals, kept as history (not a single balance)
# ---------------------------------------------------------------------------

CAPITAL_LEDGER_PATH = "combo_capital_ledger.json"


def load_ledger(path: str = CAPITAL_LEDGER_PATH) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_ledger(entries: list[dict], path: str = CAPITAL_LEDGER_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def add_ledger_entry(amount: float, note: str = "", path: str = CAPITAL_LEDGER_PATH) -> None:
    """amount: positive = deposit (הפקדה), negative = withdrawal (משיכה)."""
    entries = load_ledger(path)
    entries.append({"date": date.today().isoformat(), "amount": round(amount, 2), "note": note})
    save_ledger(entries, path)


def total_capital(path: str = CAPITAL_LEDGER_PATH) -> float:
    return round(sum(e["amount"] for e in load_ledger(path)), 2)


# ---------------------------------------------------------------------------
# Portfolio summary — capital in/committed/left, realized vs unrealized P&L
# ---------------------------------------------------------------------------

def portfolio_summary(
    watchlist_path: str = WATCHLIST_PATH,
    ledger_path: str = CAPITAL_LEDGER_PATH,
    refreshed_open: Optional[list[dict]] = None,
) -> dict:
    """
    refreshed_open: pass the already-refreshed open-position dicts from
    refresh_position() (with mtm_pnl_dollars) to include unrealized P&L;
    without it, unrealized_pnl is None rather than stale/wrong.
    """
    data = load_watchlist(watchlist_path)
    open_positions = [p for p in data if p.get("status", "open") == "open"]
    closed_positions = [p for p in data if p.get("status") == "closed"]

    total_cap = total_capital(ledger_path)
    open_margins = [get_entry_margins(p) for p in open_positions]
    margin_reg_t_total = sum(m["reg_t_estimate"] for m in open_margins)
    margin_cash_secured_total = sum(m["cash_secured"] for m in open_margins)

    unrealized = None
    if refreshed_open is not None:
        vals = [p.get("mtm_pnl_dollars") for p in refreshed_open if p.get("mtm_pnl_dollars") is not None]
        unrealized = round(sum(vals), 2) if vals else 0.0

    realized_total = round(sum(p.get("realized_pnl") or 0 for p in closed_positions), 2)
    realized_gross_total = round(
        sum(p.get("realized_pnl_gross", p.get("realized_pnl")) or 0 for p in closed_positions), 2
    )
    commission_total = round(sum(p.get("commission") or 0 for p in closed_positions), 2)
    tax_total = round(sum(p.get("tax") or 0 for p in closed_positions), 2)
    net_worth_now = round(total_cap + realized_total, 2)

    monthly: dict[str, float] = {}
    yearly: dict[str, float] = {}
    for p in closed_positions:
        cd = p.get("close_date")
        pnl = p.get("realized_pnl") or 0
        if cd:
            monthly[cd[:7]] = round(monthly.get(cd[:7], 0) + pnl, 2)
            yearly[cd[:4]] = round(yearly.get(cd[:4], 0) + pnl, 2)

    return {
        "total_capital": total_cap,
        "net_worth_now": net_worth_now,
        "margin_in_use_reg_t": round(margin_reg_t_total, 2),
        "margin_in_use_cash_secured": round(margin_cash_secured_total, 2),
        "capital_remaining_reg_t": round(net_worth_now - margin_reg_t_total, 2) if total_cap else None,
        "capital_remaining_cash_secured": round(net_worth_now - margin_cash_secured_total, 2) if total_cap else None,
        "unrealized_pnl": unrealized,
        "realized_pnl_total": realized_total,
        "realized_pnl_gross_total": realized_gross_total,
        "commission_total": commission_total,
        "tax_total": tax_total,
        "realized_pnl_by_month": dict(sorted(monthly.items())),
        "realized_pnl_by_year": dict(sorted(yearly.items())),
        "open_count": len(open_positions),
        "closed_count": len(closed_positions),
    }
