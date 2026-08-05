# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered newsletter automation system for "Automata" (오토마타) newsletter using LangGraph deepagents. Generates weekly AI/LLM news articles in Korean, published every Wednesday.

## Commands

### Development

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
```

### Running the Newsletter Generator

```bash
# Generate newsletter for next Wednesday (default)
uv run python run.py

# Generate for a specific date
uv run python run.py --date 2026-01-22

# Preview existing articles without regenerating
uv run python run.py --preview 2026-01-15

# Merge existing articles only (no generation)
uv run python run.py --merge 2026-01-15

# Quick test mode (generates only 1 article)
uv run python run.py --quick

# Enable human-in-the-loop for topic approval
uv run python run.py --hitl

# Research X and Y, pick 2 more from candidates interactively
uv run python run.py --topics "X, Y" --count 4 --hitl

# Ignore cached research candidates and re-collect
uv run python run.py --refresh
```

### Environment Setup

Required API keys in `.env`:
- `ANTHROPIC_API_KEY` - For Claude LLM via deepagents
- `TAVILY_API_KEY` - For web search functionality

Optional LangSmith tracing:
- `LANGSMITH_TRACING=true`
- `LANGCHAIN_API_KEY`
- `LANGSMITH_PROJECT="newsletter-automation"`

## Architecture

### Multi-Agent System

Built with `deepagents` (LangGraph wrapper), consisting of:

1. **Main Orchestrator** (`src/main.py`)
   - Coordinates the entire workflow
   - Uses `create_deep_agent()` with system prompt from `config.py`
   - Manages article saving and newsletter merging

2. **Topic Researcher Subagent** (`src/agents/topic_researcher.py`)
   - Researches ONE user-named topic given in natural language (`--topics`)
   - Returns a validated `TopicResearch` object via deepagents `response_format`
   - Tools: `search_ai_news`, `fetch_article_content`

3. **Weekly Research** (`src/tools/research_collector.py`) — not an agent
   - `run_weekly_research(date)` searches 7 categories, dedupes, date-filters,
     ranks, fetches, and batch-summarizes with a cheap model
   - Writes `articles/{date}/research_results.md` and caches candidates to
     `artifacts/research/{date}/candidates.json`
   - Returns only a one-line receipt; candidates never enter the model's context

4. **Tone Editor Agent** (`src/agents/tone_editor.py`)
   - Edits articles to match Automata's tone & manner
   - Friendly Korean "해요체" style
   - Technical terms in Korean/English hybrid format
   - No tools, reasoning-only

### Workflow

The standard newsletter generation follows this sequence:

1. `run.py` computes `open_slots = --count - len(--topics)`
2. Orchestrator concurrently: `topic-researcher` per named topic + `run_weekly_research`
3. Selection tool returns resolved topic dicts (user-picked or auto)
4. `article-writer` drafts all topics in parallel (research + draft + tone in one pass)
5. Articles saved to `articles/{YYYY-MM-DD}/0X_topic.md`
6. `merge_newsletter()` produces `newsletter.md`

### Directory Structure

```
src/
├── config.py                 # Prompts, API keys, templates
├── main.py                   # Orchestrator agent and streaming loop
├── agents/
│   ├── topic_researcher.py   # Single user-named topic -> TopicResearch
│   ├── article_writer.py     # Research + draft + tone in one pass
│   └── tone_editor.py        # Style editing subagent
├── tools/
│   ├── search_tools.py       # Tavily, HackerNews, PyTorch-KR forum, GitHub search
│   ├── content_tools.py      # Article fetching, official blog RSS, GitHub trending
│   ├── research_collector.py # Weekly pipeline + run_weekly_research
│   ├── research_report.py    # Pure render/parse (stdlib only)
│   └── interrupt_tools.py    # request_topic_selection, auto_select_topics
└── utils/
    └── merge_articles.py     # Newsletter assembly utilities

