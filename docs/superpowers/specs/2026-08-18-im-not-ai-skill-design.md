# im-not-ai Skill Import — Design

**Date:** 2026-08-18
**Status:** Approved for planning
**Scope:** `src/agents/article_writer.py`, `src/main.py` (subagent wiring only), new `skills/humanize-korean/`, new `scripts/humanize/`. Does not touch the orchestrator, topic-researcher, HITL flow, or the multiturn/memory work being designed in parallel.

## Problem

The user wants the [im-not-ai](https://github.com/epoko77-ai/im-not-ai) Korean AI-tell humanizer wired into the article-writer subagent, using deepagents' [skills mechanism](https://docs.langchain.com/oss/python/deepagents/skills). im-not-ai is a mature Claude Code **plugin** (v2.3.1), not a portable skill: its orchestrator `SKILL.md` calls 3 named sub-agents via Claude Code's `Agent` tool, runs Python scripts via `Bash`, and resolves paths through Claude-Code-only env vars (`${CLAUDE_SKILL_DIR}`). None of that exists inside deepagents' runtime as-is.

Investigation (live `gh api` inspection of the repo, cross-checked against the installed `deepagents==0.4.1` source) found the port is feasible with minimal new code, because:

- The 3 runtime sub-agents (`agents/humanize-monolith.md`, `-diagnostician.md`, `-finalizer.md`) only call `Read`/`Write` internally — never `Bash`. They map 1:1 onto deepagents `SubAgent` dicts.
- deepagents' `task(subagent_type=...)` tool is the structural equivalent of Claude Code's `Agent` tool.
- The plugin's `Bash`-invoked scripts (`prepare_monolith_input.py`, `verify_gates.py`, `sanitize_text.py`, `console.py`, `checks.py`, `references/metrics_v2.py`) are 100% Python stdlib — zero external deps, verified via import inspection. Pure vendoring, no rewrite.
- deepagents' `SubAgent` TypedDict has no nested-`subagents` field (one level only), but `CompiledSubAgent` accepts a pre-built `runnable` — so article-writer itself becomes a nested `create_deep_agent(...)`, solving the "give article-writer its own private sub-agent trio" requirement without touching the orchestrator.

## Goals

1. article-writer runs a humanize pass on its own draft before returning it, using ported versions of the upstream `humanize-monolith` / `humanize-diagnostician` / `humanize-finalizer` agents and the upstream deterministic scoring/gate scripts.
2. No modification to deepagents itself — all new code lives in this repo (`src/`, vendored `skills/`, vendored `scripts/humanize/`).
3. Blast radius of the new shell-execution capability (`LocalShellBackend`) is contained to article-writer's own nested subgraph — orchestrator and topic-researcher are untouched, still plain `FilesystemBackend`.
4. The existing inline-citation rule in `ARTICLE_WRITER_PROMPT` (`(출처: https://...)` markers must survive verbatim) is preserved through the humanize pass — this is a repo-specific constraint the upstream plugin has no knowledge of, and its own "don't touch quotes/proper nouns" rules don't happen to cover it.

## Non-goals

- **Heavy path / `--strict` mode / chunking** (`reassemble_chunks.py`, multi-chunk parallel rewriting). Newsletter articles are 400-600 Korean words, far under the 5,000-char light/standard boundary and nowhere near the volume that makes chunking worthwhile upstream (their own numbers: 1 single call vs 7-chunk pipeline for a 10K-char stress test). Standard path's finalizer promotion already covers the quality ceiling this repo needs.
- **`korean-ai-tell-taxonomist`** (the taxonomy-maintenance agent) and the other 5 upstream dev-only agents — not part of the runtime pipeline, not ported.
- **Any change to `ai-tell-taxonomy.md`** (the 77KB SSOT). Runtime never reads it directly upstream either (`diagnosis-rules.md` and `quick-rules.md` are pre-generated slim indexes) — not vendored.
- **Web-service extension, CLAUDE.md/GEMINI.md/codex/ platform variants, install.sh/update.sh** — plugin-distribution machinery, irrelevant once vendored into this repo directly.

## Architecture

### article-writer becomes a nested deep agent

```
orchestrator = create_deep_agent(
    subagents=[topic_researcher_agent, article_writer_agent],   # article_writer_agent is now a CompiledSubAgent
    backend=FilesystemBackend(root_dir=".", virtual_mode=True), # unchanged
    ...
)

article_writer_agent: CompiledSubAgent = {
    "name": "article-writer",
    "description": "...",
    "runnable": create_deep_agent(
        model=_agent_model_spec(),                 # same MODEL_NAME/to_model_spec() as the rest of the repo
        system_prompt=ARTICLE_WRITER_PROMPT,        # gets a new "humanize pass" section, see below
        tools=[search_ai_news, fetch_article_content],
        subagents=[humanize_monolith_agent, humanize_diagnostician_agent, humanize_finalizer_agent],
        skills=["skills/humanize-korean/"],
        backend=LocalShellBackend(root_dir=".", virtual_mode=True),  # only this subgraph gets shell exec
    ),
}
```

Why `CompiledSubAgent` and not the current plain-dict `SubAgent`: the plain dict has no way to give article-writer its own private `task` tool and its own backend. A pre-compiled nested `create_deep_agent()` gets both for free — `task` is auto-attached whenever `subagents=[...]` is non-empty, and `backend=` is scoped to that graph only. Orchestrator and topic-researcher never see `humanize-*` as callable subagent types, and never get shell exec.

### The 3 ported sub-agents

Straight `SubAgent` dicts, system_prompt = upstream `.md` body with tool names renamed (`Read`→mention of `read_file`, `Write`→`write_file`; these agents never call `Bash`/`Glob` so no other renames needed). Model: `_agent_model_spec()` (repo default), not hardcoded `opus` — matches the rest of the repo's model config.

| Name | Role | Tool-call cap (prompt-enforced, not code-enforced) |
|---|---|---|
| `humanize-monolith` | Single-call detect+rewrite+self-grade. Used by both light and standard paths. | 3 |
| `humanize-diagnostician` | Standard-path diagnosis-only pass — "what dominates this text," not span enumeration. | 3 |
| `humanize-finalizer` | Meaning-preservation + naturalness check, local-only correction (never full rewrite). Runs on standard-path promotion (change-rate 30-50%, self-check failures) or if explicitly requested. | 4 |

**Citation-preservation fix**: each of the 3 ported prompts gets one added line to their existing "Do-NOT touch" list: *"인라인 출처 표기 `(출처: https://...)` 형식은 절대 수정·삭제하지 않는다."* This is the one substantive content edit beyond tool-name renames — everything else is copied verbatim.

### Vendored files

Root-relative, no build step:

```
scripts/humanize/
├── prepare_monolith_input.py   # metric shim + route_hint (light/standard only — --chunk flag never invoked)
├── verify_gates.py             # deterministic change-rate/structure gate
├── sanitize_text.py            # zero-width/bidi/NFC cleanup, called by the shim
├── console.py
└── checks.py

skills/humanize-korean/
├── SKILL.md                    # edited copy — see below
└── references/
    ├── metrics_v2.py
    ├── metrics.py               # fallback, per upstream shim logic
    ├── baseline.json
    ├── baseline_v2.json
    ├── quick-rules.md (+ header/footer)
    ├── diagnosis-rules.md
    └── rewriting-playbook.md
```

`skills/` is passed to `SkillsMiddleware` via the nested agent's `skills=["skills/humanize-korean/"]` — resolved by the same `FilesystemBackend(root_dir=".")` convention already used for `articles/`, so no path-prefix logic is needed at all (this sidesteps the entire `${CLAUDE_SKILL_DIR}`/`SKILL_ROOT` problem the upstream plugin has to solve for arbitrary install locations).

### SKILL.md edits (vendored copy, not upstream)

1. Drop the "Heavy 경로" section and its `--chunk` sub-steps entirely (non-goal).
2. Replace all `Agent` tool-call mentions with `task` tool-call mentions (`subagent_type=humanize-monolith` etc.).
3. Replace `Bash` mentions with `execute`.
4. Replace `Glob(pattern=...)` with `glob(pattern=...)` (deepagents' actual tool name).
5. Delete the entire `${SKILL_ROOT}` / `${CLAUDE_SKILL_DIR}` resolution section — script paths become the fixed `scripts/humanize/...py`, since install location is this repo, not an arbitrary plugin install.
6. `_workspace/{run_id}/` convention is kept as-is (upstream's own ephemeral-run-directory design, cwd-relative) — no need to reinvent this. Added to `.gitignore`.

### Where the humanize pass runs

Added section in `ARTICLE_WRITER_PROMPT` (after drafting, before returning):

> 아티클 초안 작성을 마치면, `skills/humanize-korean/SKILL.md`를 읽고 그 절차(Phase 0-2, light/standard 경로만)를 따라 방금 쓴 초안에 윤문을 적용하세요. 정밀(heavy) 모드나 `--chunk`는 사용하지 않습니다. 최종적으로 반환하는 아티클은 윤문 후 `final.md` 내용이어야 하며, 인라인 출처 표기 `(출처: ...)`는 그대로 보존되어야 합니다.

This is a deliberate, explicit instruction rather than relying on `SkillsMiddleware`'s passive description-matching trigger — article-writer is given a topic to write, not a user chat message containing a trigger phrase like "AI 티 없애줘," so the skill would never self-trigger otherwise.

Data flow: article-writer drafts per existing `ARTICLE_WRITER_PROMPT` rules → writes draft text to `_workspace/{run_id}/01_input.txt` → follows vendored `SKILL.md` (shim → route_hint → monolith, and diagnostician+monolith+maybe-finalizer for standard) → reads back `final.md` → that becomes the subagent's returned content, which the orchestrator saves via the existing `save_article` tool exactly as today. No change to how the orchestrator calls article-writer or saves output.

## Testing

No framework beyond existing `pytest` conventions (`test_agents_wiring.py` pattern):
- `article_writer_agent` is a `CompiledSubAgent` (has `"runnable"`, not `"tools"`/`"system_prompt"` directly).
- The nested runnable's backend is `LocalShellBackend`; orchestrator's own backend (built in `create_newsletter_agent`) is still plain `FilesystemBackend`.
- All vendored file paths listed above exist on disk.

Actual humanization quality is not unit-testable cheaply (LLM judgment) — out of scope for automated tests, same as the rest of this repo's LLM-authored content.

## Accepted tradeoffs / risks

- **Extra LLM calls per article**: light path adds 1 call (monolith), standard adds 2 (diagnostician + monolith), promoted standard adds 3. This increases per-article cost and latency — accepted since the user explicitly asked for this quality pass.
- **Unrestricted local shell exec** on article-writer's nested subgraph (`LocalShellBackend`) — accepted per user sign-off, scoped away from orchestrator/topic-researcher.
- **route_hint quality on Korean newsletter prose specifically** is unverified — upstream's baseline/metrics were tuned on their own corpus (칼럼/리포트/블로그/공적 genres), not newsletter tech-news paragraphs specifically. First real runs should be spot-checked.
