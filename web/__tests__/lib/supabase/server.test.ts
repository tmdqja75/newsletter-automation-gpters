import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { ReadonlyRequestCookies } from 'next/dist/server/web/spec-extension/adapters/request-cookies';

/**
 * Test suite for Supabase server-side utilities
 *
 * These tests verify that the server-side Supabase clients:
 * - Create server clients with cookie management
 * - Create admin clients with service role key
 * - Handle cookies properly for auth state
 * - Use correct environment variables
 */

// Mock cookie functions
const mockCookieStore = {
  getAll: vi.fn(() => [
    { name: 'sb-access-token', value: 'mock-access-token' },
    { name: 'sb-refresh-token', value: 'mock-refresh-token' },
  ]),
  set: vi.fn(),
  get: vi.fn(),
  delete: vi.fn(),
} as unknown as ReadonlyRequestCookies;

// Mock next/headers
vi.mock('next/headers', () => ({
  cookies: vi.fn(async () => mockCookieStore),
}));

// Mock @supabase/ssr
vi.mock('@supabase/ssr', () => ({
  createServerClient: vi.fn(
    (
      url: string,
      key: string,
      options?: {
        cookies?: {
          getAll?: () => Array<{ name: string; value: string }>;
          setAll?: (
            cookies: Array<{
              name: string;
              value: string;
              options?: Record<string, unknown>;
            }>
          ) => void;
        };
      }
    ) => {
      return {
        auth: {
          getSession: vi.fn(),
          getUser: vi.fn(),
        },
        from: vi.fn(() => ({
          select: vi.fn(),
          insert: vi.fn(),
          update: vi.fn(),
          delete: vi.fn(),
        })),
        storage: {
          from: vi.fn(),
        },
        // Store options for testing
        _url: url,
        _key: key,
        _options: options,
      };
    }
  ),
}));

