# Stage 2 Patch — alpha_paper_trading.py
# עובדים לפי הסדר, שומרים ובודקים אחרי כל שלב.
# את כבר על branch mobile-nav-redesign, אז יש רשת ביטחון.

## שלב א' — הוספת import
מוצאת (שורה 14):
```python
from streamlit_autorefresh import st_autorefresh
```
מוסיפה מתחת לה:
```python
from streamlit_option_menu import option_menu
```

## שלב ב' — החלפת הצהרת הטאבים
מוצאת (שורות 2070-2076):
```python
# ── MAIN TABS ──
# ── Tab groups ──
thome, t1, t2, t3, t4, t9, t10, t11, t12, t13, t7 = st.tabs([
    "🏠 Home", "📈 גרף", "🎯 ניתוח", "⏳ Backtest",
    "🛒 מסחר", "⚖️ השוואה", "💼 תיק",
    "🔔 התראות", "📅 דוחות", "👁️ Watchlist", "📖 מדריך"
])
```

מחליפה בכל הבלוק הזה:
```python
# ── MOBILE NAV SHELL — replaces st.tabs() ──
NAV_GROUPS = {
    "בית":   {"icon": "house",      "subs": ["🏠 Home"]},
    "גרף":   {"icon": "graph-up",   "subs": ["📈 גרף"]},
    "ניתוח": {"icon": "cpu",        "subs": ["🎯 ניתוח", "⚖️ השוואה"]},
    "מסחר":  {"icon": "cart",       "subs": ["🛒 מסחר", "💼 תיק"]},
    "עוד":   {"icon": "three-dots", "subs": ["⏳ Backtest", "🔔 התראות", "📅 דוחות", "👁️ Watchlist", "📖 מדריך"]},
}
GROUP_ORDER = ["בית", "גרף", "ניתוח", "מסחר", "עוד"]
GROUP_BOTTOM_ICONS = {"בית": "🏠", "גרף": "📈", "ניתוח": "🎯", "מסחר": "🛒", "עוד": "⋯"}

st.markdown("""
<style>
.st-key-top_nav {
    position: sticky; top: 0; width: 100%;
    background: rgba(5, 7, 13, 0.94);
    backdrop-filter: var(--glass-blur);
    border-bottom: 1px solid var(--c-border);
    padding: 0.5rem 0.6rem; z-index: 999; margin-bottom: 0.8rem;
}
.st-key-top_nav .stButton > button {
    background: transparent !important; border: none !important; box-shadow: none !important;
    font-size: 1.3rem !important; color: var(--c-text-3) !important;
    height: 42px !important; width: 100% !important; padding: 0 !important;
}
.st-key-top_nav .stButton > button[kind="primary"] {
    background: var(--c-blue-dim) !important; border-radius: 50% !important;
    color: var(--c-blue) !important; width: 42px !important; margin: 0 auto !important;
}
.top-pill-wrap nav[role="tablist"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)


def render_top_nav(active_group):
    with st.container(key="top_nav"):
        cols = st.columns(len(GROUP_ORDER))
        for i, group in enumerate(GROUP_ORDER):
            with cols[i]:
                is_active = (group == active_group)
                if st.button(GROUP_BOTTOM_ICONS[group], key=f"nav_{group}",
                             use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.active_group = group
                    st.rerun()


def render_top_pill(active_group):
    subs = NAV_GROUPS[active_group]["subs"]
    if len(subs) == 1:
        return subs[0]
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


if "active_group" not in st.session_state:
    st.session_state.active_group = "בית"

active_group = st.session_state.active_group
render_top_nav(active_group)
active_sub = render_top_pill(active_group)
```

## שלב ג' — 11 שינויי כותרת בלבד (תוכן הטאבים לא זז!)
משתמשת ב-Find & Replace של PyCharm (Ctrl+R), "Find" ו-"Replace" בדיוק כמו כאן,
פעם אחת בכל פעם, לא replace-all גורף (יש עוד "with" בקוד שלא קשורים לטאבים):

| מוצאת (exact match) | מחליפה ב |
|---|---|
| `with thome:` | `if active_sub == "🏠 Home":` |
| `with t1:` | `if active_sub == "📈 גרף":` |
| `with t2:` | `if active_sub == "🎯 ניתוח":` |
| `with t3:` | `if active_sub == "⏳ Backtest":` |
| `with t4:` | `if active_sub == "🛒 מסחר":` |
| `with t7:` | `if active_sub == "📖 מדריך":` |
| `with t9:` | `if active_sub == "⚖️ השוואה":` |
| `with t10:` | `if active_sub == "💼 תיק":` |
| `with t11:` | `if active_sub == "🔔 התראות":` |
| `with t12:` | `if active_sub == "📅 דוחות":` |
| `with t13:` | `if active_sub == "👁️ Watchlist":` |

חשוב: יש בקוד גם בלוקים מקוננים כמו `an_sub1, an_sub2... = st.tabs([...])`
בתוך תוכן טאב "ניתוח" (עם `with an_sub1:` וכו') — **אלה לא נוגעים בהם**,
אלה תת-טאבים פנימיים אחרים, לא קשורים לשינוי הזה.

## שלב ד' — בדיקה
```
streamlit run alpha_paper_trading.py
```
בודקת: הדף עולה בלי traceback אדום, הבוטום/טופ-נאב מופיע למעלה,
לוחצת "📈" (גרף) ובודקת שהתוכן האמיתי (מחירים, גרף אמיתי) מופיע.

## שלב ה' — קומיט
```
git add .
git commit -m "Stage 2: replace st.tabs with mobile nav shell (all 11 tabs wired)"
```
