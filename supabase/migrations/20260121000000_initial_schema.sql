-- Migration: Initial database schema for personalized research newsletter service
-- Created: 2026-01-21
-- Description: Creates 10 tables for user management, topic tracking, personalization,
--              newsletter generation, feedback, preferences, email tracking, and audit logs

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. USERS TABLE
-- Extended user profile that extends Supabase Auth
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,

    -- User metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,

    -- User status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,

    -- Onboarding
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,

    -- Additional metadata (JSONB for flexibility)
    metadata JSONB DEFAULT '{}'::JSONB,

    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Indexes for users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Comments for users
COMMENT ON TABLE users IS 'Extended user profiles that extend Supabase Auth users';
COMMENT ON COLUMN users.id IS 'References auth.users(id) from Supabase Auth';
COMMENT ON COLUMN users.metadata IS 'Flexible JSONB field for additional user data';

-- =============================================================================
-- 2. USER_TOPICS TABLE
-- User's research topics (one user can have multiple topics)
-- =============================================================================
CREATE TABLE user_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Topic content
    topic_text TEXT NOT NULL,
    topic_description TEXT,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}'::JSONB,

    CONSTRAINT user_topics_topic_text_check CHECK (char_length(topic_text) >= 5)
);

-- Indexes for user_topics
CREATE INDEX idx_user_topics_user_id ON user_topics(user_id);
CREATE INDEX idx_user_topics_is_active ON user_topics(is_active);
CREATE INDEX idx_user_topics_created_at ON user_topics(created_at);
CREATE INDEX idx_user_topics_user_id_is_active ON user_topics(user_id, is_active);

-- Comments for user_topics
COMMENT ON TABLE user_topics IS 'Research topics that users want to track';
COMMENT ON COLUMN user_topics.topic_text IS 'Main topic text (minimum 5 characters)';
COMMENT ON COLUMN user_topics.is_active IS 'Whether topic is actively being tracked';

-- =============================================================================
-- 3. PERSONALIZATION_QUESTIONS TABLE
-- AI-generated personalization questions for topics
-- =============================================================================
CREATE TABLE personalization_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id UUID NOT NULL REFERENCES user_topics(id) ON DELETE CASCADE,

    -- Question content
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL, -- 'goal', 'difficulty', 'scope', 'time', 'source', 'subtopic', 'custom'

    -- Options for multiple choice questions (JSONB array)
    options JSONB DEFAULT '[]'::JSONB,

    -- Question order
    display_order INTEGER NOT NULL DEFAULT 0,

    -- Status
    is_required BOOLEAN NOT NULL DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}'::JSONB,

    CONSTRAINT personalization_questions_type_check CHECK (
        question_type IN ('goal', 'difficulty', 'scope', 'time', 'source', 'subtopic', 'custom')
    )
);

-- Indexes for personalization_questions
CREATE INDEX idx_personalization_questions_topic_id ON personalization_questions(topic_id);
CREATE INDEX idx_personalization_questions_display_order ON personalization_questions(display_order);
CREATE INDEX idx_personalization_questions_topic_id_display_order ON personalization_questions(topic_id, display_order);

-- Comments for personalization_questions
COMMENT ON TABLE personalization_questions IS 'AI-generated questions to personalize newsletter content (3-7 questions per topic)';
COMMENT ON COLUMN personalization_questions.question_type IS 'Type of question: goal, difficulty, scope, time, source, subtopic, custom';
COMMENT ON COLUMN personalization_questions.options IS 'JSONB array of multiple choice options (if applicable)';

-- =============================================================================
-- 4. USER_ANSWERS TABLE
-- User responses to personalization questions
-- =============================================================================
CREATE TABLE user_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES personalization_questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Answer content
    answer_text TEXT,
    answer_value JSONB, -- For structured answers (multiple choice, rating, etc.)

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Ensure one answer per user per question
    CONSTRAINT user_answers_unique_user_question UNIQUE (user_id, question_id)
);

-- Indexes for user_answers
CREATE INDEX idx_user_answers_question_id ON user_answers(question_id);
CREATE INDEX idx_user_answers_user_id ON user_answers(user_id);
CREATE INDEX idx_user_answers_created_at ON user_answers(created_at);

-- Comments for user_answers
COMMENT ON TABLE user_answers IS 'User responses to personalization questions';
COMMENT ON COLUMN user_answers.answer_text IS 'Free-form text answer';
COMMENT ON COLUMN user_answers.answer_value IS 'Structured answer data (JSONB)';

