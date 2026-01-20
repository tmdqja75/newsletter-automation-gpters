# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered newsletter automation system for "Automata" (오토마타) newsletter using LangGraph deepagents. This project consists of three main components:

1. **CLI Newsletter Generator** (`src/`) - Automated AI/LLM news article generation in Korean, published every Wednesday
2. **Web Application** (`web/`) - Next.js 16 frontend for personalized research newsletter service (in development)
3. **API Backend** (`api/`) - FastAPI backend for web service integration (placeholder)

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
```

### Web Application (Next.js)

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Run development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Start production server
npm run start

# Lint code
npm run lint

# Format code with Prettier
npm run format

# Check formatting
npm run format:check
```

### API Backend (FastAPI)

```bash
# Install FastAPI dependencies
uv pip install -r api/requirements.txt

# Run development server (http://localhost:8000)
cd api
uv run uvicorn main:app --reload --port 8000

# Test health endpoint
curl http://localhost:8000/api/health
```

### Environment Setup

#### CLI Newsletter Generator

Required API keys in `.env`:
- `ANTHROPIC_API_KEY` - For Claude LLM via deepagents
- `TAVILY_API_KEY` - For web search functionality

Optional LangSmith tracing:
- `LANGSMITH_TRACING=true`
- `LANGCHAIN_API_KEY`
- `LANGSMITH_PROJECT="newsletter-automation"`

#### Web Application

Required environment variables in `web/.env.local`:
- `NEXT_PUBLIC_SUPABASE_URL` - Supabase project URL (client-side)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase anonymous key (client-side)
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key (server-side)
- `RESEND_API_KEY` - Resend email service API key
- `API_SECRET_KEY` - Internal API authentication secret

Create from template:
```bash
cp web/.env.example web/.env.local
# Edit web/.env.local with actual API keys
```

Environment variables are validated at runtime using Zod schema in `web/lib/env.ts`.

## Architecture

### Monorepo Structure

The project uses a monorepo structure with three independent components:

```
newsletter-automation-gpters/
├── src/              # Python CLI newsletter generator (existing)
├── web/              # Next.js frontend (new)
├── api/              # FastAPI backend (placeholder)
├── .github/workflows/  # CI/CD pipelines
│   ├── ci-web.yml      # Next.js CI (lint, type-check, build)
│   └── ci-python.yml   # Python CI (uv, pytest)
└── vercel.json       # Vercel deployment config
```

### Multi-Agent System

Built with `deepagents` (LangGraph wrapper), consisting of:

1. **Main Orchestrator** (`src/main.py`)
   - Coordinates the entire workflow
   - Uses `create_deep_agent()` with system prompt from `config.py`
   - Manages article saving and newsletter merging

2. **Research Subagent** (`src/agents/research.py`)
   - Searches AI/LLM news via Tavily API
   - Monitors HackerNews for trending discussions
   - Fetches article content for analysis
   - Tools: `search_ai_news`, `search_hackernews`, `fetch_article_content`

3. **Topic Selection Agent** (`src/agents/topic_selector.py`)
   - Selects 3 main topics + 1 study café topic
   - Supports Human-in-the-Loop approval via `interrupt_on` config
   - Pure reasoning agent (no tools)

4. **Tone Editor Agent** (`src/agents/tone_editor.py`)
   - Edits articles to match Automata's tone & manner
   - Friendly Korean "해요체" style
   - Technical terms in Korean/English hybrid format
   - No tools, reasoning-only

### Workflow

The standard newsletter generation follows this sequence:

1. Research Agent collects latest AI/LLM news
2. Topic Selector chooses 4 topics (3 main + 1 study café)
3. Main agent drafts 400-600 word articles for each topic
4. Tone Editor refines each article to Automata style
5. Articles saved to `articles/{YYYY-MM-DD}/0X_topic.md`
6. `merge_newsletter()` combines articles into final `newsletter.md`

### Directory Structure

