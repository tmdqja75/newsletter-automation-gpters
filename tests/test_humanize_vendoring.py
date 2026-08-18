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


VENDORED_REFERENCES = [
    "skills/humanize-korean/references/metrics_v2.py",
    "skills/humanize-korean/references/metrics.py",
    "skills/humanize-korean/references/baseline.json",
    "skills/humanize-korean/references/baseline_v2.json",
    "skills/humanize-korean/references/quick-rules.md",
    "skills/humanize-korean/references/quick-rules.header.md",
    "skills/humanize-korean/references/quick-rules.footer.md",
    "skills/humanize-korean/references/diagnosis-rules.md",
    "skills/humanize-korean/references/rewriting-playbook.md",
]


def test_vendored_references_exist():
    for rel_path in VENDORED_REFERENCES:
        assert Path(rel_path).exists(), f"missing vendored file: {rel_path}"


def test_skill_md_exists_with_frontmatter():
    skill_md = Path("skills/humanize-korean/SKILL.md")
    assert skill_md.exists()
    content = skill_md.read_text(encoding="utf-8")
    assert content.startswith("---\nname: humanize-korean\n")
    assert "(출처: https://" in content  # citation-preservation rule present
