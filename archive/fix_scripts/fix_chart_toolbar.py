"""
Stage 3 fix script — redesigns the chart tab toolbar.
Run from the project folder:  python fix_chart_toolbar.py

What it does:
- Removes the "IND" toggle button and the entire indicator checkbox panel
  (CH, TL, Fib, S/R, BB, 200, MA20, MA50). Those overlays keep whatever
  their default is (MA20 + MA50 ON, everything else OFF — same as what
  you're seeing right now, so the chart won't look different) — they just
  can't be toggled from the UI anymore.
- Replaces the tiny display-only period/chart-type text row with real,
  clickable pill buttons styled like Yahoo/Investing (rounded, blue when
  active), using the same st.container(key=...) technique already
  proven working for the nav bar.

Safe by design: matches the OLD block as one exact contiguous string.
If your file doesn't match exactly (already hand-edited), it stops
and tells you, without touching anything.
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    # ── Time range — segmented ──
    _periods_list = list(PERIODS.keys())
    _cur_period   = st.session_state.period

    _period_html = ""
    for _pk in _periods_list:
        _pa = _pk == _cur_period
        _period_html += (
            f'<span style="padding:3px 9px;cursor:pointer;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;font-weight:{"700" if _pa else "400"};'
            f'color:{"#E8ECF1" if _pa else "#7C8897"};'
            f'background:{"rgba(255,255,255,0.09)" if _pa else "transparent"};'
            f'border-radius:3px;white-space:nowrap;">{_pk}</span>'
        )

    # ── Chart type — segmented ──
    _ct_opts   = [("L","line","קווי"),("C","candlestick","נרות"),("A","area","שטח")]
    _ct_html   = ""
    for _clab, _cval, _ctip in _ct_opts:
        _ca = st.session_state.ct == _cval
        _ct_html += (
            f'<span title="{_ctip}" style="padding:3px 8px;cursor:pointer;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;font-weight:{"700" if _ca else "400"};'
            f'color:{"#E8ECF1" if _ca else "#7C8897"};'
            f'background:{"rgba(255,255,255,0.09)" if _ca else "transparent"};'
            f'border-radius:3px;">{_clab}</span>'
        )

    # ── Display-only toolbar ──
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0;background:#0A0D13;'
        f'border:1px solid rgba(255,255,255,0.08);border-radius:5px;'
        f'padding:3px 8px;margin-bottom:6px;direction:ltr;overflow:hidden;">'
        # Time range group
        f'<div style="display:flex;align-items:center;gap:1px;padding-right:10px;'
        f'border-right:1px solid rgba(255,255,255,0.08);">'
        f'{_period_html}</div>'
        # Sep
        f'<div style="width:1px;height:16px;background:rgba(255,255,255,0.08);margin:0 8px;"></div>'
        # Chart type
        f'<div style="display:flex;align-items:center;gap:1px;border:1px solid rgba(255,255,255,0.08);'
        f'border-radius:3px;padding:1px;">{_ct_html}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Functional controls (hidden label, compact) ──
    _tc1, _tc2, _tc3, _tc4, _tc5, _tc6, _tc7 = st.columns([4, 2, 1, 1, 1, 1, 1])

    with _tc1:
        _np = st.radio("P", _periods_list,
                        index=_periods_list.index(_cur_period),
                        horizontal=True, label_visibility="collapsed", key="pr")
        if _np != st.session_state.period:
            st.session_state.period = _np; st.rerun()

    with _tc2:
        _ct_labels = ["קווי", "נרות", "שטח"]
        _ct_vals   = {"קווי":"line","נרות":"candlestick","שטח":"area"}
        _ct_inv    = {"line":"קווי","candlestick":"נרות","area":"שטח"}
        _nct = st.radio("T", _ct_labels,
                         index=_ct_labels.index(_ct_inv[st.session_state.ct]),
                         horizontal=True, label_visibility="collapsed", key="ctr")
        if _ct_vals[_nct] != st.session_state.ct:
            st.session_state.ct = _ct_vals[_nct]; st.rerun()

    with _tc3:
        _ind_on = st.session_state.show_ind
        if st.button("IND" + ("●" if _ind_on else ""), key="aind",
                     use_container_width=True,
                     type="primary" if _ind_on else "secondary"):
            st.session_state.show_ind = not _ind_on; st.rerun()

    with _tc4:
        _an_on = st.session_state.show_an
        if st.button("DATA" + ("●" if _an_on else ""), key="aan",
                     use_container_width=True,
                     type="primary" if _an_on else "secondary"):
            st.session_state.show_an = not _an_on; st.rerun()

    with _tc5:
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

    with _tc6:
        pass  # spacer

    with _tc7:
        if st.button("↺", key="arst", use_container_width=True):
            st.session_state.period   = "1Y"
            st.session_state.ct       = "line"
            st.session_state.show_an  = False
            st.session_state.show_ai  = False
            st.session_state.show_ind = True
            st.rerun()

    # ── Indicators panel — compact terminal group ──
    if st.session_state.show_ind:
        st.markdown(
            '<div style="background:#0A0D13;border:1px solid rgba(255,255,255,0.08);'
            'border-radius:4px;padding:5px 10px;margin:3px 0 6px;direction:rtl;">'
            '<span style="font-size:10px;font-weight:600;color:rgba(255,255,255,0.28);'
            'text-transform:uppercase;letter-spacing:0.08em;margin-left:10px;">MA</span>',
            unsafe_allow_html=True
        )
        _ic1, _ic2, _ic3, _ic4, _ic5, _ic6, _ic7, _ic8 = st.columns(8)
        st.session_state.ma20      = _ic1.checkbox("20",  value=st.session_state.ma20,      key="c20")
        st.session_state.ma50      = _ic2.checkbox("50",  value=st.session_state.ma50,      key="c50")
        st.session_state.ma200     = _ic3.checkbox("200", value=st.session_state.ma200,     key="c200")
        st.session_state.bb        = _ic4.checkbox("BB",  value=st.session_state.bb,        key="cbb")
        st.session_state.sr        = _ic5.checkbox("S/R", value=st.session_state.sr,        key="csr")
        st.session_state.fib       = _ic6.checkbox("Fib", value=st.session_state.fib,       key="cfib")
        st.session_state.trendline = _ic7.checkbox("TL",  value=st.session_state.trendline, key="ctrl")
        st.session_state.channel   = _ic8.checkbox("CH",  value=st.session_state.channel,   key="cch")
        st.markdown('</div>', unsafe_allow_html=True)
'''

NEW_BLOCK = '''    # ── Time range + chart type — clean pill buttons (Yahoo/Investing style) ──
    _periods_list = list(PERIODS.keys())
    _cur_period   = st.session_state.period

    st.markdown("""
    <style>
    .st-key-period_pills .stButton > button,
    .st-key-charttype_pills .stButton > button {
        background: var(--c-surface-2) !important;
        border: 1px solid var(--c-border) !important;
        color: var(--c-text-2) !important;
        border-radius: var(--r4) !important;
        font-family: var(--ff-mono) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 4px 0 !important;
    }
    .st-key-period_pills .stButton > button[kind="primary"],
    .st-key-charttype_pills .stButton > button[kind="primary"] {
        background: var(--c-blue) !important;
        border-color: var(--c-blue) !important;
        color: #fff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="period_pills"):
        _p_cols = st.columns(len(_periods_list))
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


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written.")
        print("The toolbar block in your file doesn't match exactly what this script expects.")
        print("This can happen if you've already hand-edited that section.")
        print("Tell Claude, and paste the current content of the toolbar section")
        print('(from "# ── Time range — segmented ──" through the indicators panel).')
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1). Tell Claude before proceeding.")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — chart toolbar redesigned: pill buttons for period/chart-type, indicator checkboxes removed.")


if __name__ == "__main__":
    main()
