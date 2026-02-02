import { beforeEach, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';

/**
 * Reset all mocks before each test
 */
beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Mock Next.js environment
 */
vi.mock('next/headers', () => ({
  cookies: vi.fn(),
}));

/**
 * Setup default environment variables for tests
 */
(process.env as Record<string, string>).NODE_ENV = 'test';
process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test.supabase.co';
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-key';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-service-role-key';
process.env.RESEND_API_KEY = 'test-resend-key';
process.env.API_SECRET_KEY = 'test-api-secret-key-minimum-32-chars-long';
