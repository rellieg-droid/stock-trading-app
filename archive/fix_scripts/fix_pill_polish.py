"""
Stage 3b fix script — refines the period-pill design + adds a settings
dropdown button at the right edge (RTL start).
Run from the project folder:  python fix_pill_polish.py
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    st.markdown("""
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
'''

NEW_BLOCK = '''    st.markdown("""
    <style>
    .st-key-period_pills .stButton > button,
    .st-key-charttype_pills .stButton > button {
        background: transparent !important;
        border: 1px solid var(--c-border) !important;
        color: var(--c-text-2) !important;
        border-radius: 999px !important;
        font-family: var(--ff-mono) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 6px 4px !important;
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
'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written.")
        print("The pill block doesn't match exactly (maybe already changed).")
        print("Tell Claude and paste the current content from")
        print('"st.markdown(\\"\\"\\"\\n    <style>\\n    .st-key-period_pills" through the closing')
        print('"for _pk, _pcol in zip(...)" loop.')
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1). Tell Claude before proceeding.")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — pill hover/focus states added, true pill shape, settings dropdown added at right edge.")


if __name__ == "__main__":
    main()
