# Article SVG Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `article-writer` a tool that generates an SVG diagram for a topic when the topic warrants one, and let the existing text feedback loop revise that diagram in place.

**Architecture:** A new `create_svg_diagram` tool function (not a `deepagents` subagent — the orchestrator's `subagents` list is flat) makes one isolated LLM call with its own `SVG_DIAGRAM_PROMPT`. `article-writer` calls it during drafting to create a diagram; the orchestrator calls it during feedback rounds to revise one, reusing the same file path.

**Tech Stack:** Python, `langchain.chat_models.init_chat_model` (same pattern as `research_collector.py:_default_summarizer`), `webbrowser` stdlib, `xml.etree.ElementTree` stdlib for SVG validation, `pytest`.

**Spec:** `docs/superpowers/specs/2026-08-23-article-svg-diagrams-design.md`

## Global Constraints

- SVG is embedded via markdown `![]()` into a static file — it does not inherit host-page CSS. No `currentColor`, no external font links, no `<script>`/`<style>`/`<foreignObject>`.
- Text labels are Korean — font-family must include a CJK fallback (`'Apple SD Gothic Neo'`, `'Malgun Gothic'`) or labels render as tofu boxes.
- `viewBox` width capped near newsletter body width (~600-700px equivalent).
- A revision (`existing_svg_path` + `feedback` passed) must overwrite the same file path — never create a second file for the same topic.
- Tool failures return a string starting with `"오류:"` — this is the existing convention both `ORCHESTRATOR_PROMPT` and `ARTICLE_WRITER_PROMPT` already know to report-and-stop on for that one topic, not the whole run (`ORCHESTRATOR_PROMPT`'s `## 금지` section, verbatim: `리서치 결과가 없거나 도구가 "오류:"를 반환하면 토픽을 지어내지 말고 그대로 보고하고 중단하세요.`).
- `worth_it: false` is not an error — returns `"다이어그램 생략: ..."`, writes nothing.

---

### Task 1: `SVG_DIAGRAM_PROMPT` constant

**Files:**
- Modify: `src/config.py` (insert after the `ARTICLE_WRITER_PROMPT` block, i.e. after its closing `"""` and before the `# Newsletter template` comment)
- Test: `tests/test_prompts.py`

**Interfaces:**
- Produces: `config.SVG_DIAGRAM_PROMPT` (str) — consumed by Task 2's `_default_llm_call`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_prompts.py`, updating the existing import block at the top:

```python
from src.config import (
    TOPIC_RESEARCHER_PROMPT,
    ORCHESTRATOR_PROMPT,
    ARTICLE_WRITER_PROMPT,
    SVG_DIAGRAM_PROMPT,
)
```

Append these tests to the file:

```python
# --- SVG diagram prompt ---

def test_svg_diagram_prompt_scopes_to_one_diagram():
    """Must not write article prose, only draw one diagram."""
    assert "글은 쓰지 않습니다" in SVG_DIAGRAM_PROMPT or "다이어그램 1개" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_requires_viewbox():
    assert "viewBox" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_forbids_host_dependent_styling():
    """Embedded via <img>, so no currentColor / external font links / script."""
    assert "currentColor" in SVG_DIAGRAM_PROMPT
    assert "<script>" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_requires_cjk_font_fallback():
    assert "Gothic" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_requires_worth_it_output_field():
    assert "worth_it" in SVG_DIAGRAM_PROMPT
    assert "caption" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_handles_revision_mode():
    assert "existing_svg" in SVG_DIAGRAM_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_prompts.py -v -k svg_diagram`
Expected: FAIL — `ImportError: cannot import name 'SVG_DIAGRAM_PROMPT'`

- [ ] **Step 3: Add the constant**

In `src/config.py`, insert immediately after the `ARTICLE_WRITER_PROMPT` block's closing `"""` (the line right before `# Newsletter template`):

```python
SVG_DIAGRAM_PROMPT = """당신은 '오토마타' 뉴스레터의 다이어그램 전문가입니다. 아티클 하나에 들어갈
SVG 다이어그램 1개만 그립니다. 글은 쓰지 않습니다.

## 입력
- article_text: 완성된 아티클 본문
- focus: article-writer가 지정한 "이 다이어그램이 보여줘야 할 것" 한 문장
  (예: "온디바이스 추론이 클라우드 호출을 건너뛰는 경로")
- existing_svg (수정 요청일 때만): 이전에 그린 SVG + 사용자 피드백

## 그릴 것 정하기
- **이름이 아니라 메커니즘을 그리세요.** "캐시"라는 상자 하나가 아니라, 요청이
  캐시를 통과하는 경로, 캐시 앞뒤의 두 저장소, 캐시가 없으면 사라지는 화살표를
  그리세요. focus 문장이 가리키는 것만 그리고 나머지는 생략하세요.
- **비교라면 차이를 그리세요.** 두 구조를 나란히 놓고, 무엇이 다른지(추가/제거된
  화살표 하나, 우회하는 경로 하나)를 짚으세요. 연결선 없이 상자만 두 개 놓는 건
  비교가 아니라 목록입니다.
- **화살표에 라벨을 다세요.** 화살표는 "요청", "invalidate", "30초마다 polling"
  처럼 관계를 말해야 합니다. 라벨 없는 화살표는 정보가 아닙니다.
- **복잡도는 논지에 맞추세요.** 개념 하나면 상자 3개로 충분하고, 파이프라인
  전체를 다루면 그만큼 그리세요. 억지로 단순화하지도, 전체 시스템을 욱여넣지도
  마세요.
- 이 focus를 뒷받침하지 못하는 요소(로고, 장식, 무관한 컴포넌트)는 그리지 않습니다.

## SVG 작성 규칙
- `<svg viewBox="0 0 W H">` 하나만 출력하세요. W/H는 내용에 맞게 정하되 뉴스레터
  본문 폭 기준 가로 600~700px 상당을 넘기지 마세요.
- 순수 SVG 마크업만 사용: rect, circle, line, polyline, path, text, defs/marker.
  `<script>`, `<style>`, `<foreignObject>`, 외부 이미지/폰트 링크는 절대 넣지
  마세요 — 마크다운 이미지로 삽입되므로 외부 리소스는 로드되지 않습니다.
- 색상은 `currentColor`가 아니라 **직접 hex 값**을 지정하세요(임베드된 이미지는
  페이지 테마를 상속받지 못합니다). 밝은 배경(#FFFFFF 또는 #FAFAF8)을 가정하고,
  강조색 1개(오토마타 브랜드 톤 — 지정 없으면 #4F46E5 계열) + 중립 회색조
  2~3단계로 제한하세요.
- 텍스트는 `font-family="-apple-system, 'Apple SD Gothic Neo', 'Malgun Gothic',
  sans-serif"` 로 고정하세요 — 한글 라벨이 깨지지 않으려면 CJK 폴백이 필수입니다.
  글자 크기는 11~13px, 라벨은 단어 1~3개로 짧게. 설명 문장은 다이어그램 밖(캡션)에.
- 화살표 끝은 `<marker>` 또는 작은 `<polygon>`으로 그리세요.
- 요소는 격자에 맞춰 정렬하세요(같은 baseline, 균등한 간격) — 눈대중 배치는
  허술해 보입니다.
- 접근성을 위해 `<svg>`에 `role="img"`와 `<title>`(다이어그램이 보여주는 것 한 줄)을
  넣으세요.

## 출력
다음 필드를 가진 JSON만 반환하세요:
- svg: 완성된 <svg>...</svg> 마크업 (마크다운 코드펜스 없이 원본 그대로)
- caption: 다이어그램 아래에 넣을 한 줄 캡션 (해요체, 한국어)
- worth_it: 이 다이어그램이 글의 이해를 실제로 돕는지 (boolean). false면 svg는
  빈 문자열로 둡니다.

## 수정 요청 처리
existing_svg가 있으면 처음부터 다시 그리지 말고, 피드백이 가리키는 요소만
바꾸세요. 나머지 배치/색상/라벨은 그대로 유지합니다.
"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_prompts.py -v -k svg_diagram`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_prompts.py
git commit -m "feat: add SVG_DIAGRAM_PROMPT for diagram generation"
```

---

### Task 2: `create_svg_diagram` tool

**Files:**
- Create: `src/tools/diagram_tools.py`
- Test: `tests/test_diagram_tools.py`

**Interfaces:**
- Consumes: `config.SVG_DIAGRAM_PROMPT` (Task 1), `config.to_model_spec` and `config.MODEL_NAME` (existing, `src/config.py:14,23-33`), `config.ARTICLES_DIR` (existing, `src/config.py:36`).
- Produces: `create_svg_diagram(topic_slug: str, date_dir: str, article_text: str = "", focus: str = "", existing_svg_path: str | None = None, feedback: str | None = None, llm_call=None) -> str` — consumed by Task 3 (`article-writer`) and Task 4 (orchestrator). `llm_call` is `Callable[[str, str], str]` (system_prompt, user_content) -> raw text; defaults to a real LLM call, injectable in tests (same DI pattern as `research_collector.py`'s `summarizer` param).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_diagram_tools.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_diagram_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.tools.diagram_tools'`

- [ ] **Step 3: Implement the tool**

Create `src/tools/diagram_tools.py`:

```python
"""SVG diagram generation and revision for newsletter articles."""

import json
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import config


def _default_llm_call(system_prompt: str, user_content: str) -> str:
    """Make one isolated LLM call and return its raw text content."""
    from langchain.chat_models import init_chat_model

    model = init_chat_model(config.to_model_spec(config.MODEL_NAME))
    response = model.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ])
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)


def create_svg_diagram(
    topic_slug: str,
    date_dir: str,
    article_text: str = "",
    focus: str = "",
    existing_svg_path: str | None = None,
    feedback: str | None = None,
    llm_call=None,
) -> str:
    """Generate or revise one SVG diagram for an article topic.

    Creation: pass article_text + focus.
    Revision: pass existing_svg_path + feedback (article_text/focus omitted
    — the existing markup + feedback fully determine the edit).

    Returns a markdown snippet ready to paste into the article
    ("![caption](topic_slug.svg)\\n\\ncaption"), "다이어그램 생략: ..." if the
    LLM judged it not worth drawing, or "오류: ..." on failure.
    """
    if llm_call is None:
        llm_call = _default_llm_call

    user_parts = []
    if article_text:
        user_parts.append(f"article_text:\n{article_text}")
    if focus:
        user_parts.append(f"focus:\n{focus}")
    if existing_svg_path:
        existing_svg = Path(existing_svg_path).read_text(encoding="utf-8")
        user_parts.append(f"existing_svg:\n{existing_svg}")
    if feedback:
        user_parts.append(f"feedback:\n{feedback}")
    user_content = "\n\n".join(user_parts)

    try:
        raw = llm_call(config.SVG_DIAGRAM_PROMPT, user_content)
        data = json.loads(raw)
    except Exception as exc:
        return f"오류: SVG 생성 실패 - {exc}"

    if not data.get("worth_it"):
        return "다이어그램 생략: 이 토픽엔 다이어그램이 필요 없다고 판단했어요."

    svg = data.get("svg", "")
    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        return f"오류: SVG 생성 실패 - 잘못된 SVG 마크업 ({exc})"

    if existing_svg_path:
        svg_path = Path(existing_svg_path)
    else:
        svg_path = Path(config.ARTICLES_DIR) / date_dir / f"{topic_slug}.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")

    try:
        webbrowser.open(f"file://{svg_path.resolve()}")
    except Exception:
        pass

    caption = data.get("caption", "")
    return f"![{caption}]({svg_path.name})\n\n{caption}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_diagram_tools.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tools/diagram_tools.py tests/test_diagram_tools.py
git commit -m "feat: add create_svg_diagram tool"
```

---

### Task 3: Wire into `article-writer`

**Files:**
- Modify: `src/agents/article_writer.py`
- Modify: `src/config.py` (`ARTICLE_WRITER_PROMPT`, insert before the worked-example intro line)
- Test: `tests/test_agents_wiring.py`, `tests/test_prompts.py`

**Interfaces:**
- Consumes: `create_svg_diagram` (Task 2, `src/tools/diagram_tools.py`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_agents_wiring.py`, updating the top import block:

```python
from src.tools.diagram_tools import create_svg_diagram
```

Append:

```python
def test_article_writer_agent_has_diagram_tool():
    agent = build_article_writer_agent()
    assert create_svg_diagram in agent["tools"]
```

Add to `tests/test_prompts.py`, updating the import block to include `SVG_DIAGRAM_PROMPT` (already added in Task 1) — no further import needed since `ARTICLE_WRITER_PROMPT` is already imported. Append:

```python
def test_article_writer_prompt_instructs_diagram_tool():
    """Must know when and how to call create_svg_diagram and splice the result in."""
    assert "create_svg_diagram" in ARTICLE_WRITER_PROMPT
    assert "focus" in ARTICLE_WRITER_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_agents_wiring.py tests/test_prompts.py -v -k diagram`
Expected: FAIL — `ImportError: cannot import name 'create_svg_diagram' from 'src.tools.diagram_tools'` is not the case (Task 2 created it), so instead: `AssertionError` (tool not in `agent["tools"]`, text not in prompt).

- [ ] **Step 3: Wire the tool in**

In `src/agents/article_writer.py`, add the import and register the tool:

```python
from ..tools.search_tools import search_ai_news
from ..tools.content_tools import fetch_article_content
from ..tools.diagram_tools import create_svg_diagram
from ..config import ARTICLE_WRITER_PROMPT
```

```python
    return {
        "name": "article-writer",
        "description": "토픽별 아티클 작성 전문가. 필요 시 Tavily로 추가 리서치를 하고, 오토마타 톤앤매너에 맞춰 최종 아티클을 작성합니다.",
        "system_prompt": system_prompt,
        "tools": [search_ai_news, fetch_article_content, create_svg_diagram],
    }
```

In `src/config.py`, in `ARTICLE_WRITER_PROMPT`, insert a new section right after:

```
### 인라인 출처 유지
본문에 포함된 `(출처: https://...)` 형태의 인라인 출처 표기를 절대 제거하거나 수정하지 마세요.
```

and before:

```
아래는 위 가이드가 적용된 아티클 예시입니다:
```

insert:

```
## 다이어그램 (선택)
토픽의 핵심이 메커니즘이나 비교(예: A vs B 구조, 데이터가 오가는 경로)에 있다면
다이어그램이 도움이 되는지 판단하세요. 단순 발표/출시 소식이면 다이어그램 없이
넘어가세요.
다이어그램이 도움이 된다고 판단하면 create_svg_diagram(topic_slug, date_dir,
article_text=아티클 본문, focus="다이어그램이 보여줘야 할 것 한 문장")을 호출하세요.
topic_slug은 파일명으로 쓰이므로 영문 소문자와 하이픈만 사용한 짧은 slug로
지정하세요(예: "langgraph-subgraph-state"). 한글, 공백, 슬래시는 쓰지 마세요.
반환값이 "다이어그램 생략" 또는 "오류:"로 시작하면 다이어그램 없이 아티클만
반환하세요. 그 외의 경우 반환된 마크다운 스니펫을 아티클 본문 적절한 위치에
그대로 삽입하세요.

```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agents_wiring.py tests/test_prompts.py -v -k diagram`
Expected: PASS (2 tests)

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest tests/ -v`
Expected: PASS (all tests, including previously-passing ones)

- [ ] **Step 6: Commit**

```bash
git add src/agents/article_writer.py src/config.py tests/test_agents_wiring.py tests/test_prompts.py
git commit -m "feat: wire create_svg_diagram into article-writer"
```

---

### Task 4: Wire into orchestrator feedback loop

**Files:**
- Modify: `src/main.py`
- Modify: `src/config.py` (`ORCHESTRATOR_PROMPT`, `## 피드백 반영` section)
- Test: `tests/test_agents_wiring.py`, `tests/test_prompts.py`

**Interfaces:**
- Consumes: `create_svg_diagram` (Task 2).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_agents_wiring.py`:

```python
def test_create_newsletter_agent_registers_diagram_tool(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr("src.main._build_checkpointer", lambda: SimpleNamespace())

    create_newsletter_agent("2026-06-17")

    assert create_svg_diagram in captured["tools"]
```

Add to `tests/test_prompts.py`:

```python
def test_orchestrator_prompt_handles_diagram_feedback():
    """SVG-shaped feedback must call create_svg_diagram with the existing path, not edit .md text."""
    assert "create_svg_diagram" in ORCHESTRATOR_PROMPT
    assert "existing_svg_path" in ORCHESTRATOR_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_agents_wiring.py tests/test_prompts.py -v -k diagram`
Expected: FAIL — `create_svg_diagram not in captured["tools"]` / `"create_svg_diagram" not in ORCHESTRATOR_PROMPT`

- [ ] **Step 3: Wire the tool in**

In `src/main.py`, add the import:

```python
from .tools.diagram_tools import create_svg_diagram
```

Change the base tools list in `create_newsletter_agent`:

```python
    tools = [save_article, merge_newsletter, create_svg_diagram]
```

In `src/config.py`, in `ORCHESTRATOR_PROMPT`, replace:

```
## 피드백 반영 (후속 대화)
초안 완성 후 사용자가 피드백을 보내면, 전체를 다시 쓰지 말고 이미 저장된
아티클 파일(articles/{date}/*.md)을 직접 읽고 피드백이 가리키는 파일만
수정한 뒤 merge_newsletter를 다시 호출해 뉴스레터를 갱신하세요.
```

with:

```
## 피드백 반영 (후속 대화)
초안 완성 후 사용자가 피드백을 보내면, 전체를 다시 쓰지 말고 이미 저장된
아티클 파일(articles/{date}/*.md)을 직접 읽고 피드백이 가리키는 파일만
수정한 뒤 merge_newsletter를 다시 호출해 뉴스레터를 갱신하세요.

피드백이 다이어그램(화살표, 색상, 라벨, 배치 등 시각적 요소)을 가리키면 텍스트를
직접 고치지 말고 create_svg_diagram(topic_slug, date_dir,
existing_svg_path=해당 .svg 경로, feedback=사용자 피드백)을 호출해 같은 파일을
갱신하세요. 텍스트 내용에 대한 피드백은 기존대로 .md 파일을 직접 수정하세요.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agents_wiring.py tests/test_prompts.py -v -k diagram`
Expected: PASS (2 tests)

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add src/main.py src/config.py tests/test_agents_wiring.py tests/test_prompts.py
git commit -m "feat: wire create_svg_diagram into orchestrator feedback loop"
```

---

### Task 5: Manual smoke verification

**Files:** none (no code changes — this task verifies Tasks 1-4 work end to end through the real LLM, which unit tests with injected `llm_call` can't cover).

- [ ] **Step 1: Run a quick generation on a diagram-worthy topic**

Run: `uv run python run.py --quick --topics "LangGraph 서브그래프와 메인 그래프 간 상태 전달 구조"`

Expected: run completes, an `articles/{date}/01_*.svg` file exists, it opened in the browser automatically, and `articles/{date}/01_*.md` contains a `![...](01_*.svg)` link.

- [ ] **Step 2: Test the revision path**

When prompted for feedback (`_run_feedback_loop`), type a diagram-specific edit, e.g. `화살표 방향을 반대로 바꿔줘`.

Expected: the same `.svg` file is overwritten (not duplicated — confirm with `ls articles/{date}/*.svg`, should still be exactly one file for that topic), reopens in the browser showing the change, and the `.md` file's image link/caption line is unchanged.

- [ ] **Step 3: Confirm graceful skip on a non-visual topic**

Run: `uv run python run.py --quick --topics "OpenAI가 새 API 가격을 발표했다"`

Expected: run completes, no `.svg` file is produced for that topic (pure announcement, `worth_it: false` expected), article text is unaffected.