-- =============================================================================
-- 5. NEWSLETTER_REQUESTS TABLE
-- Newsletter generation tracking (request lifecycle)
-- =============================================================================
CREATE TABLE newsletter_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES user_topics(id) ON DELETE CASCADE,

    -- Request details
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'

    -- Processing timestamps
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,

    -- Error tracking
    error_message TEXT,
    error_details JSONB,

    -- Processing metadata
    agent_metadata JSONB DEFAULT '{}'::JSONB, -- LangGraph execution metadata

    -- Retry tracking
    retry_count INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT newsletter_requests_status_check CHECK (
        status IN ('pending', 'processing', 'completed', 'failed')
    ),
    CONSTRAINT newsletter_requests_retry_count_check CHECK (retry_count >= 0)
);

-- Indexes for newsletter_requests
CREATE INDEX idx_newsletter_requests_user_id ON newsletter_requests(user_id);
CREATE INDEX idx_newsletter_requests_topic_id ON newsletter_requests(topic_id);
CREATE INDEX idx_newsletter_requests_status ON newsletter_requests(status);
CREATE INDEX idx_newsletter_requests_requested_at ON newsletter_requests(requested_at);
CREATE INDEX idx_newsletter_requests_user_id_status ON newsletter_requests(user_id, status);

-- Comments for newsletter_requests
COMMENT ON TABLE newsletter_requests IS 'Tracks newsletter generation requests and their lifecycle';
COMMENT ON COLUMN newsletter_requests.status IS 'Request status: pending, processing, completed, failed';
COMMENT ON COLUMN newsletter_requests.agent_metadata IS 'LangGraph agent execution metadata (steps, tokens, etc.)';

-- =============================================================================
-- 6. NEWSLETTERS TABLE
-- Generated newsletter content
-- =============================================================================
CREATE TABLE newsletters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES newsletter_requests(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES user_topics(id) ON DELETE CASCADE,

    -- Newsletter content
    title TEXT NOT NULL,

    -- Content sections (all in Korean)
    tldr TEXT NOT NULL, -- 3-6 lines summary
    core_issues JSONB NOT NULL, -- Array of 3-5 core issues [{title, summary, links}]
    deep_dive JSONB NOT NULL, -- Deep dive section {title, content, additional_readings}
    next_questions JSONB DEFAULT '[]'::JSONB, -- Suggested next research questions
    sources JSONB NOT NULL, -- Array of source links with metadata

    -- Metadata
    word_count INTEGER,
    estimated_reading_time INTEGER, -- in minutes

    -- Publication
    published_at TIMESTAMPTZ,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,

    -- Email tracking
    email_sent_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Additional metadata
    metadata JSONB DEFAULT '{}'::JSONB
);

-- Indexes for newsletters
CREATE INDEX idx_newsletters_request_id ON newsletters(request_id);
CREATE INDEX idx_newsletters_user_id ON newsletters(user_id);
CREATE INDEX idx_newsletters_topic_id ON newsletters(topic_id);
CREATE INDEX idx_newsletters_published_at ON newsletters(published_at);
CREATE INDEX idx_newsletters_is_published ON newsletters(is_published);
CREATE INDEX idx_newsletters_user_id_published_at ON newsletters(user_id, published_at);

-- Comments for newsletters
COMMENT ON TABLE newsletters IS 'Generated newsletter content with TL;DR, core issues, and deep dive sections';
COMMENT ON COLUMN newsletters.tldr IS 'TL;DR summary (3-6 lines in Korean)';
COMMENT ON COLUMN newsletters.core_issues IS 'JSONB array of 3-5 core issues with summaries and links';
COMMENT ON COLUMN newsletters.deep_dive IS 'JSONB object with detailed deep dive content';
COMMENT ON COLUMN newsletters.sources IS 'JSONB array of all source links with metadata';

-- =============================================================================
-- 7. NEWSLETTER_FEEDBACK TABLE
-- User feedback on newsletters (thumbs up/down + comments)
-- =============================================================================
CREATE TABLE newsletter_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Feedback content
    feedback_type TEXT NOT NULL, -- 'thumbs_up', 'thumbs_down'
    comment TEXT,

    -- Structured feedback (optional)
    detailed_feedback JSONB DEFAULT '{}'::JSONB, -- {too_long, too_short, too_easy, too_hard, etc.}

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure one feedback per user per newsletter
    CONSTRAINT newsletter_feedback_unique_user_newsletter UNIQUE (user_id, newsletter_id),
    CONSTRAINT newsletter_feedback_type_check CHECK (
        feedback_type IN ('thumbs_up', 'thumbs_down')
    ),
    CONSTRAINT newsletter_feedback_comment_length_check CHECK (
        comment IS NULL OR char_length(comment) <= 500
    )
);

