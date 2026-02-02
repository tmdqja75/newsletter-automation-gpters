# Database Quick Start Guide

This guide will help you set up and use the database schema for the personalized research newsletter service.

## Prerequisites

- Supabase CLI installed: `npm install -g supabase`
- Docker installed and running (for local development)
- Node.js 20+ installed

## Step 1: Start Local Supabase

```bash
cd /Users/seungbeomha/Documents/personal_projects/newsletter-automation-gpters

# Start Supabase (will download Docker images on first run)
supabase start

# Note the credentials shown after startup:
# - API URL: http://localhost:54321
# - Anon key: eyJh...
# - Service role key: eyJh...
```

## Step 2: Apply Migration

```bash
# Reset database and apply all migrations
supabase db reset

# This will:
# 1. Drop all existing tables
# 2. Apply migrations in order
# 3. Create all 10 tables + indexes + triggers + RLS policies
```

## Step 3: Configure Environment Variables

```bash
cd web

# Copy environment template
cp .env.example .env.local

# Edit .env.local with Supabase credentials
# NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
# NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key_from_supabase_start>
# SUPABASE_SERVICE_ROLE_KEY=<service_role_key_from_supabase_start>
```

## Step 4: Install Required Packages

```bash
cd web

npm install @supabase/supabase-js @supabase/auth-helpers-nextjs
```

## Step 5: Test the Schema

### Option A: Using Supabase Studio

1. Open http://localhost:54323 in your browser
2. Navigate to "Table Editor"
3. You should see all 10 tables
4. Try inserting test data manually

### Option B: Using SQL Editor

```sql
-- Create test user (in Supabase Studio SQL Editor)
INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at)
VALUES (
  gen_random_uuid(),
  'test@example.com',
  crypt('password123', gen_salt('bf')),
  NOW()
);

-- Get the user ID
SELECT id FROM auth.users WHERE email = 'test@example.com';

-- Create user profile (replace <user_id> with actual ID)
INSERT INTO users (id, email, display_name)
VALUES ('<user_id>', 'test@example.com', 'Test User');

-- Create a topic
INSERT INTO user_topics (user_id, topic_text, topic_description)
VALUES ('<user_id>', 'LangGraph 멀티에이전트 패턴', '최신 멀티에이전트 시스템 구축 패턴');

-- Query topics
SELECT * FROM user_topics WHERE user_id = '<user_id>';
```

### Option C: Using Next.js API Route

Create `web/app/api/test-db/route.ts`:

```typescript
import { createServerClient } from '@/lib/supabase';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const supabase = createServerClient();

    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Get user's topics
    const { data: topics, error: topicsError } = await supabase
      .from('user_topics')
      .select('*')
      .eq('user_id', user.id)
      .eq('is_active', true);

    if (topicsError) {
      return NextResponse.json(
        { error: topicsError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      user: {
        id: user.id,
        email: user.email,
      },
      topics,
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

Test it:
```bash
# Start Next.js dev server
npm run dev

# Visit http://localhost:3000/api/test-db
```

## Step 6: Common Operations

### Create a Topic

```typescript
import { createServerClient } from '@/lib/supabase';

const supabase = createServerClient();
const { data: { user } } = await supabase.auth.getUser();

const { data, error } = await supabase
  .from('user_topics')
  .insert({
    user_id: user!.id,
    topic_text: 'AI 에이전트 프레임워크 2026',
    topic_description: '최신 에이전트 프레임워크 동향',
  })
  .select()
  .single();
```

### Create Personalization Questions

```typescript
const { data: topic } = await supabase
  .from('user_topics')
  .select('id')
  .eq('user_id', user!.id)
  .single();

const questions = [
  {
    topic_id: topic!.id,
    question_text: '이 주제를 왜 알고 싶으신가요?',
    question_type: 'goal' as const,
    options: ['업무', '학습', '취미', '기타'],
    display_order: 1,
  },
  {
    topic_id: topic!.id,
    question_text: '현재 이해 수준은 어느 정도인가요?',
    question_type: 'difficulty' as const,
    options: ['초급', '중급', '고급'],
    display_order: 2,
  },
];

const { data, error } = await supabase
  .from('personalization_questions')
  .insert(questions)
  .select();
```

### Create Newsletter Request

```typescript
const { data: request, error } = await supabase
  .from('newsletter_requests')
  .insert({
    user_id: user!.id,
    topic_id: topic!.id,
    status: 'pending',
  })
  .select()
  .single();
