# Design: Hallucination Reduction & Real-World Use Case Discovery

**Date:** 2026-03-18
**Problems addressed:**
1. Articles contain hallucinated facts (invented numbers, dates, feature names not from source material)
2. Topic selection produces generic/uninteresting topics — model releases and framework updates rather than novel real-world use cases

---

## Problem 1: Hallucination / Fact Accuracy

### Root Causes
- The research agent collects search snippets (short excerpts), but the orchestrator writes full articles that extrapolate beyond what the snippets contain — inventing specific numbers, dates, and feature names
- `fetch_article_content` exists but is not required to be used before writing
- Prompt does not constrain the writer to only state facts present in source material

### Solution: Mandatory Fetch + Citation Enforcement

**No new files, no new tools, no new subagents.** Three prompt changes only:

#### 1. `RESEARCH_AGENT_PROMPT` — mandatory fetch step
After identifying candidate articles via `search_ai_news` or `search_hackernews`, the research agent **must** call `fetch_article_content` for every article it plans to recommend as a topic. The research output must include the fetched full content alongside the snippet, not just search snippets alone.

#### 2. `ORCHESTRATOR_PROMPT` — citation-constrained writing
Add a hard constraint section to the article writing instructions:
- Every factual claim (numbers, dates, model names, benchmark scores, company details) must come directly from the fetched source content provided by the research agent
- No synthesizing facts across multiple sources — use one primary source per claim
- Every factual claim must include an inline source URL citation, e.g.: `(출처: https://...)`
- If a fact cannot be traced to a fetched source, do not include it

#### 3. `TONE_EDITOR_PROMPT` — preserve citations
Add one line: do not remove or alter inline source citations when editing for style.

---

## Problem 2: Boring Topic Selection — Find Novel Real-World Use Cases

### Root Cause
- Research categories target generic news (model releases, framework updates, research papers)
- HackerNews queries are not targeted at `Show HN` / "I built this" type posts
- Topic selector has no preference signal for compelling real-world use stories

### Solution: New Research Category + Query Guidance + Topic Selector Weighting

**No new files, no new tools, no new subagents.** Two prompt changes:

#### 1. `RESEARCH_AGENT_PROMPT` — new "Real-World AI Deployment" category
Add a dedicated category **#8: 실제 AI 에이전트/LLM 활용 사례** with:
- Targeted HackerNews queries:
  - `"Show HN" AI agent`
  - `"Show HN" LLM`
  - `"I built" AI agent`
  - `"using Claude" OR "using ChatGPT" production`
- Targeted Tavily queries:
  - `"AI agent" "deployed" OR "in production" real world results`
  - `LLM automation case study 2026`
- What to look for:
  - Individual or company stories deploying AI agents to solve concrete problems
  - Before/after impact metrics (time saved, cost reduced, outcomes improved)
  - Surprising cross-industry use (healthcare, legal, construction, agriculture, personal projects)
  - Small teams or individuals doing something previously impossible without AI

#### 2. `TOPIC_SELECTOR_PROMPT` — prioritize use-case stories
Add explicit weighting: a compelling real-world use case story should be ranked higher than a generic model release or framework update, unless the release is exceptionally significant (e.g., GPT-5, Claude 4). The selection criteria should favor stories that a non-technical reader would find surprising or inspiring.

---

## What Does NOT Change
- Agent architecture (no new subagents)
- Tool implementations (no new tools)
- Newsletter structure (4 articles, same format)
- HITL flow
- `merge_newsletter` or `save_article` utilities

## Success Criteria
1. Every published article has at least one inline source citation per factual claim
2. At least one of the 3 main topics per newsletter is a real-world deployment story (not a model release or paper summary)
3. HackerNews `Show HN` type posts appear regularly in topic candidates