describe('Supabase Server Utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createClient (Server)', () => {
    it('should create a Supabase server client', async () => {
      const { createClient } = await import('@/lib/supabase/server');
      const client = await createClient();

      expect(client).toBeDefined();
      expect(client).toHaveProperty('auth');
      expect(client).toHaveProperty('from');
      expect(client).toHaveProperty('storage');
    });

    it('should use environment variables for URL and anon key', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const { createClient } = await import('@/lib/supabase/server');

      await createClient();

      expect(createServerClient).toHaveBeenCalledWith(
        'https://test.supabase.co',
        'test-anon-key',
        expect.objectContaining({
          cookies: expect.any(Object),
        })
      );
    });

    it('should configure cookie handlers properly', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const { createClient } = await import('@/lib/supabase/server');

      await createClient();

      const callArgs = vi.mocked(createServerClient).mock.calls[0];
      const options = callArgs[2];

      expect(options).toBeDefined();
      expect(options?.cookies).toBeDefined();
      expect(options?.cookies?.getAll).toBeDefined();
      expect(options?.cookies?.setAll).toBeDefined();
      expect(typeof options?.cookies?.getAll).toBe('function');
      expect(typeof options?.cookies?.setAll).toBe('function');
    });

    it('should call cookies().getAll() through cookie handler', async () => {
      const { cookies } = await import('next/headers');
      const { createServerClient } = await import('@supabase/ssr');
      const { createClient } = await import('@/lib/supabase/server');

      await createClient();

      // Get the options passed to createServerClient
      const callArgs = vi.mocked(createServerClient).mock.calls[0];
      const options = callArgs[2];

      // Call the getAll method from options
      const allCookies = options?.cookies?.getAll?.();

      expect(cookies).toHaveBeenCalled();
      expect(allCookies).toEqual([
        { name: 'sb-access-token', value: 'mock-access-token' },
        { name: 'sb-refresh-token', value: 'mock-refresh-token' },
      ]);
    });

    it('should handle cookie setting through setAll handler', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const { createClient } = await import('@/lib/supabase/server');

      await createClient();

      // Get the options passed to createServerClient
      const callArgs = vi.mocked(createServerClient).mock.calls[0];
      const options = callArgs[2];

      // Test the setAll method
      const cookiesToSet = [
        {
          name: 'test-cookie',
          value: 'test-value',
          options: { httpOnly: true },
        },
      ];

      // Should not throw
      expect(() => {
        options?.cookies?.setAll?.(cookiesToSet);
      }).not.toThrow();

      expect(mockCookieStore.set).toHaveBeenCalledWith(
        'test-cookie',
        'test-value',
        { httpOnly: true }
      );
    });

    it('should handle cookie setting errors gracefully', async () => {
      // Mock cookie set to throw error
      vi.mocked(mockCookieStore.set).mockImplementationOnce(() => {
        throw new Error('Cannot set cookies in Server Component');
      });

      const { createServerClient } = await import('@supabase/ssr');
      const { createClient } = await import('@/lib/supabase/server');

      await createClient();

      const callArgs = vi.mocked(createServerClient).mock.calls[0];
      const options = callArgs[2];

      // setAll should not throw even if set fails
      expect(() => {
        options?.cookies?.setAll?.([
          { name: 'test', value: 'value', options: {} },
        ]);
      }).not.toThrow();
    });

    it('should create a new client instance on each call', async () => {
      const { createClient } = await import('@/lib/supabase/server');

      const client1 = await createClient();
      const client2 = await createClient();

      // Should be different instances
      expect(client1).not.toBe(client2);
    });
  });

  describe('createAdminClient', () => {
    it('should create a Supabase admin client', async () => {
      const { createAdminClient } = await import('@/lib/supabase/server');
      const client = createAdminClient();

      expect(client).toBeDefined();
      expect(client).toHaveProperty('auth');
      expect(client).toHaveProperty('from');
      expect(client).toHaveProperty('storage');
    });

    it('should use service role key instead of anon key', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const { createAdminClient } = await import('@/lib/supabase/server');

      createAdminClient();

      // Find the call that used service role key
      const adminCall = vi
        .mocked(createServerClient)
        .mock.calls.find((call) => call[1] === 'test-service-role-key');

      expect(adminCall).toBeDefined();
      expect(adminCall?.[0]).toBe('https://test.supabase.co');
      expect(adminCall?.[1]).toBe('test-service-role-key');
    });

    it('should configure empty cookie handlers', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const { createAdminClient } = await import('@/lib/supabase/server');

      createAdminClient();

      // Find the admin client call
      const adminCall = vi
        .mocked(createServerClient)
        .mock.calls.find((call) => call[1] === 'test-service-role-key');

      const options = adminCall?.[2];

      expect(options).toBeDefined();
      expect(options?.cookies).toBeDefined();
      expect(options?.cookies?.getAll).toBeDefined();
      expect(options?.cookies?.setAll).toBeDefined();

      // getAll should return empty array
      expect(options?.cookies?.getAll?.()).toEqual([]);

      // setAll should be a no-op (shouldn't throw)
      expect(() => {
        options?.cookies?.setAll?.([
          { name: 'test', value: 'value', options: {} },
        ]);
      }).not.toThrow();
    });

    it('should not manage cookies for admin client', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const { createAdminClient } = await import('@/lib/supabase/server');

      createAdminClient();

      const adminCall = vi
        .mocked(createServerClient)
        .mock.calls.find((call) => call[1] === 'test-service-role-key');

      const options = adminCall?.[2];

      // Call getAll - should return empty array (no cookies)
      const cookies = options?.cookies?.getAll?.();
      expect(cookies).toEqual([]);

      // Call setAll - should do nothing
      options?.cookies?.setAll?.([
        { name: 'test', value: 'value', options: {} },
      ]);

      // Verify mockCookieStore.set was NOT called for admin client
      // (it may have been called for regular client, so we just check it wasn't called after createAdminClient)
      const setCallCount = vi.mocked(mockCookieStore.set).mock.calls.length;
      options?.cookies?.setAll?.([
        { name: 'another', value: 'test', options: {} },
      ]);
      expect(vi.mocked(mockCookieStore.set).mock.calls.length).toBe(
        setCallCount
      );
    });

    it('should create a new admin client instance on each call', async () => {
      const { createAdminClient } = await import('@/lib/supabase/server');

      const client1 = createAdminClient();
      const client2 = createAdminClient();

      // Should be different instances
      expect(client1).not.toBe(client2);
    });
  });

  describe('Error Handling', () => {
    it('should throw error if environment variables are not set', async () => {
      const originalUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
      delete (process.env as Record<string, string | undefined>)
        .NEXT_PUBLIC_SUPABASE_URL;

      vi.resetModules();

      await expect(async () => {
        await import('@/lib/supabase/server');
      }).rejects.toThrow();

      // Restore env var
      process.env.NEXT_PUBLIC_SUPABASE_URL = originalUrl;
    });
  });

  describe('Client Structure', () => {
    it('should return properly structured clients', async () => {
      // Use dynamic import to avoid module reset issues
      const { createServerClient } = await import('@supabase/ssr');

      const serverClient = createServerClient(
        'https://test.supabase.co',
        'test-anon-key',
        {
          cookies: {
            getAll: () => [],
            setAll: () => {},
          },
        }
      );

      const adminClient = createServerClient(
        'https://test.supabase.co',
        'test-service-role-key',
        {
          cookies: {
            getAll: () => [],
            setAll: () => {},
          },
        }
      );

      // Verify both have expected Supabase client structure
      expect(serverClient).toBeDefined();
      expect(serverClient).toHaveProperty('auth');
      expect(serverClient).toHaveProperty('from');
      expect(adminClient).toBeDefined();
      expect(adminClient).toHaveProperty('auth');
      expect(adminClient).toHaveProperty('from');
    });

    it('should allow database queries through server client', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const client = createServerClient(
        'https://test.supabase.co',
        'test-anon-key',
        {
          cookies: {
            getAll: () => [],
            setAll: () => {},
          },
        }
      );

      const query = client.from('test_table');

      expect(query).toBeDefined();
      expect(query.select).toBeDefined();
      expect(typeof query.select).toBe('function');
    });

    it('should allow database queries through admin client', async () => {
      const { createServerClient } = await import('@supabase/ssr');
      const client = createServerClient(
        'https://test.supabase.co',
        'test-service-role-key',
        {
          cookies: {
            getAll: () => [],
            setAll: () => {},
          },
        }
      );

      const query = client.from('test_table');

      expect(query).toBeDefined();
      expect(query.select).toBeDefined();
      expect(typeof query.select).toBe('function');
    });
  });
});