```

### Create Newsletter

```typescript
const { data: newsletter, error } = await supabase
  .from('newsletters')
  .insert({
    request_id: request!.id,
    user_id: user!.id,
    topic_id: topic!.id,
    title: 'AI 에이전트 프레임워크 2026 - 주간 업데이트',
    tldr: '이번 주 AI 에이전트 분야의 핵심 업데이트를 정리했습니다...',
    core_issues: [
      {
        title: 'LangGraph 0.2.0 출시',
        summary: '새로운 멀티에이전트 기능 추가...',
        links: [
          {
            url: 'https://example.com',
            title: 'LangGraph 0.2.0 Release Notes',
          },
        ],
      },
    ],
    deep_dive: {
      title: '멀티에이전트 시스템의 미래',
      content: '상세한 분석 내용...',
      additional_readings: [
        {
          url: 'https://example.com/deep-dive',
          title: 'Multi-Agent Systems: A Deep Dive',
        },
      ],
    },
    sources: [
      {
        url: 'https://example.com',
        title: 'Source Article',
        domain: 'example.com',
      },
    ],
    is_published: true,
    published_at: new Date().toISOString(),
  })
  .select()
  .single();
```

### Submit Feedback

```typescript
const { data: feedback, error } = await supabase
  .from('newsletter_feedback')
  .insert({
    newsletter_id: newsletter!.id,
    user_id: user!.id,
    feedback_type: 'thumbs_up',
    comment: '정말 유용한 정보였어요!',
    detailed_feedback: {
      loved_sections: ['Deep Dive', 'Core Issues'],
    },
  })
  .select()
  .single();
```

### Update User Preferences

```typescript
const { data: prefs, error } = await supabase
  .from('user_preferences')
  .upsert({
    user_id: user!.id,
    send_frequency: 'weekly',
    preferred_difficulty: 'intermediate',
    preferred_length: 'medium',
    source_whitelist: [
      'blog.langchain.dev',
      'anthropic.com',
      'openai.com',
    ],
    email_enabled: true,
  })
  .select()
  .single();
```

### Query with Views

```typescript
// Get active topics with latest newsletter
const { data: topics, error } = await supabase
  .from('active_topics_with_latest_newsletter')
  .select('*')
  .eq('user_id', user!.id);

// Get newsletter engagement metrics
const { data: metrics, error: metricsError } = await supabase
  .from('newsletter_engagement_metrics')
  .select('*')
  .eq('user_id', user!.id);
```

## Step 7: Verify RLS Policies

```sql
-- Test RLS (in Supabase Studio SQL Editor)

-- Switch to user context
SET request.jwt.claims = '{"sub": "<user_id>"}';

-- Try to access another user's data (should return empty)
SELECT * FROM user_topics WHERE user_id != '<user_id>';

-- Access own data (should work)
SELECT * FROM user_topics WHERE user_id = '<user_id>';
```

## Step 8: Monitor & Debug

### View Database Schema

```bash
# Generate TypeScript types from database
supabase gen types typescript --local > web/lib/database.types.generated.ts
```

### Check Migration Status

```bash
# List all migrations
supabase migration list

# Check if migrations are applied
supabase db diff
```

### View Logs

```bash
# View Supabase logs
supabase logs

# View PostgreSQL logs
docker logs <supabase_db_container_id>
```

### Query Statistics

```sql
-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## Troubleshooting

### Migration Fails

```bash
# Reset everything and try again
supabase db reset

# If that doesn't work, stop and restart
supabase stop
supabase start
supabase db reset
```

### RLS Policy Errors

```bash
# Check if RLS is enabled
supabase db diff

# Temporarily disable RLS for debugging (NEVER in production!)
ALTER TABLE user_topics DISABLE ROW LEVEL SECURITY;
```

### Connection Issues

```bash
# Check Supabase status
supabase status

# Verify Docker containers
docker ps | grep supabase
```

### Type Errors

```bash
# Regenerate types from database
cd web
supabase gen types typescript --local > lib/database.types.ts
```

## Next Steps

1. Create seed data for development: `supabase/seed.sql`
2. Set up database backups
3. Configure Supabase Edge Functions (if needed)
4. Set up Realtime subscriptions
5. Deploy to production Supabase project

## Production Deployment

### Link to Production Project

```bash
# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref <your-project-ref>

# Push migrations
supabase db push

# Verify
supabase db diff
```

### Update Environment Variables

```bash
# web/.env.production (or Vercel environment variables)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<production_anon_key>
SUPABASE_SERVICE_ROLE_KEY=<production_service_role_key>
```

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase CLI Reference](https://supabase.com/docs/reference/cli)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- Migration file: `supabase/migrations/20260121000000_initial_schema.sql`
- Type definitions: `web/lib/database.types.ts`
- Utilities: `web/lib/supabase.ts`
- Detailed docs: `supabase/migrations/README.md`
- Summary: `supabase/MIGRATION_SUMMARY.md`
