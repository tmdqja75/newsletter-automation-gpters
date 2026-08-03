# Research Process Cleanup — Design

**Date:** 2026-08-03
**Status:** Approved for planning
**Scope:** The research and research-summary phase of newsletter generation, plus the HITL topic-selection loop it feeds.

## Problem

`collect_weekly_research()` produces ranked, structured candidates — `title, url, source, published_at, summary, key_facts, why_it_matters, topic_type, category, score` — and persists them to `artifacts/research/{date}/candidates.json`. That data is deterministic.

It then passes through four LLM re-transcriptions before reaching the user:

| # | Where | What happens |
|---|---|---|
| 1 | `research-agent` | rewrites the JSON as free-text numbered Korean markdown, format enforced only by prompt |
| 2 | orchestrator | copies that text into `research_results.md` |
| 3 | orchestrator | copies it again into `request_topic_selection(topic_candidates=…)` |
| 4 | orchestrator | maps `"선택된 토픽 번호: 1,3,5"` back to titles and URLs from memory |

The list the user selects from is the third rewrite. Nothing guarantees item 3 in `research_results.md` is item 3 in the interrupt payload, and nothing verifies the URL handed to `article-writer` survived intact. This is the nondeterminism in the HITL loop.

### Defects found during assessment

- **`topic-selector` is dead code.** `src/main.py:23` imports `topic_selection_agent`; `src/main.py:220` passes `subagents=[research_subagent, article_writer_agent]`. It is never registered. Consequences: `TOPIC_SELECTOR_PROMPT` (39 lines) is unreachable; `ORCHESTRATOR_PROMPT` instructs the model to use a "토픽 선택 에이전트" that does not exist; the reject path at `src/main.py:328` tells it to "call topic-selector only" — undefined behavior; `CLAUDE.md:143` documents an `interrupt_on: {"topic-selector": …}` config absent from the code.
- **Interrupt handling is hand-nested three levels deep** (`src/main.py:276–392`, ~180 lines of near-duplicate event printing) and supports exactly two reject rounds. A third reject dead-ends.
- **`response_format` is unused.** deepagents 0.6.8 is installed; structured subagent output has been available since 0.5.3.
- **Two contradictory orchestrator prompts.** `config.ORCHESTRATOR_PROMPT` (3 main + 1 study café, chosen by an agent) versus the inline HITL prompt at `src/main.py:197–212` (user picks freely, any count).
- **`run_quick_test` duplicates ~90 lines** of `run_newsletter_generation`'s stream handling.
- **Context bloat.** `_normalize_candidates` sets `prefetched_content = summary` for PyTorch-KR candidates (`research_collector.py:181`) and nothing removes it. Full forum post text ships twice in both `candidates.json` and the JSON handed to the model.

## Goals

1. The candidate list the user approves is byte-identical to the one written to disk and to the one resolved into topics.
2. Numbers map to topics in Python, never in model memory.
3. Support mixed requests: `--topics "X,Y" --count 4` means two user-named topics plus two chosen from candidates.
4. User-named topics and collector candidates are the same shape downstream — no branching in the writer.
5. Delete dead code and collapse duplicated control flow.

## Non-goals

- Changing the collector pipeline itself (search, dedupe, date filter, ranking, fetch, summarize). It works and is well tested (476 lines of tests). Untouched except for the `prefetched_content` cleanup.
- Changing `article-writer`'s prompt, tone rules, or fact-citation rules.
- Changing `merge_newsletter` or the newsletter templates.

## Architecture

The orchestrator owns sequencing. It overlaps user-topic research with weekly collection, then interrupts for selection.