```
# CLI Newsletter Generator
src/
├── config.py              # System prompts, API keys, templates
├── main.py                # Orchestrator agent and workflow
├── agents/
│   ├── research.py        # News gathering subagent
│   ├── topic_selector.py  # Topic curation subagent
│   └── tone_editor.py     # Style editing subagent
├── tools/
│   ├── search_tools.py    # Tavily & HackerNews search
│   └── content_tools.py   # Article content fetching
└── utils/
    └── merge_articles.py  # Newsletter assembly utilities

articles/{YYYY-MM-DD}/     # Generated articles by date
├── 01_topic1.md
├── 02_topic2.md
├── 03_topic3.md
├── 04_study_cafe.md
└── newsletter.md          # Final merged newsletter

# Web Application (Next.js)
web/
├── app/                   # Next.js App Router
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   └── globals.css        # Global styles
├── lib/                   # Utilities
│   └── env.ts             # Environment validation
├── .prettierrc            # Prettier config
├── eslint.config.mjs      # ESLint config
├── env.d.ts               # TypeScript env types
├── next.config.ts         # Next.js config
├── tailwind.config.ts     # Tailwind config
└── tsconfig.json          # TypeScript config

# API Backend (FastAPI)
api/
├── main.py                # FastAPI application
└── requirements.txt       # Python dependencies
```

## Important Implementation Details

### Agent Configuration

Subagents are defined as dictionaries with:
- `name`: Agent identifier (used in `interrupt_on`)
- `description`: What the agent does
- `system_prompt`: Detailed instructions (from `config.py`)
- `tools`: List of function references

Example from `src/agents/research.py`:
```python
research_subagent = {
    "name": "research-agent",
    "description": "...",
    "system_prompt": RESEARCH_AGENT_PROMPT,
    "tools": [search_ai_news, search_hackernews, fetch_article_content],
}
```

### Human-in-the-Loop

Enable topic approval by passing `use_hitl=True` to `create_newsletter_agent()`:

```python
agent_config["interrupt_on"] = {
    "topic-selector": {
        "allowed_decisions": ["approve", "edit", "reject"]
    }
}
```

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

Uses `search_depth="advanced"` for comprehensive results.

### HackerNews Search (`search_hackernews`)

Uses Algolia HN API with `tags=story` filter.
Returns: title, URL, HN discussion URL, points, comment count, author, timestamp.

## Web Application Details

### Technology Stack

- **Framework**: Next.js 16 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Linting**: ESLint with Next.js and TypeScript rules
- **Formatting**: Prettier with Tailwind CSS plugin
- **Database**: Supabase (PostgreSQL)
- **Email**: Resend
- **State Management**: React hooks (no external state library yet)
- **Validation**: Zod

### Code Style

The web application follows these conventions:

1. **TypeScript**: Strict mode enabled
   - All environment variables must be typed in `env.d.ts`
   - Runtime validation via Zod in `lib/env.ts`

2. **Formatting**: Prettier with single quotes
   - Automatically sorts Tailwind classes
   - 2-space indentation
   - Semicolons required

3. **ESLint Rules**:
   - `@typescript-eslint/no-unused-vars`: error
   - `@typescript-eslint/no-explicit-any`: warn

4. **Component Structure**:
   - Use Server Components by default
   - Add `'use client'` only when needed (hooks, event handlers)
   - Prefer composition over prop drilling

### API Routes

Next.js API routes follow this pattern:
```typescript
// app/api/[endpoint]/route.ts
export async function GET(request: Request) {
  // Handler logic
}
```

## CI/CD

### GitHub Actions Workflows

Two independent CI pipelines run on push/PR to main and dev branches:

#### Web CI (`.github/workflows/ci-web.yml`)
Triggers on changes to `web/**`:
1. Install Node.js 20 and dependencies
2. Run ESLint
3. Run Prettier check
4. TypeScript type checking (`tsc --noEmit`)
5. Build Next.js application

#### Python CI (`.github/workflows/ci-python.yml`)
Triggers on changes to `api/**`, `src/**`, or Python config files:
1. Install uv package manager
2. Set up Python 3.11
3. Install dependencies with `uv sync`
4. Run pytest (continues on error)

### Deployment

The application is configured for Vercel deployment:
- `vercel.json` defines build and routing configuration
- Next.js app in `web/` directory
- FastAPI routes under `/api/*` path
- Both frontend and backend deploy together

## Package Managers

### Python: uv

This project uses `uv` (not poetry/pip). All dependency management through:
- `uv sync` - Install dependencies
- `uv add <package>` - Add new dependency
- `uv run <command>` - Run commands in virtual environment

### JavaScript: npm

The web application uses npm (package-lock.json committed):
- `npm install` - Install dependencies
- `npm run dev` - Start development server
- `npm run build` - Build for production

## Model Configuration

Default model: `claude-sonnet-4-5-20250929` (via deepagents)
Override in `.env`: `MODEL_NAME=claude-sonnet-4-5-20250929`
