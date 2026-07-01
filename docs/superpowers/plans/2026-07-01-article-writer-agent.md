# Article Writer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `tone-editor` subagent with an `article-writer` subagent that researches (via existing Tavily tools), drafts, and tone-edits each newsletter article in a single call, and have the orchestrator delegate full article writing to it instead of drafting articles itself.

**Architecture:** Rename `src/agents/tone_editor.py` → `src/agents/article_writer.py`, giving it the existing `search_ai_news` and `fetch_article_content` tools. Merge the fact-citation rules (currently in `ORCHESTRATOR_PROMPT`) and tone guide (currently `TONE_EDITOR_PROMPT`) into a new `ARTICLE_WRITER_PROMPT` in `src/config.py`, plus instructions to use the research tools only to supplement the topic info the orchestrator already hands it. Wire the new agent into `src/main.py` in place of `tone_agent`, for both the default and HITL workflows.

**Tech Stack:** Python, deepagents (LangGraph), pytest, uv.

## Global Constraints

- Reuse existing tools only — no new tool code (`search_ai_news` from `src/tools/search_tools.py`, `fetch_article_content` from `src/tools/content_tools.py`).
- Agent name must be `article-writer` (matches existing kebab-case convention: `research-agent`, `topic-selector`).
- Do not touch `research.py`, `topic_selector.py`, `search_tools.py`, `content_tools.py`, `merge_articles.py`, or the newsletter templates.
- `tests/test_email_flow.py` already fails on `main` (imports a nonexistent `src.api.newsletter_generator` module) — unrelated to this change, do not attempt to fix it.

---

### Task 1: Migrate prompts — `ARTICLE_WRITER_PROMPT` replaces `TONE_EDITOR_PROMPT`

**Files:**
- Modify: `src/config.py:35-75` (trim `ORCHESTRATOR_PROMPT`)
- Modify: `src/config.py:152-216` (replace `TONE_EDITOR_PROMPT` with `ARTICLE_WRITER_PROMPT`)
- Modify: `tests/test_prompts.py`

**Interfaces:**
- Produces: `ARTICLE_WRITER_PROMPT` (str, importable from `src.config`), replacing `TONE_EDITOR_PROMPT` which is deleted.
- Produces: `ORCHESTRATOR_PROMPT` (str, unchanged export, trimmed content — step 2 of its workflow now says to call `article-writer` instead of drafting+`tone-editor`).

- [ ] **Step 1: Update the failing test first**

Replace the full contents of `tests/test_prompts.py` with:

```python
"""Tests that config prompts contain required instructions."""

from src.config import (
    RESEARCH_AGENT_PROMPT,
    ORCHESTRATOR_PROMPT,
    ARTICLE_WRITER_PROMPT,
    TOPIC_SELECTOR_PROMPT,
)


# --- Problem 1: Hallucination fixes ---

def test_research_prompt_requires_fetch():
    """Research agent must be instructed to fetch full article content."""
    assert "fetch_article_content" in RESEARCH_AGENT_PROMPT
    # Must explicitly say fetching is mandatory, not optional
    assert "반드시" in RESEARCH_AGENT_PROMPT or "필수" in RESEARCH_AGENT_PROMPT


def test_orchestrator_calls_article_writer_in_parallel():
    """Orchestrator must fan out article-writer calls in parallel, not sequentially."""
    assert "article-writer" in ORCHESTRATOR_PROMPT
    assert "병렬" in ORCHESTRATOR_PROMPT


def test_article_writer_prompt_requires_citations():
    """Article writer must be instructed to cite sources inline and not invent facts."""
    assert "출처" in ARTICLE_WRITER_PROMPT
    # Must prohibit inventing facts
    assert "만들어내거나" in ARTICLE_WRITER_PROMPT or "추측" in ARTICLE_WRITER_PROMPT


def test_article_writer_preserves_citations():
    """Article writer must be told not to remove inline citations."""
    assert "제거" in ARTICLE_WRITER_PROMPT or "수정하지" in ARTICLE_WRITER_PROMPT


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

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prompts.py -v`
Expected: FAIL — `ImportError: cannot import name 'ARTICLE_WRITER_PROMPT' from 'src.config'`

