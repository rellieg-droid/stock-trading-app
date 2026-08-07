"""
Alpha Charts Pro — MOBILE NAV SHELL TEST (Stage 1)
Standalone test of bottom-nav + top-pill navigation, wired to the REAL
design tokens from alpha_paper_trading.py (--c-base, --glass-blur, etc.)
instead of mobile_layout_test.py's separate color dict.

Pages are still placeholders. This file only proves the navigation shell
+ CSS integrate cleanly. Real tab content gets ported in Stage 2, group
by group, once this shell is confirmed working.

Run separately: streamlit run mobile_nav_shell_test.py
"""

import streamlit as st
from streamlit_option_menu import option_menu

st.set_page_config(
    page_title="Alpha Charts Pro — Nav Shell Test",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────────
# NAV STRUCTURE — mapped to the REAL 11 tabs in alpha_paper_trading.py
# (see: thome, t1, t2, t3, t4, t9, t10, t11, t12, t13, t7 = st.tabs([...]))
# ──────────────────────────────────────────────────────────────────────────

NAV_GROUPS = {
    "בית":   {"icon": "house",      "subs": ["🏠 Home"]},
    "גרף":   {"icon": "graph-up",   "subs": ["📈 גרף"]},
    "ניתוח": {"icon": "cpu",        "subs": ["🎯 ניתוח", "⚖️ השוואה"]},
    "מסחר":  {"icon": "cart",       "subs": ["🛒 מסחר", "💼 תיק"]},
    "עוד":   {"icon": "three-dots", "subs": ["⏳ Backtest", "🔔 התראות", "📅 דוחות", "👁️ Watchlist", "📖 מדריך"]},
}
GROUP_ORDER = ["בית", "גרף", "ניתוח", "מסחר", "עוד"]
GROUP_BOTTOM_ICONS = {"בית": "🏠", "גרף": "📈", "ניתוח": "🎯", "מסחר": "🛒", "עוד": "⋯"}


# ──────────────────────────────────────────────────────────────────────────
# CSS — reuses the REAL :root tokens from alpha_paper_trading.py.
# Paste this whole @import + :root block from your main file here so the
# preview is accurate. Only the nav-specific rules below are new.
# ──────────────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
      --c-base:       #05070D;
      --c-surface-1:  rgba(255,255,255,0.035);
      --c-surface-2:  rgba(255,255,255,0.045);
      --c-surface-3:  rgba(255,255,255,0.07);
      --c-border:     rgba(255,255,255,0.08);
      --c-border-md:  rgba(255,255,255,0.14);
      --c-border-act: rgba(77,127,255,0.5);
      --c-text-1:  #F4F6FB;
      --c-text-2:  #8B93A7;
      --c-text-3:  #5A6178;
      --c-blue:    #4D7FFF;
      --c-green:   #2BD46B;
      --c-red:     #F5454F;
      --c-amber:   #E8B84B;
      --c-blue-dim:  rgba(77,127,255,0.14);
      --ff-ui:   'IBM Plex Sans', sans-serif;
      --r4: 12px; --r8: 16px;
      --glass-blur: blur(20px) saturate(150%);
      --glass-shadow: 0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04);
    }

    html, body, .stApp {
      font-family: var(--ff-ui) !important;
      background: radial-gradient(circle at 20% 0%, #0E1730 0%, var(--c-base) 50%) fixed !important;
      color: var(--c-text-1) !important;
      direction: rtl !important;
    }
    #MainMenu, footer, header { visibility: hidden; }
    div[data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stSidebar"] { display: none !important; }

    .block-container {
        padding-top: 0.6rem;
        padding-bottom: 5.5rem;
        max-width: 1100px;
        width: 100%;
        margin: 0 auto;
        min-height: 100vh;
        direction: rtl !important;
    }

    /* ===== TOP PILL NAV (sub-tabs within a group) ===== */
    .top-pill-wrap nav[role="tablist"] { background: transparent !important; }

    /* ===== BOTTOM NAV — real navigation via button form ===== */
    .bottom-nav-spacer { height: 4.6rem; }

    div[data-testid="stHorizontalBlock"]:has(.bottom-nav-marker) {
        position: fixed;
        bottom: 0; left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 1100px;
        background: rgba(5, 7, 13, 0.94);
        backdrop-filter: var(--glass-blur);
        border-top: 1px solid var(--c-border);
        padding: 0.5rem 0.6rem calc(0.5rem + env(safe-area-inset-bottom, 0px));
        z-index: 999;
        margin: 0 !important;
    }
    .bottom-nav-btn button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 1.3rem !important;
        color: var(--c-text-3) !important;
        height: 42px !important;
        width: 100% !important;
        padding: 0 !important;
    }
    .bottom-nav-btn-active button {
        background: var(--c-blue-dim) !important;
        border-radius: 50% !important;
        color: var(--c-blue) !important;
        width: 42px !important;
        margin: 0 auto !important;
    }

    .placeholder-card {
        background: var(--c-surface-1);
        border: 1px solid var(--c-border);
        border-radius: var(--r8);
        backdrop-filter: var(--glass-blur);
        box-shadow: var(--glass-shadow);
        padding: 1.5rem;
        text-align: center;
        color: var(--c-text-2);
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# PLACEHOLDER PAGE BODY — real content gets ported here group by group
# in Stage 2. For now this just proves navigation switches correctly.
# ──────────────────────────────────────────────────────────────────────────

def page_placeholder(sub_tab_name):
    st.markdown(
        f'<div class="placeholder-card">תוכן הטאב "{sub_tab_name}" יעבור לכאן בשלב 2</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────
# NAV RENDERING
# ──────────────────────────────────────────────────────────────────────────

def render_top_pill(active_group):
    subs = NAV_GROUPS[active_group]["subs"]
    if len(subs) == 1:
        return subs[0]  # no sub-nav needed, single page in this group
    default_sub = st.session_state.get(f"sub_{active_group}", subs[0])
    default_idx = subs.index(default_sub) if default_sub in subs else 0

    st.markdown('<div class="top-pill-wrap">', unsafe_allow_html=True)
    selected = option_menu(
        menu_title=None, options=subs, default_index=default_idx,
        orientation="horizontal",
        styles={
            "container": {"padding": "4px", "background-color": "rgba(255,255,255,0.035)",
                          "border": "1px solid rgba(255,255,255,0.08)", "border-radius": "999px",
                          "margin": "0 0 0.9rem 0"},
            "nav-link": {"font-size": "11px", "font-weight": "600", "color": "#5A6178",
                        "text-align": "center", "border-radius": "999px", "padding": "8px 6px", "margin": "0px"},
            "nav-link-selected": {"background-color": "#4D7FFF", "color": "#FFFFFF"},
        },
        key=f"pill_{active_group}",
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.session_state[f"sub_{active_group}"] = selected
    return selected


def render_bottom_nav(active_group):
    st.markdown('<div class="bottom-nav-spacer"></div>', unsafe_allow_html=True)
    cols = st.columns(len(GROUP_ORDER))
    for i, group in enumerate(GROUP_ORDER):
        with cols[i]:
            is_active = (group == active_group)
            st.markdown(
                f'<div class="bottom-nav-btn{" bottom-nav-btn-active" if is_active else ""} bottom-nav-marker">',
                unsafe_allow_html=True,
            )
            if st.button(GROUP_BOTTOM_ICONS[group], key=f"nav_{group}", use_container_width=True):
                st.session_state.active_group = group
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────

def main():
    inject_css()

    if "active_group" not in st.session_state:
        st.session_state.active_group = "בית"

    st.markdown('<h3 style="text-align:center;">Alpha Charts Pro 👑</h3>', unsafe_allow_html=True)
    st.write("")

    active_group = st.session_state.active_group
    active_sub = render_top_pill(active_group)

    page_placeholder(active_sub)

    render_bottom_nav(active_group)


if __name__ == "__main__":
    main()
