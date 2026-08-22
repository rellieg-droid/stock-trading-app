"""
repro_slider_overlap.py

מטרה: לבודד את הבאג של חפיפה בין number_input ל-slider בתוך st.columns(2),
כדי לוודא אם המקור הוא כלל ה-CSS הגלובלי `direction: rtl !important` על כל
ה-div-ים באפליקציה (מ-alpha_paper_trading.py), או משהו ספציפי לסקשן הדוח.

שימוש:
    streamlit run repro_slider_overlap.py

בדיקה:
    1. תראי שני מצבים בזה אחר זה - "בלי CSS גלובלי" ו"עם CSS גלובלי" (בדיוק
       הכלל מהאפליקציה האמיתית).
    2. אם החפיפה מופיעה רק במצב השני - זה מוכיח את המקור, ואפשר לתקן ב-CSS
       ממוקד בלי לגעת בכלל הגלובלי (שעובד טוב בכל שאר האפליקציה).
    3. אם החפיפה מופיעה בשני המצבים - המקור הוא משהו אחר (גרסת Streamlit,
       או ה-slider עצמו), וצריך לחקור אחרת.
"""

import streamlit as st

st.set_page_config(layout="wide")

st.markdown("## מצב 1: בלי הכלל הגלובלי הבעייתי")
i1, i2 = st.columns(2)
ref_price = i1.number_input(
    "מחיר סגירה לפני הדוח", min_value=0.01, value=304.29,
    step=0.01, format="%.2f", key="no_css_ref")
span = i2.slider("טווח פערים לבדיקה (%)", 5, 40, 20, 5, key="no_css_span")

st.divider()

st.markdown("## מצב 2: עם הכלל הגלובלי (בדיוק כמו באפליקציה האמיתית)")
st.markdown(
    """
    <style>
    div, p, span, label { direction: rtl !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
i3, i4 = st.columns(2)
ref_price2 = i3.number_input(
    "מחיר סגירה לפני הדוח", min_value=0.01, value=304.29,
    step=0.01, format="%.2f", key="with_css_ref")
span2 = i4.slider("טווח פערים לבדיקה (%)", 5, 40, 20, 5, key="with_css_span")

st.divider()
st.info(
    "גררי את הסליידר בשני המצבים (בפרט זה שבתחתית). תראי אם 'הבועה' עם "
    "המספר שצפה מעל הידית של הסליידר נשארת בתוך תחום הסליידר, "
    "או שהיא קופצת/חופפת לתוך התיבה של number_input שלידה."
)
