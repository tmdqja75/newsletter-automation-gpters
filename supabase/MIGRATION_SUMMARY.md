# Database Schema Migration Summary

## Overview

Comprehensive database schema migration created for the personalized research newsletter service based on PRD requirements.

## Files Created

### 1. Migration File
**Location**: `supabase/migrations/20260121000000_initial_schema.sql`
- **Size**: 29KB
- **Lines**: 723 lines
- **Database Objects**: 87 objects created

### 2. Documentation
**Location**: `supabase/migrations/README.md`
- Comprehensive documentation of schema
- Migration instructions
- Troubleshooting guide

### 3. TypeScript Types
**Location**: `web/lib/database.types.ts`
- Type-safe database access
- Helper types for JSONB fields
- Full TypeScript support

### 4. Supabase Utilities
**Location**: `web/lib/supabase.ts`
- Client creation utilities
- Type-safe helpers
- Authentication helpers

## Database Objects Summary

### Tables (10)

1. **users** - Extended user profiles
   - Extends Supabase Auth
   - Email validation
   - Onboarding status
   - Flexible metadata (JSONB)

2. **user_topics** - Research topics
   - Multiple topics per user
   - Active/inactive status
   - Minimum 5 characters validation

3. **personalization_questions** - AI-generated questions
   - 7 question types (goal, difficulty, scope, time, source, subtopic, custom)
   - Multiple choice options (JSONB)
   - Display order
   - Required/optional flags

4. **user_answers** - Question responses
   - Text and structured answers
   - One answer per user per question
   - Flexible answer format (JSONB)

5. **newsletter_requests** - Request tracking
   - Status: pending, processing, completed, failed
   - Processing timestamps
   - Error tracking
   - Retry mechanism
   - Agent metadata (LangGraph)

6. **newsletters** - Generated content
   - Title, TL;DR, core issues, deep dive
   - JSONB for flexible content structure
   - Word count and reading time
   - Publication and email tracking
   - Sources with metadata

7. **newsletter_feedback** - User feedback
   - Binary feedback (thumbs_up/thumbs_down)
   - Optional comment (max 500 chars)
   - Structured feedback (JSONB)
   - One feedback per user per newsletter

8. **user_preferences** - User settings
   - Send frequency (on_demand, daily, weekly, bi_weekly)
   - Difficulty level (beginner, intermediate, advanced)
   - Length preference (short, medium, long)
   - Source whitelist/blacklist (JSONB arrays)
   - Email and digest mode settings

9. **email_events** - Email tracking
   - 7 event types (sent, delivered, opened, clicked, bounced, complained, unsubscribed)
   - Provider tracking (Resend, SendGrid, etc.)
   - Click tracking with URLs
   - User agent and IP tracking

10. **audit_logs** - Audit trail
    - Immutable logs (no updated_at)
    - Actor tracking (user, system, admin)
    - Resource tracking
    - Before/after values (JSONB)
    - IP and user agent

### Indexes (30+)

Strategic indexes on:
- Foreign keys
- Frequently queried columns (user_id, created_at, status)
- Composite indexes for common patterns
- Email tracking indexes

### Triggers (8)

Automatic `updated_at` timestamp updates on:
- users
- user_topics
- personalization_questions
- user_answers
- newsletter_requests
- newsletters
- newsletter_feedback
- user_preferences

### Views (2)

1. **active_topics_with_latest_newsletter**
   - Active topics with their most recent published newsletter
   - Useful for dashboard displays

2. **newsletter_engagement_metrics**
   - Newsletter performance metrics
   - Opens, clicks, bounces
   - Feedback aggregation

### Row Level Security (RLS)

- Enabled on all 10 tables
- 23 RLS policies created
- Users can only access their own data
- Read/write policies per table
- Admin access via service role

## Key Features

### 1. Type Safety
```typescript
import { TableRow, TableInsert, createServerClient } from '@/lib/supabase';

type UserTopic = TableRow<'user_topics'>;
type NewTopic = TableInsert<'user_topics'>;

const supabase = createServerClient();
const { data, error } = await supabase
  .from('user_topics')
  .select('*')
  .eq('user_id', userId);
```

### 2. JSONB Flexibility

All tables include strategic JSONB fields for:
- **newsletters.core_issues** - Array of issues with links
- **newsletters.deep_dive** - Rich content with readings
- **newsletters.sources** - Source metadata
- **user_preferences.source_whitelist** - Preferred sources
- **newsletter_feedback.detailed_feedback** - Structured feedback
- **newsletter_requests.agent_metadata** - LangGraph metrics

### 3. Audit Trail