-- Indexes for newsletter_feedback
CREATE INDEX idx_newsletter_feedback_newsletter_id ON newsletter_feedback(newsletter_id);
CREATE INDEX idx_newsletter_feedback_user_id ON newsletter_feedback(user_id);
CREATE INDEX idx_newsletter_feedback_feedback_type ON newsletter_feedback(feedback_type);
CREATE INDEX idx_newsletter_feedback_created_at ON newsletter_feedback(created_at);

-- Comments for newsletter_feedback
COMMENT ON TABLE newsletter_feedback IS 'User feedback on newsletters (thumbs up/down with optional comment)';
COMMENT ON COLUMN newsletter_feedback.feedback_type IS 'Binary feedback: thumbs_up or thumbs_down';
COMMENT ON COLUMN newsletter_feedback.comment IS 'Optional comment (max 500 characters)';
COMMENT ON COLUMN newsletter_feedback.detailed_feedback IS 'JSONB for structured feedback (difficulty, length, etc.)';

-- =============================================================================
-- 8. USER_PREFERENCES TABLE
-- User preferences for newsletter delivery and content
-- =============================================================================
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Delivery preferences
    send_frequency TEXT NOT NULL DEFAULT 'on_demand', -- 'on_demand', 'daily', 'weekly', 'bi_weekly'
    preferred_send_time TIME, -- Preferred time of day for scheduled newsletters
    preferred_send_day INTEGER, -- Day of week (0-6, 0=Sunday) for weekly newsletters

    -- Content preferences
    preferred_difficulty TEXT NOT NULL DEFAULT 'intermediate', -- 'beginner', 'intermediate', 'advanced'
    preferred_length TEXT NOT NULL DEFAULT 'medium', -- 'short' (3min), 'medium' (5-10min), 'long' (15min+)

    -- Source preferences
    source_whitelist JSONB DEFAULT '[]'::JSONB, -- Array of preferred sources/domains
    source_blacklist JSONB DEFAULT '[]'::JSONB, -- Array of blocked sources/domains

    -- Email preferences
    email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    digest_mode BOOLEAN NOT NULL DEFAULT FALSE, -- Combine multiple topics into one email

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Additional preferences
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Ensure one preference row per user
    CONSTRAINT user_preferences_unique_user UNIQUE (user_id),
    CONSTRAINT user_preferences_send_frequency_check CHECK (
        send_frequency IN ('on_demand', 'daily', 'weekly', 'bi_weekly')
    ),
    CONSTRAINT user_preferences_difficulty_check CHECK (
        preferred_difficulty IN ('beginner', 'intermediate', 'advanced')
    ),
    CONSTRAINT user_preferences_length_check CHECK (
        preferred_length IN ('short', 'medium', 'long')
    ),
    CONSTRAINT user_preferences_send_day_check CHECK (
        preferred_send_day IS NULL OR (preferred_send_day >= 0 AND preferred_send_day <= 6)
    )
);

-- Indexes for user_preferences
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_send_frequency ON user_preferences(send_frequency);
CREATE INDEX idx_user_preferences_email_enabled ON user_preferences(email_enabled);

-- Comments for user_preferences
COMMENT ON TABLE user_preferences IS 'User preferences for newsletter scheduling, difficulty, length, and source filtering';
COMMENT ON COLUMN user_preferences.send_frequency IS 'Delivery frequency: on_demand, daily, weekly, bi_weekly';
COMMENT ON COLUMN user_preferences.preferred_difficulty IS 'Content difficulty: beginner, intermediate, advanced';
COMMENT ON COLUMN user_preferences.preferred_length IS 'Article length: short (3min), medium (5-10min), long (15min+)';
COMMENT ON COLUMN user_preferences.source_whitelist IS 'JSONB array of preferred sources/domains';
COMMENT ON COLUMN user_preferences.source_blacklist IS 'JSONB array of blocked sources/domains';

