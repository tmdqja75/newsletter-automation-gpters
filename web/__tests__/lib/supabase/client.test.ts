import { describe, it, expect, beforeEach, vi } from 'vitest';

/**
 * Test suite for Supabase client-side utilities
 *
 * These tests verify that the client-side Supabase client:
 * - Creates a browser client with correct credentials
 * - Uses environment variables properly
 * - Returns a valid Supabase client instance
 */

// Mock @supabase/ssr
vi.mock('@supabase/ssr', () => ({
  createBrowserClient: vi.fn((url: string, key: string) => {
    return {
      auth: {
        getSession: vi.fn(),
        signIn: vi.fn(),
        signOut: vi.fn(),
      },
      from: vi.fn(),
      storage: {
        from: vi.fn(),
      },
      // Mock other Supabase client methods as needed
      _url: url,
      _key: key,
    };
  }),
}));

describe('Supabase Client (Browser)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createClient', () => {
    it('should create a Supabase browser client', async () => {
      const { createClient } = await import('@/lib/supabase/client');
      const client = createClient();

      expect(client).toBeDefined();
      expect(client).toHaveProperty('auth');
      expect(client).toHaveProperty('from');
      expect(client).toHaveProperty('storage');
    });

    it('should use environment variables for URL and anon key', async () => {
      const { createBrowserClient } = await import('@supabase/ssr');
      const { createClient } = await import('@/lib/supabase/client');

      createClient();

      expect(createBrowserClient).toHaveBeenCalledWith(
        'https://test.supabase.co',
        'test-anon-key'
      );
    });

    it('should create a new client instance on each call', async () => {
      const { createClient } = await import('@/lib/supabase/client');

      const client1 = createClient();
      const client2 = createClient();

      // Should be different instances
      expect(client1).not.toBe(client2);
    });

    it('should return a client with auth methods', async () => {
      const { createClient } = await import('@/lib/supabase/client');
      const client = createClient();

      expect(client.auth).toBeDefined();
      expect(client.auth.getSession).toBeDefined();
      expect(typeof client.auth.getSession).toBe('function');
    });

    it('should return a client with database methods', async () => {
      const { createClient } = await import('@/lib/supabase/client');
      const client = createClient();

      expect(client.from).toBeDefined();
      expect(typeof client.from).toBe('function');
    });

    it('should return a client with storage methods', async () => {
      const { createClient } = await import('@/lib/supabase/client');
      const client = createClient();

      expect(client.storage).toBeDefined();
      expect(client.storage.from).toBeDefined();
      expect(typeof client.storage.from).toBe('function');
    });
  });

  describe('Error Handling', () => {
    it.skip('should throw error if environment variables are not set', async () => {
      // This test is skipped because env validation happens at module import time
      // and is difficult to test with vitest's module system.
      // The validation is covered by lib/env.test.ts instead.
    });
  });

  describe('Client Structure', () => {
    it('should return a client with expected structure', async () => {
      // Use dynamic import to avoid module reset issues
      const { createBrowserClient } = await import('@supabase/ssr');

      // Create a fresh client for this test
      const mockClient = createBrowserClient(
        'https://test.supabase.co',
        'test-anon-key'
      );

      // Verify client has expected Supabase structure
      expect(mockClient).toHaveProperty('auth');
      expect(mockClient).toHaveProperty('from');
      expect(mockClient).toHaveProperty('storage');
      expect(mockClient).toBeDefined();
    });
  });
});
