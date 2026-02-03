import { describe, it, expect, beforeEach, vi } from 'vitest';
import { GET } from '@/app/api/cron/send-newsletters/route';

const mockFrom = vi.fn();

vi.mock('@/lib/supabase/server', () => ({
  createAdminClient: vi.fn(() => ({
    from: mockFrom,
  })),
}));

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

vi.stubEnv('CRON_SECRET', 'test-cron-secret');
vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');

describe('GET /api/cron/send-newsletters', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const makeRequest = (authToken?: string) =>
    new Request('http://localhost:3000/api/cron/send-newsletters', {
      method: 'GET',
      headers: authToken
        ? { authorization: `Bearer ${authToken}` }
        : {},
    });

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

  it('should return message when no users are scheduled for tomorrow', async () => {
    mockFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockResolvedValue({
              data: [],
              error: null,
            }),
          }),
        }),
      }),
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.message).toBe('No users scheduled for tomorrow');
  });

  it('should return 500 when fetching preferences fails', async () => {
    mockFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            eq: vi.fn().mockResolvedValue({
              data: null,
              error: { message: 'DB error' },
            }),
          }),
        }),
      }),
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
      if (callCount === 1) {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                eq: vi.fn().mockResolvedValue({
                  data: [{ user_id: 'user-1' }],
                  error: null,
                }),
              }),
            }),
          }),
        };
      }
      return {
        select: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            eq: vi.fn().mockResolvedValue({
              data: [],
              error: null,
            }),
          }),
        }),
      };
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.message).toBe('No active topics found');
  });

  it('should trigger generation for each topic and return results', async () => {
    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                eq: vi.fn().mockResolvedValue({
                  data: [{ user_id: 'user-1' }, { user_id: 'user-2' }],
                  error: null,
                }),
              }),
            }),
          }),
        };
      }
      return {
        select: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            eq: vi.fn().mockResolvedValue({
              data: [
                { id: 'topic-1', user_id: 'user-1' },
                { id: 'topic-2', user_id: 'user-2' },
              ],
              error: null,
            }),
          }),
        }),
      };
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
      if (callCount === 1) {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                eq: vi.fn().mockResolvedValue({
                  data: [{ user_id: 'user-1' }],
                  error: null,
                }),
              }),
            }),
          }),
        };
      }
      return {
        select: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            eq: vi.fn().mockResolvedValue({
              data: [
                { id: 'topic-ok', user_id: 'user-1' },
                { id: 'topic-fail', user_id: 'user-1' },
              ],
              error: null,
            }),
          }),
        }),
      };
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
      if (callCount === 1) {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                eq: vi.fn().mockResolvedValue({
                  data: [{ user_id: 'user-1' }],
                  error: null,
                }),
              }),
            }),
          }),
        };
      }
      return {
        select: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            eq: vi.fn().mockResolvedValue({
              data: null,
              error: { message: 'Topics DB error' },
            }),
          }),
        }),
      };
    });

    const response = await GET(makeRequest('test-cron-secret'));
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Failed to fetch topics');
  });
});