-- =============================================================================
-- 9. EMAIL_EVENTS TABLE
-- Email tracking (open, click, bounce, etc.)
-- =============================================================================
CREATE TABLE email_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Event details
    event_type TEXT NOT NULL, -- 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained', 'unsubscribed'

    -- Event metadata
    email_provider TEXT, -- Provider that sent the email (e.g., 'resend', 'sendgrid')
    email_provider_id TEXT, -- External email ID from provider

    -- Click tracking
    clicked_url TEXT, -- URL that was clicked (for 'clicked' events)

    -- User agent and location
    user_agent TEXT,
    ip_address INET,

    -- Event timestamp
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Additional metadata
    metadata JSONB DEFAULT '{}'::JSONB,

    CONSTRAINT email_events_type_check CHECK (
        event_type IN ('sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained', 'unsubscribed')
    )
);

-- Indexes for email_events
CREATE INDEX idx_email_events_newsletter_id ON email_events(newsletter_id);
CREATE INDEX idx_email_events_user_id ON email_events(user_id);
CREATE INDEX idx_email_events_event_type ON email_events(event_type);
CREATE INDEX idx_email_events_event_timestamp ON email_events(event_timestamp);
CREATE INDEX idx_email_events_email_provider_id ON email_events(email_provider_id);
CREATE INDEX idx_email_events_user_id_event_type ON email_events(user_id, event_type);

-- Comments for email_events
COMMENT ON TABLE email_events IS 'Email tracking events (sent, delivered, opened, clicked, bounced, etc.)';
COMMENT ON COLUMN email_events.event_type IS 'Event type: sent, delivered, opened, clicked, bounced, complained, unsubscribed';
COMMENT ON COLUMN email_events.email_provider_id IS 'External email ID from email service provider';
COMMENT ON COLUMN email_events.clicked_url IS 'URL that was clicked (for clicked events)';

-- =============================================================================
-- 10. AUDIT_LOGS TABLE
-- Audit trail for compliance and debugging
-- =============================================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Actor (who performed the action)
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- NULL for system actions
    actor_type TEXT NOT NULL, -- 'user', 'system', 'admin'

    -- Action details
    action TEXT NOT NULL, -- 'create', 'update', 'delete', 'login', 'logout', etc.
    resource_type TEXT NOT NULL, -- 'user', 'topic', 'newsletter', etc.
    resource_id UUID, -- ID of the affected resource

    -- Changes (for update actions)
    old_values JSONB,
    new_values JSONB,

    -- Context
    ip_address INET,
    user_agent TEXT,

    -- Timestamp (no updated_at for audit logs - they are immutable)
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Additional metadata
    metadata JSONB DEFAULT '{}'::JSONB,

    CONSTRAINT audit_logs_actor_type_check CHECK (
        actor_type IN ('user', 'system', 'admin')
    )
);

-- Indexes for audit_logs
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_actor_type ON audit_logs(actor_type);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_user_id_timestamp ON audit_logs(user_id, timestamp DESC);

-- Comments for audit_logs
COMMENT ON TABLE audit_logs IS 'Immutable audit trail for compliance and debugging';
COMMENT ON COLUMN audit_logs.actor_type IS 'Type of actor: user, system, admin';
COMMENT ON COLUMN audit_logs.action IS 'Action performed: create, update, delete, login, logout, etc.';
COMMENT ON COLUMN audit_logs.old_values IS 'JSONB snapshot of values before update';
COMMENT ON COLUMN audit_logs.new_values IS 'JSONB snapshot of values after update';

-- =============================================================================
-- TRIGGERS
-- Auto-update updated_at timestamps
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_topics_updated_at
    BEFORE UPDATE ON user_topics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_personalization_questions_updated_at
    BEFORE UPDATE ON personalization_questions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_answers_updated_at
    BEFORE UPDATE ON user_answers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_newsletter_requests_updated_at
    BEFORE UPDATE ON newsletter_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_newsletters_updated_at
    BEFORE UPDATE ON newsletters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_newsletter_feedback_updated_at
    BEFORE UPDATE ON newsletter_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Enable RLS for all tables to ensure data security
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE personalization_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletters ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- RLS POLICIES
-- Users can only access their own data
-- =============================================================================

-- Users table policies
CREATE POLICY "Users can view their own profile"
    ON users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- User topics policies
CREATE POLICY "Users can view their own topics"
    ON user_topics FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own topics"
    ON user_topics FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own topics"
    ON user_topics FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own topics"
    ON user_topics FOR DELETE
    USING (auth.uid() = user_id);

