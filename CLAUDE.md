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

# Test newsletter generation
curl -X POST http://localhost:8000/api/newsletter/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-uuid", "topic_id": "topic-uuid"}'

# Check generation status
curl http://localhost:8000/api/newsletter/status/{request_id}

# Get generated newsletter
curl http://localhost:8000/api/newsletter/{newsletter_id}
```

**Available Endpoints:**
- `GET /api/health` - Health check
- `POST /api/newsletter/generate` - Generate newsletter (sync)
- `POST /api/newsletter/generate/stream` - Generate with SSE streaming
- `GET /api/newsletter/status/{request_id}` - Check generation status
- `GET /api/newsletter/{newsletter_id}` - Retrieve newsletter content

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
- `NEXT_PUBLIC_API_URL` - FastAPI backend URL (default: http://localhost:8000)
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key (server-side)
- `RESEND_API_KEY` - Resend email service API key
- `API_SECRET_KEY` - Internal API authentication secret

Create from template:
```bash
cp web/.env.example web/.env.local
# Edit web/.env.local with actual API keys
```

Environment variables are validated at runtime using Zod schema in `web/lib/env.ts`.

#### API Backend

Required environment variables in `api/.env`:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key (for database access)
- `ANTHROPIC_API_KEY` - Claude API key for LLM
- `TAVILY_API_KEY` - Tavily API key for web search
- `LANGCHAIN_API_KEY` or `LANGSMITH_API_KEY` - LangSmith API key for job tracking
- `LANGSMITH_TRACING=true` - Enable LangSmith tracing
- `LANGSMITH_PROJECT="newsletter-automation"` - LangSmith project name

Create from template:
```bash
cp api/.env.example api/.env
# Edit api/.env with actual API keys
```

**Note:** The API backend shares the same Python environment as the CLI, so API keys can also be set in the root `.env` file.

## Architecture

### Monorepo Structure

The project uses a monorepo structure with three main components:

```
newsletter-automation-gpters/
├── src/              # Python CLI newsletter generator + API wrapper
│   ├── agents/       # LangGraph agents (research, topic_selector, tone_editor)
│   ├── api/          # API wrapper modules (NEW)
│   │   ├── models.py              # Pydantic models
│   │   ├── newsletter_generator.py # Newsletter generation orchestrator
│   │   └── supabase_client.py     # Database integration
│   ├── tools/        # Search and content tools
│   └── main.py       # CLI orchestrator
├── web/              # Next.js frontend
├── api/              # FastAPI backend endpoints
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
│   ├── (auth)/            # Auth route group
│   │   ├── login/         # Login page
│   │   ├── signup/        # Signup page
│   │   └── layout.tsx     # Centered auth layout
│   ├── questions/[topicId]/ # Question collection page
│   │   └── page.tsx       # Questions page with progress tracking
│   ├── api/auth/callback/ # Email confirmation callback
│   ├── layout.tsx         # Root layout with Toaster
│   ├── page.tsx           # Landing page (topic input)
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── auth/              # Auth components
│   │   ├── auth-status.tsx    # Login/logout state display
│   │   ├── login-form.tsx     # Login form
│   │   └── signup-form.tsx    # Signup form
│   ├── ui/                # Base UI components
│   │   ├── button.tsx     # Reusable button
│   │   ├── input.tsx      # Reusable input
│   │   └── label.tsx      # Reusable label
│   ├── question-card.tsx  # Question card component (radio/checkbox/text)
│   ├── topic-input.tsx    # Topic input with validation
│   └── example-topics.tsx # Example topic chips
├── lib/                   # Utilities
│   ├── actions/           # Server actions
│   │   ├── auth.ts        # Login, signup, logout
│   │   ├── topic.ts       # Topic creation, retrieval
│   │   └── question.ts    # Question & answer management
│   ├── supabase/          # Supabase clients
│   │   ├── client.ts      # Browser client
│   │   ├── server.ts      # Server client
│   │   └── middleware.ts  # Auth middleware
│   ├── validation/        # Validation schemas
│   │   ├── auth.ts        # Auth validation (Zod)
│   │   ├── topic.ts       # Topic validation (Zod)
│   │   ├── question.ts    # Question & answer validation (Zod)
│   │   └── profanity.ts   # Korean profanity filter
│   ├── default-questions.ts # Default question templates (6 questions)
│   ├── env.ts             # Environment validation
│   └── utils.ts           # Utility functions (cn)
├── types/                 # TypeScript declarations
│   └── badwords-ko.d.ts   # Type defs for badwords-ko
├── __tests__/             # Test files
│   ├── components/        # Component tests
│   │   ├── auth/          # Auth component tests
│   │   └── question-card.test.tsx # Question card tests
│   ├── lib/
│   │   ├── actions/       # Server action tests
│   │   │   ├── auth.test.ts
│   │   │   ├── topic.test.ts
│   │   │   └── question.test.ts
│   │   ├── validation/    # Validation tests
│   │   │   └── question.test.ts
│   │   └── supabase/      # Supabase client tests
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
- **Authentication**: Supabase Auth (email/password with confirmation)
- **Email**: Resend
- **Forms**: React Hook Form with Zod validation
- **State Management**: React hooks + useTransition
- **Validation**: Zod
- **Profanity Filter**: badwords-ko (Korean)

