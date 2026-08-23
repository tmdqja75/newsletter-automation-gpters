"""Tests for preference-memory reading and prompt injection."""

from pathlib import Path

import src.main as main


def test_read_memory_returns_empty_string_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "MEMORY_FILE", "memory/preferences.md")

    assert main._read_memory() == ""


def test_read_memory_returns_file_contents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "MEMORY_FILE", "memory/preferences.md")
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "preferences.md").write_text("이모지 쓰지 마세요", encoding="utf-8")

    assert main._read_memory() == "이모지 쓰지 마세요"


def test_build_prompt_includes_preferences_when_present():
    prompt = main._build_prompt("2026-08-05", [], 4, "이모지 쓰지 마세요")
    assert "이모지 쓰지 마세요" in prompt
    assert "사용자 선호" in prompt


def test_build_prompt_omits_preferences_section_when_empty():
    prompt = main._build_prompt("2026-08-05", [], 4, "")
    assert "사용자 선호" not in prompt
