# -*- coding: utf-8 -*-
"""
strategy_scan.py
================
מריץ את מנוע האסטרטגיה על רשימת מניות ומדפיס שורה אחת לכל אחת.

שתי מטרות:
  1. בדיקת שפיות. אם כל המניות מחזירות את אותו HV Rank ואת אותו ציון,
     הקריטריון לא מבדיל בין כלום וצריך לתקן אותו.
  2. סורק Watchlist בפועל. אותה לוגיקה בדיוק, על כמה שמות במכה.

הרצה:
    py strategy_scan.py
    py strategy_scan.py NVDA KO MSFT PLTR
"""

from __future__ import annotations

import sys

import pandas as pd

import strategy_data as sd

DEFAULT_UNIVERSE = ["NVDA", "KO", "MSFT", "AAPL", "TSLA",
                    "JNJ", "PLTR", "XOM", "AMD", "PG"]


def scan(tickers: list[str], portfolio_value: float = 100_000,
         position_pct: float = 0.05,
         risk_profile: str = "medium") -> pd.DataFrame:
    rows = []
    for t in tickers:
        try:
            rep, diag = sd.build_report(t, portfolio_value, position_pct, risk_profile)
        except Exception as exc:
            rows.append({"מניה": t, "ציון": "שגיאה", "פסק דין": str(exc)[:40]})
            continue

        if rep is None:
            rows.append({"מניה": t, "ציון": "אין נתונים",
                         "פסק דין": "; ".join(diag.failures)[:40]})
            continue

        by_key = {c.key: c for c in rep.criteria}
        rows.append({
            "מניה": t,
            "ציון": rep.score_text,
            "פסק דין": rep.verdict_label,
            "יחסי אחוזון": f"{by_key['atr'].value:.0f}%" if by_key["atr"].value is not None else "-",
            "HV אחוזון": f"{by_key['hv_rank'].value:.0f}%" if by_key["hv_rank"].value is not None else "-",
            "ATR%": f"{by_key['atr'].current.split('ATR ')[-1]}" if "ATR " in by_key["atr"].current else "-",
            "דוח בעוד": by_key["events"].current,
            "וטו": ", ".join(rep.vetoes) or "-",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe = sys.argv[1:] or DEFAULT_UNIVERSE
    print(f"סורק {len(universe)} מניות. זה לוקח כדקה בגלל שרשראות האופציות.\n")
    df = scan(universe)
    print(df.to_string(index=False))

    ranks = pd.to_numeric(
        df.get("HV אחוזון", pd.Series(dtype=str)).astype(str).str.rstrip("%"),
        errors="coerce",
    ).dropna()
    if len(ranks) >= 3:
        print(f"\nפיזור אחוזון HV: מינימום {ranks.min():.0f}% | "
              f"חציון {ranks.median():.0f}% | מקסימום {ranks.max():.0f}% | "
              f"טווח {ranks.max() - ranks.min():.0f} נקודות")
        if ranks.max() - ranks.min() < 25:
            print("אזהרה: כל המניות באותו אזור. הקריטריון לא מבדיל ביניהן.")
