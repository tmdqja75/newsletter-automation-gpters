import { describe, it, expect, vi, beforeEach } from 'vitest';
import { POST } from '@/app/api/webhooks/resend/route';
import { NextRequest } from 'next/server';

// Mock dependencies
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(),
}));

describe('POST /api/webhooks/resend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should process email.sent event', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockSupabase = {
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  newsletter_id: 'newsletter-123',
                  user_id: 'user-123',
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

    const webhookEvent = {
      type: 'email.sent',
      created_at: '2026-01-01T00:00:00Z',
      data: {
        email_id: 'email-123',
        from: 'newsletter@automata.com',
        to: ['user@example.com'],
        subject: 'Test Newsletter',
        created_at: '2026-01-01T00:00:00Z',
      },
    };

    const request = new NextRequest('https://example.com/api/webhooks/resend', {
      method: 'POST',
      body: JSON.stringify(webhookEvent),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.received).toBe(true);
  });

  it('should process email.opened event', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockSupabase = {
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  newsletter_id: 'newsletter-123',
                  user_id: 'user-123',
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

    const webhookEvent = {
      type: 'email.opened',
      created_at: '2026-01-01T00:00:00Z',
      data: {
        email_id: 'email-123',
        from: 'newsletter@automata.com',
        to: ['user@example.com'],
        subject: 'Test Newsletter',
        created_at: '2026-01-01T00:00:00Z',
      },
    };

    const request = new NextRequest('https://example.com/api/webhooks/resend', {
      method: 'POST',
      body: JSON.stringify(webhookEvent),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.received).toBe(true);
  });

  it('should process email.clicked event with URL', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockInsert = vi.fn().mockResolvedValue({ error: null });
    const mockSupabase = {
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  newsletter_id: 'newsletter-123',
                  user_id: 'user-123',
                },
                error: null,
              }),
            }),
          }),
        }),
        insert: mockInsert,
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const webhookEvent = {
      type: 'email.clicked',
      created_at: '2026-01-01T00:00:00Z',
      data: {
        email_id: 'email-123',
        from: 'newsletter@automata.com',
        to: ['user@example.com'],
        subject: 'Test Newsletter',
        created_at: '2026-01-01T00:00:00Z',
        link: {
          url: 'https://example.com/newsletters/123',
        },
      },
    };

    const request = new NextRequest('https://example.com/api/webhooks/resend', {
      method: 'POST',
      body: JSON.stringify(webhookEvent),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.received).toBe(true);

    // Verify clicked URL was captured
    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: 'clicked',
        clicked_url: 'https://example.com/newsletters/123',
      })
    );
  });

  it('should process email.bounced event', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockInsert = vi.fn().mockResolvedValue({ error: null });
    const mockSupabase = {
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  newsletter_id: 'newsletter-123',
                  user_id: 'user-123',
                },
                error: null,
              }),
            }),
          }),
        }),
        insert: mockInsert,
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const webhookEvent = {
      type: 'email.bounced',
      created_at: '2026-01-01T00:00:00Z',
      data: {
        email_id: 'email-123',
        from: 'newsletter@automata.com',
        to: ['user@example.com'],
        subject: 'Test Newsletter',
        created_at: '2026-01-01T00:00:00Z',
        bounce: {
          type: 'hard',
        },
      },
    };

    const request = new NextRequest('https://example.com/api/webhooks/resend', {
      method: 'POST',
      body: JSON.stringify(webhookEvent),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.received).toBe(true);
  });

  it('should handle missing email event gracefully', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockInsert = vi.fn().mockResolvedValue({ error: null });
    const mockSupabase = {
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
        insert: mockInsert,
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const webhookEvent = {
      type: 'email.delivered',
      created_at: '2026-01-01T00:00:00Z',
      data: {
        email_id: 'unknown-email-123',
        from: 'newsletter@automata.com',
        to: ['user@example.com'],
        subject: 'Test Newsletter',
        created_at: '2026-01-01T00:00:00Z',
      },
    };

    const request = new NextRequest('https://example.com/api/webhooks/resend', {
      method: 'POST',
      body: JSON.stringify(webhookEvent),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.received).toBe(true);

    // Should still insert event but without newsletter/user association
    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: 'delivered',
        email_provider: 'resend',
        email_provider_id: 'unknown-email-123',
      })
    );
  });

  it('should return 500 if insert fails', async () => {
    const { createClient } = await import('@/lib/supabase/server');

    const mockSupabase = {
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: {
                  newsletter_id: 'newsletter-123',
                  user_id: 'user-123',
                },
                error: null,
              }),
            }),
          }),
        }),
        insert: vi.fn().mockResolvedValue({
          error: new Error('Database error'),
        }),
      }),
    };

    (createClient as any).mockResolvedValue(mockSupabase);

    const webhookEvent = {
      type: 'email.sent',
      created_at: '2026-01-01T00:00:00Z',
      data: {
        email_id: 'email-123',
        from: 'newsletter@automata.com',
        to: ['user@example.com'],
        subject: 'Test Newsletter',
        created_at: '2026-01-01T00:00:00Z',
      },
    };

    const request = new NextRequest('https://example.com/api/webhooks/resend', {
      method: 'POST',
      body: JSON.stringify(webhookEvent),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Failed to log event');
  });
});
