# SVG Diagram Skill for Article Writer

## Problem

`article-writer` (`src/agents/article_writer.py`) writes 400-600 word Korean
articles as pure prose. Some topics (an architecture change, a pipeline, a
before/after comparison) are genuinely clearer with a picture than a
paragraph — but the agent has no guidance on when a diagram earns its place
or how to produce one that isn't decorative.

Claude Code ships an `artifact-diagramming` skill for exactly this judgment
call, written for inline SVG inside HTML Artifacts (viewer theme tokens,
sandboxed page, `<figure>`/`role="img"` wrapper). Those mechanics don't
transfer directly — Automata articles are Markdown, and the newsletter is
hand-copied into Maily's editor (no HTML/inline-SVG pipeline, no light/dark
theme to inherit). The content judgment does transfer.

## Goal

Give `article-writer` the judgment and mechanics to draw a diagram *when a
topic's mechanism genuinely needs one*, save it as a standalone SVG file next
to the article, and reference it inline — via a deepagents Skill, not a new
tool or an always-loaded prompt block.

## Why a Skill, not a tool or a prompt addendum

`article-writer` already has `write_file`/`read_file`/`edit_file` — deepagents
attaches `FilesystemMiddleware` to every subagent regardless of its declared
`tools` list (`deepagents/graph.py:618-624`), so no new tool is needed to
save an `.svg` file.

Two ways to deliver the guidance:

- **Inline prompt addendum** (append to `ARTICLE_WRITER_PROMPT`): loads on
  every article-writer call, even for the majority of topics that will never
  need a diagram. `ARTICLE_WRITER_PROMPT` is already large (it embeds a full
  worked example article).
- **deepagents Skill** (`skills=[...]` on the subagent dict, loaded via
  `SkillsMiddleware`): progressive disclosure — the skill's content only
  enters context when the agent's own judgment pulls it in. This is also the
  structural shape Claude Code itself uses for `artifact-diagramming`, which
  is what was asked to be adapted.

Skill wins on both YAGNI (most articles carry zero diagram-context cost) and
fidelity to the thing being adapted.

## Design

### `skills/svg-diagrams/SKILL.md` (new)

YAML frontmatter (`name`, `description`) per the Agent Skills spec deepagents'
`SkillsMiddleware` expects (`deepagents/middleware/skills.py`), then:

- **When to draw**: mechanism-first judgment carried over from
  `artifact-diagramming` — a diagram earns its place when a cold reader would
  otherwise have to assemble a flow/boundary/comparison from prose. Depict the
  mechanism, not its name (a labeled box says less than the path a request
  takes through it). Match complexity to stakes — a one-hop relationship is a
  three-box diagram, not a system inventory. If a sentence says it faster,
  write the sentence — most articles get **no** diagram.
- **Mechanics, adapted for a standalone file** (no viewer, no theme, no HTML
  wrapper):
  - `viewBox="0 0 W H"` sized to content, not a preset.
  - Fixed light-mode color palette (white background, dark strokes/text) —
    `currentColor` has nothing to inherit from in a standalone file that gets
    copy-pasted into an email editor.
  - Arrowheads via `<marker>` or a small `<polygon>`, never an image.
  - Label the arrows (`writes`, `invalidates`, `호출` — not bare lines).
  - Legible text (~11-13px at drawn scale), grid-aligned shapes.
  - No `<script>`, `<style>`, `<foreignObject>` — self-contained SVG only.
- **Save + reference**: `write_file` the SVG to
  `articles/{date}/0X_topic_diagram.svg` (same numeric prefix as the article
  it belongs to), then embed it in the article body as
  `![설명](0X_topic_diagram.svg)` with a one-line Korean caption underneath
  (replaces the HTML `<figure>`/`<figcaption>` wrapper, which has no Markdown
  equivalent).

### `src/agents/article_writer.py`

```python
article_writer_agent = {
    "name": "article-writer",
    "description": "...",
    "system_prompt": ARTICLE_WRITER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
    "skills": ["skills/svg-diagrams"],
}
```

One new key. No new tool, no prompt changes.

## Data Flow

1. `article-writer` drafts the topic as usual.
2. If (and only if) the topic's mechanism genuinely benefits from a picture,
   the skill's guidance pulls into context, the agent hand-writes SVG markup,
   and calls `write_file` to save `articles/{date}/0X_topic_diagram.svg`.
3. The agent embeds the image reference + caption in the article body it
   returns.
4. `save_article` writes the returned article text; the `.svg` file is
   already on disk from step 2.
5. `merge_newsletter` globs `*.md` only (`get_article_files` in
   `src/utils/merge_articles.py`) — the `.svg` is untouched, sitting as a
   sibling asset in `articles/{date}/`.
6. Delivery is manual and unchanged: the user copy-pastes `newsletter.md`
   into Maily and separately re-uploads any `.svg` files as image assets —
   same as they'd handle any other image today. This spec does not touch
   delivery/publishing, which lives entirely outside this repo.

## Error Handling

No new failure modes: no new tool, no new dependency, no new API call. Worst
case is a malformed or unhelpful SVG, caught the same way a bad prose
paragraph would be — human review before publishing. If malformed SVGs turn
out to be a real recurring problem, a validating `save_diagram()` tool is the
next escalation (rejected here as premature).

## Testing

- One small test alongside `test_agents_wiring.py`'s existing pattern:
  assert `article_writer_agent["skills"]` is present and points at a
  `skills/svg-diagrams/SKILL.md` that actually exists on disk.
- Manual verification: `uv run python run.py --quick` on a topic likely to
  trigger a diagram (e.g. an architecture/pipeline-shaped topic) and confirm
  an `.svg` file appears in the article directory and is referenced in the
  article body.

## Out of Scope

- Maily/email delivery automation — no delivery pipeline exists in this repo
  today; not introduced here.
- A validating `save_diagram()` tool (see Error Handling).
- Diagram support for `topic-researcher` or the orchestrator — the user's ask
  was specifically "article writing subagents," and `article-writer` is the
  only one that produces article prose.
