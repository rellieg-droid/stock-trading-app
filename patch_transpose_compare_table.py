"""
patch_transpose_compare_table.py
===================================
הופך את טבלת ההשוואה: סטרייקים כעמודות, מדדים כשורות - בדיוק הפורמט
שאושר כקריא וברור יותר. תג הנזילות משולב כאייקון (✅/⚠️) בתוך שורת
נפח/עניין פתוח במקום שורה נפרדת.

שימוש:
    python patch_transpose_compare_table.py            # dry-run
    python patch_transpose_compare_table.py --apply     # מבצע בפועל
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path("riskshield_tab.py")

OLD_BLOCK = (
    '                _cols = ["סטרייק", "פרמיה", "IV (%)", "Breakeven",\n'
    '                         "הסתברות מודל (%)", "מרחק (xEM)", "נפח", "עניין פתוח", "נזילות"]\n'
    '                _thead = "".join(f"<th>{c}</th>" for c in _cols)\n'
    '                _trs = ""\n'
    '                for r in _rows_for_ticker:\n'
    '                    _tds = "".join(\n'
    '                        f"<td>{r[c]:.2f}</td>" if isinstance(r.get(c), float) else f"<td>{r.get(c, \'—\')}</td>"\n'
    '                        for c in _cols\n'
    '                    )\n'
    '                    _trs += f"<tr>{_tds}</tr>"\n'
    '                st.markdown(\n'
    '                    f\'<table class="rs-table"><thead><tr>{_thead}</tr></thead>\'\n'
    '                    f\'<tbody>{_trs}</tbody></table>\',\n'
    '                    unsafe_allow_html=True,\n'
    '                )\n'
)

NEW_BLOCK = '''                _metric_rows = [
                    ("פרמיה", lambda r: f"${r['פרמיה']:.2f}"),
                    ("IV (%)", lambda r: f"{r['IV (%)']:.1f}%"),
                    ("הסתברות מודל OTM", lambda r: (
                        f"{r['הסתברות מודל (%)']:.1f}%" if r["הסתברות מודל (%)"] is not None else "—"
                    )),
                    ("Breakeven", lambda r: f"${r['Breakeven']:.2f}"),
                    ("מרחק (xEM)", lambda r: (
                        f"{r['מרחק (xEM)']:.2f}x" if r["מרחק (xEM)"] is not None else "—"
                    )),
                    ("עניין פתוח / נפח", lambda r: (
                        f"{'✅' if r['נזילות'] == 'תקינה' else '⚠️'} "
                        f"{int(r['עניין פתוח'])} / {int(r['נפח'])}"
                    )),
                ]
                _thead = "<th></th>" + "".join(
                    f"<th>סטרייק {r['סטרייק']:g}</th>" for r in _rows_for_ticker
                )
                _trs = ""
                for _label, _fmt in _metric_rows:
                    _tds = "".join(f"<td>{_fmt(r)}</td>" for r in _rows_for_ticker)
                    _trs += f"<tr><td>{_label}</td>{_tds}</tr>"
                st.markdown(
                    f'<table class="rs-table"><thead><tr>{_thead}</tr></thead>'
                    f'<tbody>{_trs}</tbody></table>',
                    unsafe_allow_html=True,
                )
'''


def normalize(text_bytes: bytes) -> tuple[str, str]:
    style = "\r\n" if b"\r\n" in text_bytes else "\n"
    text = text_bytes.decode("utf-8")
    if style == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, style


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not TARGET.exists():
        print(f"לא נמצא: {TARGET.resolve()}")
        return 1

    raw = TARGET.read_bytes()
    text, line_style = normalize(raw)

    count = text.count(OLD_BLOCK)
    if count != 1:
        print(f"עוגן נמצא {count} פעמים (צריך בדיוק 1). לא בוצע שינוי.")
        return 1

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"שגיאת syntax אחרי הפאץ' - לא נכתב כלום: {e}")
        return 1

    print("עוגן נמצא פעם אחת. ast.parse עבר בהצלחה.")

    if not args.apply:
        print("Dry-run בלבד. הרץ עם --apply כדי לבצע בפועל.")
        return 0

    backup = TARGET.with_suffix(f".py.{datetime.now():%Y%m%d_%H%M%S}.bak")
    shutil.copy2(TARGET, backup)
    print(f"גיבוי נוצר: {backup}")

    out_bytes = new_text.replace("\n", line_style).encode("utf-8")
    TARGET.write_bytes(out_bytes)
    print(f"נכתב בהצלחה: {TARGET.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
