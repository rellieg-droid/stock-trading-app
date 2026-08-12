"""
cleanup_project.py — Alpha Charts Pro
מארגן את שורש הפרויקט: מעביר סקריפטי תיקון, קבצי ניסוי, גרסאות ישנות
ותיעוד לתיקיות ייעודיות. משאיר בשורש רק את מה שנדרש להרצה.

שימוש:
    py cleanup_project.py            <- הצגת התוכנית בלבד, לא מזיז כלום
    py cleanup_project.py --apply    <- ביצוע בפועל

מריצים מתוך C:\\PhyCharm_projects\\Stock_tracking
"""

import os
import sys
import glob
import shutil
import subprocess

APPLY = "--apply" in sys.argv

# ── קבצים שנשארים בשורש בכל מקרה ──────────────────────────────────────
KEEP_IN_ROOT = {
    "alpha_paper_trading.py",   # האפליקציה
    "requirements.txt",
    "paper_portfolio.json",     # נתיב יחסי בקוד
    "user_data.json",           # נתיב יחסי בקוד
    ".gitignore",
    "cleanup_project.py",
}

# ── יעדי ההעברה ───────────────────────────────────────────────────────
MOVES = {
    "archive/fix_scripts": [
        "fix_chart_density.py",
        "fix_chart_dynamic_ticks.py",
        "fix_chart_gaps.py",
        "fix_chart_rightmargin.py",
        "fix_chart_ticks.py",
        "fix_chart_toolbar.py",
        "fix_pill_polish.py",
        "fix_pill_size.py",
        "fix_stage2.py",
        "fix_ticker_escape_hatch.py",
        "fix_toolbar_merge.py",
        "revert_rightmargin.py",
        "chart_axis_reference.py",
    ],
    "archive/experiments": [
        "mobile_layout_test.py",
        "mobile_nav_shell_test.py",
    ],
    "archive/legacy": [
        "main.py",
    ],
    "docs": [
        "PATCH_stage2_nav_shell.md",
        "ALPHA CHARTS PRO.docx",
        "Alpha_Charts_Design_Brief.docx",
    ],
}


def is_git_repo():
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"],
                       check=True, capture_output=True)
        return True
    except Exception:
        return False


def is_tracked(path):
    r = subprocess.run(["git", "ls-files", "--error-unmatch", path],
                       capture_output=True)
    return r.returncode == 0


def check_runner_references():
    """
    בודק אם run_app.* מפנה לקובץ שאנחנו עומדים להזיז.
    זו הסכנה היחידה האמיתית כאן.
    """
    targets = {f for files in MOVES.values() for f in files}
    problems = []
    for runner in glob.glob("run_app*"):
        try:
            with open(runner, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue
        for t in targets:
            if t in content:
                problems.append((runner, t))
    return problems


def main():
    if not os.path.exists("alpha_paper_trading.py"):
        print("[עצירה] alpha_paper_trading.py לא נמצא כאן.")
        print("        הרצת את הסקריפט מהתיקייה הלא נכונה?")
        return 1

    git = is_git_repo()
    if not git:
        print("[אזהרה] לא זוהה ריפו git. ההעברה תתבצע עם shutil, בלי היסטוריה.\n")

    # בדיקת בטיחות: run_app מפנה לקובץ שזז?
    problems = check_runner_references()
    if problems:
        print("[עצירה] run_app מפנה לקובץ שעומד לזוז:\n")
        for runner, target in problems:
            print(f"        {runner}  ->  {target}")
        print("\n        עדכני את run_app או הסירי את הקובץ מרשימת ההעברה.")
        return 1

    planned, missing = [], []
    for dest, files in MOVES.items():
        for f in files:
            if f in KEEP_IN_ROOT:
                continue
            if os.path.exists(f):
                planned.append((f, dest))
            else:
                missing.append(f)

    print("=" * 62)
    print("תוכנית ניקוי" + ("  [ביצוע]" if APPLY else "  [תצוגה מקדימה בלבד]"))
    print("=" * 62)

    current_dest = None
    for f, dest in sorted(planned, key=lambda x: x[1]):
        if dest != current_dest:
            print(f"\n  -> {dest}/")
            current_dest = dest
        print(f"       {f}")

    if missing:
        print(f"\n  לא נמצאו (מדולגים): {', '.join(missing)}")

    stay = sorted(f for f in os.listdir(".")
                  if os.path.isfile(f) and f not in {p[0] for p in planned})
    print(f"\n  נשאר בשורש: {', '.join(stay)}")
    print(f"\n  סה\"כ להעברה: {len(planned)} קבצים")

    if not APPLY:
        print("\n" + "=" * 62)
        print("לא הוזז כלום. לביצוע:  py cleanup_project.py --apply")
        return 0

    print("\n" + "-" * 62)
    moved, failed = 0, []
    for f, dest in planned:
        os.makedirs(dest, exist_ok=True)
        target = os.path.join(dest, os.path.basename(f))
        try:
            if git and is_tracked(f):
                subprocess.run(["git", "mv", f, target], check=True,
                               capture_output=True)
                tag = "git mv"
            else:
                shutil.move(f, target)
                tag = "move  "
            print(f"  [{tag}] {f} -> {dest}/")
            moved += 1
        except Exception as e:
            print(f"  [כשל  ] {f}: {e}")
            failed.append(f)

    # README קצר בכל ארכיון כדי שהתיקיות לא ייראו כמו זבל בעוד חודשיים
    notes = {
        "archive/fix_scripts": "סקריפטי תיקון חד פעמיים שכבר רצו.\n"
                               "השינויים שלהם כבר בתוך alpha_paper_trading.py.\n"
                               "נשמרים לתיעוד בלבד. אין להריץ שוב.\n",
        "archive/experiments": "קבצי ניסוי ויזואלי עצמאיים מתקופת עיצוב הניווט.\n"
                               "הניווט מוזג לאפליקציה. לא נדרשים להרצה.\n",
        "archive/legacy":      "main.py — גרסה ישנה ונטושה של האפליקציה (4 טאבים).\n"
                               "הוחלפה במלואה על ידי alpha_paper_trading.py.\n",
    }
    for folder, text in notes.items():
        if os.path.isdir(folder):
            with open(os.path.join(folder, "README.md"), "w",
                      encoding="utf-8") as fh:
                fh.write(text)

    print("-" * 62)
    print(f"הועברו {moved} קבצים." + (f" נכשלו: {failed}" if failed else ""))
    print("\nהצעד הבא:")
    print("  streamlit run alpha_paper_trading.py")
    print("  ואם עולה תקין:")
    print('  git add -A && git commit -m "chore: reorganize project structure"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
