# -*- coding: utf-8 -*-
"""
position_sizing.py
===================
עטיפה דקה סביב strategy_engine.build_position_plan.

המטרה: לשני מקומות באפליקציה שבהם יש מחשבון Position Sizing
(render_position_module בטאב "סיכום והחלטה", ותת-הטאב הנפרד
"⚠️ Position Sizing") יש היום שני סטים נפרדים של אחוזי
Stop/Target קשיחים (5%/12% מול 5%/10%). המודול הזה נותן להם
מקור חישוב אחד, מבוסס ATR, במקום שני ניחושים שרירותיים.

עקרונות:
    * מודול טהור. אין כאן Streamlit ואין yfinance.
    * לא תלוי ב-alpha_paper_trading.py, כדי למנוע circular import —
      במקום true_atr() המקומי של האפליקציה, נעזרים ב-atr_wilder()
      שכבר קיים ב-strategy_engine ומחשב אותו הדבר (Wilder smoothing).
    * מחזיר PositionPlan של strategy_engine, או None אם אין מספיק
      נתונים לחישוב ATR (למשל טיקר עם פחות מ-15 ימי מסחר) — במקרה
      כזה קוד הקריאה חייב ליפול חזרה לברירת מחדל אחוזית ולא לקרוס.

__version__: 0.1.0
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from strategy_engine import StrategyConfig, PositionPlan, atr_wilder, build_position_plan

__version__ = "0.1.0"

MIN_BARS_FOR_ATR = 15


def atr_position_defaults(
    df: Optional[pd.DataFrame],
    entry_price: Optional[float],
    account_value: float,
    risk_pct: float,
    risk_profile: str = "medium",
    take_profit_multiplier: float = 3.0,
) -> Optional[PositionPlan]:
    """
    מחשבת Stop/Target מבוססי ATR, לשימוש כברירת מחדל בכל מסך
    Position Sizing באפליקציה.

    df             — DataFrame עם עמודות High/Low/Close של הטיקר
                      (אותו df שכבר נטען בטאב, לא צריך לטעון מחדש)
    entry_price    — מחיר הכניסה שהמשתמשת הזינה
    account_value  — גודל התיק שהמשתמשת הזינה
    risk_pct       — אחוז הסיכון לעסקה (0.5–5.0), נשלט ע"י ה-slider הקיים
    risk_profile   — "low" / "medium" / "high", קובע את מכפיל ה-ATR ל-Stop
    take_profit_multiplier — כפולות ATR עד ליעד (ברירת מחדל 3, כמו בטאב אסטרטגיה)

    מחזירה None אם אין מספיק נרות לחישוב ATR אמין. במקרה הזה קוד
    הקריאה צריך ליפול חזרה לברירת המחדל האחוזית הישנה, לא לקרוס.
    """
    if df is None or len(df) < MIN_BARS_FOR_ATR:
        return None
    if entry_price is None or entry_price <= 0:
        return None
    if "High" not in df.columns or "Low" not in df.columns or "Close" not in df.columns:
        return None

    atr_series = atr_wilder(df["High"], df["Low"], df["Close"])
    if atr_series.empty:
        return None
    atr_val = float(atr_series.iloc[-1])
    if not (atr_val == atr_val) or atr_val <= 0:  # NaN check בלי תלות ב-math/numpy
        return None

    base_cfg = StrategyConfig.for_profile(risk_profile)
    cfg = StrategyConfig(
        risk_profile=base_cfg.risk_profile,
        atr_stop_multiplier=base_cfg.atr_stop_multiplier,
        max_risk_pct=max(float(risk_pct), 0.1) / 100.0,
    )

    return build_position_plan(
        price=float(entry_price),
        atr=atr_val,
        portfolio_value=float(account_value),
        position_pct=1.0,  # לא מגבילים לפי % מהתיק כאן, רק לפי כלל הסיכון (max_risk_pct)
        cfg=cfg,
        take_profit_multiplier=take_profit_multiplier,
    )