### Home Screen Implementation (Issue #9)

The home screen (`web/app/page.tsx`) includes:

**Implemented:**
- Topic input component with validation (5-100 chars, Korean profanity filter)
- Character counter (0/100) with visual feedback
- Example topic chips that populate the input when clicked
- Login/logout state display (UI only, no actual auth flow yet)
- Toast notifications for validation errors and success messages
- Responsive design with mobile-first approach
- Dark mode support

**Components:**
- `web/components/topic-input.tsx` - Main topic input with form validation
- `web/components/example-topics.tsx` - Example topic chips
- `web/components/auth-status.tsx` - Auth state display (shows user email or login button)

**Validation:**
- `web/lib/validation/topic.ts` - Zod schema for topic validation
- `web/lib/validation/profanity.ts` - Korean profanity filter using `badwords-ko`

**Completed Features:**
1. ✅ **Login/Logout Flow** (Issue #6)
   - Supabase Auth with email/password
   - Email confirmation workflow
   - Session management via middleware

2. ✅ **Topic Submission** (Issue #10)
   - Server Action for topic creation
   - Save topic to Supabase database
   - Automatic generation of 6 default questions
   - Navigation to question page after submission

3. ✅ **Question Page** (Issue #10)
   - Display 6 personalization questions
   - Support for radio, checkbox, and text input types
   - Skip functionality for optional questions
   - Save answers to database

**Future Implementation Required:**
1. **Newsletter Generation** (Next Issue)
   - Integrate LangGraph agent for research
   - Display "리서치 중입니다..." progress indicator
   - Generate personalized newsletter based on topic + answers
   - Send newsletter via Resend email service
   - Show result preview on web

2. **Dynamic Question Generation** (Future Enhancement)
   - LLM-based question generation based on topic content
   - Adaptive questions based on user profile

3. **Newsletter Archive** (Future)
   - View past generated newsletters
   - Bookmark and share functionality

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

### Authentication Implementation

**Status:** ✅ Implemented (Issue #6)

The application uses **Supabase Auth** with email/password authentication:

#### Authentication Flow

1. **Signup** (`/signup`)
   - User enters email, password, and password confirmation
   - Form validated with react-hook-form + Zod
   - Server action calls `supabase.auth.signUp()` with email confirmation required
   - User receives confirmation email
   - Cannot login until email is confirmed

2. **Email Confirmation**
   - User clicks link in email
   - Redirected to `/api/auth/callback` which exchanges code for session
   - Session stored in cookies
   - User can now login

3. **Login** (`/login`)
   - User enters email and password
   - Form validated with react-hook-form + Zod
   - Server action calls `supabase.auth.signInWithPassword()`
   - On success: redirects to home page using Next.js `redirect()`
   - Uses `useTransition` to handle redirect properly

4. **Session Management**
   - Middleware (`web/lib/supabase/middleware.ts`) runs on every request
   - Automatically refreshes expired sessions
   - Cookies managed by Supabase SSR package

5. **Logout**
   - Calls `supabase.auth.signOut()`
   - Clears session cookies
   - Redirects to home page

#### Protected Routes

The middleware protects routes by checking authentication:
- **Protected:** `/dashboard`, `/settings` → redirect to `/login` if not authenticated
- **Public:** `/`, `/login`, `/signup`, `/api/auth/callback`
- **Auth redirect:** logged-in users accessing `/login` or `/signup` → redirect to home

#### Components

- **AuthStatus** (`components/auth/auth-status.tsx`)
  - Shows user email when logged in with logout button
  - Shows login/signup buttons when logged out
  - Real-time updates via `supabase.auth.onAuthStateChange()`

- **LoginForm** (`components/auth/login-form.tsx`)
  - Email + password fields
  - React Hook Form with Zod validation
  - useTransition for proper redirect handling
  - Korean error messages

- **SignupForm** (`components/auth/signup-form.tsx`)
  - Email + password + confirm password
  - Shows success screen after signup
  - Korean error messages

#### Server Actions

Located in `web/lib/actions/auth.ts`:

```typescript
// Login with password
export async function login(formData: FormData)

// Signup with email confirmation
export async function signup(formData: FormData)

// Logout and redirect
export async function logout()
```

All actions return `{ success: boolean, message: string }` with Korean messages.

#### Validation

- **Auth validation** (`web/lib/validation/auth.ts`)
  - Email format validation
  - Password minimum 8 characters
  - Password confirmation matching
  - Korean error messages

- **Topic validation** (`web/lib/validation/topic.ts`)
  - 5-100 character limit
  - Korean profanity filter using `badwords-ko`

#### Environment Variables

Client-side (browser):
```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_SITE_URL=http://localhost:3000  # For email redirects
```

Server-side only (never sent to browser):
```bash
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
RESEND_API_KEY=your_resend_key
API_SECRET_KEY=your_secret_key_min_32_chars
```

**Important:** `lib/env.ts` validates server-only vars only when available (server/tests), avoiding browser errors.

#### Supabase Configuration Required

In Supabase Dashboard:
1. Go to Authentication → Settings → Email Auth
2. Enable "Confirm email" option
3. Set Site URL to your app URL (`http://localhost:3000` for dev)
4. Email templates use default Supabase templates

### Landing Page

**Status:** ✅ Implemented (from issue-9, restored in issue-6)

The landing page (`/`) features:

#### Components

- **TopicInput** (`components/topic-input.tsx`)
  - Text input with 5-100 character validation
  - Korean profanity filter
  - Character counter (0/100)
  - Submit button with loading state
  - Korean placeholder: "어떤 주제로 리서치해 드릴까요?"
  - Toast notifications for validation errors

- **ExampleTopics** (`components/example-topics.tsx`)
  - Clickable topic chips that populate the input
  - Topics: "AI 에이전트 최신 동향", "LLM 프롬프팅 기법", "RAG 시스템 구현 방법"

- **AuthStatus** (in header)
  - Shows user email + logout button when logged in
  - Shows login/signup buttons when logged out

#### Layout

```
┌─────────────────────────────────────┐
│  Automata              [Auth Status] │ ← Header
├─────────────────────────────────────┤
│                                     │
│    개인화된 리서치 뉴스레터               │ ← Title
│    관심 있는 주제를 입력하면...          │ ← Description
│                                     │
│    [Topic Input Field         0/100] │ ← TopicInput
│    [리서치 시작하기 Button]             │
│                                     │
│    예시 주제를 클릭해보세요               │ ← ExampleTopics
│    [AI 에이전트] [LLM 프롬프팅] [RAG]    │
│                                     │
├─────────────────────────────────────┤
│  © 2026 Automata. AI-powered...    │ ← Footer
└─────────────────────────────────────┘
```

#### Validation

Topic validation (`lib/validation/topic.ts`):
- Minimum 5 characters
- Maximum 100 characters
- Korean profanity filter using `badwords-ko`
- Korean error messages

**TODO (Future Issues):**
- Topic submission logic (currently just shows success toast)
- Generate follow-up questions based on topic
- Route to question page after submission

### Testing

**Status:** ✅ Comprehensive test coverage (171 tests)

Test organization:
```
__tests__/
├── lib/
│   ├── env.test.ts                 # 14 tests - Environment validation
│   ├── validation/auth.test.ts     # 48 tests - Auth schemas
│   ├── actions/auth.test.ts        # 22 tests - Server actions
│   └── supabase/
│       ├── client.test.ts          # 8 tests - Browser client
│       └── server.test.ts          # 16 tests - Server client
└── components/auth/
    ├── login-form.test.tsx         # 35 tests - Login form
    └── signup-form.test.tsx        # 28 tests - Signup form
```

**Test Coverage:**
- Validation schemas: 100%
- Server actions: 100% (93.75% branches)
- Auth components: 100%
- Overall: 94.73%

**Testing Patterns:**
- Vitest as test framework
- @testing-library/react for component testing
- @testing-library/user-event for user interactions
- Mock Supabase clients
- Korean text verification in all UI tests

**Run tests:**
```bash
npm test                    # Run all tests
npm test -- __tests__/lib/  # Run specific test directory
npm run test:coverage       # Generate coverage report
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

### Key Web Dependencies

**Authentication & Forms:**
- `@supabase/ssr@^0.8.0` - Supabase SSR integration
- `@supabase/supabase-js@^2.91.0` - Supabase client
- `react-hook-form@^7.54.2` - Form state management
- `@hookform/resolvers@^4.0.1` - Zod integration for forms

**Validation:**
- `zod@^4.3.5` - Schema validation
- `badwords-ko` - Korean profanity filtering

**UI Utilities:**
- `clsx@^2.1.1` - Conditional className construction
- `tailwind-merge@^3.0.2` - Merge Tailwind classes without conflicts
- `react-hot-toast@^2.6.0` - Toast notifications

**Email:**
- `resend@^6.8.0` - Email service integration

**Testing:**
- `vitest@^4.0.17` - Test framework
- `@testing-library/react@^16.1.0` - Component testing
- `@testing-library/user-event@^14.6.1` - User interaction testing
- `happy-dom@^16.3.2` - DOM simulation for tests

## Model Configuration

Default model: `claude-sonnet-4-5-20250929` (via deepagents)
Override in `.env`: `MODEL_NAME=claude-sonnet-4-5-20250929`