Complete audit logging for:
- User actions
- System operations
- Data changes (before/after)
- Compliance requirements

### 4. Email Tracking

Comprehensive email event tracking:
- Delivery status
- Open rates
- Click tracking
- Bounce handling
- Unsubscribe tracking

## Next Steps

### 1. Apply Migration

```bash
# Local development
cd /Users/seungbeomha/Documents/personal_projects/newsletter-automation-gpters
supabase start
supabase db reset

# Production
supabase link --project-ref your-project-ref
supabase db push
```

### 2. Install Supabase Packages

```bash
cd web
npm install @supabase/supabase-js @supabase/auth-helpers-nextjs
```

### 3. Update Environment Variables

```bash
# web/.env.local
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### 4. Test the Schema

```typescript
// Example: Create a new topic
import { createServerClient } from '@/lib/supabase';

export async function POST(request: Request) {
  const supabase = createServerClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { data, error } = await supabase
    .from('user_topics')
    .insert({
      user_id: user.id,
      topic_text: 'LangGraph multi-agent patterns',
      topic_description: 'Latest patterns for building multi-agent systems',
    })
    .select()
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ data });
}
```

### 5. Create Seed Data

Create `supabase/seed.sql` for development data:
```sql
-- Example seed data for testing
INSERT INTO user_preferences (user_id, send_frequency, preferred_difficulty, preferred_length)
SELECT id, 'on_demand', 'intermediate', 'medium'
FROM auth.users
WHERE email = 'test@example.com';
```

### 6. Set Up Real-time (Optional)

```typescript
// Subscribe to newsletter updates
const supabase = createBrowserClient();

const channel = supabase
  .channel('newsletter_updates')
  .on(
    'postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'newsletters',
      filter: `user_id=eq.${userId}`,
    },
    (payload) => {
      console.log('New newsletter:', payload.new);
    }
  )
  .subscribe();
```

### 7. Monitor Performance

```sql
-- Check slow queries
SELECT
  query,
  calls,
  total_time,
  mean_time
FROM pg_stat_statements
WHERE query LIKE '%newsletters%'
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
```

## Schema Validation

### Check Constraints

All tables include check constraints for data integrity:
- Email format validation
- Enum value validation
- Length constraints
- Range validation

### Foreign Keys

Proper cascading deletes:
- When user is deleted, all related data is deleted
- When topic is deleted, questions and newsletters are deleted
- Data consistency maintained

### Unique Constraints

- One preference per user
- One feedback per user per newsletter
- One answer per user per question

## Compliance Features

### GDPR Compliance

- User data deletion cascades properly
- Audit logs track all data access
- Email unsubscribe tracking
- User preferences for email opt-out

### Data Retention

- Audit logs are immutable
- No automatic deletion
- Archive strategies can be implemented

### Security

- RLS enforces data isolation
- Service role for admin operations only
- IP and user agent tracking
- Email validation

## Performance Considerations

### Indexes

- All foreign keys indexed
- Composite indexes for common queries
- Timestamp columns indexed for sorting
- Status columns indexed for filtering

### JSONB

- Use JSONB for flexible schema
- Can add GIN indexes on JSONB fields if needed:
```sql
CREATE INDEX idx_newsletters_sources_gin
ON newsletters USING GIN (sources);
```

### Partitioning (Future)

Consider partitioning large tables:
- email_events by event_timestamp
- audit_logs by timestamp
- newsletters by created_at

## Migration Statistics

- **Total Objects**: 87
- **Tables**: 10
- **Indexes**: 30+
- **Triggers**: 8
- **Views**: 2
- **RLS Policies**: 23
- **Check Constraints**: 15+
- **Foreign Keys**: 17
- **Unique Constraints**: 4

## Estimated Database Size

Initial estimates (production, 1000 users):
- **users**: ~100KB
- **user_topics**: ~500KB (5 topics/user avg)
- **personalization_questions**: ~200KB
- **user_answers**: ~1MB
- **newsletter_requests**: ~2MB
- **newsletters**: ~50MB (rich content)
- **newsletter_feedback**: ~500KB
- **user_preferences**: ~100KB
- **email_events**: ~5MB
- **audit_logs**: ~10MB

**Total**: ~70MB for 1000 users with moderate usage

## Support

For issues or questions:
1. Check `supabase/migrations/README.md`
2. Review `web/lib/database.types.ts` for type definitions
3. Consult Supabase documentation: https://supabase.com/docs

## Version History

- **v1.0.0** (2026-01-21) - Initial schema migration
  - 10 tables
  - Full RLS policies
  - Comprehensive indexes
  - Type-safe utilities
