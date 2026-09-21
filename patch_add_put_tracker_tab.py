# -*- coding: utf-8 -*-
"""
patch_add_put_tracker_tab.py

Adds a "📒 מעקב פרמיות" sub-tab to riskshield_tab.py's render_riskshield_tab(),
wired to put_tracker_tab.render_put_tracker_tab().

All three anchors below were verified against the actual uploaded
riskshield_tab.py (each occurs exactly once):
  - the closing lines of the `from options_engine import (...)` block
  - the `tab_bs, tab_iv, tab_rv, tab_prob, tab_screener = st.tabs(...)` block
  - the final `st.markdown('</div>', unsafe_allow_html=True)` line that
    closes the .rs-wrap div at the end of render_riskshield_tab()

The real file uses LF line endings (not CRLF) — this script auto-detects
either and preserves whatever the file already uses.

Usage:
    python patch_add_put_tracker_tab.py            # dry run — shows diff, writes nothing
    python patch_add_put_tracker_tab.py --apply    # applies the patch
"""

import argparse
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_FILE = Path("riskshield_tab.py")

# --- Anchors, verified against the real file -------------------------------

IMPORT_ANCHOR = "    bull_put_spread, CONTRACT_MULTIPLIER,\n)"
IMPORT_INSERT = "\n\nfrom put_tracker_tab import render_put_tracker_tab"

TAB_ANCHOR = (
    "tab_bs, tab_iv, tab_rv, tab_prob, tab_screener = st.tabs(\n"
    '        ["מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)", '
    '"הסתברות OTM (Put)", "סורק רב-מניות"]\n'
    "    )"
)
TAB_REPLACEMENT = (
    "tab_bs, tab_iv, tab_rv, tab_prob, tab_screener, tab_tracker = st.tabs(\n"
    '        ["מחיר וגריקס", "תנודתיות גלומה (IV)", "תנודתיות ממומשת (RV)", '
    '"הסתברות OTM (Put)", "סורק רב-מניות", "📒 מעקב פרמיות"]\n'
    "    )"
)

DISPATCH_ANCHOR = "    st.markdown('</div>', unsafe_allow_html=True)"
DISPATCH_INSERT = (
    "    with tab_tracker:\n"
    "        render_put_tracker_tab()\n\n"
)


def read_normalized(path: Path) -> tuple[str, bool]:
    """Read file as raw bytes, detect CRLF, return (text_with_lf, was_crlf)."""
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


def validate_single_anchor(text: str, anchor: str, label: str) -> None:
    count = text.count(anchor)
    if count == 0:
        print(f"[FAIL] {label} anchor not found: {anchor!r}")
        sys.exit(1)
    if count > 1:
        print(f"[FAIL] {label} anchor found {count} times (must be exactly 1): {anchor!r}")
        sys.exit(1)
    print(f"[OK] {label} anchor found exactly once")


def apply_patch(text: str) -> str:
    # 1. Add the import, right after the options_engine import block closes.
    text = text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_INSERT, 1)

    # 2. Add the new tab variable + label to the st.tabs() call.
    text = text.replace(TAB_ANCHOR, TAB_REPLACEMENT, 1)

    # 3. Add the new `with tab_tracker:` block right before the function's
    #    final closing-div markdown call.
    text = text.replace(DISPATCH_ANCHOR, DISPATCH_INSERT + DISPATCH_ANCHOR, 1)

    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    if not TARGET_FILE.exists():
        print(f"[FAIL] {TARGET_FILE} not found in current directory")
        sys.exit(1)

    original_text, was_crlf = read_normalized(TARGET_FILE)

    validate_single_anchor(original_text, IMPORT_ANCHOR, "import")
    validate_single_anchor(original_text, TAB_ANCHOR, "tab registration")
    validate_single_anchor(original_text, DISPATCH_ANCHOR, "dispatch (closing div)")

    patched_text = apply_patch(original_text)

    # Syntax check before writing anything
    try:
        ast.parse(patched_text)
    except SyntaxError as e:
        print(f"[FAIL] Patched file would not parse: {e}")
        sys.exit(1)
    print("[OK] Patched content passes ast.parse")

    if not args.apply:
        print("\n--- DRY RUN — no changes written. Re-run with --apply to write. ---")
        print("Preview of inserted lines:")
        print(" +", IMPORT_INSERT.strip())
        print(" + (tab tuple/list updated to include tab_tracker / \"📒 מעקב פרמיות\")")
        print(" +", DISPATCH_INSERT.strip())
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = TARGET_FILE.with_suffix(TARGET_FILE.suffix + f".{timestamp}.bak")
    shutil.copy2(TARGET_FILE, backup_path)
    print(f"[OK] Backup written to {backup_path}")

    write_normalized(TARGET_FILE, patched_text, restore_crlf=was_crlf)
    print(f"[OK] {TARGET_FILE} patched (CRLF preserved: {was_crlf})")


if __name__ == "__main__":
    main()