```
run.py --hitl --topics "Claude Agent SDK 2.0, 국내 AI 규제" --count 4
  │  open_slots = 4 - 2 = 2      ← computed in run.py, stated in the prompt
  ▼
orchestrator (MemorySaver checkpointer)

  turn 1 ── three tool calls emitted together; ToolNode runs them concurrently
     ├─ topic-researcher("Claude Agent SDK 2.0")   → TopicResearch JSON
     ├─ topic-researcher("국내 AI 규제")            → TopicResearch JSON
     └─ run_weekly_research("2026-08-05")
          └─ collect_weekly_research() → render → writes research_results.md
             returns only: "후보 20개 수집 완료. articles/2026-08-05/research_results.md"

  turn 2 ── request_topic_selection(date, open_slots=2, confirmed_titles=[…])
     └─ tool body loads candidates.json, renders the list, calls interrupt()
        ⏸ CLI prints the list → input("3,7") → validated locally → resume
        └─ tool parses "3,7" in Python → returns two resolved topic dicts as JSON

  turn 3 ── article-writer ×4 in parallel → save_article → merge_newsletter
```

Non-HITL replaces `request_topic_selection` with `auto_select_topics`, which returns the same JSON shape.

### Why determinism survives an in-run interrupt

1. **The orchestrator never sees the candidate list.** `run_weekly_research` returns a one-line receipt. The 20 candidates go to disk and to the user, never into the model's context. Nothing to paraphrase, and the candidate payload — 20 entries carrying up to 1500 characters of fetched content each — leaves every subsequent turn.
2. **The interrupt payload is rendered from disk.** `interrupt()` is called *inside* the tool body, after it has loaded `candidates.json`. deepagents' native `interrupt_on` was rejected for this reason: it fires *before* the tool body runs, so its payload can only carry model-authored arguments.
3. **Number→topic resolution is Python.** `parse_selection` indexes into the same list `render_selection_list` enumerated. Item 3 on screen is item 3 returned, with its exact URL.

### Mode is encoded in tool registration

`create_newsletter_agent` builds its tool list from the run config, so the model cannot take a path that does not apply:

| Run config | Tools registered |
|---|---|
| `--hitl`, `open_slots > 0` | `run_weekly_research`, `request_topic_selection`, `save_article`, `merge_newsletter` |
| no `--hitl`, `open_slots > 0` | `run_weekly_research`, `auto_select_topics`, `save_article`, `merge_newsletter` |
| `open_slots == 0` | `save_article`, `merge_newsletter` only |

Exactly one selection tool always exists, so the orchestrator prompt describes a single flow and "should I ask the user?" stops being a model decision. The third row means a fully-specified run cannot reach Tavily — the tools are absent.

## Components

| Module | Job | Deps | Change |
|---|---|---|---|
| `src/tools/research_collector.py` | search → normalize → dedupe → filter → rank → fetch → summarize → persist | network, haiku | + `run_weekly_research()` wrapper; `prefetched_content` pop |
| `src/tools/research_report.py` | candidate dicts → text; text → candidate dicts | **stdlib only** | new, ~110 lines |
| `src/tools/interrupt_tools.py` | selection tools | report | revamped |
| `src/agents/topic_researcher.py` | one NL topic → validated object | search tools | new |
| `src/agents/research.py` | — | — | **deleted** |
| `src/agents/topic_selector.py` | — | — | **deleted** |
| `src/main.py` | build agent, stream it, handle interrupts | deepagents | 507 → ~300 lines |

Dependency direction is acyclic, with the network-touching layer as a leaf:

```
run.py ──► main ──► agents.{topic_researcher, article_writer}
             └────► tools.{research_collector, interrupt_tools}
                          └──────────► tools.research_report   (stdlib only)
```

### `src/tools/research_report.py`

Pure: no I/O, no network, no model. Testable with zero mocks.

```python
def render_research_results(result: dict) -> str           # → research_results.md
def render_selection_list(candidates: list[dict]) -> str   # → terminal / interrupt payload
def parse_selection(text: str, candidates: list[dict], expected: int) -> list[dict]
def auto_select(candidates: list[dict], n: int) -> list[dict]
```

`load_candidates(publication_date) -> list[dict]`, the read counterpart of `_persist_artifacts`, lives in `research_collector.py` instead — this module stays free of filesystem access so its tests need no `tmp_path`.

`render_research_results` and `render_selection_list` both iterate `enumerate(candidates, 1)` over the same list object; `parse_selection` indexes back into it. Numbering agreement is structural, not conventional.