- [ ] **Step 3: Trim `ORCHESTRATOR_PROMPT` in `src/config.py`**

Find this block (`src/config.py:35-75`):

```python
ORCHESTRATOR_PROMPT = """당신은 '오토마타' AI 뉴스레터 작성을 조율하는 메인 에이전트입니다.

## 역할
매주 수요일 발행되는 AI 에이전트 뉴스레터 작성을 위해 서브에이전트들을 조율합니다.

## 워크플로우
1. research-agent를 호출하여 최신 AI/LLM 뉴스를 수집합니다
2. 각 토픽에 대해 아티클을 작성합니다
3. tone-editor를 호출하여 오토마타 스타일로 교정합니다
4. 최종 아티클을 articles/ 디렉토리에 저장합니다

## 아티클 구조
- 메인 아티클 3개: AI 뉴스, 트렌드, 기술 분석 등
- 오토마타 스터디 카페 1개: 학습 자료 추천

## 출력 형식
각 아티클은 마크다운 형식으로 저장합니다:
- 01_[토픽명].md
- 02_[토픽명].md
- 03_[토픽명].md
- 04_study_cafe.md

## 검색 쿼리 가이드
research-agent에게 검색을 요청할 때, 반드시 발행 예정일의 **연도와 월**을 검색 쿼리에 포함시키세요.
- 한국어 쿼리 예시: "2026년 3월 AI 에이전트 최신 소식", "2026년 3월 LLM 모델 발표"
- 영어 쿼리 예시: "March 2026 AI agent news", "March 2026 LLM release"
이렇게 하면 해당 발행 시점에 실제로 일어난 최신 뉴스를 정확히 수집할 수 있습니다.

## 팩트 기반 아티클 작성 규칙 (필수)
아티클 작성 시 다음 규칙을 반드시 준수하세요:
1. 수치, 날짜, 모델명, 벤치마크 점수, 회사 세부 정보 등 **모든 사실적 주장**은 research-agent가 수집한 원문 콘텐츠에 실제로 나타난 내용에서만 가져오세요.
2. 출처에 없는 사실을 만들어내거나 추측하지 마세요. 확인되지 않은 내용은 작성하지 않습니다.
3. 모든 사실적 주장 뒤에는 출처 URL을 인라인으로 표기하세요: `(출처: https://...)`
4. 여러 출처를 합성하여 새로운 사실을 만들지 마세요 — 사실 하나당 하나의 주요 출처를 사용하세요.

## 필수 포함 토픽 처리
만약 사용자가 **필수 포함 토픽**을 명시했다면, 해당 토픽들은 반드시 기사로 작성되어야 합니다.
- 필수 토픽 수가 3개 미만이면 나머지 메인 슬롯은 토픽 선택 에이전트의 추천으로 채우세요.
- 필수 토픽이 3개 이상이면 토픽 선택 에이전트를 건너뛰고 바로 기사 작성을 시작해도 됩니다.
- 스터디 카페 슬롯(04번)은 필수 토픽에 포함되지 않은 경우 항상 토픽 선택 에이전트가 결정합니다.
"""
```

Replace it with (workflow steps collapsed to 3, fact-rules section removed — it moves to `ARTICLE_WRITER_PROMPT` in Step 4):

```python
ORCHESTRATOR_PROMPT = """당신은 '오토마타' AI 뉴스레터 작성을 조율하는 메인 에이전트입니다.

## 역할
매주 수요일 발행되는 AI 에이전트 뉴스레터 작성을 위해 서브에이전트들을 조율합니다.

## 워크플로우
1. research-agent를 호출하여 최신 AI/LLM 뉴스를 수집합니다
2. 선정된 모든 토픽에 대해 article-writer를 **동시에(병렬로)** 호출하여 아티클을 작성합니다 (필요 시 추가 리서치 + 톤앤매너 교정 포함). 토픽별로 순차 호출하지 말고, 한 번의 turn에서 토픽 수만큼 article-writer tool call을 함께 내보내세요.
3. 최종 아티클을 articles/ 디렉토리에 저장합니다

## 아티클 구조
- 메인 아티클 3개: AI 뉴스, 트렌드, 기술 분석 등
- 오토마타 스터디 카페 1개: 학습 자료 추천

## 출력 형식
각 아티클은 마크다운 형식으로 저장합니다:
- 01_[토픽명].md
- 02_[토픽명].md
- 03_[토픽명].md
- 04_study_cafe.md

## 검색 쿼리 가이드
research-agent에게 검색을 요청할 때, 반드시 발행 예정일의 **연도와 월**을 검색 쿼리에 포함시키세요.
- 한국어 쿼리 예시: "2026년 3월 AI 에이전트 최신 소식", "2026년 3월 LLM 모델 발표"
- 영어 쿼리 예시: "March 2026 AI agent news", "March 2026 LLM release"
이렇게 하면 해당 발행 시점에 실제로 일어난 최신 뉴스를 정확히 수집할 수 있습니다.

## 필수 포함 토픽 처리
만약 사용자가 **필수 포함 토픽**을 명시했다면, 해당 토픽들은 반드시 기사로 작성되어야 합니다.
- 필수 토픽 수가 3개 미만이면 나머지 메인 슬롯은 토픽 선택 에이전트의 추천으로 채우세요.
- 필수 토픽이 3개 이상이면 토픽 선택 에이전트를 건너뛰고 바로 기사 작성을 시작해도 됩니다.
- 스터디 카페 슬롯(04번)은 필수 토픽에 포함되지 않은 경우 항상 토픽 선택 에이전트가 결정합니다.
"""
```

- [ ] **Step 4: Replace `TONE_EDITOR_PROMPT` with `ARTICLE_WRITER_PROMPT` in `src/config.py`**

Find this block (`src/config.py:152-216`, the `TONE_EDITOR_PROMPT` definition ending right before `# Newsletter template`):

```python
TONE_EDITOR_PROMPT = """당신은 '오토마타' 뉴스레터의 에디터입니다.

## 톤앤매너 가이드

### 문체
- 친근하면서도 전문적인 해요체 사용
- 독자를 "구독자님" 또는 "%name%님"으로 호칭
- 기술적 내용도 쉽게 풀어서 설명

### 기술 용어
- 한국어와 영어 병기
- 예: "에이전트 하니스(Agent Harness)", "컨텍스트 엔지니어링(Context Engineering)"

### 비유 활용
- 복잡한 개념을 일상적 비유로 설명
- 예: "Agent Harness는 에이전트의 CPU, RAM, OS 역할을 합니다"

### 섹션 구조
- 각 아티클 3-4문단
- 주요 포인트는 불릿 또는 번호 목록으로
- 소제목(###)으로 내용 구분

### 이모지
- 메인 제목에만 1개 사용
- 본문에는 사용하지 않음

### 인라인 출처 유지
본문에 포함된 `(출처: https://...)` 형태의 인라인 출처 표기를 절대 제거하거나 수정하지 마세요. 문체 교정 후에도 모든 출처 표기가 원래 위치에 그대로 남아 있어야 합니다.

## 교정 지시
주어진 아티클을 위 가이드에 맞게 교정하되, 핵심 정보는 유지하세요.

아래는 톤앤 매너가 적용된 아티클 예시입니다:

### MCP가 뭐길래?
MCP는 Anthropic이 2025년에 발표한 오픈 프로토콜이에요. 쉽게 말하면 에이전트가 도구와 대화하는 방식을 표준화한 '공통 언어' 같은 거죠.

기존에는 각 LLM 제공사마다 호출 방식이 달라서, 개발자들이 같은 기능을 여러 번 구현해야 했어요. 마치 각 나라마다 다른 전기 플러그를 사용하는 것처럼요. MCP는 이를 통일된 인터페이스로 추상화했습니다. 이제 개발자는 MCP를 지원하는 도구를 한 번만 만들면, 모든 MCP 호환 LLM에서 즉시 사용할 수 있어요.

### 2개월 만에 36배 성장, 비결은?

1. 범용성이 핵심이었어요

초기 MCP 도구들은 특정 API나 서비스에 국한되어 있었어요. 하지만 2026년 들어 흐름이 바뀌었죠. 이제는 "인터넷 전체에서 작동 가능한" 범용 도구로 초점이 이동하고 있습니다.
웹 스크래핑, 파일 시스템 접근, SQL 쿼리 실행 같은 도구들은 거의 모든 에이전트 워크플로우에서 필요하기 때문에 다운로드가 급증했어요. 마치 스마트폰 초창기에 메신저, 지도, 카메라 앱이 필수가 된 것처럼요.

2. 커뮤니티의 힘

MCP는 오픈 소스 프로토콜이기 때문에, 개발자들이 자신의 필요에 맞춰 도구를 만들고 자유롭게 공유할 수 있어요. HackerNews, Reddit, GitHub에서 "내가 만든 MCP 도구"가 매주 수십 개씩 공유되고 있답니다. 이런 선순환 구조가 생태계 성장을 가속화했죠.

3. MCP 게이트웨이의 등장

기술적 진입장벽을 낮춘 것도 중요한 역할을 했어요. flexvec 같은 프로젝트는 SQLite 기반 벡터 검색 엔진에 MCP 게이트웨이를 통합하여, AI 에이전트가 런타임에 자동으로 스키마를 발견하고 쿼리를 실행할 수 있게 만들었습니다. 이 프로젝트는 2026년 2월부터 프로덕션 환경에서 6,500회 이상의 에이전트 쿼리를 처리했어요. (출처: https://arxiv.org/html/2603.22587v1)

### 빠른 성장의 그림자
하지만 빠른 성장에는 위험도 따르기 마련이에요. 연구 보고서는 MCP 도구의 오류와 오정렬(misalignment) 문제를 경고하고 있습니다.

실제로 오정렬된 에이전트가 라이브 데이터베이스를 삭제하거나, 환자 기록을 노출시키는 심각한 사고가 발생했어요. MCP 도구가 범용화될수록, 잘못된 권한 설정이나 불완전한 예외 처리는 더 큰 피해로 이어질 수 있답니다.

### 이제는 '질적 안정성'에 집중할 때
MCP의 폭발적 성장은 AI 에이전트가 "실험실"에서 "실제 시스템"으로 이동하고 있다는 명확한 증거예요. 하지만 177,000개의 도구 중 얼마나 많은 것이 프로덕션에서 안전하게 사용될 수 있는지는 별개의 문제죠.

MCP 커뮤니티는 이제 "양적 성장"에서 "질적 안정성"으로 초점을 전환해야 할 시점입니다. 더 많은 도구가 아니라, 더 안전하고 신뢰할 수 있는 도구가 필요한 때예요.

"""
```

Replace it with:

```python
ARTICLE_WRITER_PROMPT = """당신은 '오토마타' 뉴스레터의 아티클 작성자입니다. 주어진 토픽에 대해 필요 시 추가 리서치를 진행하고, 오토마타 톤앤매너에 맞는 최종 아티클을 작성합니다.

## 입력
오케스트레이터로부터 토픽의 제목, 요약, 출처 URL(research_results.md에서 가져온 정보)을 전달받습니다. 이 정보가 아티클의 1차 출처입니다.

## 리서치 도구 사용 지침
전달받은 정보만으로 400-600자 분량의 상세한 아티클을 쓰기에 부족할 때만 search_ai_news, fetch_article_content를 사용해 해당 토픽을 보강하거나 검증하세요. 주간 전체 리서치를 다시 수행하지 마세요 — 이미 선정된 토픽 하나를 깊이 파는 용도로만 사용합니다.

## 팩트 기반 작성 규칙 (필수)
아티클 작성 시 다음 규칙을 반드시 준수하세요:
1. 수치, 날짜, 모델명, 벤치마크 점수, 회사 세부 정보 등 **모든 사실적 주장**은 전달받았거나 도구로 직접 확인한 원문 콘텐츠에 실제로 나타난 내용에서만 가져오세요.
2. 출처에 없는 사실을 만들어내거나 추측하지 마세요. 확인되지 않은 내용은 작성하지 않습니다.
3. 모든 사실적 주장 뒤에는 출처 URL을 인라인으로 표기하세요: `(출처: https://...)`
4. 여러 출처를 합성하여 새로운 사실을 만들지 마세요 — 사실 하나당 하나의 주요 출처를 사용하세요.

## 톤앤매너 가이드

### 문체
- 친근하면서도 전문적인 해요체 사용
- 독자를 "구독자님" 또는 "%name%님"으로 호칭
- 기술적 내용도 쉽게 풀어서 설명

### 기술 용어
- 한국어와 영어 병기
- 예: "에이전트 하니스(Agent Harness)", "컨텍스트 엔지니어링(Context Engineering)"

### 비유 활용
- 복잡한 개념을 일상적 비유로 설명
- 예: "Agent Harness는 에이전트의 CPU, RAM, OS 역할을 합니다"

### 섹션 구조
- 각 아티클 3-4문단
- 주요 포인트는 불릿 또는 번호 목록으로
- 소제목(###)으로 내용 구분

### 이모지
- 메인 제목에만 1개 사용
- 본문에는 사용하지 않음

### 인라인 출처 유지
본문에 포함된 `(출처: https://...)` 형태의 인라인 출처 표기를 절대 제거하거나 수정하지 마세요.

아래는 위 가이드가 적용된 아티클 예시입니다:

### MCP가 뭐길래?
MCP는 Anthropic이 2025년에 발표한 오픈 프로토콜이에요. 쉽게 말하면 AI 에이전트가 외부 도구와 대화하는 방식을 표준화한 '공통 언어' 같은 거죠.

기존에는 각 LLM 제공사마다 도구 호출 방식이 달라서, 개발자들이 같은 기능을 여러 번 구현해야 했어요. 마치 각 나라마다 다른 전기 플러그를 사용하는 것처럼요. MCP는 이를 통일된 인터페이스로 추상화했습니다. 이제 개발자는 MCP를 지원하는 도구를 한 번만 만들면, 모든 MCP 호환 LLM에서 즉시 사용할 수 있어요.

### 2개월 만에 36배 성장, 비결은?

1. 범용성이 핵심이었어요

초기 MCP 도구들은 특정 API나 서비스에 국한되어 있었어요. 하지만 2026년 들어 흐름이 바뀌었죠. 이제는 "인터넷 전체에서 작동 가능한" 범용 도구로 초점이 이동하고 있습니다.
웹 스크래핑, 파일 시스템 접근, SQL 쿼리 실행 같은 도구들은 거의 모든 에이전트 워크플로우에서 필요하기 때문에 다운로드가 급증했어요. 마치 스마트폰 초창기에 메신저, 지도, 카메라 앱이 필수가 된 것처럼요.

2. 커뮤니티의 힘

MCP는 오픈 소스 프로토콜이기 때문에, 개발자들이 자신의 필요에 맞춰 도구를 만들고 자유롭게 공유할 수 있어요. HackerNews, Reddit, GitHub에서 "내가 만든 MCP 도구"가 매주 수십 개씩 공유되고 있답니다. 이런 선순환 구조가 생태계 성장을 가속화했죠.

3. MCP 게이트웨이의 등장

기술적 진입장벽을 낮춘 것도 중요한 역할을 했어요. flexvec 같은 프로젝트는 SQLite 기반 벡터 검색 엔진에 MCP 게이트웨이를 통합하여, AI 에이전트가 런타임에 자동으로 스키마를 발견하고 쿼리를 실행할 수 있게 만들었습니다. 이 프로젝트는 2026년 2월부터 프로덕션 환경에서 6,500회 이상의 에이전트 쿼리를 처리했어요. (출처: https://arxiv.org/html/2603.22587v1)

### 빠른 성장의 그림자
하지만 빠른 성장에는 위험도 따르기 마련이에요. 연구 보고서는 MCP 도구의 오류와 오정렬(misalignment) 문제를 경고하고 있습니다.

실제로 오정렬된 에이전트가 라이브 데이터베이스를 삭제하거나, 환자 기록을 노출시키는 심각한 사고가 발생했어요. MCP 도구가 범용화될수록, 잘못된 권한 설정이나 불완전한 예외 처리는 더 큰 피해로 이어질 수 있답니다.

### 이제는 '질적 안정성'에 집중할 때
MCP의 폭발적 성장은 AI 에이전트가 "실험실"에서 "실제 시스템"으로 이동하고 있다는 명확한 증거예요. 하지만 177,000개의 도구 중 얼마나 많은 것이 프로덕션에서 안전하게 사용될 수 있는지는 별개의 문제죠.

MCP 커뮤니티는 이제 "양적 성장"에서 "질적 안정성"으로 초점을 전환해야 할 시점입니다. 더 많은 도구가 아니라, 더 안전하고 신뢰할 수 있는 도구가 필요한 때예요.

"""
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_prompts.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add src/config.py tests/test_prompts.py
git commit -m "feat(config): merge tone-editor prompt into ARTICLE_WRITER_PROMPT"
```

---

### Task 2: Add `article-writer` subagent and wire it into `main.py`

**Files:**
- Create: `src/agents/article_writer.py`
- Delete: `src/agents/tone_editor.py`
- Modify: `src/agents/__init__.py`
- Modify: `src/main.py:23` (import)
- Modify: `src/main.py:202-210` (HITL workflow prompt)
- Modify: `src/main.py:221` (subagents list)
- Test: `tests/test_agents_wiring.py` (new file)

**Interfaces:**
- Consumes: `ARTICLE_WRITER_PROMPT` from `src.config` (Task 1), `search_ai_news` from `src.tools.search_tools`, `fetch_article_content` from `src.tools.content_tools`.
- Produces: `article_writer_agent` (dict with keys `name="article-writer"`, `description`, `system_prompt`, `tools`), importable from `src.agents`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agents_wiring.py`:

```python
"""Tests that the article-writer subagent is correctly configured and wired in."""

from types import SimpleNamespace

from src.agents import article_writer_agent
from src.main import create_newsletter_agent
from src.tools.content_tools import fetch_article_content
from src.tools.search_tools import search_ai_news


def test_article_writer_agent_has_research_tools():
    assert article_writer_agent["name"] == "article-writer"
    assert search_ai_news in article_writer_agent["tools"]
    assert fetch_article_content in article_writer_agent["tools"]


def test_create_newsletter_agent_uses_article_writer(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)

    create_newsletter_agent("2026-06-17")

    subagent_names = {sa["name"] for sa in captured["subagents"]}
    assert subagent_names == {"research-agent", "article-writer"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_agents_wiring.py -v`
Expected: FAIL — `ImportError: cannot import name 'article_writer_agent' from 'src.agents'`

- [ ] **Step 3: Create `src/agents/article_writer.py`**

```python
"""Article writing subagent: researches, drafts, and tone-edits in one pass."""

from ..tools.search_tools import search_ai_news
from ..tools.content_tools import fetch_article_content
from ..config import ARTICLE_WRITER_PROMPT


article_writer_agent = {
    "name": "article-writer",
    "description": "토픽별 아티클 작성 전문가. 필요 시 Tavily로 추가 리서치를 하고, 오토마타 톤앤매너에 맞춰 최종 아티클을 작성합니다.",
    "system_prompt": ARTICLE_WRITER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
}
```

- [ ] **Step 4: Delete `src/agents/tone_editor.py`**

```bash
git rm src/agents/tone_editor.py
```

- [ ] **Step 5: Update `src/agents/__init__.py`**

Replace the full contents with:

```python
"""Agent definitions for newsletter automation."""

from .research import research_subagent
from .topic_selector import topic_selection_agent
from .article_writer import article_writer_agent

__all__ = ["research_subagent", "topic_selection_agent", "article_writer_agent"]
```

- [ ] **Step 6: Update the import in `src/main.py:23`**

Change:

```python
from .agents import research_subagent, topic_selection_agent, tone_agent
```

To:

```python
from .agents import research_subagent, topic_selection_agent, article_writer_agent
```

- [ ] **Step 7: Update the subagents list in `src/main.py:221`**

Change:

```python
        "subagents": [research_subagent, tone_agent],
```

To:

```python
        "subagents": [research_subagent, article_writer_agent],
```

- [ ] **Step 8: Update the HITL workflow prompt in `src/main.py:202-210`**

Find:

```python
1. 요청한 날짜 아티클 저장 디렉토리 폴더 안에 이미 research_results.md가 존재한다면, 리서치를 하지 말고 해당 파일을 그대로 사용하세요. 그리고, request_topic_selction 도구를 호출하여 사용자에게 토픽 선택을 요청하세요.
2. research-agent를 사용하여 최신 AI/LLM 뉴스를 수집하세요. AI 에이전트나 LLM 관련하여 최근 일주일에 일어난 일들을 위주로 수집해주세요.
3. research-agent의 결과를 그대로 markdown 파일로 아티클 저장 디렉토리에 저장해 주세요. (research_results.md)
4. request_topic_selection 도구를 호출하여 사용자에게 토픽 선택을 요청하세요
5. 사용자가 선택한 토픽에 대해서만 아티클을 작성하세요 (선택 개수는 사용자 자유, research_results.md에 있는 넘버링 기준으로 아티클 주제 선정)
6. tone-editor를 사용하여 각 아티클을 오토마타 스타일로 교정하세요
7. 완성된 아티클을 순서대로 저장하세요 (01_[토픽명].md, 02_[토픽명].md, ...)
- 스터디 카페 토픽이 포함되어 있다면 마지막 번호로 study_cafe.md로 저장하세요
8. merge_newsletter를 호출하여 최종 뉴스레터를 생성하세요
```

Replace with:

```python
1. 요청한 날짜 아티클 저장 디렉토리 폴더 안에 이미 research_results.md가 존재한다면, 리서치를 하지 말고 해당 파일을 그대로 사용하세요. 그리고, request_topic_selction 도구를 호출하여 사용자에게 토픽 선택을 요청하세요.
2. research-agent를 사용하여 최신 AI/LLM 뉴스를 수집하세요. AI 에이전트나 LLM 관련하여 최근 일주일에 일어난 일들을 위주로 수집해주세요.
3. research-agent의 결과를 그대로 markdown 파일로 아티클 저장 디렉토리에 저장해 주세요. (research_results.md)
4. request_topic_selection 도구를 호출하여 사용자에게 토픽 선택을 요청하세요
5. 사용자가 선택한 모든 토픽에 대해 article-writer를 **동시에(병렬로)** 호출하여 아티클을 작성하세요 (선택 개수는 사용자 자유, research_results.md에 있는 넘버링 기준으로 아티클 주제·요약·출처 URL을 전달). 토픽별로 순차 호출하지 말고, 한 번의 turn에서 선택된 토픽 수만큼 article-writer tool call을 함께 내보내세요.
6. 완성된 아티클을 순서대로 저장하세요 (01_[토픽명].md, 02_[토픽명].md, ...)
- 스터디 카페 토픽이 포함되어 있다면 마지막 번호로 study_cafe.md로 저장하세요
7. merge_newsletter를 호출하여 최종 뉴스레터를 생성하세요
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `uv run pytest tests/test_agents_wiring.py tests/test_phase1_cost_controls.py tests/test_prompts.py -v`
Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add src/agents/article_writer.py src/agents/__init__.py src/main.py tests/test_agents_wiring.py
git commit -m "feat(agents): replace tone-editor with article-writer (research + draft + tone in one call)"
```

---

### Task 3: End-to-end smoke verification

**Files:** none (verification only, no commit)

- [ ] **Step 1: Run the full test suite (excluding the pre-existing broken `src.api` tests and integration tests)**

Run: `uv run pytest tests/ -q -m "not integration" --ignore=tests/test_email_flow.py`
Expected: no failures related to `article-writer`, `tone-editor`, or `ARTICLE_WRITER_PROMPT`. (`tests/test_blog_scraping.py::TestIntegration::test_anthropic_html_returns_posts` may still fail — it's a pre-existing, unrelated live-network test.)

- [ ] **Step 2: Run a quick end-to-end generation**

Run: `uv run python run.py --quick`
Expected: console output shows a tool call to `article-writer` (not `tone-editor`), the run completes without errors, and `articles/<date>/test_article.md` is written.

- [ ] **Step 3: Confirm no leftover references**

Run: `grep -rn "tone_editor\|tone_agent\|tone-editor\|TONE_EDITOR_PROMPT" src/`
Expected: no output.
