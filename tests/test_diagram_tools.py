"""Tests for SVG diagram generation and revision."""

import json

from src.tools.diagram_tools import create_svg_diagram

VALID_SVG = '<svg viewBox="0 0 100 100"><rect width="10" height="10"/></svg>'


def _fake_llm(response: dict):
    def llm_call(system_prompt, user_content):
        return json.dumps(response)
    return llm_call


def test_create_svg_diagram_worth_it_writes_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    llm_call = _fake_llm({"svg": VALID_SVG, "caption": "테스트 캡션", "worth_it": True})

    result = create_svg_diagram(
        "01_topic", "2026-08-23", article_text="본문", focus="핵심 흐름", llm_call=llm_call
    )

    svg_path = tmp_path / "articles" / "2026-08-23" / "01_topic.svg"
    assert svg_path.exists()
    assert svg_path.read_text(encoding="utf-8") == VALID_SVG
    assert result == "![테스트 캡션](01_topic.svg)\n\n테스트 캡션"


def test_create_svg_diagram_not_worth_it_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    llm_call = _fake_llm({"svg": "", "caption": "", "worth_it": False})

    result = create_svg_diagram(
        "01_topic", "2026-08-23", article_text="본문", focus="핵심 흐름", llm_call=llm_call
    )

    assert not (tmp_path / "articles" / "2026-08-23" / "01_topic.svg").exists()
    assert result.startswith("다이어그램 생략")


def test_create_svg_diagram_malformed_svg_returns_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    llm_call = _fake_llm({"svg": "<svg><rect></svg>", "caption": "c", "worth_it": True})

    result = create_svg_diagram(
        "01_topic", "2026-08-23", article_text="본문", focus="핵심 흐름", llm_call=llm_call
    )

    assert not (tmp_path / "articles" / "2026-08-23" / "01_topic.svg").exists()
    assert result.startswith("오류:")


def test_create_svg_diagram_revision_overwrites_existing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    svg_dir = tmp_path / "articles" / "2026-08-23"
    svg_dir.mkdir(parents=True)
    existing_path = svg_dir / "01_topic.svg"
    existing_path.write_text(VALID_SVG, encoding="utf-8")

    revised_svg = '<svg viewBox="0 0 100 100"><circle r="5"/></svg>'
    llm_call = _fake_llm({"svg": revised_svg, "caption": "수정됨", "worth_it": True})

    result = create_svg_diagram(
        "01_topic", "2026-08-23",
        existing_svg_path=str(existing_path), feedback="화살표 방향 바꿔줘",
        llm_call=llm_call,
    )

    assert existing_path.read_text(encoding="utf-8") == revised_svg
    assert len(list(svg_dir.glob("*.svg"))) == 1
    assert result == "![수정됨](01_topic.svg)\n\n수정됨"


def test_create_svg_diagram_llm_failure_returns_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def broken_llm(system_prompt, user_content):
        raise RuntimeError("network down")

    result = create_svg_diagram(
        "01_topic", "2026-08-23", article_text="본문", focus="핵심 흐름", llm_call=broken_llm
    )

    assert result.startswith("오류:")
    assert not (tmp_path / "articles").exists()


def test_create_svg_diagram_webbrowser_failure_does_not_propagate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import src.tools.diagram_tools as diagram_tools

    def broken_open(url):
        raise RuntimeError("no display")

    monkeypatch.setattr(diagram_tools.webbrowser, "open", broken_open)
    llm_call = _fake_llm({"svg": VALID_SVG, "caption": "c", "worth_it": True})

    result = create_svg_diagram(
        "01_topic", "2026-08-23", article_text="본문", focus="핵심 흐름", llm_call=llm_call
    )

    assert result == "![c](01_topic.svg)\n\nc"
