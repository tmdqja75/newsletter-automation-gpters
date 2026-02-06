import { describe, it, expect, beforeEach, vi } from 'vitest';
import { sendUnsentNewsletter } from '@/lib/email/send-newsletter';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------
const mockFrom = vi.fn();
const mockGetUserById = vi.fn();

vi.mock('@/lib/supabase/server', () => ({
  createAdminClient: vi.fn(() => ({
    from: mockFrom,
    auth: { admin: { getUserById: mockGetUserById } },
  })),
}));

const mockSendNewsletterEmail = vi.fn();
vi.mock('@/lib/email/resend', () => ({
  sendNewsletterEmail: (...args: unknown[]) => mockSendNewsletterEmail(...args),
}));

vi.mock('@/lib/env', () => ({
  env: {
    NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: 'anon-key',
    SUPABASE_SERVICE_ROLE_KEY: 'service-key',
    RESEND_API_KEY: 'resend-key',
    API_SECRET_KEY: 'a'.repeat(32),
    NEXT_PUBLIC_SITE_URL: 'http://localhost:3000',
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const NEWSLETTER_ID = 'nl-1';
const USER_ID = 'user-1';
const USER_EMAIL = 'user@example.com';
const TOPIC_TEXT = 'AI 에이전트';

/** Returns a newsletter row with sane defaults. */
function makeNewsletter(overrides: Record<string, unknown> = {}) {
  return {
    id: NEWSLETTER_ID,
    user_id: USER_ID,
    topic_id: 'topic-1',
    email_sent_at: null,
    user_topics: {
      topic_text: TOPIC_TEXT,
      created_at: new Date().toISOString(), // now → well within 4-week window
    },
    ...overrides,
  };
}

/**
 * Wire up mockFrom so that:
 *   call 1 (.from('newsletters').select...single) → { data: newsletter, error }
 *   call 2+ (.from('newsletters').update / .from('email_events').insert) → { error: null }
 */
function mockNewsletterQuery(
  newsletter: ReturnType<typeof makeNewsletter> | null,
  error: unknown = null
) {
  let callCount = 0;
  mockFrom.mockImplementation(() => {
    callCount++;
    if (callCount === 1) {
      // newsletters SELECT … single
      return {
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            single: vi.fn().mockResolvedValue({
              data: newsletter,
              error,
            }),
          }),
        }),
      };
    }
    // newsletters UPDATE or email_events INSERT
    return {
      update: vi.fn().mockReturnValue({
        eq: vi.fn().mockResolvedValue({ error: null }),
      }),
      insert: vi.fn().mockResolvedValue({ error: null }),
    };
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('sendUnsentNewsletter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('successfully sends email and updates email_sent_at', async () => {
    mockNewsletterQuery(makeNewsletter());
    mockGetUserById.mockResolvedValue({
      data: { user: { email: USER_EMAIL } },
      error: null,
    });
    mockSendNewsletterEmail.mockResolvedValue({ success: true, id: 'email-1' });

    const result = await sendUnsentNewsletter(NEWSLETTER_ID);

    expect(result).toEqual({ success: true, emailId: 'email-1' });
    expect(mockSendNewsletterEmail).toHaveBeenCalledWith({
      userEmail: USER_EMAIL,
      topic: TOPIC_TEXT,
      newsletterId: NEWSLETTER_ID,
      newsletterUrl: `http://localhost:3000/newsletter/${NEWSLETTER_ID}`,
    });
  });

  it('returns alreadySent when email_sent_at is set', async () => {
    mockNewsletterQuery(
      makeNewsletter({ email_sent_at: '2026-01-01T00:00:00.000Z' })
    );

    const result = await sendUnsentNewsletter(NEWSLETTER_ID);

    expect(result).toEqual({ success: false, alreadySent: true });
    expect(mockSendNewsletterEmail).not.toHaveBeenCalled();
  });

  it('returns error when newsletter not found', async () => {
    mockNewsletterQuery(null);

    const result = await sendUnsentNewsletter(NEWSLETTER_ID);

    expect(result).toEqual({ success: false, error: 'Newsletter not found' });
    expect(mockSendNewsletterEmail).not.toHaveBeenCalled();
  });

  it('returns error when user email lookup fails', async () => {
    mockNewsletterQuery(makeNewsletter());
    mockGetUserById.mockResolvedValue({
      data: { user: null },
      error: { message: 'User not found' },
    });

    const result = await sendUnsentNewsletter(NEWSLETTER_ID);

    expect(result).toEqual({
      success: false,
      error: 'Failed to fetch user email',
    });
    expect(mockSendNewsletterEmail).not.toHaveBeenCalled();
  });

  it('returns error when Resend fails and logs failed event', async () => {
    mockNewsletterQuery(makeNewsletter());
    mockGetUserById.mockResolvedValue({
      data: { user: { email: USER_EMAIL } },
      error: null,
    });
    mockSendNewsletterEmail.mockResolvedValue({
      success: false,
      id: '',
      error: 'Resend API error',
    });

    const result = await sendUnsentNewsletter(NEWSLETTER_ID);

    expect(result).toEqual({ success: false, error: 'Resend API error' });

    // Verify the failed event was inserted (second mockFrom call)
    const insertCall = mockFrom.mock.calls.find(
      (call: string[]) => call[0] === 'email_events'
    );
    expect(insertCall).toBeDefined();
  });

  it('skips send when topic exceeds 4-week limit', async () => {
    const fiveWeeksAgo = new Date(
      Date.now() - 5 * 7 * 24 * 60 * 60 * 1000
    ).toISOString();

    mockNewsletterQuery(
      makeNewsletter({
        user_topics: { topic_text: TOPIC_TEXT, created_at: fiveWeeksAgo },
      })
    );

    const result = await sendUnsentNewsletter(NEWSLETTER_ID);

    expect(result).toEqual({
      success: false,
      error: 'Topic exceeded 4-week limit',
    });
    expect(mockSendNewsletterEmail).not.toHaveBeenCalled();
  });

  it('handles DB errors gracefully when newsletter query errors', async () => {
    mockNewsletterQuery(null, { message: 'Connection refused' });

    const result = await sendUnsentNewsletter(NEWSLETTER_ID);

    expect(result).toEqual({ success: false, error: 'Newsletter not found' });
  });
});
