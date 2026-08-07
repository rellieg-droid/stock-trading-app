"""
Stage 3d fix script — merges the two toolbar rows (period pills + chart
type/DATA/AI/reset) into a single row, and fixes the settings button
that was showing solid white instead of transparent (the CSS selector
targeting Streamlit's internal popover markup wasn't matching reliably
— switched to the same st.container(key=...) technique already proven
to work everywhere else in this app).
Run from the project folder:  python fix_toolbar_merge.py
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    # ── Time range + chart type — clean pill buttons (Yahoo/Investing style) ──
    _periods_list = list(PERIODS.keys())
    _cur_period   = st.session_state.period

    st.markdown("""
    <style>
    .st-key-period_pills .stButton > button,
    .st-key-charttype_pills .stButton > button {
        background: transparent !important;
        border: 1px solid var(--c-border) !important;
        color: var(--c-text-2) !important;
        border-radius: 999px !important;
        font-family: var(--ff-mono) !important;
        font-size: 10.5px !important;
        font-weight: 600 !important;
        padding: 4px 2px !important;
        white-space: nowrap !important;
        min-width: 0 !important;
        transition: all 0.15s ease !important;
    }
    .st-key-period_pills .stButton > button:hover,
    .st-key-charttype_pills .stButton > button:hover {
        background: var(--c-surface-2) !important;
        border-color: var(--c-border-md) !important;
        color: var(--c-text-1) !important;
    }
    .st-key-period_pills .stButton > button:focus-visible,
    .st-key-charttype_pills .stButton > button:focus-visible {
        outline: 2px solid var(--c-blue) !important;
        outline-offset: 1px !important;
    }
    .st-key-period_pills .stButton > button[kind="primary"],
    .st-key-charttype_pills .stButton > button[kind="primary"] {
        background: var(--c-blue) !important;
        border-color: var(--c-blue) !important;
        color: #fff !important;
    }
    .st-key-period_pills .stButton > button[kind="primary"]:hover,
    .st-key-charttype_pills .stButton > button[kind="primary"]:hover {
        background: var(--c-blue-lt) !important;
        border-color: var(--c-blue-lt) !important;
    }
    .st-key-period_pills [data-testid="stPopover"] > button {
        background: transparent !important;
        border: 1px solid var(--c-border) !important;
        border-radius: 999px !important;
        color: var(--c-text-2) !important;
        font-size: 13px !important;
        padding: 6px 4px !important;
        transition: all 0.15s ease !important;
    }
    .st-key-period_pills [data-testid="stPopover"] > button:hover {
        background: var(--c-surface-2) !important;
        color: var(--c-text-1) !important;
        border-color: var(--c-border-md) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="period_pills"):
        _settings_col, *_p_cols = st.columns([1] + [1] * len(_periods_list))
        with _settings_col:
            with st.popover("⚙ ⌄", use_container_width=True):
                st.caption("הגדרות תצוגה נוספות")
                st.caption("(מקום שמור להרחבות עתידיות)")
        for _pk, _pcol in zip(_periods_list, _p_cols):
            with _pcol:
                if st.button(_pk, key=f"period_{_pk}", use_container_width=True,
                             type="primary" if _pk == _cur_period else "secondary"):
                    st.session_state.period = _pk
                    st.rerun()

    _tc2, _tc3, _tc4, _tc5 = st.columns([3, 1, 1, 1])

    with _tc2:
        with st.container(key="charttype_pills"):
            _ct_opts = [("line", "קווי"), ("candlestick", "נרות"), ("area", "שטח")]
            _ct_cols = st.columns(len(_ct_opts))
            for (_cval, _clab), _ccol in zip(_ct_opts, _ct_cols):
                with _ccol:
                    if st.button(_clab, key=f"ct_{_cval}", use_container_width=True,
                                 type="primary" if st.session_state.ct == _cval else "secondary"):
                        st.session_state.ct = _cval
                        st.rerun()

    with _tc3:
        _an_on = st.session_state.show_an
        if st.button("DATA" + ("●" if _an_on else ""), key="aan",
                     use_container_width=True,
                     type="primary" if _an_on else "secondary"):
            st.session_state.show_an = not _an_on; st.rerun()

    with _tc4:
        _ai_on = st.session_state.show_ai
        if st.button("AI" + ("●" if _ai_on else ""), key="aai",
                     use_container_width=True,
                     type="primary" if _ai_on else "secondary"):
            st.session_state.show_ai = not _ai_on
            if st.session_state.show_ai and st.session_state.ai_res is None:
                with st.spinner(""):
                    try:
                        cl2     = df['Close'].astype(float)
                        lc2     = float(cl2.iloc[-1]); pc2 = float(cl2.iloc[-2])
                        dc2     = (lc2 - pc2) / pc2 * 100
                        rsi2    = float(df['RSI'].iloc[-1]) if 'RSI' in df.columns else 50
                        ma200_2 = float(df['MA200'].iloc[-1]) if 'MA200' in df.columns else lc2
                        vok2    = False
                        if 'Volume' in df.columns:
                            vol2 = df['Volume'].astype(float)
                            avg2 = float(vol2.rolling(20).mean().iloc[-1])
                            vok2 = float(vol2.iloc[-1]) > avg2 * 1.2 if avg2 > 0 else False
                        prompt = (
                            f"Analyze {ticker}: price {lc2:.2f}, change {dc2:+.2f}%, "
                            f"RSI {rsi2:.0f}, "
                            + ("above" if lc2 > ma200_2 else "below")
                            + " MA200. Return ONLY JSON no markdown: "
                            '{"trend":"שורי/דובי/נייטרלי","strength":"חזק/בינוני/חלש",'
                            '"signal":"3 words Hebrew","vol_ok":' + str(vok2).lower() + ','
                            '"summary":"2 sentences Hebrew","detail":"1 sentence Hebrew"}'
                        )
                        resp = requests.post(
                            "https://api.anthropic.com/v1/messages",
                            headers=ai_headers(),
                            json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                                  "messages": [{"role": "user", "content": prompt}]},
                            timeout=15
                        )
                        if resp.status_code == 200:
                            txt = resp.json()['content'][0]['text'].strip().replace("```json","").replace("```","")
                            st.session_state.ai_res = json.loads(txt)
                        else:
                            raise Exception()
                    except:
                        st.session_state.ai_res = {
                            "trend": "שורי" if dc2 > 0 else "דובי",
                            "strength": "בינוני", "signal": "איתות מתון",
                            "vol_ok": False,
                            "summary": f"המניה {ticker} שינתה {dc2:+.2f}% עם RSI {rsi2:.0f}.",
                            "detail": f"הנר נסגר {'בעלייה' if dc2>0 else 'בירידה'}.",
                        }
            st.rerun()

    with _tc5:
        if st.button("↺", key="arst", use_container_width=True):
            st.session_state.period   = "1Y"
            st.session_state.ct       = "line"
            st.session_state.show_an  = False
            st.session_state.show_ai  = False
            st.rerun()
