#!/usr/bin/env python3
"""
Format Qt Designer .ui (XML) and .qss (Qt stylesheet) files.

- .ui: pretty-printed via lxml with remove_blank_text=True.
- .qss: formatted via jsbeautifier with sensible defaults.

Usage (from project root):
    python tools/format_assets.py

This script formats:
- All .ui under ./ui
- All .qss under ./assets (recursively)

Notes:
- XML attribute ordering may change when re-serialized. This is not semantically significant.
- Back up or commit changes before large formatting runs.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# Optional imports with friendly messages
try:
    from lxml import etree as ET
except Exception as e:
    print("[format] Missing dependency: lxml. Install with: pip install lxml")
    raise

try:
    import jsbeautifier
except Exception as e:
    print("[format] Missing dependency: jsbeautifier. Install with: pip install jsbeautifier")
    raise

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = PROJECT_ROOT / 'ui'
ASSETS_DIR = PROJECT_ROOT / 'assets'


def format_ui_file(path: Path) -> bool:
    try:
        parser = ET.XMLParser(remove_blank_text=True)
        tree = ET.parse(str(path), parser)
        tree.write(str(path), pretty_print=True, xml_declaration=True, encoding='utf-8')
        return True
    except Exception as e:
        print(f"[format][ui] Failed: {path} -> {e}")
        return False


def format_qss_file(path: Path) -> bool:
    try:
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        opts.end_with_newline = True
        opts.preserve_newlines = True
        beautified = jsbeautifier.beautify(path.read_text(encoding='utf-8'), opts)
        path.write_text(beautified, encoding='utf-8')
        return True
    except Exception as e:
        print(f"[format][qss] Failed: {path} -> {e}")
        return False


def main() -> int:
    ui_count = 0
    ui_ok = 0
    qss_count = 0
    qss_ok = 0

    # .ui files under ui/
    if UI_DIR.exists():
        for p in sorted(UI_DIR.glob('*.ui')):
            ui_count += 1
            if format_ui_file(p):
                ui_ok += 1
    else:
        print(f"[format] UI dir not found: {UI_DIR}")

    # .qss files under assets/ (recursive)
    if ASSETS_DIR.exists():
        for p in sorted(ASSETS_DIR.rglob('*.qss')):
            qss_count += 1
            if format_qss_file(p):
                qss_ok += 1
    else:
        print(f"[format] Assets dir not found: {ASSETS_DIR}")

    print(f"[format] UI: {ui_ok}/{ui_count} formatted | QSS: {qss_ok}/{qss_count} formatted")
    return 0 if (ui_ok == ui_count and qss_ok == qss_count) else 1


if __name__ == '__main__':
    sys.exit(main())
