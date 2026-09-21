"""
patch_add_yaxis_autoscale.py

מטרה: להוסיף קנה מידה אוטומטי לציר ה-Y בזמן זום/גלילה על ציר ה-X
בגרף הראשי (כמו ב-Yahoo Finance) -- מגבלה ידועה של Plotly.js עצמו
(GitHub plotly.js#5544, פתוח כבר שנים, אין הגדרה מובנית לזה).

הפתרון: לא בונים את הגרף מחדש ב-JS. לוקחים את אובייקט ה-fig הקיים
(עם כל העיצוב, ה-subplots, האינדיקטורים) כמו שהוא, מייצאים ל-JSON
(fig.to_json()), ומטמיעים HTML מותאם (streamlit.components.v1.html)
שמריץ Plotly.newPlot עם אותו JSON ומאזין לאירוע plotly_relayout:

    בכל שינוי טווח X (זום/גלילה) -- מסננים את נקודות הנתונים של כל
    trace ששייך לציר ה-Y הראשי (לא yaxis2/yaxis3 -- כלומר לא
    Volume/RSI), מוצאים min/max בטווח הנראה, מוסיפים ריפוד 5%,
    ומעדכנים yaxis.range דרך Plotly.relayout.

    בדאבל-קליק לאיפוס זום (autorange:true חוזר על ה-X) -- גם ה-Y
    חוזר ל-autorange, כדי לא "להיתקע" בטווח הצר האחרון.

תומך גם בסוגי גרפים שאינם candlestick (line/area) -- קורא high/low
לאם trace.type==='candlestick', אחרת קורא מ-trace.y.

שימוש:
    python patch_add_yaxis_autoscale.py                 # dry-run (ברירת מחדל)
    python patch_add_yaxis_autoscale.py --apply          # ביצוע בפועל + גיבוי אוטומטי
"""

import argparse
import ast
import datetime
import difflib
import sys
from pathlib import Path

TARGET_FILE = "alpha_paper_trading.py"

OLD_LINES = [
    'st.plotly_chart(fig, width="stretch",',
    '                config={"scrollZoom": True, "displayModeBar": True,',
    '                        "modeBarButtonsToRemove": ["lasso2d", "select2d"]})',
]

# תבנית ה-HTML/JS -- מחרוזת רגילה (לא f-string!) עם placeholders מילוליים
# שמוחלפים ב-.replace() בהמשך, כדי למנוע לגמרי בעיות escaping של { }
# בין Python ל-JSON ל-JavaScript (ראו למידה קודמת מהיום עם {sym}).
_AUTOSCALE_HTML_TEMPLATE = r"""
<div id="__DIV_ID__" style="width:100%;"></div>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
(function() {
    var figSpec = __FIG_JSON__;
    var gd = document.getElementById("__DIV_ID__");
    var config = {scrollZoom: true, displayModeBar: true,
                  modeBarButtonsToRemove: ["lasso2d", "select2d"]};
    Plotly.newPlot(gd, figSpec.data, figSpec.layout, config);

    function isPrimaryYAxisTrace(trace) {
        return !trace.yaxis || trace.yaxis === "y";
    }

    gd.on("plotly_relayout", function(eventData) {
        if (eventData["xaxis.autorange"]) {
            Plotly.relayout(gd, {"yaxis.autorange": true});
            return;
        }
        var xmin = eventData["xaxis.range[0]"];
        var xmax = eventData["xaxis.range[1]"];
        if (xmin === undefined || xmax === undefined) { return; }

        var yMin = null, yMax = null;
        figSpec.data.forEach(function(trace) {
            if (!isPrimaryYAxisTrace(trace)) { return; }
            if (!trace.x) { return; }
            var isCandle = trace.type === "candlestick";
            var highArr = isCandle ? trace.high : trace.y;
            var lowArr = isCandle ? trace.low : trace.y;
            if (!highArr || !lowArr) { return; }
            for (var i = 0; i < trace.x.length; i++) {
                var xi = trace.x[i];
                if (xi >= xmin && xi <= xmax) {
                    var hv = highArr[i], lv = lowArr[i];
                    if (hv !== null && hv !== undefined && !isNaN(hv)) {
                        if (yMax === null || hv > yMax) { yMax = hv; }
                    }
                    if (lv !== null && lv !== undefined && !isNaN(lv)) {
                        if (yMin === null || lv < yMin) { yMin = lv; }
                    }
                }
            }
        });
        if (yMin === null || yMax === null) { return; }
        var pad = (yMax - yMin) * 0.05;
        if (pad === 0) { pad = Math.abs(yMax) * 0.05 || 1; }
        Plotly.relayout(gd, {"yaxis.range": [yMin - pad, yMax + pad], "yaxis.autorange": false});
    });
})();
</script>
"""


