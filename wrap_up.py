#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
wrap_up.py
==========
סגירת יום עבודה: גיבוי, ניקוי, ורשימת פעולות git.

סדר הפעולות מכוון. גיבוי לפני ניקוי, וניקוי רק אחרי שהקוד בטוח.
שום קובץ לא נמחק — הכל עובר ל-_archive/ עם חותמת זמן.

מה הוא עושה:
  1. בודק שאתה בתוך ריפו git ומדווח על מצב העץ
  2. יוצר snapshot מכווץ של הפרויקט ב-_snapshots/
  3. משלים שורות חסרות ב-.gitignore
  4. מעביר קבצי .bak ל-_archive/backups/
  5. מעביר סקריפטי patch ו-fix שכבר הורצו ל-_archive/patches/
  6. מוחק תיקיות __pycache__
  7. מדפיס את פקודות ה-git לסיום

הרצה:
    py wrap_up.py                 # דמה בלבד, מדפיס מה יקרה
    py wrap_up.py --apply         # מבצע
    py wrap_up.py --apply --keep-patches   # משאיר את סקריפטי הפאץ' במקום
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# קבצים שנשארים תמיד בשורש
CORE = {
    "alpha_paper_trading.py",
    "rr_engine.py", "rr_tab.py", "rr_guide.py", "test_rr_engine.py",
    "strategy_engine.py", "strategy_data.py", "strategy_tab.py",
    "strategy_guide.py", "test_strategy_engine.py", "strategy_scan.py",
    "wrap_up.py", "requirements.txt", "README.md", ".gitignore",
}

ARCHIVE_PATTERNS = ("patch_*.py", "fix_*.py", "cleanup_*.py")
BACKUP_PATTERNS = ("*.bak", "*.bak.*", "*.orig", "*.rej")

GITIGNORE_LINES = [
    "*.bak", "*.orig", "*.rej",
    "__pycache__/", "*.pyc",
    ".venv/",
    "_snapshots/",
    ".streamlit/secrets.toml",
    "portfolio.json", "user_data.json",
]

SNAPSHOT_SKIP_DIRS = {".git", ".venv", "__pycache__", ".idea", ".pytest_cache",
                      "_snapshots", "node_modules"}


def git(*args, cwd: Path) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except FileNotFoundError:
        return 127, "git לא נמצא ב-PATH"


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def collect(root: Path, patterns) -> list[Path]:
    out = []
    for p in sorted(root.iterdir()):
        if not p.is_file() or p.name in CORE:
            continue
        if any(fnmatch.fnmatch(p.name, pat) for pat in patterns):
            out.append(p)
    return out


def make_snapshot(root: Path, apply: bool) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_dir = root / "_snapshots"
    dest = dest_dir / f"snapshot_{stamp}.zip"

    files, total = [], 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SNAPSHOT_SKIP_DIRS for part in p.parts):
            continue
        files.append(p)
        total += p.stat().st_size

    print(f"\n[1] Snapshot: {len(files)} קבצים, {human(total)} → _snapshots/{dest.name}")
    if not apply:
        return dest

    dest_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files:
            z.write(p, p.relative_to(root))
    print(f"    נוצר: {dest.name} ({human(dest.stat().st_size)})")
    return dest


def fix_gitignore(root: Path, apply: bool) -> None:
    gi = root / ".gitignore"
    existing = set()
    if gi.exists():
        existing = {ln.strip() for ln in gi.read_text(encoding="utf-8").splitlines()}
    missing = [ln for ln in GITIGNORE_LINES if ln not in existing]

    print(f"\n[2] .gitignore: {len(missing)} שורות חסרות")
    for ln in missing:
        print(f"    + {ln}")
    if not missing or not apply:
        return

    with open(gi, "a", encoding="utf-8", newline="\n") as f:
        if existing:
            f.write("\n")
        f.write("# נוסף אוטומטית ע\"י wrap_up.py\n")
        f.write("\n".join(missing) + "\n")
    print("    עודכן.")


