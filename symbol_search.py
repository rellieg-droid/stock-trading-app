# -*- coding: utf-8 -*-
"""
symbol_search.py

רכיב בחירת סימבול לשימוש חוזר: רשימה נגללת לפי אותיות, כמו החיפוש בכותרת.

    from symbol_search import symbol_picker
    ticker = symbol_picker("טיקר", key="combo_scan_ticker_sb", default="SOXL")

- האפשרות הראשונה ברשימה היא תמיד מה שהוקלד (▶ TERM), כך שהזנה ידנית
  עובדת גם כשהחיפוש של Yahoo לא זמין.
- החיפוש עצמו: אותו endpoint של החיפוש בכותרת, לא דורש crumb.
- לא לשים בתוך st.form: הרכיב צריך להריץ את האפליקציה תוך כדי הקלדה.
"""
from __future__ import annotations

import re

import requests
import streamlit as st
from streamlit_searchbox import st_searchbox

_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-^=]{0,11}$")


@st.cache_data(ttl=300, show_spinner=False)
def yahoo_symbol_search(query: str) -> list[dict]:
    """חיפוש סימבולים ב-Yahoo לפי שם או סימבול. נכשל בשקט לרשימה ריקה."""
    try:
        r = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": query, "quotesCount": 6, "newsCount": 0, "listsCount": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=6,
        )
        if r.status_code != 200:
            return []
        out = []
        for q in r.json().get("quotes", []):
            sym = q.get("symbol", "")
            if q.get("quoteType", "") in ("EQUITY", "ETF") and sym:
                out.append({
                    "sym": sym,
                    "name": q.get("longname") or q.get("shortname") or sym,
                    "exch": q.get("exchDisp", ""),
                })
        return out[:6]
    except Exception:
        return []


def _symbol_options(term: str) -> list[tuple[str, str]]:
    """(תווית להצגה, סימבול). מתחת ל-2 תווים לא פונים ל-Yahoo."""
    term = (term or "").strip()
    if not term:
        return []
    opts, seen = [], set()
    typed = term.upper()
    if _TICKER_RE.match(typed):
        opts.append((f"▶  {typed}", typed))
        seen.add(typed)
    if len(term) >= 2:
        for r in yahoo_symbol_search(term):
            sym = r["sym"].upper()
            if sym in seen:
                continue
            seen.add(sym)
            opts.append((f'{sym}  ·  {r["name"][:34]}  ·  {r["exch"]}', sym))
    return opts


def symbol_picker(label: str, key: str, default: str = "",
                  placeholder: str = "🔍  סימבול או שם חברה") -> str:
    """מחזיר את הסימבול שנבחר, או את default אם עוד לא נבחר כלום."""
    default = (default or "").upper().strip()
    picked = st_searchbox(
        _symbol_options,
        placeholder=f"{placeholder} (כעת: {default})" if default else placeholder,
        label=label,
        default=default or None,
        key=key,
        debounce=250,
    )
    return (picked or default or "").upper().strip()
