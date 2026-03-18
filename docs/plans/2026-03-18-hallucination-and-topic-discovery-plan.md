# Hallucination Reduction & Real-World Use Case Discovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two problems in the newsletter agent: (1) articles contain hallucinated facts, and (2) topic selection produces generic/uninteresting topics instead of compelling real-world AI use cases.

**Architecture:** All changes are prompt modifications in `src/config.py`. No new files, no new tools, no new subagents. Problem 1 is fixed by requiring the research agent to always fetch full article content before recommending topics, and requiring the orchestrator to cite sources inline. Problem 2 is fixed by adding a high-priority research category targeting real-world AI deployments, plus telling the topic selector to prefer use-case stories.

**Tech Stack:** Python, `src/config.py` prompt strings, `pytest` for tests.

---

### Task 1: Add prompt test file

**Files:**
- Create: `tests/test_prompts.py`

These tests verify the prompts contain the required instructions. They will fail until Tasks 2 and 3 are complete.

**Step 1: Write the failing tests**

Create `tests/test_prompts.py` with this content:

```python
"""Tests that config prompts contain required instructions."""

from src.config import (
    RESEARCH_AGENT_PROMPT,
    ORCHESTRATOR_PROMPT,
    TONE_EDITOR_PROMPT,
    TOPIC_SELECTOR_PROMPT,
)


# --- Problem 1: Hallucination fixes ---

def test_research_prompt_requires_fetch():
    """Research agent must be instructed to fetch full article content."""
    assert "fetch_article_content" in RESEARCH_AGENT_PROMPT
    # Must explicitly say fetching is mandatory, not optional
    assert "반드시" in RESEARCH_AGENT_PROMPT or "필수" in RESEARCH_AGENT_PROMPT


def test_orchestrator_prompt_requires_citations():
    """Orchestrator must be instructed to cite sources inline."""
    assert "출처" in ORCHESTRATOR_PROMPT
    # Must prohibit inventing facts
    assert "만들어내거나" in ORCHESTRATOR_PROMPT or "추측" in ORCHESTRATOR_PROMPT


def test_tone_editor_preserves_citations():
    """Tone editor must be told not to remove inline citations."""
    assert "출처" in TONE_EDITOR_PROMPT
    assert "제거" in TONE_EDITOR_PROMPT or "수정하지" in TONE_EDITOR_PROMPT


# --- Problem 2: Real-world use case discovery ---

def test_research_prompt_has_usecase_category():
    """Research agent must have a category for real-world AI use cases."""
    assert "실제 AI" in RESEARCH_AGENT_PROMPT or "활용 사례" in RESEARCH_AGENT_PROMPT
    # Must include Show HN targeting
    assert "Show HN" in RESEARCH_AGENT_PROMPT


def test_topic_selector_prioritizes_usecases():
    """Topic selector must be told to rank use-case stories highly."""
    assert "활용 사례" in TOPIC_SELECTOR_PROMPT or "실제" in TOPIC_SELECTOR_PROMPT
    # Must have weighting or priority guidance
    assert "우선" in TOPIC_SELECTOR_PROMPT or "높은" in TOPIC_SELECTOR_PROMPT
```

**Step 2: Run tests to verify they all fail**

```bash
uv run pytest tests/test_prompts.py -v
```