`parse_selection` raises `ValueError` with a Korean message on out-of-range indices, wrong selection count, or empty input. It tolerates `"3, 7"`, `"3번,7번"`, and full-width commas.

`auto_select` takes the top `n` by score, reserving one `topic_type == "study_cafe"` slot when any candidate has it.

Field-to-output mapping, replacing what `RESEARCH_AGENT_PROMPT` (`config.py:89–101`) asked the model to transcribe:

| Report field | Source |
|---|---|
| 제목 | `c["title"]` |
| 요약 | `c["summary"]` + `key_facts` + `why_it_matters` |
| 출처 URL / 원문 URL | `c["url"]`, `c["original_url"]` when they differ |
| 발표/게시 날짜 | `c["published_at"]` or `"날짜 미상"` |
| 중요도 | `_importance(c)` |
| 카테고리 | `CATEGORY_LABELS_KO` lookup |

Only 중요도 was a judgment call, and the prompt's own rule — *"category가 real_world_usecases이거나 why_it_matters가 강한 후보는 높음"* — is already encoded in the score formula at `research_collector.py:188–191` (`real_world_usecases +0.3`, HN >50 points `+0.2`, missing date `−0.5`). A threshold on that score applies the stated rule more faithfully than re-asking a model to eyeball it.

Prose (`summary`, `key_facts`, `why_it_matters`) is still model-written, but by the existing single batched haiku call inside `_summarize_candidates` (`research_collector.py:328`), URL-keyed with a snippet fallback. The renderer writes no prose.

### `run_weekly_research(publication_date) -> str`

Orchestrator tool. Calls `collect_weekly_research()`, renders, writes `articles/{date}/research_results.md`, returns a receipt naming the candidate count and file path — **never the candidate JSON**.

`candidates.json` stays at `artifacts/research/{date}/candidates.json` (asserted by `test_research_collector.py:363`; `artifacts/` is gitignored). Within a run the dict returned by `collect_weekly_research()` is the source of truth, because `_persist_artifacts` is deliberately best-effort and catches `OSError` (`:415`, `:427`). Across runs the file is a reuse cache: `run_weekly_research` reads it when present and skips ~13 searches, 8 fetches, and a haiku call. `--refresh` forces re-collection.

This replaces the prompt hack at `src/main.py:202` — *"if research_results.md already exists, don't research"* — which asked the model to decide whether to spend money on Tavily.

### `src/tools/interrupt_tools.py`

```python
def request_topic_selection(publication_date: str, open_slots: int,
                            confirmed_titles: list[str]) -> str:
    """리서치 후보 중 사용자가 직접 토픽을 고르게 합니다. 리서치 완료 후에 호출하세요."""
    candidates = load_candidates(publication_date)
    if not candidates:
        return "오류: 후보가 없습니다. run_weekly_research를 먼저 호출하세요."

    selection = interrupt({
        "type": "topic_selection",
        "topics": render_selection_list(candidates),
        "confirmed": confirmed_titles,
        "open_slots": open_slots,
    })
    return json.dumps(parse_selection(selection, candidates, open_slots),
                      ensure_ascii=False)


def auto_select_topics(publication_date: str, open_slots: int) -> str:
    """비대화형 모드에서 상위 후보를 자동 선택합니다."""
```

The empty-candidates guard also enforces ordering: a selection requested in the same turn as the research gets an error string telling the model to research first, instead of interrupting against an empty list.

`confirmed_titles` is display-only context for the user ("확정된 토픽: X, Y — 나머지 2개를 골라주세요") and carries no downstream effect.

### `src/agents/topic_researcher.py`

```python
class TopicResearch(BaseModel):
    """One user-specified topic, researched."""
    title: str               = Field(description="정확한 한국어 제목")
    url: str                 = Field(description="1차 출처 URL")
    original_url: str | None = None
    published_at: str | None = Field(default=None, description="YYYY-MM-DD")
    summary: str             = Field(description="2-3문장 한국어 요약")
    key_facts: list[str]     = Field(default_factory=list, description="확인된 사실, 최대 5개")
    why_it_matters: str      = ""
    topic_type: Literal["main", "study_cafe"] = "main"

topic_researcher_agent = {
    "name": "topic-researcher",
    "description": "사용자가 자연어로 지정한 단일 토픽을 리서치해 구조화된 결과를 반환합니다.",
    "system_prompt": TOPIC_RESEARCHER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
    "response_format": TopicResearch,
}
```

