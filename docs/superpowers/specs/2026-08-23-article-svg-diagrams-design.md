# Article SVG Diagrams Design

## Problem

Articles are text-only. Some topics (architecture changes, pipeline
comparisons, "before vs after" stories) are easier to grasp with a diagram
than with prose alone, and `article-writer` has no way to produce one. There's
also no way to review or correct a generated diagram — the pipeline's only
feedback mechanism today is text-in/text-out (`_run_feedback_loop` in
`src/main.py`, resumes the agent thread with a text message).

## Goal

Give `article-writer` a tool that can produce an SVG diagram for a topic when
the topic actually benefits from one, save it alongside the article, and let
the existing feedback loop drive corrections (arrow direction, wrong label,
colors, etc.) without regenerating the diagram from scratch or touching the
article text.

## Approach

Two options considered:

1. **Embed diagram generation in `ARTICLE_WRITER_PROMPT` directly** — no new
   tool, article-writer reasons its way to SVG markup inline. Rejected:
   `ARTICLE_WRITER_PROMPT` already carries research + fact rules + tone/style
   rules; adding SVG layout/style rules on top dilutes prose quality and drags
   diagram instructions into every text-only edit round.
2. **Separate focused prompt, invoked as a tool call, not a `deepagents`
   subagent** — chosen. `main.py`'s `subagents` list is flat (registered only
   on the top-level orchestrator), so a true nested subagent under
   `article-writer` doesn't fit the current wiring. A plain tool function that
   makes its own isolated LLM call (same pattern as
   `research_collector.py:_default_summarizer`) gets the prompt isolation of
   a subagent without restructuring the orchestrator.

## Workflow