artifacts/research/{DATE}/   # candidates.json, raw_search_results.json (gitignored)
articles/{YYYY-MM-DD}/       # research_results.md, 0X_topic.md, newsletter.md
```

## Important Implementation Details

### Agent Configuration

Subagents are defined as dictionaries with:
- `name`: Agent identifier
- `description`: What the agent does
- `system_prompt`: Detailed instructions (from `config.py`)
- `tools`: List of function references
- `response_format`: Optional pydantic model for structured output

Example from `src/agents/topic_researcher.py`:
```python
topic_researcher_agent = {
    "name": "topic-researcher",
    "description": "...",
    "system_prompt": TOPIC_RESEARCHER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
    "response_format": TopicResearch,
}
```

### Human-in-the-Loop

`--hitl` swaps which selection tool is registered on the orchestrator:

| Run config | Selection tool |
|---|---|
| `--hitl`, open slots > 0 | `request_topic_selection` — interrupts, user picks by number |
| no `--hitl`, open slots > 0 | `auto_select_topics` — top-N by score |
| open slots == 0 | neither; no research tools registered at all |

`request_topic_selection` loads `candidates.json`, renders the list itself, and
resolves the user's numbers to candidate dicts in Python. The orchestrator never
sees the candidate list and never maps numbers to topics.

HITL requires a checkpointer (`MemorySaver`), wired automatically.

### Newsletter Merging

The `merge_newsletter()` function:
- Reads all `.md` files from `articles/{date}/` (excluding `newsletter.md`)
- Extracts titles from each article
- Generates table of contents
- Applies header/footer templates from `config.py`
- Outputs to `articles/{date}/newsletter.md`

### Streaming Output

The main agent uses `.stream()` for real-time progress:
- `"model"` events: Agent responses and tool calls
- `"tools"` events: Tool execution results
- `"__interrupt__"` events: Human-in-the-loop pauses

Always flush stdout for immediate CLI output: `sys.stdout.flush()`

## Tone & Manner Guidelines

When editing newsletter content, follow these rules from `TONE_EDITOR_PROMPT`:

- Use friendly Korean "해요체" (polite informal)
- Address readers as "구독자님" or "여러분"
- Technical terms: Korean + English in parentheses
  - Example: "에이전트 하니스(Agent Harness)"
- Use everyday analogies for complex concepts
- Section structure: 400-600 words per article
- Emoji: Only 1 in main title, none in body
- Opening: "안녕하세요, 이번 주 수요일도 새로운 소식으로 돌아왔어요!"
- Closing: "다음 주에도 더 유익한 소식으로 찾아올게요!"

## Search Tools

### Tavily Search (`search_ai_news`)

Whitelisted domains:
- Official blogs: anthropic.com, openai.com, ai.google, blog.google
- Tech platforms: huggingface.co, arxiv.org
- News outlets: techcrunch.com, theverge.com, venturebeat.com, wired.com, arstechnica.com

Uses `search_depth="advanced"` and `topic="news"` (required for Tavily to
populate `published_date` — the default topic never returns it) for
recent, dated results.

### HackerNews Search (`search_hackernews`)

Uses Algolia HN API with `tags=story` filter.
Returns: title, URL, HN discussion URL, points, comment count, author, timestamp.

### GitHub (`search_github_repos`, `fetch_github_trending`)

Two signals under the `github_trending` category:
- `search_github_repos`: GitHub Search API, repos created in the last 14 days, sorted by stars — "just launched."
- `fetch_github_trending`: scrapes `github.com/trending?since=weekly`, keyword-filtered to AI/agent-related repos — "viral this week" (stars gained, not total; the Search API can't expose this).

No `GITHUB_TOKEN` required — unauthenticated rate limit (10 req/min) comfortably covers this project's usage.

## Package Manager: uv

This project uses `uv` (not poetry/pip). All dependency management through:
- `uv sync` - Install dependencies
- `uv add <package>` - Add new dependency
- `uv run <command>` - Run commands in virtual environment

## Model Configuration

Default model: `claude-sonnet-4-6` (via deepagents)
Override in `.env`: `MODEL_NAME=claude-sonnet-4-6`