The field list is deliberately identical to a collector candidate, so a researched topic and a picked candidate are the same shape. `render_topics_for_prompt` and `article-writer` stay single-path.

`TOPIC_RESEARCHER_PROMPT` is roughly 15 lines against `RESEARCH_AGENT_PROMPT`'s 38: given one topic in natural language, search, fetch one to three primary sources, fill the schema from fetched content only, prefer official and primary sources over aggregators, leave a field empty rather than guess. It no longer describes `collect_weekly_research`'s return fields — the schema does that.

### `src/main.py`

The nested interrupt handling flattens to one loop:

```python
def _run_with_interrupts(agent, initial, config, metrics):
    stream_input, final = initial, None
    while True:
        pending = None
        for event in agent.stream(stream_input, config=config):
            metrics.record_stream_event(event)
            final, pending = _handle_event(event, metrics, final, pending)
        if pending is None:
            return final
        stream_input = Command(resume=_prompt_user(pending))
```

~30 lines replacing `src/main.py:276–392`. Reject and re-pick become unbounded rather than capped at two rounds. `_handle_event` is shared with `run_quick_test`, deleting its ~90 duplicated lines.

`ORCHESTRATOR_PROMPT` loses its research, search-query, and topic-selection sections — that work is now in Python — and the inline HITL prompt at `src/main.py:197–212` is deleted. One prompt describes one flow: research the named topics and the week concurrently, get topics from the selection tool, fan out `article-writer` in parallel, save `0N_slug.md` in order with study-café last, merge.

### `run.py`

Two new flags, one changed meaning:

| Flag | Status | Behavior |
|---|---|---|
| `--count N` | **new** | Total articles for the issue. Default 4, preserving today's 3 main + 1 study café. |
| `--refresh` | **new** | Ignore cached `candidates.json` and re-collect. |
| `--topics "X,Y"` | unchanged flag, new path | Titles are researched by `topic-researcher` instead of being appended to the prompt as free text (`src/main.py:260–266`). |
| `--hitl` | unchanged | Now selects which selection tool is registered rather than swapping in a second prompt. |

`run.py` computes `open_slots = count - len(topics)` and errors before starting the agent if it is negative. The value is stated in the initial prompt and passed to the selection tool.

## Data contract

The single shape crossing every boundary:

```python
{
  "title": str,
  "url": str | None,           # None for an unresearchable --topics entry
  "original_url": str | None,  # PyTorch-KR: verify facts against this
  "published_at": str | None,
  "summary": str,              # "" when sources are unavailable
  "key_facts": list[str],
  "why_it_matters": str,
  "topic_type": "main" | "study_cafe",
}
```

Produced by `collect_weekly_research` (candidates) and `topic-researcher` (`TopicResearch`). Consumed by `render_*`, `parse_selection`, and `article-writer`.

When `topic-researcher` cannot source a topic, the orchestrator passes the bare title to `article-writer` with no sources, which is the branch `ARTICLE_WRITER_PROMPT` already handles (`config.py:154`) — it researches the topic inline. No separate rendering path is needed for sourceless topics.

## Error handling

