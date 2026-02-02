import { describe, it, expect, vi, beforeEach } from 'vitest';
import { POST } from '@/app/api/newsletters/[id]/send/route';
import { NextRequest } from 'next/server';

// Mock dependencies
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(),
}));

vi.mock('@/lib/email/resend', () => ({
  sendNewsletterEmail: vi.fn(),
}));

vi.mock('@/lib/env', () => ({
  env: {
    NEXT_PUBLIC_SITE_URL: 'https://example.com',
  },
}));

describe('POST /api/newsletters/[id]/send', () => {
  const mockNewsletterId = 'newsletter-123';
  const mockUserId = 'user-123';
  const mockUserEmail = 'user@example.com';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should send email successfully', async () => {
    const { createClient } = await import('@/lib/supabase/server');
    const { sendNewsletterEmail } = await import('@/lib/email/resend');

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  id: mockNewsletterId,
                  user_id: mockUserId,
                  topic_id: 'topic-123',
                  title: 'Test Newsletter',
                  body: 'Test content',
                  email_sent_at: null,
                  user_topics: { topic_text: 'AI 에이전트' },
                },
                error: null,
              }),
            }),
          }),
        }),
        update: vi.fn().mockReturnValue({
          eq: vi.fn().mockResolvedValue({ error: null }),
        }),
        insert: vi.fn().mockResolvedValue({ error: null }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);
    (sendNewsletterEmail as any).mockResolvedValue({
      success: true,
      id: 'email-123',
    });

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
    expect(data.emailId).toBe('email-123');
    expect(data.message).toContain('성공적으로 발송');
  });

  it('should return 401 if user is not authenticated', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: null },
          error: new Error('Not authenticated'),
        }),
      },
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(401);
    expect(data.error).toBe('Unauthorized');
  });

  it('should return 404 if newsletter not found', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: null,
                error: new Error('Not found'),
              }),
            }),
          }),
        }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.error).toBe('Not found');
  });

  it('should return 400 if email already sent', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  id: mockNewsletterId,
                  user_id: mockUserId,
                  email_sent_at: '2026-01-01T00:00:00Z',
                  user_topics: { topic_text: 'AI 에이전트' },
                },
                error: null,
              }),
            }),
          }),
        }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.error).toBe('Already sent');
  });

  it('should return 500 if email sending fails', async () => {
    const { createClient } = await import('@/lib/supabase/server');
    const { sendNewsletterEmail } = await import('@/lib/email/resend');

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  id: mockNewsletterId,
                  user_id: mockUserId,
                  email_sent_at: null,
                  user_topics: { topic_text: 'AI 에이전트' },
                },
                error: null,
              }),
            }),
          }),
        }),
        insert: vi.fn().mockResolvedValue({ error: null }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);
    (sendNewsletterEmail as any).mockResolvedValue({
      success: false,
      error: 'API error',
    });

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Email send failed');
  });

  it('should reject if topic is 29 days old (exceeds limit)', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const twentyNineDaysAgo = new Date();
    twentyNineDaysAgo.setDate(twentyNineDaysAgo.getDate() - 29);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  id: mockNewsletterId,
                  user_id: mockUserId,
                  email_sent_at: null,
                  user_topics: {
                    topic_text: 'AI 에이전트',
                    created_at: twentyNineDaysAgo.toISOString(),
                  },
                },
                error: null,
              }),
            }),
          }),
        }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.error).toBe('Time limit exceeded');
    expect(data.message).toContain('4주를 초과');
    expect(data.topicCreatedAt).toBe(twentyNineDaysAgo.toISOString());
    expect(data.daysElapsed).toBe(29);
  });

  it('should allow if topic is exactly 28 days old (boundary)', async () => {
    const { createClient } = await import('@/lib/supabase/server');
    const { sendNewsletterEmail } = await import('@/lib/email/resend');

    const twentyEightDaysAgo = new Date();
    twentyEightDaysAgo.setDate(twentyEightDaysAgo.getDate() - 28);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  id: mockNewsletterId,
                  user_id: mockUserId,
                  email_sent_at: null,
                  user_topics: {
                    topic_text: 'AI 에이전트',
                    created_at: twentyEightDaysAgo.toISOString(),
                  },
                },
                error: null,
              }),
            }),
          }),
        }),
        update: vi.fn().mockReturnValue({
          eq: vi.fn().mockResolvedValue({ error: null }),
        }),
        insert: vi.fn().mockResolvedValue({ error: null }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);
    (sendNewsletterEmail as any).mockResolvedValue({
      success: true,
      id: 'email-123',
    });

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
  });

  it('should allow if topic is 27 days old (within limit)', async () => {
    const { createClient } = await import('@/lib/supabase/server');
    const { sendNewsletterEmail } = await import('@/lib/email/resend');

    const twentySevenDaysAgo = new Date();
    twentySevenDaysAgo.setDate(twentySevenDaysAgo.getDate() - 27);

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  id: mockNewsletterId,
                  user_id: mockUserId,
                  email_sent_at: null,
                  user_topics: {
                    topic_text: 'AI 에이전트',
                    created_at: twentySevenDaysAgo.toISOString(),
                  },
                },
                error: null,
              }),
            }),
          }),
        }),
        update: vi.fn().mockReturnValue({
          eq: vi.fn().mockResolvedValue({ error: null }),
        }),
        insert: vi.fn().mockResolvedValue({ error: null }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);
    (sendNewsletterEmail as any).mockResolvedValue({
      success: true,
      id: 'email-123',
    });

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
  });

  it('should reject if topic is 28 days + 1 second old (just over)', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const twentyEightDaysAndOneSecondAgo = new Date();
    twentyEightDaysAndOneSecondAgo.setDate(
      twentyEightDaysAndOneSecondAgo.getDate() - 28
    );
    twentyEightDaysAndOneSecondAgo.setSeconds(
      twentyEightDaysAndOneSecondAgo.getSeconds() - 1
    );

    const mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: mockUserId, email: mockUserEmail } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  id: mockNewsletterId,
                  user_id: mockUserId,
                  email_sent_at: null,
                  user_topics: {
                    topic_text: 'AI 에이전트',
                    created_at: twentyEightDaysAndOneSecondAgo.toISOString(),
                  },
                },
                error: null,
              }),
            }),
          }),
        }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const request = new NextRequest(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      { method: 'POST' }
    );
    const params = Promise.resolve({ id: mockNewsletterId });

    const response = await POST(request, { params });
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.error).toBe('Time limit exceeded');
    expect(data.message).toContain('4주를 초과');
    expect(data.daysElapsed).toBeGreaterThanOrEqual(28);
  });
});
