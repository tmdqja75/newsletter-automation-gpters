# Database Migrations

This directory contains SQL migration files for the personalized research newsletter service.

## Migration Files

### 20260121000000_initial_schema.sql

Initial database schema with 10 tables:

1. **users** - Extended user profiles (extends Supabase Auth)
2. **user_topics** - Research topics tracked by users
3. **personalization_questions** - AI-generated questions for personalization
4. **user_answers** - User responses to personalization questions
5. **newsletter_requests** - Newsletter generation request tracking
6. **newsletters** - Generated newsletter content
7. **newsletter_feedback** - User feedback (thumbs up/down + comments)
8. **user_preferences** - User preferences (scheduling, difficulty, length)
9. **email_events** - Email tracking (sent, opened, clicked, bounced)
10. **audit_logs** - Immutable audit trail for compliance

## Features

### Foreign Key Relationships

```
users (1) ─── (many) user_topics
user_topics (1) ─── (many) personalization_questions
personalization_questions (1) ─── (many) user_answers
users (1) ─── (many) user_answers
users (1) ─── (many) newsletter_requests
user_topics (1) ─── (many) newsletter_requests
newsletter_requests (1) ─── (1) newsletters
newsletters (1) ─── (many) newsletter_feedback
newsletters (1) ─── (many) email_events
users (1) ─── (1) user_preferences
users (1) ─── (many) audit_logs
```

### JSONB Fields

The schema uses JSONB for flexible data storage:

- **users.metadata** - Additional user data
- **user_topics.metadata** - Topic metadata
- **personalization_questions.options** - Multiple choice options
- **personalization_questions.metadata** - Question metadata
- **user_answers.answer_value** - Structured answers
- **newsletter_requests.error_details** - Error information
- **newsletter_requests.agent_metadata** - LangGraph execution metadata
- **newsletters.core_issues** - Array of core issues with links
- **newsletters.deep_dive** - Deep dive section content
- **newsletters.next_questions** - Suggested questions
- **newsletters.sources** - Source links with metadata
- **newsletters.metadata** - Additional newsletter data
- **newsletter_feedback.detailed_feedback** - Structured feedback
- **user_preferences.source_whitelist** - Preferred sources
- **user_preferences.source_blacklist** - Blocked sources
- **user_preferences.metadata** - Additional preferences
- **email_events.metadata** - Event metadata
- **audit_logs.old_values** - Values before update
- **audit_logs.new_values** - Values after update
- **audit_logs.metadata** - Audit metadata

### Indexes

All tables have appropriate indexes for:
- Foreign key columns
- Frequently queried columns (user_id, created_at, status, etc.)
- Composite indexes for common query patterns

### Triggers

Automatic `updated_at` timestamp updates via triggers on:
- users
- user_topics
- personalization_questions
- user_answers
- newsletter_requests
- newsletters
- newsletter_feedback
- user_preferences

Note: `audit_logs` and `email_events` don't have `updated_at` as they are immutable.

### Row Level Security (RLS)

All tables have RLS enabled with policies to ensure:
- Users can only access their own data
- System/admin operations use service role
- Data isolation between users

### Views

Two helpful views are created:

1. **active_topics_with_latest_newsletter** - Active topics with their most recent newsletter
2. **newsletter_engagement_metrics** - Newsletter engagement metrics (opens, clicks, feedback)

## Running Migrations

### Local Development

```bash
# Start Supabase locally
supabase start

# Apply migrations
supabase db reset

# Or apply specific migration
supabase migration up
```

### Production

```bash
# Link to your project
supabase link --project-ref your-project-ref

# Apply migrations
supabase db push
```

## Schema Diagram

```
┌─────────────────┐
│     users       │
│  (Supabase)     │
└────────┬────────┘
         │
         ├──────────────────────────┐
         │                          │
         │                          │
┌────────▼───────┐          ┌──────▼──────────┐
│  user_topics   │          │ user_preferences│
└────────┬───────┘          └─────────────────┘
         │
         ├──────────────────┐
         │                  │
┌────────▼───────────────┐  │
│ personalization_       │  │
│    questions           │  │
└────────┬───────────────┘  │
         │                  │
         │                  │
┌────────▼──────────┐       │
│  user_answers     │       │
└───────────────────┘       │
                            │
                    ┌───────▼───────────┐
                    │ newsletter_       │
                    │   requests        │
                    └───────┬───────────┘
                            │
                            │
                    ┌───────▼───────────┐
                    │  newsletters      │
                    └───────┬───────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
        ┌───────▼──────┐    │    ┌──────▼──────┐
        │ newsletter_  │    │    │   email_    │
        │  feedback    │    │    │   events    │
        └──────────────┘    │    └─────────────┘
                            │
                    ┌───────▼──────┐
                    │ audit_logs   │
                    └──────────────┘
```

## Best Practices

1. **Always use transactions** for multi-table operations
2. **Use JSONB judiciously** - index specific keys if queried frequently
3. **Respect RLS policies** - use service role only when necessary
4. **Keep audit logs** - don't delete, archive if needed
5. **Monitor index usage** - add/remove indexes based on actual query patterns
6. **Use prepared statements** to prevent SQL injection
7. **Validate JSONB structure** at application level before insert/update

## Environment Variables

Required in `web/.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Troubleshooting

### Migration Failed

```bash
# Check migration status
supabase migration list

# View migration errors
supabase db reset --debug
```

### RLS Policy Issues

```bash
# Check if RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';

# View policies
SELECT *
FROM pg_policies
WHERE schemaname = 'public';
```

### Index Performance

```bash
# Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
```

## Next Steps

1. Apply migration to local Supabase instance
2. Test RLS policies with different user contexts
3. Create seed data for development
4. Set up Supabase functions for complex operations (if needed)
5. Configure real-time subscriptions (if needed)
6. Set up database backups
