"""
Stage 3c fix script — shrinks the pill buttons (smaller padding/font,
no text wrap) so all 9 fit cleanly in one row.
Run from the project folder:  python fix_pill_size.py
"""

import sys

FILE = "alpha_paper_trading.py"

OLD_BLOCK = '''    .st-key-period_pills .stButton > button,
    .st-key-charttype_pills .stButton > button {
        background: transparent !important;
        border: 1px solid var(--c-border) !important;
        color: var(--c-text-2) !important;
        border-radius: 999px !important;
        font-family: var(--ff-mono) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 6px 4px !important;
        transition: all 0.15s ease !important;
    }'''

NEW_BLOCK = '''    .st-key-period_pills .stButton > button,
    .st-key-charttype_pills .stButton > button {
        background: transparent !important;
        border: 1px solid var(--c-border) !important;
        color: var(--c-text-2) !important;
        border-radius: 999px !important;
        font-family: var(--ff-mono) !important;
        font-size: 10.5px !important;
        font-weight: 600 !important;
        padding: 4px 2px !important;
        white-space: nowrap !important;
        min-width: 0 !important;
        transition: all 0.15s ease !important;
    }'''


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD_BLOCK)
    if count == 0:
        print("STOPPED — nothing was written. Block not found (maybe already changed).")
        sys.exit(1)
    if count > 1:
        print(f"STOPPED — found {count} matches (expected exactly 1).")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("SUCCESS — pill buttons shrunk to fit one row.")


if __name__ == "__main__":
    main()
