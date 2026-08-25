"""
macro_events.py

לוח שנה סטטי של אירועי מאקרו ידועים מראש (FOMC, CPI) לשנת 2026.

מקורות:
    FOMC -- Federal Reserve, federalreserve.gov/monetarypolicy/fomccalendars.htm
            (תאריך ההכרזה = היום השני של כל פגישה דו-יומית, 14:00 ET)
    CPI  -- Bureau of Labor Statistics, bls.gov/schedule/news_release/cpi.htm
            (כל פרסום ב-8:30 ET)

הרשימה סטטית ומוזנת ידנית -- כשמתפרסם הלוח הרשמי ל-2027 (בדרך כלל
בסוף 2026), יש להוסיף אותו כאן באותה תבנית.
"""

from datetime import date, timedelta

FOMC_DATES_2026 = [
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
]

CPI_DATES_2026 = [
    date(2026, 1, 13),
    date(2026, 2, 13),
    date(2026, 3, 11),
    date(2026, 4, 10),
    date(2026, 5, 12),
    date(2026, 6, 10),
    date(2026, 7, 14),
    date(2026, 8, 12),
    date(2026, 9, 11),
    date(2026, 10, 14),
    date(2026, 11, 10),
    date(2026, 12, 10),
]

FOMC_LABEL = "החלטת ריבית פד (FOMC)"
CPI_LABEL = "פרסום מדד CPI"


def get_macro_events(start=None, end=None):
    """
    מחזירה רשימת (date, label) לכל אירועי המאקרו הידועים, ממוינת כרונולוגית.
    אם start/end לא ניתנים -- מחזירה את כל האירועים הידועים (2026).
    """
    events = [(d, FOMC_LABEL) for d in FOMC_DATES_2026]
    events += [(d, CPI_LABEL) for d in CPI_DATES_2026]
    events.sort(key=lambda x: x[0])
    if start is not None:
        events = [e for e in events if e[0] >= start]
    if end is not None:
        events = [e for e in events if e[0] <= end]
    return events


def next_macro_event(from_date=None):
    """(date, label) של האירוע הקרוב ביותר מ-from_date ואילך, או None אם אין."""
    if from_date is None:
        from_date = date.today()
    upcoming = get_macro_events(start=from_date)
    return upcoming[0] if upcoming else None


def macro_event_within(days, from_date=None):
    """
    אם יש אירוע מאקרו בטווח של 'days' הימים הקרובים -- מחזירה תיאור
    טקסטואלי קצר (בפורמט שמתאים למילוי שדה "אירוע מאקרו ידוע"),
    אחרת מחזירה מחרוזת ריקה.
    """
    if from_date is None:
        from_date = date.today()
    end = from_date + timedelta(days=int(days))
    events = get_macro_events(start=from_date, end=end)
    if not events:
        return ""
    d, label = events[0]
    delta = (d - from_date).days
    when = "היום" if delta == 0 else f"בעוד {delta} ימים"
    return f"{label} ({when}, {d.strftime('%d/%m')})"
