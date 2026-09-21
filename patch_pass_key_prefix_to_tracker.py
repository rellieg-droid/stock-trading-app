# -*- coding: utf-8 -*-
"""
patch_pass_key_prefix_to_tracker.py

Follow-up patch: updates the call inside render_riskshield_tab()'s
`with tab_tracker:` block from render_put_tracker_tab() to
render_put_tracker_tab(key_prefix=key_prefix), so the new
"pull from OTM tab" button can find that tab's session_state values.

Only needed if you already ran patch_add_put_tracker_tab.py successfully.

Usage:
    python patch_pass_key_prefix_to_tracker.py            # dry run
    python patch_pass_key_prefix_to_tracker.py --apply    # applies the patch
"""

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = Path("riskshield_tab.py")

ANCHOR = "    with tab_tracker:\n        render_put_tracker_tab()\n"
REPLACEMENT = "    with tab_tracker:\n        render_put_tracker_tab(key_prefix=key_prefix)\n"


def read_normalized(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    was_crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    if was_crlf:
        text = text.replace("\r\n", "\n")
    return text, was_crlf


def write_normalized(path: Path, text: str, restore_crlf: bool) -> None:
    if restore_crlf:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    if not TARGET_FILE.exists():
        print(f"[FAIL] {TARGET_FILE} not found in current directory")
        sys.exit(1)

    text, was_crlf = read_normalized(TARGET_FILE)

    count = text.count(ANCHOR)
    if count == 0:
        print(f"[FAIL] anchor not found — the tracker tab block may look different than expected: {ANCHOR!r}")
        print("Open riskshield_tab.py, find the `with tab_tracker:` block, and check it matches this pattern.")
        sys.exit(1)
    if count > 1:
        print(f"[FAIL] anchor found {count} times (expected exactly 1)")
        sys.exit(1)
    print("[OK] anchor found exactly once")

    patched = text.replace(ANCHOR, REPLACEMENT, 1)

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[FAIL] Patched file would not parse: {e}")
        sys.exit(1)
    print("[OK] Patched content passes ast.parse")

    if not args.apply:
        print("\n--- DRY RUN — no changes written. Re-run with --apply to write. ---")
        print("Will change:")
        print(" -", ANCHOR.strip().splitlines()[-1])
        print(" +", REPLACEMENT.strip().splitlines()[-1])
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = TARGET_FILE.with_suffix(TARGET_FILE.suffix + f".{timestamp}.bak")
    shutil.copy2(TARGET_FILE, backup_path)
    print(f"[OK] Backup written to {backup_path}")

    write_normalized(TARGET_FILE, patched, restore_crlf=was_crlf)
    print(f"[OK] {TARGET_FILE} patched (CRLF preserved: {was_crlf})")


if __name__ == "__main__":
    main()