'''

NEW_BLOCK = '''    # ── Toolbar — single unified row (Yahoo/Investing style pills) ──
    _periods_list = list(PERIODS.keys())
    _cur_period   = st.session_state.period
    _ct_opts      = [("line", "קווי"), ("candlestick", "נרות"), ("area", "שטח")]

    st.markdown("""
    <style>
    .st-key-toolbar_row .stButton > button {
        background: transparent !important;
        border: 1px solid var(--c-border) !important;
        color: var(--c-text-2) !important;
        border-radius: 999px !important;
        font-family: var(--ff-mono) !important;
        font-size: 10.5px !important;
        font-weight: 600 !important;
        padding: 4px 2px !important;
        white-space: nowrap !important;
        min-width: 0 !important;
        transition: all 0.15s ease !important;
    }
    .st-key-toolbar_row .stButton > button:hover {
        background: var(--c-surface-2) !important;
        border-color: var(--c-border-md) !important;
        color: var(--c-text-1) !important;
    }
    .st-key-toolbar_row .stButton > button:focus-visible {
        outline: 2px solid var(--c-blue) !important;
        outline-offset: 1px !important;
    }
    .st-key-toolbar_row .stButton > button[kind="primary"] {
        background: var(--c-blue) !important;
        border-color: var(--c-blue) !important;
        color: #fff !important;
    }
    .st-key-toolbar_row .stButton > button[kind="primary"]:hover {
        background: var(--c-blue-lt) !important;
        border-color: var(--c-blue-lt) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="toolbar_row"):
        _n_items = 1 + len(_periods_list) + len(_ct_opts) + 3  # settings + periods + chart-types + DATA + AI + reset
        _tb_cols = st.columns(_n_items)
        _i = 0

        with _tb_cols[_i]:
            with st.popover("⚙ ⌄", use_container_width=True):
                st.caption("הגדרות תצוגה נוספות")
                st.caption("(מקום שמור להרחבות עתידיות)")
        _i += 1

        for _pk in _periods_list:
            with _tb_cols[_i]:
                if st.button(_pk, key=f"period_{_pk}", use_container_width=True,
                             type="primary" if _pk == _cur_period else "secondary"):
                    st.session_state.period = _pk
                    st.rerun()
            _i += 1

        for _cval, _clab in _ct_opts:
            with _tb_cols[_i]:
                if st.button(_clab, key=f"ct_{_cval}", use_container_width=True,
                             type="primary" if st.session_state.ct == _cval else "secondary"):
                    st.session_state.ct = _cval
                    st.rerun()
            _i += 1

        with _tb_cols[_i]:
            _an_on = st.session_state.show_an
            if st.button("DATA" + ("●" if _an_on else ""), key="aan",
                         use_container_width=True,
                         type="primary" if _an_on else "secondary"):
                st.session_state.show_an = not _an_on; st.rerun()
        _i += 1

        with _tb_cols[_i]:
            _ai_on = st.session_state.show_ai
            if st.button("AI" + ("●" if _ai_on else ""), key="aai",
                         use_container_width=True,
                         type="primary" if _ai_on else "secondary"):
                st.session_state.show_ai = not _ai_on
                if st.session_state.show_ai and st.session_state.ai_res is None:
                    with st.spinner(""):
                        try:
                            cl2     = df['Close'].astype(float)
                            lc2     = float(cl2.iloc[-1]); pc2 = float(cl2.iloc[-2])
                            dc2     = (lc2 - pc2) / pc2 * 100
                            rsi2    = float(df['RSI'].iloc[-1]) if 'RSI' in df.columns else 50
                            ma200_2 = float(df['MA200'].iloc[-1]) if 'MA200' in df.columns else lc2
                            vok2    = False
                            if 'Volume' in df.columns:
                                vol2 = df['Volume'].astype(float)
                                avg2 = float(vol2.rolling(20).mean().iloc[-1])
                                vok2 = float(vol2.iloc[-1]) > avg2 * 1.2 if avg2 > 0 else False
                            prompt = (
                                f"Analyze {ticker}: price {lc2:.2f}, change {dc2:+.2f}%, "
                                f"RSI {rsi2:.0f}, "
                                + ("above" if lc2 > ma200_2 else "below")
                                + " MA200. Return ONLY JSON no markdown: "
                                '{"trend":"שורי/דובי/נייטרלי","strength":"חזק/בינוני/חלש",'
                                '"signal":"3 words Hebrew","vol_ok":' + str(vok2).lower() + ','
                                '"summary":"2 sentences Hebrew","detail":"1 sentence Hebrew"}'
                            )
                            resp = requests.post(
                                "https://api.anthropic.com/v1/messages",
                                headers=ai_headers(),
                                json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                                      "messages": [{"role": "user", "content": prompt}]},
                                timeout=15
                            )
                            if resp.status_code == 200:
                                txt = resp.json()['content'][0]['text'].strip().replace("```json","").replace("```","")
                                st.session_state.ai_res = json.loads(txt)
                            else:
                                raise Exception()
                        except:
                            st.session_state.ai_res = {
                                "trend": "שורי" if dc2 > 0 else "דובי",
                                "strength": "בינוני", "signal": "איתות מתון",
                                "vol_ok": False,
                                "summary": f"המניה {ticker} שינתה {dc2:+.2f}% עם RSI {rsi2:.0f}.",
                                "detail": f"הנר נסגר {'בעלייה' if dc2>0 else 'בירידה'}.",
                            }
                st.rerun()
        _i += 1

        with _tb_cols[_i]:
            if st.button("↺", key="arst", use_container_width=True):
                st.session_state.period   = "1Y"
                st.session_state.ct       = "line"
                st.session_state.show_an  = False
                st.session_state.show_ai  = False
                st.rerun()
'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written. Block not found (maybe already changed).")
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1).")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — toolbar merged into one row, settings button fixed.")


if __name__ == "__main__":
    main()