def archive(root: Path, files: list[Path], subdir: str, apply: bool, label: str) -> int:
    print(f"\n{label}: {len(files)} קבצים")
    if not files:
        return 0
    total = sum(f.stat().st_size for f in files)
    for f in files[:12]:
        print(f"    · {f.name}")
    if len(files) > 12:
        print(f"    · ... ועוד {len(files) - 12}")
    print(f"    סה\"כ {human(total)} → _archive/{subdir}/")
    if not apply:
        return 0

    dest = root / "_archive" / subdir
    dest.mkdir(parents=True, exist_ok=True)
    moved = 0
    for f in files:
        target = dest / f.name
        if target.exists():
            target = dest / f"{f.stem}_{datetime.now():%H%M%S}{f.suffix}"
        rc, _ = git("ls-files", "--error-unmatch", f.name, cwd=root)
        if rc == 0:
            # קובץ במעקב git — git mv שומר על ההיסטוריה
            git("mv", str(f.relative_to(root)),
                str(target.relative_to(root)), cwd=root)
        else:
            shutil.move(str(f), str(target))
        moved += 1
    print(f"    הועברו {moved}.")
    return moved


def clear_pycache(root: Path, apply: bool) -> None:
    dirs = [p for p in root.rglob("__pycache__")
            if p.is_dir() and ".venv" not in p.parts]
    print(f"\n[5] __pycache__: {len(dirs)} תיקיות")
    if not apply:
        return
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
    print("    נמחקו.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="בצע בפועל")
    ap.add_argument("--keep-patches", action="store_true",
                    help="אל תעביר סקריפטי patch/fix לארכיון")
    ap.add_argument("--path", default=".", help="שורש הפרויקט")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"[עצירה] התיקייה לא נמצאה: {root}")
        sys.exit(1)

    print("=" * 62)
    print(f"סגירת יום · {root}")
    print("=" * 62)

    # ── 0. מצב git ──
    rc, branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=root)
    is_repo = rc == 0
    if is_repo:
        branch = branch.strip()
        _, status = git("status", "--porcelain", cwd=root)
        dirty = [ln for ln in status.splitlines() if ln.strip()]
        print(f"\n[0] git: ענף {branch} · {len(dirty)} קבצים לא מקובעים")
        if dirty:
            for ln in dirty[:10]:
                print(f"    {ln}")
            if len(dirty) > 10:
                print(f"    ... ועוד {len(dirty) - 10}")
    else:
        print("\n[0] git: לא זוהה ריפו. הארכוב יתבצע כהעברת קבצים רגילה.")

    # ── 1. גיבוי ──
    make_snapshot(root, args.apply)

    # ── 2. gitignore ──
    fix_gitignore(root, args.apply)

    # ── 3 + 4. ארכוב ──
    baks = collect(root, BACKUP_PATTERNS)
    archive(root, baks, "backups", args.apply, "[3] קבצי גיבוי מקומיים")

    if args.keep_patches:
        print("\n[4] סקריפטי patch/fix: דילוג לפי בקשה")
    else:
        patches = collect(root, ARCHIVE_PATTERNS)
        archive(root, patches, "patches", args.apply, "[4] סקריפטי patch ו-fix")

    # ── 5. pycache ──
    clear_pycache(root, args.apply)

    # ── 6. מה נשאר לעשות ידנית ──
    print("\n" + "=" * 62)
    if not args.apply:
        print("זו הרצת דמה. לביצוע:  py wrap_up.py --apply")
        print("=" * 62)
        return

    print("נותר לך להריץ ידנית, בסדר הזה:\n")
    print("  .\\.venv\\Scripts\\python.exe -m pytest test_rr_engine.py -q")
    print("  git add -A")
    print('  git commit -m "מודול סיכון-סיכוי, תוויות ניווט ותיקוני RTL"')
    if is_repo:
        print(f"  git push -u origin {branch}")
    print("\nהבדיקות ראשונות בכוונה. אין טעם לקבע קוד שלא עובר.")
    print("=" * 62)


if __name__ == "__main__":
    main()
