import { describe, it, expect, beforeEach, vi } from 'vitest';
import { GET } from '@/app/api/cron/send-newsletters/route';

const mockFrom = vi.fn();

vi.mock('@/lib/supabase/server', () => ({
  createAdminClient: vi.fn(() => ({
    from: mockFrom,
  })),
}));

const mockSendUnsentNewsletter = vi.fn();
vi.mock('@/lib/email/send-newsletter', () => ({
  sendUnsentNewsletter: (...args: unknown[]) =>
    mockSendUnsentNewsletter(...args),
}));

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

vi.stubEnv('CRON_SECRET', 'test-cron-secret');
vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Default Phase-1 mock: no unsent newsletters.
 * Returns the newsletters SELECT chain that resolves to { data: [], error: null }.
 */
function newslettersPhase1(unsent: { id: string }[] = []) {
  return {
    select: vi.fn().mockReturnValue({
      eq: vi.fn().mockReturnValue({
        is: vi.fn().mockResolvedValue({ data: unsent, error: null }),
      }),
    }),
  };
}

/**
 * user_preferences SELECT chain (Phase 2, first query).
 */
function preferencesChain(data: { user_id: string }[] | null, error = null) {
  return {
    select: vi.fn().mockReturnValue({
      eq: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockResolvedValue({ data, error }),
        }),
      }),
    }),
  };
}

/**
 * user_topics SELECT chain (Phase 2, second query).
 */
function topicsChain(
  data: { id: string; user_id: string }[] | null,
  error = null
) {
  return {
    select: vi.fn().mockReturnValue({
      in: vi.fn().mockReturnValue({
        eq: vi.fn().mockResolvedValue({ data, error }),
      }),
    }),
  };
}

describe('GET /api/cron/send-newsletters', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const makeRequest = (authToken?: string) =>
    new Request('http://localhost:3000/api/cron/send-newsletters', {
      method: 'GET',
      headers: authToken ? { authorization: `Bearer ${authToken}` } : {},
    });

  // -----------------------------------------------------------------------
  // Auth guards
  // -----------------------------------------------------------------------
  it('should return 401 without authorization header', async () => {
    const response = await GET(makeRequest());
    const data = await response.json();

    expect(response.status).toBe(401);
    expect(data.error).toBe('Unauthorized');
  });

  it('should return 401 with invalid CRON_SECRET', async () => {
    const response = await GET(makeRequest('wrong-secret'));
    const data = await response.json();

    expect(response.status).toBe(401);
    expect(data.error).toBe('Unauthorized');
  });

  // -----------------------------------------------------------------------
  // Phase 2 – existing scenarios (Phase 1 returns empty unsent list)
  // -----------------------------------------------------------------------
  it('should return message when no users are scheduled for tomorrow', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return newslettersPhase1();
      return preferencesChain([]);
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.message).toBe('No users scheduled for tomorrow');
    expect(data.emails).toEqual({ sent: 0, alreadySent: 0, failed: 0 });
  });

  it('should return 500 when fetching preferences fails', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return newslettersPhase1();
      return preferencesChain(null, { message: 'DB error' });
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Failed to fetch preferences');
  });

  it('should return message when users found but no active topics', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return newslettersPhase1();
      if (callCount === 2) return preferencesChain([{ user_id: 'user-1' }]);
      return topicsChain([]);
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.message).toBe('No active topics found');
    expect(data.emails).toEqual({ sent: 0, alreadySent: 0, failed: 0 });
  });

  it('should trigger generation for each topic and return results', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return newslettersPhase1();
      if (callCount === 2)
        return preferencesChain([{ user_id: 'user-1' }, { user_id: 'user-2' }]);
      return topicsChain([
        { id: 'topic-1', user_id: 'user-1' },
        { id: 'topic-2', user_id: 'user-2' },
      ]);
    });

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ request_id: 'req-1' }),
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.topics_triggered).toBe(2);
    expect(data.fulfilled).toBe(2);
    expect(data.rejected).toBe(0);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/newsletter/generate',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ user_id: 'user-1', topic_id: 'topic-1' }),
      })
    );
  });

  it('should count rejected promises when generation fails for some topics', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return newslettersPhase1();
      if (callCount === 2) return preferencesChain([{ user_id: 'user-1' }]);
      return topicsChain([
        { id: 'topic-ok', user_id: 'user-1' },
        { id: 'topic-fail', user_id: 'user-1' },
      ]);
    });

    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ ok: false, status: 500 });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(data.fulfilled).toBe(1);
    expect(data.rejected).toBe(1);
  });

  it('should return 500 when fetching topics fails', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return newslettersPhase1();
      if (callCount === 2) return preferencesChain([{ user_id: 'user-1' }]);
      return topicsChain(null, { message: 'Topics DB error' });
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Failed to fetch topics');
  });

  // -----------------------------------------------------------------------
  // Phase 1 – send unsent newsletters
  // -----------------------------------------------------------------------
  it('should send unsent newsletters before triggering generation', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1)
        return newslettersPhase1([{ id: 'nl-1' }, { id: 'nl-2' }]);
      // Phase 2: no users scheduled → early return after email phase
      return preferencesChain([]);
    });

    mockSendUnsentNewsletter
      .mockResolvedValueOnce({ success: true, emailId: 'email-1' })
      .mockResolvedValueOnce({ success: true, emailId: 'email-2' });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(mockSendUnsentNewsletter).toHaveBeenCalledTimes(2);
    expect(mockSendUnsentNewsletter).toHaveBeenCalledWith('nl-1');
    expect(mockSendUnsentNewsletter).toHaveBeenCalledWith('nl-2');
    expect(data.emails).toEqual({ sent: 2, alreadySent: 0, failed: 0 });
  });

  it('should skip already-sent newsletters in the send-unsent phase', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1)
        return newslettersPhase1([{ id: 'nl-sent' }, { id: 'nl-new' }]);
      return preferencesChain([]);
    });

    mockSendUnsentNewsletter
      .mockResolvedValueOnce({ success: false, alreadySent: true })
      .mockResolvedValueOnce({ success: true, emailId: 'email-new' });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.emails).toEqual({ sent: 1, alreadySent: 1, failed: 0 });
  });
});