-- Personalization questions policies
CREATE POLICY "Users can view questions for their topics"
    ON personalization_questions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_topics
            WHERE user_topics.id = personalization_questions.topic_id
            AND user_topics.user_id = auth.uid()
        )
    );

-- User answers policies
CREATE POLICY "Users can view their own answers"
    ON user_answers FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own answers"
    ON user_answers FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own answers"
    ON user_answers FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own answers"
    ON user_answers FOR DELETE
    USING (auth.uid() = user_id);

-- Newsletter requests policies
CREATE POLICY "Users can view their own newsletter requests"
    ON newsletter_requests FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own newsletter requests"
    ON newsletter_requests FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Newsletters policies
CREATE POLICY "Users can view their own newsletters"
    ON newsletters FOR SELECT
    USING (auth.uid() = user_id);

-- Newsletter feedback policies
CREATE POLICY "Users can view their own feedback"
    ON newsletter_feedback FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own feedback"
    ON newsletter_feedback FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own feedback"
    ON newsletter_feedback FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own feedback"
    ON newsletter_feedback FOR DELETE
    USING (auth.uid() = user_id);

-- User preferences policies
CREATE POLICY "Users can view their own preferences"
    ON user_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own preferences"
    ON user_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON user_preferences FOR UPDATE
    USING (auth.uid() = user_id);

-- Email events policies (read-only for users)
CREATE POLICY "Users can view their own email events"
    ON email_events FOR SELECT
    USING (auth.uid() = user_id);

-- Audit logs policies (read-only for users)
CREATE POLICY "Users can view their own audit logs"
    ON audit_logs FOR SELECT
    USING (auth.uid() = user_id);

-- =============================================================================
-- HELPFUL VIEWS
-- Create views for common queries
-- =============================================================================

-- View: Active topics with latest newsletter
CREATE VIEW active_topics_with_latest_newsletter AS
SELECT
    ut.id AS topic_id,
    ut.user_id,
    ut.topic_text,
    ut.topic_description,
    ut.created_at AS topic_created_at,
    n.id AS latest_newsletter_id,
    n.title AS latest_newsletter_title,
    n.published_at AS latest_newsletter_published_at,
    n.email_sent_at AS latest_newsletter_sent_at
FROM user_topics ut
LEFT JOIN LATERAL (
    SELECT id, title, published_at, email_sent_at
    FROM newsletters
    WHERE newsletters.topic_id = ut.id
    AND newsletters.is_published = true
    ORDER BY published_at DESC
    LIMIT 1
) n ON true
WHERE ut.is_active = true;

COMMENT ON VIEW active_topics_with_latest_newsletter IS 'Active topics with their most recent published newsletter';

-- View: Newsletter engagement metrics
CREATE VIEW newsletter_engagement_metrics AS
SELECT
    n.id AS newsletter_id,
    n.user_id,
    n.topic_id,
    n.title,
    n.published_at,
    n.email_sent_at,
    COUNT(DISTINCT CASE WHEN ee.event_type = 'opened' THEN ee.id END) AS open_count,
    COUNT(DISTINCT CASE WHEN ee.event_type = 'clicked' THEN ee.id END) AS click_count,
    COUNT(DISTINCT CASE WHEN ee.event_type = 'bounced' THEN ee.id END) AS bounce_count,
    nf.feedback_type,
    nf.comment AS feedback_comment
FROM newsletters n
LEFT JOIN email_events ee ON ee.newsletter_id = n.id
LEFT JOIN newsletter_feedback nf ON nf.newsletter_id = n.id
WHERE n.is_published = true
GROUP BY n.id, n.user_id, n.topic_id, n.title, n.published_at, n.email_sent_at, nf.feedback_type, nf.comment;

COMMENT ON VIEW newsletter_engagement_metrics IS 'Newsletter engagement metrics (opens, clicks, bounces, feedback)';

-- =============================================================================
-- INITIAL DATA
-- Insert default preferences for demonstration
-- =============================================================================

-- Note: Default user preferences will be inserted via application logic when user signs up

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Initial schema migration completed successfully';
    RAISE NOTICE 'Created 10 tables: users, user_topics, personalization_questions, user_answers, newsletter_requests, newsletters, newsletter_feedback, user_preferences, email_events, audit_logs';
    RAISE NOTICE 'Created triggers for automatic updated_at timestamp updates';
    RAISE NOTICE 'Enabled Row Level Security (RLS) on all tables';
    RAISE NOTICE 'Created RLS policies for user data isolation';
    RAISE NOTICE 'Created helpful views for common queries';
END $$;
