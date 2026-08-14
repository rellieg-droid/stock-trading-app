"""
test_searchbox.py

בדיקה עצמאית: האם streamlit-searchbox עובד עם Streamlit 1.55, ומה
ההתנהגות מול ה-API של Yahoo תוך כדי הקלדה חיה.

הרצה:
    py -m streamlit run test_searchbox.py --server.port 8502

מה לבדוק:
  1. מקלידים "a" — לא קורה כלום (מינימום 2 תווים)
  2. מקלידים "aa" — נפתחת רשימה תוך כדי הקלדה, בלי ללחוץ על כלום
  3. ממשיכים ל-"aapl" — הרשימה מצטמצמת
  4. בוחרים שורה — הסימול נבחר ומוצג למטה
  5. מקלידים מהר מאוד — אין הקפאה ואין שגיאות בטרמינל
"""
import requests
import streamlit as st
from streamlit_searchbox import st_searchbox

st.set_page_config(page_title="searchbox test", layout="wide")


@st.cache_data(ttl=600, show_spinner=False)
def _yahoo_lookup(term: str) -> list[dict]:
    """מחזיר תוצאות גולמיות מ-Yahoo. מטמון כדי לא להציף את ה-API."""
    url = (
        "https://query2.finance.yahoo.com/v1/finance/search"
        f"?q={term}&quotesCount=8&newsCount=0&listsCount=0"
    )
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
    r.raise_for_status()
    out = []
    for q in r.json().get("quotes", []):
        sym = q.get("symbol", "")
        if not sym or q.get("quoteType") not in ("EQUITY", "ETF"):
            continue
        out.append({
            "sym": sym,
            "name": q.get("longname") or q.get("shortname") or sym,
            "exch": q.get("exchDisp", ""),
        })
    return out


def search_stocks(searchterm: str) -> list[tuple[str, str]]:
    """
    מוחזר (תווית להצגה, ערך מוחזר).
    שגיאות רשת לא מפילות את הרכיב — מחזירים רשימה ריקה.
    """
    if not searchterm or len(searchterm.strip()) < 2:
        return []
    try:
        hits = _yahoo_lookup(searchterm.strip())
    except Exception as exc:
        st.session_state["_searchbox_error"] = f"{type(exc).__name__}: {exc}"
        return []
    st.session_state.pop("_searchbox_error", None)
    return [(f"{h['sym']} — {h['name']} · {h['exch']}", h["sym"]) for h in hits]


st.title("בדיקת searchbox")
st.caption("Streamlit " + st.__version__)

selected = st_searchbox(
    search_stocks,
    placeholder="סימול או שם חברה...",
    key="test_sb",
    debounce=250,          # ממתין לרגע שקט בהקלדה לפני שקורא ל-API
    clear_on_submit=False,
    reset_function=None,
)

if err := st.session_state.get("_searchbox_error"):
    st.error(f"שגיאת חיפוש: {err}")

if selected:
    st.success(f"נבחר: {selected}")
else:
    st.info("הקלידי לפחות 2 תווים")
