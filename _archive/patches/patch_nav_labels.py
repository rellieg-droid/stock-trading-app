#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
patch_nav_labels.py
===================
מתקן את סרגל הניווט התחתון ב-alpha_paper_trading.py.

הבעיה: חמישה אייקונים בלי שום טקסט. אי אפשר לדעת מה כל אחד עושה,
והאייקון של "עוד" (⋯) כמעט בלתי נראה.

התיקון:
  1. תווית טקסט קבועה מתחת לכל אייקון (בית, גרף, ניתוח, מסחר, עוד)
  2. tooltip בריחוף עם הסבר מלא מה יש בכל קבוצה
  3. אייקונים גדולים יותר (1.3rem ← 1.55rem), כפתור פעיל 48px
  4. האייקון ⋯ מוחלף ב-☰ שנראה בבירור

שלושה שינויים בקובץ: מילון האייקונים, בלוק ה-CSS, ופונקציית render_top_nav.

הרצה:
    py patch_nav_labels.py                # דמה בלבד
    py patch_nav_labels.py --apply        # ביצוע, אחרי גיבוי עם חותמת זמן
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = "alpha_paper_trading.py"

# ---------------------------------------------------------------------------
# 1. אייקונים + טקסטים ל-tooltip
# ---------------------------------------------------------------------------

OLD_ICONS = (
    'GROUP_BOTTOM_ICONS = {"בית": "🏠", "גרף": "📈", "ניתוח": "🎯", '
    '"מסחר": "🛒", "עוד": "⋯"}\n'
)

NEW_ICONS = (
    'GROUP_BOTTOM_ICONS = {"בית": "🏠", "גרף": "📈", "ניתוח": "🎯", '
    '"מסחר": "🛒", "עוד": "☰"}\n'
    '\n'
    '# טקסט ה-tooltip בריחוף. מפרט מה יש בכל קבוצה, כי האייקון לבדו לא מספיק.\n'
    'GROUP_TOOLTIPS = {\n'
    '    "בית":   "בית — סקירת שוק, מומלצות AI, מדדים וקריפטו",\n'
    '    "גרף":   "גרף — נרות, אינדיקטורים וזיהוי תבניות",\n'
    '    "ניתוח": "ניתוח — ציון משולב, השוואה, Backtest ואסטרטגיה",\n'
    '    "מסחר":  "מסחר — קנייה ומכירה, תיק אחזקות, Watchlist וניהול יעדים",\n'
    '    "עוד":   "עוד — התראות, לוח דוחות ומדריך",\n'
    '}\n'
)

# ---------------------------------------------------------------------------
# 2. CSS
# ---------------------------------------------------------------------------

OLD_CSS_TAIL = '''.top-pill-wrap iframe { display: block; }
</style>
'''

NEW_CSS_TAIL = '''.top-pill-wrap iframe { display: block; }

/* NAV_LABELS — אייקון בלי טקסט לא ניתן לפענוח. כאן מגדילים את הכפתור,
   מוסיפים תווית קבועה מתחתיו, ומצמצמים את המרווח ביניהם לאפס. */
.st-key-top_nav { padding: 0.45rem 0.5rem 0.3rem !important; }
.st-key-top_nav div[data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-top_nav .stButton > button {
    font-size: 1.55rem !important;
    height: 48px !important;
    line-height: 1 !important;
}
.st-key-top_nav .stButton > button[kind="primary"] {
    width: 48px !important;
    height: 48px !important;
}
.nav-label {
    text-align: center;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: .01em;
    color: var(--c-text-3);
    margin: 1px 0 0;
    white-space: nowrap;
    user-select: none;
}
.nav-label-on { color: var(--c-blue); font-weight: 800; }
</style>
'''

# ---------------------------------------------------------------------------
# 3. render_top_nav
# ---------------------------------------------------------------------------

OLD_NAV_FN = '''def render_top_nav(active_group):
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
'''

NEW_NAV_FN = '''def render_top_nav(active_group):
    with st.container(key="top_nav"):
        cols = st.columns(len(GROUP_ORDER))
        for i, group in enumerate(GROUP_ORDER):
            with cols[i]:
                is_active = (group == active_group)
                if st.button(GROUP_BOTTOM_ICONS[group], key=f"nav_{group}",
                             use_container_width=True,
                             help=GROUP_TOOLTIPS.get(group, group),
                             type="primary" if is_active else "secondary"):
                    st.session_state.active_group = group
                    st.rerun()
                # תווית קבועה. tooltip לבדו לא עוזר במגע, שם אין ריחוף.
                st.markdown(
                    f'<div class="nav-label{" nav-label-on" if is_active else ""}">'
                    f'{group}</div>',
                    unsafe_allow_html=True)
'''

EDITS = [
    {"name": "אייקון ☰ במקום ⋯ ומילון tooltips",
     "old": OLD_ICONS, "new": NEW_ICONS, "skip_if": "GROUP_TOOLTIPS"},
    {"name": "CSS לתוויות ולהגדלת הכפתורים",
     "old": OLD_CSS_TAIL, "new": NEW_CSS_TAIL, "skip_if": "NAV_LABELS"},
    {"name": "render_top_nav עם תווית ו-tooltip",
     "old": OLD_NAV_FN, "new": NEW_NAV_FN, "skip_if": 'class="nav-label'},
]


def fail(msg: str) -> None:
    print(f"\n[עצירה] {msg}")
    print("לא בוצע שום שינוי בקובץ.")
    sys.exit(1)


def read_keep_eol(path: Path) -> tuple[str, str]:
    with open(path, encoding="utf-8", newline="") as f:
        raw = f.read()
    crlf = raw.count("\r\n")
    eol = "\r\n" if crlf > (raw.count("\n") - crlf) else "\n"
    return raw.replace("\r\n", "\n"), eol


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="בצע בפועל")
    ap.add_argument("--path", default=TARGET, help="נתיב ל-alpha_paper_trading.py")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        fail(f"הקובץ לא נמצא: {path.resolve()}")

    original, eol = read_keep_eol(path)
    text = original
    applied, skipped = [], []

    for edit in EDITS:
        if edit["skip_if"] in text:
            skipped.append(edit["name"])
            continue
        count = text.count(edit["old"])
        if count == 0:
            fail(f"עוגן לא נמצא עבור: {edit['name']}\n"
                 f"סרגל הניווט כנראה נערך מאז. שלחי לי את הקובץ.")
        if count > 1:
            fail(f"עוגן מופיע {count} פעמים עבור: {edit['name']}. "
                 f"החלפה לא חד-משמעית.")
        text = text.replace(edit["old"], edit["new"], 1)
        applied.append(edit["name"])

    for name in skipped:
        print(f"[דילוג] כבר קיים: {name}")

    if text == original:
        print("\nאין מה לשנות.")
        return

    diff = difflib.unified_diff(
        original.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=f"a/{path.name}", tofile=f"b/{path.name}", n=2,
    )
    print("\n" + "".join(diff))
    print(f"שינויים מתוכננים: {len(applied)}")
    for name in applied:
        print(f"  · {name}")

    if not args.apply:
        print("\nזו הרצת דמה. להחלה בפועל:  py patch_nav_labels.py --apply")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".py.{stamp}.bak")
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", eol))
    print(f"\nבוצע. גיבוי נשמר ב: {backup.name}")
    print(f"שחזור:  copy /Y \"{backup.name}\" \"{path.name}\"")


if __name__ == "__main__":
    main()
