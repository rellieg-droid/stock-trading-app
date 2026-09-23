"""
combo_strategy_tab.py

Streamlit UI for the "אסטרטגיות משולבות" (Combo Strategies) tab.
All calculation logic lives in combo_strategy_engine.py — this file only
renders it.

INTEGRATION NOTE (read before wiring in):
This is a standalone module. To add it to alpha_paper_trading.py:
  1. Copy this file and combo_strategy_engine.py into the project folder.
  2. Add an entry for "אסטרטגיות משולבות" wherever the nav menu / _TAB_KEYS
     list is defined, following the same pattern used for the RiskShield
     entry.
  3. Where the selected tab is dispatched, call render_combo_strategy_tab()
     for this new entry — same pattern as riskshield_tab.py.
  4. This file uses plain st.container(border=True) / st.metric styling
     rather than your existing color constants — swap in your theme
     variables (the ones riskshield_tab.py uses) if you want a visual match.
  5. Not wired into a patch script on purpose: patch scripts need to match
     an exact anchor in the live file, which wasn't available when this was
     written. Share the nav-registration snippet if you'd like an exact
     patch script instead of manual wiring.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

import combo_strategy_engine as engine
from symbol_search import symbol_picker  # SYMBOL_PICKER_V1

WATCHLIST_PATH = "combo_strategies.json"
LEDGER_PATH = "combo_capital_ledger.json"


def render_combo_strategy_tab():
    st.markdown("<div style='direction: rtl; text-align: right;'>", unsafe_allow_html=True)
    st.header("🎯 אסטרטגיות משולבות")
    st.caption(
        "אסטרטגיית ריסק ריברסל ממומן: קול לונג + קול שורט, ממומן ע\"י מכירת פוטים. "
        "כלי מעקב וחישוב בלבד — לא המלצה."
    )

    _render_guide()

    tab_scan, tab_watch, tab_summary = st.tabs(
        ["🔍 סריקת אסטרטגיה חדשה", "📋 רשימת מעקב", "📊 סיכום תיק"]
    )
    with tab_scan:
        _render_scanner()
    with tab_watch:
        _render_watchlist()
    with tab_summary:
        _render_portfolio_summary()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_guide():
    with st.expander("📄 מדריך: מה זו האסטרטגיה, ומה כל טאב עושה"):
        st.markdown(
            """
**המבנה**: קניית CALL קרוב למחיר הנוכחי (העוגן), מכירת CALL בסטרייק גבוה יותר
(בדרך כלל בפרמיה שקרובה לחצי מהעוגן), וכתיבת כמה PUT-ים בסטרייק נמוך יותר כדי
לממן את כל זה. אם הפרמיה מהפוטים מכסה את עלות מרווח הקולים, נכנסים כמעט
בעלות אפס.

| טווח מחיר בתפוגה | מה קורה |
|---|---|
| מתחת לסטרייק הפוט | הפוטים מוקצים — קונים בפועל מניות במחיר קבוע, גם אם השוק ממשיך ליפול |
| בין סטרייק הפוט לעוגן | הכול פוקע חסר-ערך — נשאר רק הקרדיט/חיוב מהכניסה |
| בין העוגן לסטרייק השני | מרווח הקולים בתוך הכסף — הרווח גדל |
| מעל הסטרייק השני | רווח מקסימלי קבוע — הקול השורט מגביל אותו |

**⚠️ הסיכון האמיתי**: אין הגנה מתחת לסטרייק הפוט. "עלות אפס" לא אומר "סיכון
אפס" — זו רק עלות המימון לכניסה, לא שיקוף של החשיפה בפועל.

---

**🔍 סריקת אסטרטגיה חדשה** — טיקר (עם אישור שם אוטומטי), תאריך פקיעה אחד
לשלוש הרגליים, הון זמין (לחישוב % ואזהרת "אין מספיק הון"), ובחירה בין זיהוי
אוטומטי (עד 3 מועמדים מדורגים) לבחירה ידנית מרשימות הסטרייקים. כל כרטיס תוצאה
מציג עלות נטו, רווח מקסימלי, נקודת איזון, הפסד בקריסה ל-0, מרג'ין, וסדר הזנה
מומלץ (לונג לפני שורט).