| Failure | Behavior |
|---|---|
| Some searches fail | Already caught per-query (`research_collector.py:114`); errors now surface in the `research_results.md` error block instead of being swallowed into JSON the model may skip |
| Collector returns 0 candidates | Receipt says so; `request_topic_selection` guard returns an error string. Prompt: report and stop, never invent topics. Backstop: `run.py` verifies expected article files exist and exits non-zero |
| Summarizer returns bad JSON | Existing snippet fallback (`research_collector.py:397`), unchanged |
| `topic-researcher` returns unusable output | Prompt rule: pass the bare title to `article-writer` with sources empty, which researches it inline. Model-mediated, so the softest guarantee in this design |
| Invalid selection input | Validated in the CLI before resuming; re-prompts locally until valid, so LangGraph never sees a bad resume. The tool keeps a defensive re-parse returning an error string |
| User rejects / re-picks | CLI resumes with a reject message; orchestrator calls the tool again. Unbounded rounds, and re-picking costs zero research since `candidates.json` is cached |
| `--count` < `--topics` count | `run.py` errors before the agent starts |
| `artifacts/` write fails | Run continues on the in-memory result; only cross-run reuse is lost |

## Testing

**Pure, zero mocks** (`research_report.py`):
- `render_research_results`: N candidates → `## 1.`…`## N.`; every `url` present; error block present iff `errors`
- `render_selection_list`: numbering agrees with `render_research_results` on the same input — the regression test for the drift bug
- `parse_selection`: `"3,7"` → correct dicts; tolerates `"3, 7"`, `"3번,7번"`, full-width commas; out-of-range, wrong-count, and empty each raise `ValueError`
- `auto_select`: top-n by score; reserves a study-café slot when one exists; survives `n > len(candidates)`
- `_importance`: threshold boundaries

**One-boundary monkeypatch** (tools):
- `run_weekly_research`: writes the file; receipt carries count and path; **asserts the receipt does not contain candidate JSON** — regression guard against context bloat returning
- `request_topic_selection`: fake `interrupt` → resolved JSON; empty candidates → guard string; bad selection → error string
- `auto_select_topics`: same return shape as its HITL counterpart

**Wiring** (extend `test_agents_wiring.py`):
- `subagents == [topic-researcher, article-writer]`; `research-agent` and `topic-selector` absent
- `topic_researcher_agent["response_format"] is TopicResearch`
- the three tool-registration rows
- checkpointer present iff `--hitl`

**Loop**: a fake agent yielding a scripted event sequence with **three** interrupts, asserting all three are handled and the loop terminates. No network. This is the test that would have caught the two-round cap at `src/main.py:374`.

**Collector**: one new assertion that `prefetched_content` is absent from returned candidates. The existing 476 lines stay untouched.

**Retargeted**: `test_prompts.py` drops `TOPIC_SELECTOR_PROMPT` assertions for `TOPIC_RESEARCHER_PROMPT` ones; `test_research_collector.py:472` `test_research_subagent_tools_wiring` moves to the new agent.

No new tests hit live APIs; the existing `integration` marker convention holds.

## Documentation

`CLAUDE.md` documents `research-agent`, `topic-selector`, and an `interrupt_on: {"topic-selector": …}` config that was never in the code (`CLAUDE.md:143`). All three are corrected, along with the workflow and directory sections. README's architecture section follows.

## Accepted tradeoffs

- **One transcription hop remains.** `topic-researcher`'s JSON arrives as a `ToolMessage` and the orchestrator copies those fields into the `article-writer` call. Structured-to-structured with a schema on the producing end, far more robust than the current free-text chain, but not zero. If it proves flaky, the fix is to have `topic-researcher` write `articles/{date}/topics/NN.json` and return a receipt — the same trick `run_weekly_research` uses. Not built until observed to fail.
- **Turn-1 concurrency is prompt-dependent.** ToolNode runs a turn's tool calls concurrently, but the orchestrator must emit them together. The existing prompt already relies on this for parallel `article-writer` calls. Correctness does not depend on it; only latency does.
- **The checkpointer stays.** In-run selection requires `MemorySaver` and a `thread_id`. A pre-agent selection design would have removed both, but it cannot overlap user-topic research with weekly collection.
- **The repo drops to two live subagents** (`topic-researcher`, `article-writer`) from three declared. `topic-selector` was already dead, so this reflects reality rather than reducing it.

## Net effect

Roughly 600 lines deleted, 250 added. Four LLM transcription hops reduced to one, structured-to-structured. Dead `topic-selector` removed, two contradictory orchestrator prompts merged into one, interrupt retries unbounded, and the candidate list out of the model's context entirely.
