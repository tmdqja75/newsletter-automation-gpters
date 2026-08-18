"""Vendored humanize-korean files exist and are syntactically valid."""

import ast
from pathlib import Path

VENDORED_SCRIPTS = [
    "scripts/humanize/prepare_monolith_input.py",
    "scripts/humanize/verify_gates.py",
    "scripts/humanize/sanitize_text.py",
    "scripts/humanize/console.py",
    "scripts/humanize/checks.py",
]


def test_vendored_scripts_exist_and_parse():
    for rel_path in VENDORED_SCRIPTS:
        path = Path(rel_path)
        assert path.exists(), f"missing vendored file: {rel_path}"
        ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