**📋 רשימת מעקב** — "רענן מחירים" שולף מחירים עדכניים ומחשב P&L אם נסגר עכשיו.
התראה (ברירת מחדל: 10% מ"הפסד בקריסה ל-0" של אותה פוזיציה) מתריעה באדום כשה-P&L
החי חוצה את הסף. סגירת פוזיציה מציגה פירוק מלא: עמלה, מס (רק על רווח), P&L נטו,
והון "לפני ← אחרי".

**📊 סיכום תיק** — יומן הון (הפקדות/משיכות אמיתיות מהברוקר, לא רווח/הפסד ממסחר),
הגדרות עמלה ומס, ו"הון בפועל כרגע" שכולל גם את תוצאות המסחר, לא רק מה שהופקד.

**מגבלות ידועות**: אין עדיין התראות במייל (רק חזותיות בתוך האפליקציה) —
זה מתוכנן לשלב שהאפליקציה תעלה לשרת. RiskShield עדיין לא כולל את אותה שכבת
יומן הון/עמלה/מס.
"""
        )


def _render_scanner():
    col1, col2 = st.columns([2, 1])
    with col1:
        ticker = symbol_picker("טיקר", key="combo_scan_ticker_sb", default="SOXL")  # SYMBOL_PICKER_V1
    with col2:
        num_puts = st.number_input(
            "מספר פוטים למכירה", min_value=1, max_value=10, value=2, key="combo_num_puts"
        )

    ledger_total = engine.total_capital(LEDGER_PATH)
    available_capital = st.number_input(
        "הון זמין ($, אופציונלי — להצגת % מההון ואזהרת מספיק כסף)",
        min_value=0.0, value=float(ledger_total), step=1000.0, key="combo_scan_capital",
        help="ממולא אוטומטית מיומן ההון בטאב 'סיכום תיק'. אפשר לשנות כאן לצורך תכנון בלבד — "
             "זה לא כותב חזרה ליומן.",
    )

    if not ticker:
        return

    name = engine.get_ticker_name(ticker)
    if name:
        st.markdown(
            f"<div style='color:#8FE38F;font-size:0.85rem;'>✓ {ticker} — {name}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='color:#FF9B9B;font-size:0.85rem;'>⚠️ לא זוהה סימבול בשם {ticker} — בדקי את האיות</div>",
            unsafe_allow_html=True,
        )

    try:
        expirations = engine.list_available_expirations(ticker)
    except Exception as e:
        st.error(f"שגיאה בטעינת תאריכי פקיעה עבור {ticker}: {e}")
        return

    if not expirations:
        st.warning("לא נמצאו תאריכי פקיעה זמינים עבור טיקר זה.")
        return

    expiration = st.selectbox("תאריך פקיעה", expirations, key="combo_scan_expiration")

    mode = st.radio(
        "איך לבחור את הסטרייקים?",
        ["🔍 זיהוי אוטומטי", "✍️ בחירה ידנית"],
        horizontal=True, key="combo_mode",
    )

    if mode == "🔍 זיהוי אוטומטי":
        _render_auto_scan(ticker, expiration, int(num_puts), available_capital)
    else:
        _render_manual_pick(ticker, expiration, int(num_puts), available_capital)


def _data_source_caption(spot: float, fetched_at: str):
    st.markdown(
        f"<div style='font-size:1rem;color:#FFFFFF;'>"
        f"<b>מחיר נוכחי: {spot:.2f}$</b><br>"
        f"<span style='font-size:0.85rem;color:#D0D0D0;'>"
        f"נשלף מ-Yahoo Finance ({fetched_at}) — מחיר אחרון שנסחר, לא בהכרח שידור בזמן אמת. "
        f"פרמיות: אמצע bid/ask באותו רגע.</span></div>",
        unsafe_allow_html=True,
    )


def _render_auto_scan(ticker: str, expiration: str, num_puts: int, available_capital: float):
    col3, col4 = st.columns(2)
    with col3:
        ratio_target = st.slider(
            "יחס יעד: פרמיית הקול השני מתוך פרמיית העוגן", 0.2, 0.8, 0.5, 0.05,
            key="combo_ratio_target",
        )
    with col4:
        ratio_tolerance = st.slider(
            "טווח סטייה מותר (±)", 0.05, 0.5, 0.20, 0.05, key="combo_ratio_tolerance"
        )

    if st.button("🔍 סרוק", key="combo_scan_button", use_container_width=True):
        with st.spinner("סורק שרשרת אופציות..."):
            try:
                spot = engine.get_current_price(ticker)
                calls, puts = engine.fetch_option_chain(ticker, expiration)
                candidates = engine.find_candidates(
                    calls, puts, spot, ticker, expiration,
                    ratio_target=ratio_target, ratio_tolerance=ratio_tolerance,
                    num_puts=num_puts, top_n=3,
                )
            except Exception as e:
                st.error(f"שגיאה בסריקה: {e}")
                return

        if not candidates:
            st.warning("לא נמצאו התאמות בטווח שהוגדר. נסי להרחיב את טווח הסטייה.")
            st.session_state.pop("combo_last_candidates", None)
            return

        st.session_state["combo_last_candidates"] = candidates
        st.session_state["combo_last_spot"] = spot
        st.session_state["combo_fetched_at"] = datetime.now().strftime("%H:%M:%S")

    candidates = st.session_state.get("combo_last_candidates")
    if candidates:
        _data_source_caption(
            st.session_state.get("combo_last_spot", 0.0),
            st.session_state.get("combo_fetched_at", "—"),
        )
        for i, cand in enumerate(candidates):
            _render_candidate_card(cand, i, available_capital)


def _render_manual_pick(ticker: str, expiration: str, num_puts: int, available_capital: float):
    if st.button("📥 טען שרשרת אופציות", key="combo_manual_load", use_container_width=True):
        with st.spinner("טוען..."):
            try:
                spot = engine.get_current_price(ticker)
                calls, puts = engine.fetch_option_chain(ticker, expiration)
            except Exception as e:
                st.error(f"שגיאה בטעינה: {e}")
                return
        st.session_state["combo_manual_spot"] = spot
        st.session_state["combo_manual_calls"] = calls
        st.session_state["combo_manual_puts"] = puts
        st.session_state["combo_fetched_at"] = datetime.now().strftime("%H:%M:%S")

    calls = st.session_state.get("combo_manual_calls")
    puts = st.session_state.get("combo_manual_puts")
    spot = st.session_state.get("combo_manual_spot")
    if calls is None or puts is None:
        st.info("לחצי 'טען שרשרת אופציות' כדי לבחור סטרייקים ידנית.")
        return

    _data_source_caption(spot, st.session_state.get("combo_fetched_at", "—"))

    call_strikes = sorted(calls["strike"].unique().tolist())
    put_strikes = sorted(puts["strike"].unique().tolist())

    c1, c2, c3 = st.columns(3)
    with c1:
        anchor_strike = st.selectbox("CALL לונג (עוגן)", call_strikes, key="combo_manual_anchor")
    with c2:
        second_strike = st.selectbox(
            "CALL שורט", [s for s in call_strikes if s > anchor_strike] or call_strikes,
            key="combo_manual_second",
        )
    with c3:
        put_strike = st.selectbox(
            "PUT שורט", [s for s in put_strikes if s < spot] or put_strikes,
            key="combo_manual_put",
        )

    if st.button("➕ חשבי", key="combo_manual_compute", use_container_width=True):
        try:
            candidate = engine.build_manual_candidate(
                ticker, expiration, spot, calls, puts,
                anchor_strike, second_strike, put_strike, num_puts,
            )
        except Exception as e:
            st.error(f"שגיאה בבניית האסטרטגיה: {e}")
            return
        st.session_state["combo_manual_candidate"] = candidate

    candidate = st.session_state.get("combo_manual_candidate")
    if candidate:
        _render_candidate_card(candidate, "manual", available_capital)


def _render_candidate_card(cand, idx, available_capital: float = 0.0):
    label = f"מועמד {idx + 1}" if isinstance(idx, int) else "בחירה ידנית"
    figs = engine.key_figures(cand)
    margins = engine.margin_estimates(cand)

    with st.container(border=True):
        st.subheader(
            f"{label}: CALL {cand.anchor_call_strike:.0f} / "
            f"CALL {cand.second_call_strike:.0f} / "
            f"{cand.num_puts}x PUT {cand.put_strike:.0f}"
        )

        l1, l2, l3 = st.columns(3)
        l1.markdown(
            f"<div style='color:#FFFFFF;'>CALL לונג<br>"
            f"<b style='font-size:1.1rem;'>{cand.anchor_call_strike:.0f}</b> @ {cand.anchor_call_premium:.2f}$</div>",
            unsafe_allow_html=True,
        )
        l2.markdown(
            f"<div style='color:#FFFFFF;'>CALL שורט<br>"
            f"<b style='font-size:1.1rem;'>{cand.second_call_strike:.0f}</b> @ {cand.second_call_premium:.2f}$</div>",
            unsafe_allow_html=True,
        )
        l3.markdown(
            f"<div style='color:#FFFFFF;'>PUT שורט ×{cand.num_puts}<br>"
            f"<b style='font-size:1.1rem;'>{cand.put_strike:.0f}</b> @ {cand.put_premium:.2f}$</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("עלות נטו", f"{figs['net_cost_dollars']:.0f}$",
                  help="קרדיט (חיובי) או חיוב (שלילי) בכניסה לעסקה, פעם אחת.")
        c2.metric("רווח מקסימלי", f"{figs['max_profit']:.0f}$",
                  help="הרווח הגבוה ביותר האפשרי, כשהמניה מגיעה לסטרייק הקול השורט ומעלה.")
        c3.metric("נקודת איזון תחתונה", f"{figs['breakeven_low']:.2f}$",
                  help="מחיר המניה בתפוגה שמתחתיו הפוזיציה מתחילה להפסיד בפועל. "
                       "מעליו (עד הסטרייק הראשון) היא עדיין ברווח קטן וקבוע מהקרדיט שהתקבל.")
        c4.metric("הפסד בקריסה ל-0", f"{figs['max_loss_at_zero']:.0f}$",
                  help="ההפסד המקסימלי התיאורטי, אם המניה הייתה יורדת לאפס בתפוגה.")

        margin_line = (
            f"מרג'ין משוער — cash-secured: כ-{margins['cash_secured']:.0f}$ | "
            f"Reg-T (הערכה גסה, תלוי ברוקר): כ-{margins['reg_t_estimate']:.0f}$"
        )
        if available_capital > 0:
            pct_cs = margins["cash_secured"] / available_capital * 100
            pct_rt = margins["reg_t_estimate"] / available_capital * 100
            margin_line += f"<br>ביחס להון שהזנת ({available_capital:.0f}$): cash-secured = {pct_cs:.0f}% | Reg-T = {pct_rt:.0f}%"
        st.markdown(
            f"<div style='font-size:0.95rem;color:#FFFFFF;line-height:1.6;'>{margin_line}</div>",
            unsafe_allow_html=True,
        )

        if available_capital > 0:
            if margins["reg_t_estimate"] > available_capital:
                st.markdown(
                    "<div dir='rtl' style='background:#3a1a1a;color:#FF9B9B;padding:10px 14px;"
                    "border-radius:6px;font-size:0.95rem;line-height:1.7;'>"
                    "🚨 אין מספיק הון: מרג'ין Reg-T "
                    f"(<span dir='ltr'>{margins['reg_t_estimate']:.0f}$</span>) "
                    "גבוה מההון הזמין "
                    f"(<span dir='ltr'>{available_capital:.0f}$</span>)."
                    "</div>",
                    unsafe_allow_html=True,
                )
            elif margins["cash_secured"] > available_capital:
                st.markdown(
                    "<div dir='rtl' style='background:#3a2f1a;color:#FFD27A;padding:10px 14px;"
                    "border-radius:6px;font-size:0.95rem;line-height:1.7;'>"
                    "⚠️ לכיסוי מלא "
                    f"(cash-secured, <span dir='ltr'>{margins['cash_secured']:.0f}$</span>) "
                    "אין מספיק הון "
                    f"(<span dir='ltr'>{available_capital:.0f}$</span>) — "
                    "יש כיסוי רק ברמת Reg-T."
                    "</div>",
                    unsafe_allow_html=True,
                )

        order = engine.suggested_entry_order(cand)
        order_str = " ← ".join(f"{leg.kind} {leg.strike:.0f}" for leg in order)
        st.markdown(
            f"<div style='font-size:0.95rem;color:#FFFFFF;line-height:1.6;margin-bottom:6px;'>"
            f"סדר הזנה מומלץ (לונג לפני שורט, מונע דרישת בטוחות מנופחת): {order_str}"
            f"</div>",
            unsafe_allow_html=True,
        )

        payoff_df = engine.compute_payoff_table(cand)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=payoff_df["price"], y=payoff_df["pnl"], mode="lines+markers", name="P&L",
            line=dict(width=3, color="#4D7FFF"), marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(77,127,255,0.12)",
            hovertemplate="מחיר: %{x:.1f}$<br>P&L: %{y:.0f}$<extra></extra>",
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="#888888")
        if figs["breakeven_low"] is not None:
            fig.add_vline(
                x=figs["breakeven_low"], line_dash="dot", line_color="#FF9B9B",
                annotation_text=f"איזון: {figs['breakeven_low']:.1f}$",
                annotation_font_color="#FFFFFF",
            )
        fig.update_layout(
            title=dict(
                text=f"רווח/הפסד בתפוגה — CALL {cand.anchor_call_strike:.0f}/"
                     f"{cand.second_call_strike:.0f}, {cand.num_puts}x PUT {cand.put_strike:.0f}",
                font=dict(size=13, color="#FFFFFF"),
            ),
            xaxis_title="מחיר SOXL בתפוגה ($)", yaxis_title="רווח/הפסד ($)",
            xaxis=dict(tickprefix="", ticksuffix="$", gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(tickformat=",.0f", ticksuffix="$", gridcolor="rgba(255,255,255,0.08)"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FFFFFF"),
            height=320, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, key=f"combo_chart_{idx}")
        st.markdown(
            "<div style='font-size:0.85rem;color:#D0D0D0;'>"
            "ציר X: מחיר המניה ביום הפקיעה. ציר Y: הרווח/הפסד בדולרים על הפוזיציה הזו באותו מחיר. "
            "השיפוע התלול משמאל = הפוטים מוקצים; המישור = הכל פוקע חסר-ערך; העלייה = מרווח הקולים נכנס לכסף; "
            "המישור השני מימין = הקול השורט מגביל את הרווח."
            "</div>",
            unsafe_allow_html=True,
        )

        note = st.text_input("הערה (אופציונלי)", key=f"combo_note_{idx}")
        default_alert = round(figs["max_loss_at_zero"] * 0.10, -2)  # 10% מההפסד המקסימלי, לא מספר שרירותי
        alert_threshold = st.number_input(
            "התראה: הודיעי לי כשה-P&L אם נסגר עכשיו יורד מתחת ל-",
            value=float(default_alert), step=100.0, key=f"combo_alert_{idx}",
            help="ברירת המחדל: 10% מ'הפסד בקריסה ל-0' של הפוזיציה הזו. שני לשנות לפי מה שמתאים לך.",
        )
        if st.button("➕ הוסף לרשימת מעקב", key=f"combo_add_{idx}"):
            engine.add_position(
                cand, note=note, alert_threshold=float(alert_threshold),
                available_capital=float(available_capital) if available_capital > 0 else None,
                path=WATCHLIST_PATH,
            )
            st.success("נוסף לרשימת המעקב.")


def _render_watchlist():
    data = engine.load_watchlist(WATCHLIST_PATH)
    if not data:
        st.info("רשימת המעקב ריקה. סרקי אסטרטגיה חדשה ולחצי 'הוסף לרשימת מעקב'.")
        return

    if st.button("🔄 רענן מחירים", key="combo_refresh_all"):
        refreshed = []
        for i, entry in enumerate(data):
            try:
                enriched = engine.refresh_position(entry)
            except Exception as e:
                enriched = dict(entry)
                enriched["error"] = str(e)
            refreshed.append(enriched)
            # Streamlit keeps a keyed widget's value in session_state across
            # reruns and ignores a new `value=` — must overwrite it directly
            # here, or the "P&L בסגירה" input below keeps showing whatever
            # it showed before this refresh (usually 0.00).
            st.session_state[f"combo_realized_{i}"] = enriched.get("mtm_pnl_dollars") or 0.0
        st.session_state["combo_refreshed"] = refreshed

    rows = st.session_state.get("combo_refreshed", data)
    show_closed = st.checkbox("הצג גם פוזיציות סגורות", key="combo_show_closed")

    for i, row in enumerate(rows):
        status = row.get("status", "open")
        if status == "closed" and not show_closed:
            continue

        with st.container(border=True):
            days_left = row.get("days_to_expiry", "—")
            status_badge = "🔒 סגורה" if status == "closed" else "🟢 פתוחה"
            st.markdown(
                f"**{row['ticker']}** ({status_badge}) | פקיעה: {row['expiration']} "
                f"({days_left} ימים) | נכנס ב: {row.get('entry_date', '—')}"
            )
            st.markdown(
                f"<div style='color:#FFFFFF;font-size:0.95rem;'>"
                f"CALL {row['anchor_call_strike']:.0f} / CALL {row['second_call_strike']:.0f} / "
                f"{row['num_puts']}x PUT {row['put_strike']:.0f}</div>",
                unsafe_allow_html=True,
            )

            if status == "closed":
                pnl = row.get("realized_pnl", 0) or 0
                color = "#8FE38F" if pnl >= 0 else "#FF9B9B"
                st.markdown(
                    f"<div style='color:{color};'>P&L ריאלי (נסגרה ב-{row.get('close_date','—')}): "
                    f"{pnl:.0f}$</div>",
                    unsafe_allow_html=True,
                )
                if st.button("↩️ פתח מחדש", key=f"combo_reopen_{i}"):
                    engine.reopen_position(i, path=WATCHLIST_PATH)
                    st.rerun()
                if row.get("note"):
                    st.caption(f"הערה: {row['note']}")
                continue

            if row.get("error"):
                st.warning(f"שגיאה ברענון: {row['error']}")
            elif row.get("mtm_pnl_dollars") is not None:
                pnl = row["mtm_pnl_dollars"]
                color = "#8FE38F" if pnl >= 0 else "#FF9B9B"
                st.markdown(
                    f"<div style='color:#FFFFFF;'>מחיר נוכחי: {row.get('current_spot', 0):.2f}$ | "
                    f"<span style='color:{color}'>P&L אם נסגר עכשיו: {pnl:.0f}$</span></div>",
                    unsafe_allow_html=True,
                )
                if row.get("alert_triggered"):
                    st.error(
                        f"🚨 ההתראה הופעלה: P&L ({pnl:.0f}$) ירד מתחת לסף שהגדרת "
                        f"({row.get('alert_threshold'):.0f}$)."
                    )
                elif row.get("alert_threshold") is not None:
                    ref_price = row.get("alert_reference_price")
                    ref_txt = f" (רף התייחסות בתפוגה: כ-{ref_price:.1f}$)" if ref_price else ""
                    st.caption(f"התראה מוגדרת ל-{row['alert_threshold']:.0f}${ref_txt}")

            row_margins = engine.get_entry_margins(row)
            margin_txt = (
                f"מרג'ין (בכניסה) — cash-secured: {row_margins['cash_secured']:.0f}$ | "
                f"Reg-T: {row_margins['reg_t_estimate']:.0f}$"
            )
            if row.get("available_capital"):
                margin_txt += (
                    f" | מתוך הון של {row['available_capital']:.0f}$ "
                    f"({row.get('margin_pct_cash_secured', 0):.0f}% / {row.get('margin_pct_reg_t', 0):.0f}%)"
                )
            st.markdown(
                f"<div style='font-size:0.85rem;color:#D0D0D0;'>{margin_txt}</div>",
                unsafe_allow_html=True,
            )

            if row.get("note"):
                st.caption(f"הערה: {row['note']}")

            close_col1, close_col2 = st.columns([2, 1])
            has_live_pnl = row.get("mtm_pnl_dollars") is not None
            default_realized = row.get("mtm_pnl_dollars") if has_live_pnl else None
            with close_col1:
                if not has_live_pnl:
                    st.markdown(
                        "<div style='color:#FFD27A;font-size:0.85rem;'>"
                        "⚠️ לא רועננה עדיין — לחצי 'רענן מחירים' למעלה כדי לקבל הצעה אמיתית, "
                        "או הזיני ידנית."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                realized_input = st.number_input(
                    "P&L בסגירה (מוצע מה-P&L האחרון שרוענן)",
                    value=float(default_realized) if default_realized is not None else 0.0,
                    step=10.0, key=f"combo_realized_{i}",
                )
            with close_col2:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                do_close = st.button("✅ סגור פוזיציה", key=f"combo_close_{i}")

            commission = st.session_state.get("combo_commission", 15.0)
            tax_rate = st.session_state.get("combo_tax_rate", 0.25)
            breakdown = engine.compute_net_realized(realized_input, commission, tax_rate)
            capital_before = engine.total_capital(LEDGER_PATH) + sum(
                r.get("realized_pnl") or 0 for r in rows if r.get("status") == "closed"
            )
            capital_after = capital_before + breakdown["net_pnl"]
            st.markdown(
                "<div dir='rtl' style='color:#D0D0D0;font-size:0.85rem;line-height:1.7;'>"
                f"עמלה: <span dir='ltr'>{breakdown['commission']:.1f}$</span> | "
                f"מס ({tax_rate*100:.0f}% מהרווח, רק אם חיובי): <span dir='ltr'>{breakdown['tax']:.1f}$</span> | "
                f"נטו: <span dir='ltr'>{breakdown['net_pnl']:.1f}$</span>"
                f"<br>הון בפועל: <span dir='ltr'>{capital_before:.0f}$</span> ← לפני | "
                f"<span dir='ltr'>{capital_after:.0f}$</span> ← אחרי הסגירה (משוער)"
                "</div>",
                unsafe_allow_html=True,
            )

            if do_close:
                engine.close_position(i, gross_pnl=realized_input, commission=commission,
                                       tax_rate=tax_rate, path=WATCHLIST_PATH)
                st.rerun()

            if st.button("🗑️ הסר", key=f"combo_remove_{i}"):
                engine.remove_position(i, path=WATCHLIST_PATH)
                st.session_state.pop("combo_refreshed", None)
                st.rerun()


def _render_portfolio_summary():
    with st.expander("⚙️ הגדרות עמלה ומס (חלות על כל סגירת פוזיציה)"):
        commission_input = st.number_input(
            "עמלת קנייה+מכירה יחד ($)", min_value=0.0, value=15.0, step=0.5,
            key="combo_commission_input",
        )
        tax_pct_input = st.number_input(
            "מס על רווח (%, לא חל על הפסד)", min_value=0.0, max_value=100.0, value=25.0, step=1.0,
            key="combo_tax_pct_input",
        )
        st.session_state["combo_commission"] = commission_input
        st.session_state["combo_tax_rate"] = tax_pct_input / 100.0

    st.subheader("💰 יומן הון")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        ledger_amount = st.number_input(
            "סכום (חיובי = הפקדה, שלילי = משיכה)", value=0.0, step=1000.0, key="combo_ledger_amount",
        )
    with c2:
        ledger_note = st.text_input("הערה", key="combo_ledger_note")
    with c3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ הוסף", key="combo_ledger_add") and ledger_amount != 0:
            engine.add_ledger_entry(ledger_amount, note=ledger_note, path=LEDGER_PATH)
            st.rerun()

    ledger = engine.load_ledger(LEDGER_PATH)
    if ledger:
        with st.expander(f"היסטוריית תנועות ({len(ledger)})"):
            for entry in reversed(ledger):
                sign_color = "#8FE38F" if entry["amount"] >= 0 else "#FF9B9B"
                st.markdown(
                    f"<div style='color:#FFFFFF;'>{entry['date']} — "
                    f"<span style='color:{sign_color}'>{entry['amount']:+.0f}$</span> "
                    f"{('— ' + entry['note']) if entry.get('note') else ''}</div>",
                    unsafe_allow_html=True,
                )

    st.divider()
    st.subheader("📊 מצב נוכחי")

    refreshed_open = [
        r for r in st.session_state.get("combo_refreshed", [])
        if r.get("status", "open") == "open"
    ] or None
    summary = engine.portfolio_summary(WATCHLIST_PATH, LEDGER_PATH, refreshed_open=refreshed_open)

    if not summary["total_capital"]:
        st.info("עדיין לא הוזן הון ביומן למעלה — אחוזים ו'נשאר פנוי' יוצגו ברגע שיהיה סכום.")

    m1, m2, m3 = st.columns(3)
    m1.metric("הון שהוכנס (מהיומן בלבד)", f"{summary['total_capital']:.0f}$")
    m2.metric(
        "הון בפועל כרגע", f"{summary['net_worth_now']:.0f}$",
        help="הון שהוכנס + P&L ריאלי מצטבר נטו (אחרי עמלה ומס). כולל תוצאות מסחר, לא רק הפקדות/משיכות.",
    )
    m3.metric("מרג'ין בשימוש (Reg-T)", f"{summary['margin_in_use_reg_t']:.0f}$")

    m4, m5, m6 = st.columns(3)
    remaining = summary["capital_remaining_reg_t"]
    m4.metric("נשאר פנוי (הערכה)", f"{remaining:.0f}$" if remaining is not None else "—",
              help="הון בפועל כרגע פחות המרג'ין בשימוש.")
    m5.metric("פוזיציות פתוחות", summary["open_count"])
    unrl = summary["unrealized_pnl"]
    m6.metric(
        "P&L לא ממומש", f"{unrl:.0f}$" if unrl is not None else "—",
        help="מבוסס על הרענון האחרון ברשימת המעקב. רעננה שם קודם לקבלת מספר עדכני.",
    )

    m7, m8, m9 = st.columns(3)
    m7.metric("P&L ריאלי ברוטו", f"{summary['realized_pnl_gross_total']:.0f}$",
              help="לפני עמלה ומס.")
    m8.metric("עמלות + מס ששולמו", f"{(summary['commission_total'] + summary['tax_total']):.0f}$",
              help=f"עמלה: {summary['commission_total']:.0f}$ | מס: {summary['tax_total']:.0f}$")
    m9.metric("P&L ריאלי נטו", f"{summary['realized_pnl_total']:.0f}$",
              help=f"אחרי עמלה ומס, סה\"כ על {summary['closed_count']} פוזיציות סגורות.")

    if summary["realized_pnl_by_month"]:
        st.markdown("**P&L ריאלי נטו לפי חודש**")
        for ym, pnl in summary["realized_pnl_by_month"].items():
            color = "#8FE38F" if pnl >= 0 else "#FF9B9B"
            st.markdown(
                f"<div style='color:#FFFFFF;'>{ym}: <span style='color:{color}'>{pnl:.0f}$</span></div>",
                unsafe_allow_html=True,
            )