**Creation** (per topic, inside `article-writer`'s single pass):
1. `article-writer` drafts the article text.
2. It judges whether the topic's core idea hinges on a mechanism or
   comparison worth drawing (prompt-level gate, cheap — avoids calling the
   tool for pure announcement topics).
3. If yes, calls `create_svg_diagram(article_text, focus, topic_slug,
   date_dir)`, where `focus` is a one-sentence description of what the
   diagram must show (e.g. "온디바이스 추론이 클라우드 호출을 건너뛰는 경로").
4. The tool makes one isolated LLM call with `SVG_DIAGRAM_PROMPT`, which
   independently judges `worth_it` as a final check (the tool has the actual
   diagram content to judge; `article-writer`'s step 2 only had the article
   text).
   - `worth_it: false` → tool returns `"다이어그램 생략: ..."`, writes nothing.
   - `worth_it: true` → tool writes `articles/{date}/{topic_slug}.svg`, opens
     it via `webbrowser.open`, and returns a ready-to-paste markdown snippet
     (`![caption](topic_slug.svg)\n\ncaption`).
5. `article-writer` splices the snippet into its returned article markdown
   (or skips silently if the tool reported no diagram).

**Revision** (feedback loop, `_run_feedback_loop` in `src/main.py`):
`ORCHESTRATOR_PROMPT`'s existing feedback section reads the saved article
file directly and edits it — it does not re-delegate to `article-writer` for
text feedback, so it needs `create_svg_diagram` on its own tool list too.
- SVG-shaped feedback ("화살표 방향 바꿔줘", "색 바꿔줘") → orchestrator calls
  `create_svg_diagram(existing_svg_path=..., feedback=...)`. The tool passes
  the existing SVG + feedback text to the LLM, which edits only what the
  feedback names and preserves the rest, then overwrites the same file path
  and reopens it in the browser.
- Text-only feedback → unchanged, orchestrator edits the `.md` directly.

## Component Changes

### `src/tools/diagram_tools.py` (new)

```python
def create_svg_diagram(
    topic_slug: str,
    date_dir: str,
    article_text: str = "",
    focus: str = "",
    existing_svg_path: str | None = None,
    feedback: str | None = None,
) -> str:
    """Generate or revise one SVG diagram for an article topic.

    Creation: pass article_text + focus.
    Revision: pass existing_svg_path + feedback (article_text/focus omitted
    — the existing markup + feedback fully determine the edit).

    Returns a markdown snippet ready to paste into the article
    ("![caption](topic_slug.svg)\\n\\ncaption"), "다이어그램 생략: ..." if the
    LLM judged it not worth drawing, or "오류: ..." on failure.
    """
```

- Follows `research_collector.py:_default_summarizer`'s pattern:
  `init_chat_model(config.to_model_spec(config.MODEL_NAME))`, plain
  prompt-and-parse-JSON (no `with_structured_output`), wrapped in
  `try/except` returning an `"오류: ..."` string on failure — matches the
  `"오류:"` convention `ORCHESTRATOR_PROMPT` already knows to report and stop
  on for that one topic (not the whole run).
- Validates the returned `svg` field parses as XML
  (`xml.etree.ElementTree.fromstring`) before writing; malformed markup is
  treated as a failure (`"오류: ..."`, nothing written).
- Writes to `Path(ARTICLES_DIR) / date_dir / f"{topic_slug}.svg"` — same
  directory convention as `save_article`. Revision overwrites the same path,
  never creates a second file.
- `webbrowser.open(f"file://{path}")` wrapped in its own `try/except` — must
  not fail the tool call in a headless/CI environment.

### `src/config.py`

Add `SVG_DIAGRAM_PROMPT` next to the other prompts:

```python
SVG_DIAGRAM_PROMPT = """당신은 '오토마타' 뉴스레터의 다이어그램 전문가입니다. ...
"""
```

(Full text: role scoped to diagram-only, no article writing; "그릴 것 정하기"
section — draw the mechanism not the label, draw the difference for
comparisons, label every arrow, match complexity to the point being made;
SVG mechanics — single `viewBox`, viewBox width capped near newsletter body
width, no `<script>`/`<style>`/`<foreignObject>`/external refs since this is
embedded via markdown image and won't inherit host-page CSS or load external
resources, hardcoded light-background hex palette instead of `currentColor`
since an image-embedded SVG doesn't inherit page theme, CJK-safe font stack
(`-apple-system, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif`) since
labels are Korean, marker/polygon arrowheads, grid-aligned layout, `<title>`
for accessibility; output JSON `{svg, caption, worth_it}`; revision mode
edits only what feedback names, preserves the rest.)

### `ARTICLE_WRITER_PROMPT` (`src/config.py`)

Add a short section: when to consider a diagram (mechanism/comparison
topics, not pure announcements), how to call `create_svg_diagram` with a
one-sentence `focus`, how to splice the returned snippet into the article
(or skip silently on `"다이어그램 생략"`/`"오류:"`).

### `ORCHESTRATOR_PROMPT` (`src/config.py`)

Feedback section gains one branch: SVG-shaped feedback → call
`create_svg_diagram` with `existing_svg_path` + `feedback`, overwrite the
`.svg`; otherwise unchanged (edit the `.md` directly).

### `src/agents/article_writer.py`

Add `create_svg_diagram` to the `tools` list.

### `src/main.py`

Add `create_svg_diagram` to the orchestrator's top-level `tools` list
(alongside `save_article`, `merge_newsletter`).

### Unchanged

`merge_articles.py` (relative image links resolve fine — `.svg` lives in the
same `articles/{date}/` directory as the `.md` it's linked from),
`research_collector.py`, `search_tools.py`, `content_tools.py`,
`interrupt_tools.py`, article/newsletter file naming conventions.

## Error Handling

- LLM/API failure inside `create_svg_diagram` → caught, returns
  `"오류: SVG 생성 실패 - {reason}"`. Callers (article-writer, orchestrator)
  treat this like any other `"오류:"` tool result: report and skip the
  diagram for that one topic, don't fail the whole run.
- Malformed SVG (fails XML parse) → same `"오류: ..."` path, nothing written.
- `worth_it: false` → not an error; `"다이어그램 생략: ..."`, no file, article
  proceeds text-only.
- `webbrowser.open` failure → swallowed, doesn't affect the tool's return
  value.

## Testing

`tests/test_diagram_tools.py`, mocking `init_chat_model`:
- `worth_it: true` → asserts `.svg` written at the expected path, returned
  snippet matches `![caption](topic_slug.svg)` format.
- `worth_it: false` → asserts no file written, return value starts with
  `"다이어그램 생략"`.
- Malformed `svg` field (fails XML parse) → asserts `"오류:"` return, no file
  written.
- Revision (`existing_svg_path` + `feedback` passed) → asserts the same file
  path is overwritten, not duplicated.
- `webbrowser.open` raising → asserts the tool still returns normally (open
  failure doesn't propagate).

No coverage for prompt wording itself (`SVG_DIAGRAM_PROMPT`,
`ARTICLE_WRITER_PROMPT` additions) — same as the article-writer design,
prompt/config plumbing isn't independently unit-testable. Verification is a
manual `--quick` run on a diagram-worthy topic, confirming a `.svg` is
produced, opens in the browser, and a feedback round ("화살표 방향 바꿔줘")
edits it in place.