Expected: ALL 5 tests FAIL (the prompts don't have these instructions yet).

**Step 3: Commit the failing tests**

```bash
git add tests/test_prompts.py
git commit -m "test: add failing tests for prompt requirements"
```

---

### Task 2: Fix hallucination — update research, orchestrator, and tone editor prompts

**Files:**
- Modify: `src/config.py`

**Step 1: Add mandatory fetch instruction to `RESEARCH_AGENT_PROMPT`**

In `src/config.py`, find the end of `RESEARCH_AGENT_PROMPT` (before the closing `"""`). Add this block **before** the `## 출력 형식` section:

```python
### 8. 실제 AI 에이전트/LLM 활용 사례 (우선순위 최고)
```

Wait — that's Task 3. For Task 2, we're only adding the mandatory fetch + citation instructions.

Find `RESEARCH_AGENT_PROMPT` and add this section **before** `## 출력 형식`:

```
## 필수: 아티클 전문 수집
각 카테고리에서 토픽 후보를 찾은 후, 추천할 모든 토픽에 대해 반드시 `fetch_article_content`를 호출하여 원문 전체를 읽으세요.
검색 스니펫(요약)만으로는 충분하지 않습니다. 전문을 읽은 후에만 토픽을 추천하고 요약을 작성할 수 있습니다.
수집한 전문 내용을 출력에 포함시켜, 이후 아티클 작성 단계에서 참조할 수 있도록 하세요.
```

The exact edit in `src/config.py` — find this line:

```python
## 출력 형식
각 토픽에 대해 다음 정보를 제공하세요:
```

And insert before it:

```python
## 필수: 아티클 전문 수집
각 카테고리에서 토픽 후보를 찾은 후, 추천할 모든 토픽에 대해 반드시 `fetch_article_content`를 호출하여 원문 전체를 읽으세요.
검색 스니펫(요약)만으로는 충분하지 않습니다. 전문을 읽은 후에만 토픽을 추천하고 요약을 작성할 수 있습니다.
수집한 전문 내용을 출력에 포함시켜, 이후 아티클 작성 단계에서 참조할 수 있도록 하세요.

```

**Step 2: Add citation-constrained writing rules to `ORCHESTRATOR_PROMPT`**

In `ORCHESTRATOR_PROMPT`, add this section **after** the `## 검색 쿼리 가이드` section (before `## 필수 포함 토픽 처리`):

```python
## 팩트 기반 아티클 작성 규칙 (필수)
아티클 작성 시 다음 규칙을 반드시 준수하세요:
1. 수치, 날짜, 모델명, 벤치마크 점수, 회사 세부 정보 등 **모든 사실적 주장**은 research-agent가 수집한 원문 콘텐츠에 실제로 나타난 내용에서만 가져오세요.
2. 출처에 없는 사실을 만들어내거나 추측하지 마세요. 확인되지 않은 내용은 작성하지 않습니다.
3. 모든 사실적 주장 뒤에는 출처 URL을 인라인으로 표기하세요: `(출처: https://...)`
4. 여러 출처를 합성하여 새로운 사실을 만들지 마세요 — 사실 하나당 하나의 주요 출처를 사용하세요.

```

The exact location in `src/config.py` — find:

```python
## 필수 포함 토픽 처리
만약 사용자가 **필수 포함 토픽**을 명시했다면,
```

Insert the block above it.

**Step 3: Add citation-preservation rule to `TONE_EDITOR_PROMPT`**

In `TONE_EDITOR_PROMPT`, add this section **after** `### 인사말/마무리` and before `## 교정 지시`:

```python
### 인라인 출처 유지
본문에 포함된 `(출처: https://...)` 형태의 인라인 출처 표기를 절대 제거하거나 수정하지 마세요. 문체 교정 후에도 모든 출처 표기가 원래 위치에 그대로 남아 있어야 합니다.

```

**Step 4: Run the tests — 3 should now pass**

```bash
uv run pytest tests/test_prompts.py -v
```

Expected:
- `test_research_prompt_requires_fetch` — PASS
- `test_orchestrator_prompt_requires_citations` — PASS
- `test_tone_editor_preserves_citations` — PASS
- `test_research_prompt_has_usecase_category` — FAIL (not done yet)
- `test_topic_selector_prioritizes_usecases` — FAIL (not done yet)

**Step 5: Commit**

```bash
git add src/config.py
git commit -m "feat: require fetch_article_content and inline citations to reduce hallucination"
```

---

### Task 3: Improve topic discovery — add real-world use case category and selector weighting

**Files:**
- Modify: `src/config.py`

**Step 1: Add new research category to `RESEARCH_AGENT_PROMPT`**

In `src/config.py`, find the end of the numbered categories list in `RESEARCH_AGENT_PROMPT` (after `### 7. 학습 자료 (스터디 카페용)`). Add this new category before the `## 필수: 아티클 전문 수집` block added in Task 2:

```python
### 8. 실제 AI 에이전트/LLM 활용 사례 (우선순위 최고)
이 카테고리는 **가장 높은 우선순위**로 수집하세요. 실제 세계에서 AI 에이전트나 LLM을 창의적으로 활용한 사례를 찾습니다.

**HackerNews 검색 (search_hackernews 사용):**
- `Show HN AI agent`
- `Show HN LLM`
- `I built AI agent`
- `LLM automation results`

**Tavily 검색 (search_ai_news 사용):**
- `"AI agent" deployed production results 2026`
- `LLM automation case study real world 2026`
- `built with Claude ChatGPT solved problem 2026`

**찾아야 할 내용:**
- 개인 또는 기업이 AI 에이전트로 구체적인 문제를 해결한 스토리
- 전후 비교 지표 (절약 시간, 비용 절감, 성과 개선)
- 뜻밖의 산업 적용 사례 (헬스케어, 법률, 건설, 농업, 개인 프로젝트)
- 소규모 팀이나 개인이 AI 없이는 불가능했던 일을 해낸 사례

```

**Step 2: Add use-case prioritization to `TOPIC_SELECTOR_PROMPT`**

In `TOPIC_SELECTOR_PROMPT`, add this section **after** `## 선정 기준` and before `## 출력 형식`:

```python
## 우선순위 가중치
실제 AI 활용 사례 스토리(개인·기업이 AI 에이전트/LLM으로 구체적 문제를 해결한 사례)는 일반 모델 출시나 프레임워크 업데이트보다 **높은 순위**를 부여하세요.
단, GPT-5·Claude 4처럼 업계 판도를 바꾸는 초대형 발표는 예외입니다.
비기술적 독자가 "오, 이건 신기하다!" 또는 "나도 이렇게 써볼 수 있겠다!"라고 느낄 스토리를 우선합니다.

```

**Step 3: Run all tests — all 5 should pass**

```bash
uv run pytest tests/test_prompts.py -v
```

Expected: ALL 5 tests PASS.

**Step 4: Run the full test suite to make sure nothing broke**

```bash
uv run pytest tests/ -v
```

Expected: All existing tests still pass.

**Step 5: Commit**

```bash
git add src/config.py
git commit -m "feat: add real-world AI use case research category and topic selector weighting"
```

---

## Verification

After completing all tasks, do a quick manual smoke test:

```bash
uv run python run.py --quick
```

Check the generated article in `articles/{date}/test_article.md`:
- Does it contain at least one `(출처: https://...)` citation?
- Is the article content grounded in facts that could have come from a real source?

For full verification run with HITL:
```bash
uv run python run.py --hitl
```

Check that at least one of the 10 proposed topics is a real-world use case story (not just a model release).