def get_indent(text, anchor):
    idx = text.index(anchor)
    line_start = text.rfind("\n", 0, idx) + 1
    return text[line_start:idx]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="בצע בפועל (במקום dry-run)")
    args = parser.parse_args()

    target = Path(TARGET_FILE)
    if not target.exists():
        print(f"שגיאה: לא נמצא הקובץ {TARGET_FILE} בתיקייה הנוכחית.")
        sys.exit(1)

    raw_bytes = target.read_bytes()
    uses_crlf = b"\r\n" in raw_bytes
    text = raw_bytes.decode("utf-8")
    eol = "\r\n" if uses_crlf else "\n"

    anchor = OLD_LINES[0]
    if text.count(anchor) != 1:
        print(f"שגיאה: העוגן {anchor!r} נמצא {text.count(anchor)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    indent = get_indent(text, anchor)
    old_full_block = eol.join(indent + l for l in OLD_LINES)
    if old_full_block not in text:
        print("שגיאה: הבלוק המלא לא נמצא ברצף מדויק כמו שציפינו. לא בוצע שינוי.")
        sys.exit(1)
    if text.count(old_full_block) != 1:
        print(f"שגיאה: הבלוק נמצא {text.count(old_full_block)} פעמים (צריך 1). לא בוצע שינוי.")
        sys.exit(1)

    new_lines = [
        'import streamlit.components.v1 as _stc',
        '_autoscale_html = _AUTOSCALE_HTML_TEMPLATE.replace("__DIV_ID__", "main_price_chart").replace(',
        '    "__FIG_JSON__", fig.to_json())',
        '_stc.html(_autoscale_html, height=760, scrolling=False)',
    ]
    new_full_block = "\n".join(indent + l for l in new_lines)

    new_text = text.replace(old_full_block, new_full_block, 1)

    # מוסיפים את קבוע התבנית ברמת המודול, ממש בתחילת הקובץ (אחרי ה-imports
    # הראשונים), כדי שהיא תהיה זמינה מכל מקום שבו נבנה הגרף.
    module_marker = "import streamlit as st"
    if module_marker not in new_text:
        print("שגיאה: לא נמצא 'import streamlit as st' בתחילת הקובץ להוספת התבנית אחריו.")
        sys.exit(1)
    if new_text.count(module_marker) != 1:
        print(f"שגיאה: 'import streamlit as st' נמצא {new_text.count(module_marker)} פעמים (צריך 1 בשורה 6).")
        sys.exit(1)

    template_block = (
        eol + '_AUTOSCALE_HTML_TEMPLATE = ' + repr(_AUTOSCALE_HTML_TEMPLATE)
    )
    new_text = new_text.replace(module_marker, module_marker + template_block, 1)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"\nשגיאה: הקוד החדש לא עובר ast.parse — {e}")
        print("לא בוצע שינוי בקובץ.")
        sys.exit(1)

    if not args.apply:
        print("=== DRY RUN (לא בוצע שינוי) ===\n")
        print("--- שינוי 1: הוספת קבוע התבנית אחרי import streamlit as st ---")
        print(f"(תבנית HTML/JS של {len(_AUTOSCALE_HTML_TEMPLATE)} תווים)")
        print("\n--- שינוי 2: החלפת קריאת st.plotly_chart ---")
        diff = difflib.unified_diff(
            old_full_block.splitlines(keepends=True),
            new_full_block.splitlines(keepends=True),
            fromfile="לפני", tofile="אחרי", lineterm=""
        )
        print("".join(diff))
        print("\nלביצוע בפועל, הריצי עם --apply")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_suffix(target.suffix + f".{ts}.bak")
    backup_path.write_bytes(raw_bytes)
    print(f"גיבוי נשמר ב: {backup_path}")

    out_bytes = new_text.encode("utf-8")
    if uses_crlf:
        out_bytes = out_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    target.write_bytes(out_bytes)
    print(f"בוצע בהצלחה: {TARGET_FILE} עודכן.")
    print("לבדוק בקפידה:")
    print("  1. הגרף הראשי נטען ונראה זהה לגמרי לפני (כל האינדיקטורים, הצבעים, ה-RTL)")
    print("  2. זום (גלגלת עכבר / drag-select) על ציר X -- ציר Y אמור להצטמצם לטווח הנראה")
    print("  3. דאבל-קליק לאיפוס -- ציר Y אמור לחזור לטווח המלא")
    print("  4. אם הגרף חתוך/גבוה מדי, לכוונן את height=760 בקוד")


if __name__ == "__main__":
    main()
