"""
run_iv_fix_and_commit.py
=========================
מפעיל ברצף אחד: הרצת patch_fix_iv_lower_bound.py על options_engine.py,
ואז git add + commit + push עבור השינוי הזה בלבד.

שימוש (הריצי עם מה שבפועל עובד אצלך - py, או הנתיב המלא ל-venv):
    python run_iv_fix_and_commit.py              # dry-run - רק מראה מה יקרה, לא נוגע בכלום
    python run_iv_fix_and_commit.py --apply      # מבצע בפועל: פאץ' + git add/commit/push

הרצה נדרשת מתוך Stock_tracking (איפה שגם options_engine.py וגם ה-git repo נמצאים).
לא נוגע בשום קובץ אחר - רק ב-options_engine.py והפעולות שנמצא עליו ב-git.
"""
import argparse
import subprocess
import sys
from pathlib import Path

TARGET_FILE = "options_engine.py"
PATCH_SCRIPT = "patch_fix_iv_lower_bound.py"
COMMIT_MSG = "fix: add lower-bound check to implied_vol to prevent misleading 0.0% result"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="לבצע בפועל (ברירת מחדל: dry-run)")
    args = parser.parse_args()

    if not Path(TARGET_FILE).exists():
        sys.exit(f"שגיאה: {TARGET_FILE} לא נמצא בתיקייה הנוכחית. ודאי שאת ב-Stock_tracking.")
    if not Path(PATCH_SCRIPT).exists():
        sys.exit(f"שגיאה: {PATCH_SCRIPT} לא נמצא בתיקייה הנוכחית.")

    check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if check.returncode != 0:
        sys.exit("שגיאה: התיקייה הנוכחית היא לא git repo.")

    if not args.apply:
        print("DRY RUN - הצעד הבא יריץ, בלי --apply, שום דבר לא מבוצע בפועל.")
        print(f"1) {PATCH_SCRIPT} {TARGET_FILE}  (dry-run של הפאץ' עצמו)")
        run([sys.executable, PATCH_SCRIPT, TARGET_FILE])
        print(f"\n2) לאחר מכן, עם --apply: יורץ הפאץ' בפועל, ואז git add / commit / push עבור {TARGET_FILE}.")
        return

    # שלב 1: להריץ את הפאץ' בפועל
    print(f"שלב 1/4: מריצה את {PATCH_SCRIPT} בפועל על {TARGET_FILE}")
    patch_result = run([sys.executable, PATCH_SCRIPT, TARGET_FILE, "--apply"])
    if patch_result.returncode != 0:
        sys.exit("הפאץ' נכשל או שכבר הופעל בעבר - עוצרת, לא נוגעת ב-git.")

    # שלב 2: git add
    print(f"\nשלב 2/4: git add {TARGET_FILE}")
    add_result = run(["git", "add", TARGET_FILE])
    if add_result.returncode != 0:
        sys.exit("git add נכשל - עוצרת.")

    # שלב 3: git commit
    print("\nשלב 3/4: git commit")
    commit_result = run(["git", "commit", "-m", COMMIT_MSG])
    if commit_result.returncode != 0:
        if "nothing to commit" in (commit_result.stdout + commit_result.stderr).lower():
            print(f"אין שינוי חדש ב-{TARGET_FILE} לעומת מה שכבר ב-git - כנראה כבר בוצע קומיט קודם. לא ממשיכה ל-push.")
            return
        sys.exit("git commit נכשל מסיבה אחרת - עוצרת, בדקי את הפלט למעלה.")

    # שלב 4: git push
    print("\nשלב 4/4: git push")
    push_result = run(["git", "push"])
    if push_result.returncode != 0:
        sys.exit("git push נכשל - הקומיט המקומי כן נוצר, אבל לא הגיע ל-remote. בדקי חיבור/הרשאות ונסי git push שוב.")

    print("\nהושלם: הפאץ' הורץ, ה-commit נוצר, וה-push הצליח.")


if __name__ == "__main__":
    main()
