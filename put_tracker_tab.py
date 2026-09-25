# -*- coding: utf-8 -*-
"""
put_tracker_tab.py

Streamlit tab that surfaces put_premium_tracker.py inside RiskShield.

render_put_tracker_tab(key_prefix=...) must be called with the SAME
key_prefix used by render_riskshield_tab(), so the "pull from OTM tab"
button can find that tab's session_state values
(f"{key_prefix}_ticker", f"{key_prefix}_prob_K_{ticker}", etc.).
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

import put_premium_tracker as tracker

STATUS_LABELS = {
    "open": "פתוחה",
    "expired_worthless": "פקעה חסרת ערך",
    "closed_manual": "נסגרה ידנית",
    "assigned": "הוקצתה (assignment)",
}

# Experimental fix: the app wraps everything in `.rs-wrap * { direction: rtl }`,
# which can make typing an English ticker symbol feel broken (cursor jumps).
# This targets ONLY the block immediately after the #pt-symbol-marker span,
# forcing that one input back to LTR. If this doesn't fix it, the marker
# technique itself may not be matching Streamlit's current DOM structure —
# that's useful to know either way.
_SYMBOL_LTR_CSS = """
<style>
div:has(> #pt-symbol-marker) + div input {
  direction: ltr !important;
  text-align: left !important;
  unicode-bidi: plaintext;
}
</style>
"""


def _pull_from_otm_tab(key_prefix: str) -> bool:
    """Copy symbol/strike/premium/spot/expiry date from the OTM Probability tab's
    session_state into this tab's form fields. Returns True if a ticker
    was found to pull from."""
    ticker = st.session_state.get(f"{key_prefix}_ticker", "")
    if not ticker:
        return False

    strike = st.session_state.get(f"{key_prefix}_prob_K_{ticker}")
    premium = st.session_state.get(f"{key_prefix}_prob_premium")
    stock_price = st.session_state.get(f"{key_prefix}_prob_S_{ticker}")
    # טאב OTM: selectbox מהשרשרת (מחרוזת ISO) או date_input חופשי כשאין שרשרת
    exp_raw = (st.session_state.get(f"{key_prefix}_prob_exp_{ticker}")
               or st.session_state.get(f"{key_prefix}_prob_exp_free_{ticker}"))

    st.session_state["pt_symbol"] = ticker.upper()
    if strike is not None:
        st.session_state["pt_strike"] = float(strike)
    if premium is not None:
        st.session_state["pt_premium"] = float(premium)
    if stock_price is not None:
        st.session_state["pt_stock_price"] = float(stock_price)
    st.session_state["pt_sale_date"] = date.today()
    if isinstance(exp_raw, str):
        st.session_state["pt_expiration_date"] = date.fromisoformat(exp_raw)
    elif isinstance(exp_raw, date):
        st.session_state["pt_expiration_date"] = exp_raw
    return True


def _rs_table(headers: list, rows: list) -> str:
    """Build an .rs-table HTML table (st.dataframe doesn't respect RTL in this app)."""
    thead = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return (
        f'<div style="overflow-x:auto;"><table class="rs-table">'
        f'<thead><tr>{thead}</tr></thead><tbody>{trs}</tbody></table></div>'
    )


def render_put_tracker_tab(key_prefix: str = "riskshield", db_path: str = tracker.DB_PATH) -> None:
    tracker.init_db(db_path)
    st.markdown(_SYMBOL_LTR_CSS, unsafe_allow_html=True)

    st.subheader("📒 מעקב פרמיות — מכירת PUT")

    # --- Summary metrics -----------------------------------------------
    summary = tracker.get_summary(db_path)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("סה\"כ פרמיה שנגבתה", f"${summary['total_premium_collected']:,.2f}")
    c2.metric("רווח ממומש", f"${summary['realized_pnl']:,.2f}")
    c3.metric("חשיפה פתוחה (פרמיה)", f"${summary['open_exposure_premium']:,.2f}")
    win, loss = summary["win_count"], summary["loss_count"]
    win_rate = f"{(win / (win + loss) * 100):.0f}%" if (win + loss) else "—"
    c4.metric("אחוז הצלחה", win_rate, help=f"{win} רווחיות מתוך {win + loss} סגורות")

    st.divider()

    # --- Add new position ------------------------------------------------
    with st.expander("➕ הוספת מכירת PUT חדשה", expanded=True):
        pull_col, hint_col = st.columns([1, 3])
        with pull_col:
            if st.button("⬇️ משוך מהסתברות OTM", key="pt_pull_from_otm"):
                if _pull_from_otm_tab(key_prefix):
                    st.rerun()
                else:
                    st.warning("לא נמצא טיקר בטאב 'הסתברות OTM' — מלאי שם מניה שם קודם")
        with hint_col:
            st.caption("שולף סימבול, סטרייק, פרמיה, מחיר מניה ותאריך פקיעה מהטאב 'הסתברות OTM (Put)'")

        with st.form("add_put_form", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                st.markdown('<span id="pt-symbol-marker" style="display:none"></span>', unsafe_allow_html=True)
                symbol = st.text_input("סימבול", key="pt_symbol").upper().strip()
            strike = fc2.number_input("סטרייק", min_value=0.0, step=0.5, key="pt_strike")
            contracts = fc3.number_input("מספר חוזים", min_value=1, step=1, key="pt_contracts", value=1)

            fc4, fc5, fc6 = st.columns(3)
            premium = fc4.number_input("פרמיה שהתקבלה (למניה)", min_value=0.0, step=0.05, key="pt_premium")
            stock_price = fc5.number_input("מחיר מניה בזמן המכירה", min_value=0.0, step=0.5, key="pt_stock_price")
            sale_date = fc6.date_input("תאריך מכירה", key="pt_sale_date", value=date.today())

            expiration_date = st.date_input("תאריך פקיעה", key="pt_expiration_date", value=date.today())
            notes = st.text_input("הערות (אופציונלי)", key="pt_notes")

            submitted = st.form_submit_button("שמור פוזיציה")
            if submitted:
                if not symbol or premium <= 0 or strike <= 0:
                    st.error("יש למלא סימבול, סטרייק ופרמיה תקינים")
                else:
                    tracker.add_put_sale(
                        symbol=symbol,
                        strike=strike,
                        premium_received=premium,
                        sale_date=sale_date.isoformat(),
                        expiration_date=expiration_date.isoformat(),
                        contracts=int(contracts),
                        stock_price_at_sale=stock_price or None,
                        notes=notes,
                        db_path=db_path,
                    )
                    st.success(f"נשמרה פוזיציית PUT על {symbol}")
                    st.rerun()

    st.divider()

    # --- Positions table ---------------------------------------------
    conn = _connect(db_path)
    rows = conn.execute("SELECT * FROM put_positions ORDER BY sale_date DESC").fetchall()
    conn.close()

    if not rows:
        st.info("אין עדיין פוזיציות רשומות")
        return

    df = pd.DataFrame([dict(r) for r in rows])
    df["סטטוס"] = df["status"].map(STATUS_LABELS)

    open_df = df[df["status"] == "open"]
    closed_df = df[df["status"] != "open"]

    if not open_df.empty:
        st.markdown("**פוזיציות פתוחות**")
        open_rows_html = [
            [
                r["symbol"],
                f'${r["strike"]:,.2f}',
                int(r["contracts"]),
                f'${r["premium_received"]:,.2f}',
                r["sale_date"],
                r["expiration_date"],
                r["notes"] or "—",
            ]
            for _, r in open_df.iterrows()
        ]
        st.markdown(
            _rs_table(
                ["סימבול", "סטרייק", "חוזים", "פרמיה", "תאריך מכירה", "תאריך פקיעה", "הערות"],
                open_rows_html,
            ),
            unsafe_allow_html=True,
        )

        st.markdown("**סגירת פוזיציה**")
        pos_id = st.selectbox(
            "בחר פוזיציה לסגירה",
            options=open_df["id"].tolist(),
            format_func=lambda i: f"#{i} — {open_df.loc[open_df['id']==i, 'symbol'].values[0]} "
                                   f"(סטרייק {open_df.loc[open_df['id']==i, 'strike'].values[0]})",
        )
        close_type = st.radio(
            "סוג סגירה",
            ["פקעה חסרת ערך (הרווח המלא)", "נסגרה ידנית (buyback)", "הוקצתה (assignment)"],
            horizontal=True,
        )

        if close_type == "פקעה חסרת ערך (הרווח המלא)":
            if st.button("אשר סגירה"):
                tracker.close_expired_worthless(pos_id, db_path=db_path)
                st.rerun()

        elif close_type == "נסגרה ידנית (buyback)":
            buyback_premium = st.number_input("פרמיה ששולמה לסגירה (למניה)", min_value=0.0, step=0.05)
            if st.button("אשר סגירה"):
                tracker.close_manual(pos_id, premium_paid_to_close=buyback_premium, db_path=db_path)
                st.rerun()

        else:  # assignment
            if st.button("אשר assignment"):
                tracker.mark_assigned(pos_id, db_path=db_path)
                st.rerun()

    if not closed_df.empty:
        st.markdown("**פוזיציות סגורות**")
        closed_rows_html = [
            [
                r["symbol"],
                f'${r["strike"]:,.2f}',
                int(r["contracts"]),
                f'${r["premium_received"]:,.2f}',
                r["סטטוס"],
                r["close_date"] or "—",
                f'${r["premium_paid_to_close"]:,.2f}' if pd.notna(r["premium_paid_to_close"]) else "—",
            ]
            for _, r in closed_df.iterrows()
        ]
        st.markdown(
            _rs_table(
                ["סימבול", "סטרייק", "חוזים", "פרמיה שהתקבלה", "סטטוס", "תאריך סגירה", "פרמיה ששולמה לסגירה"],
                closed_rows_html,
            ),
            unsafe_allow_html=True,
        )

    # --- Per-symbol breakdown --------------------------------------------
    if summary["by_symbol"]:
        st.divider()
        st.markdown("**פירוט לפי סימבול**")
        sym_rows_html = [
            [sym, f'${vals["premium_collected"]:,.2f}', f'${vals["realized_pnl"]:,.2f}']
            for sym, vals in summary["by_symbol"].items()
        ]
        st.markdown(
            _rs_table(["סימבול", "פרמיה שנגבתה", "רווח ממומש"], sym_rows_html),
            unsafe_allow_html=True,
        )

    # --- Monthly / yearly realized P&L breakdown -------------------------
    monthly, yearly = tracker.get_pnl_by_period(db_path)
    if monthly or yearly:
        st.divider()
        st.markdown("**רווח/הפסד ממומש לפי תקופה**")
        period_view = st.radio("תצוגה", ["חודשי", "שנתי"], horizontal=True, key="pt_period_view")

        data = monthly if period_view == "חודשי" else yearly
        period_label = "חודש" if period_view == "חודשי" else "שנה"

        rows_html = [
            [
                r["period"],
                f'${r["realized_pnl"]:,.2f}',
                r["closed_count"],
            ]
            for r in data
        ]
        st.markdown(
            _rs_table([period_label, "רווח/הפסד ממומש", "פוזיציות שנסגרו"], rows_html),
            unsafe_allow_html=True,
        )


def _connect(db_path: str):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    st.set_page_config(page_title="Put Premium Tracker", layout="wide")
    render_put_tracker_tab()
