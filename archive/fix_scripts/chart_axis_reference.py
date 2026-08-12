"""
Reference function: Plotly stock chart with correctly-behaving X/Y axes.

Covers exactly what was asked:
  1. X axis — type='date', autorange, rangebreaks that hide non-trading hours
     (nights) and weekends, so there are no flat "gap" stretches in the line.
  2. Dark terminal styling — transparent/dark background, subtle gridlines,
     monospace muted axis text.
  3. Mock data generator — runs immediately, no external data needed.

Design notes on the two bugs this avoids:
  - Y axis "disappearing" / not centered: this happens when you combine
    fill='tozeroy' with autorange — Plotly's autorange algorithm extends the
    range down to 0 to fit the fill, which either flattens the visible line
    against the bottom of the chart or, on some ranges, pushes the actual
    price data outside the visible window entirely. Fix: no fill, and let
    autorange size to the *line* data only.
  - Plotly's spike-line "halo": if you want crosshair spikes later, give
    plot_bgcolor a real color (not fully transparent) — Plotly computes the
    spike-line halo against plot_bgcolor, and falls back to solid white when
    it's transparent, which looks like a thick stray line.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ── Dark terminal design tokens ─────────────────────────────────────────
BG_BASE     = "#0E1117"
BG_SURFACE  = "#161B22"
GRID_COLOR  = "#30363D"
TEXT_MUTED  = "#8B949E"
LINE_UP     = "#3FB950"
LINE_DOWN   = "#F85149"


def generate_mock_ohlc(n_days: int = 180, start_price: float = 210.0, seed: int = 11) -> pd.DataFrame:
    """Business-day mock price series (no weekends), so rangebreaks have
    something real to hide. Returns columns: date, open, high, low, close."""
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n_days)
    n = len(dates)  # bdate_range can return fewer rows than requested if the
                     # end date itself isn't a business day — size off this, not n_days.

    rng = np.random.default_rng(seed)
    walk = rng.normal(0, 1.1, n).cumsum()
    close = start_price + walk - walk[0]

    open_ = np.roll(close, 1)
    open_[0] = close[0]
    spread = np.abs(rng.normal(0.6, 0.4, n)) + 0.05
    high = np.maximum(open_, close) + spread
    low  = np.minimum(open_, close) - spread

    return pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low, "close": close})


def build_stock_chart(df: pd.DataFrame, height: int = 420, intraday: bool = False) -> go.Figure:
    """df needs columns: date, open, high, low, close (close is what's plotted as
    the line; open/high/low only matter if you switch to a Candlestick trace).

    intraday: set True only when `date` has real time-of-day values (multiple
    bars per trading day, e.g. 5-minute bars). The overnight-hour rangebreak
    below is meaningless for daily bars — daily timestamps sit at midnight,
    which falls *inside* a 16:00-09:30 "hide overnight" window, so applying
    it to daily data hides every single point and the line vanishes. This is
    a real, easy-to-hit bug, not a hypothetical: it's exactly what happened
    while testing this function before this fix."""
    dates = df["date"]
    close = df["close"].values

    line_color = LINE_UP if close[-1] >= close[0] else LINE_DOWN

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=close, mode="lines",
        line=dict(color=line_color, width=1.8),
        # No fill — this is what keeps autorange from being pulled toward 0.
        hovertemplate="<b>$%{y:.2f}</b><extra></extra>",
    ))

    rangebreaks = [dict(bounds=["sat", "mon"])]  # hide weekends — safe for daily AND intraday
    if intraday:
        rangebreaks.append(dict(bounds=[16, 9.5], pattern="hour"))  # hide overnight hours

    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",   # transparent outer canvas
        plot_bgcolor=BG_SURFACE,         # real color — needed for correct spike/halo rendering later
        margin=dict(l=10, r=60, t=20, b=10),
        showlegend=False,
        font=dict(family="JetBrains Mono, monospace", color=TEXT_MUTED, size=11),
        xaxis=dict(
            type="date",
            autorange=True,
            rangeslider=dict(visible=False),
            showgrid=False,
            zeroline=False,
            color=TEXT_MUTED,
            tickfont=dict(family="JetBrains Mono, monospace", size=10),
            rangebreaks=rangebreaks,
        ),
        yaxis=dict(
            autorange=True,           # let Plotly size to the line data — no forced zero
            side="right",
            showgrid=True,
            gridcolor=GRID_COLOR,
            gridwidth=1,
            zeroline=False,
            tickprefix="$",
            tickformat=".2f",
            color=TEXT_MUTED,
            tickfont=dict(family="JetBrains Mono, monospace", size=10),
        ),
    )
    return fig


if __name__ == "__main__":
    # Quick standalone check — writes an HTML file you can open directly,
    # no Streamlit required, so you can eyeball axis behavior in isolation.
    df = generate_mock_ohlc()
    fig = build_stock_chart(df)
    fig.write_html("chart_preview.html", include_plotlyjs="inline")
    print("Wrote chart_preview.html — open it in a browser to check the axes.")

    # If you want it inside Streamlit instead, replace the block above with:
    #
    #   import streamlit as st
    #   st.plotly_chart(fig, use_container_width=True)
