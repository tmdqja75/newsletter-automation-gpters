import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { SupabaseClient } from '@supabase/supabase-js';

/**
 * Test suite for Auth Server Actions
 *
 * These tests verify that the auth server actions:
 * - Handle successful login and signup flows
 * - Validate user input with proper Korean error messages
 * - Handle Supabase auth errors gracefully
 * - Redirect users appropriately after auth operations
 * - Manage edge cases (duplicate email, unconfirmed email, etc.)
 */

// Mock Supabase client
const mockSupabaseClient = {
  auth: {
    signInWithPassword: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
  },
  from: vi.fn(),
} as unknown as SupabaseClient;

// Mock @/lib/supabase/server
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(async () => mockSupabaseClient),
}));

// Mock next/navigation
const mockRedirect = vi.fn((path: string) => {
  throw new Error(`NEXT_REDIRECT: ${path}`);
});

vi.mock('next/navigation', () => ({
  redirect: mockRedirect,
}));

describe('Auth Server Actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('login()', () => {
    it('should successfully login with valid credentials', async () => {
      // Mock successful login
      vi.mocked(mockSupabaseClient.auth.signInWithPassword).mockResolvedValue({
        data: {
          user: {
            id: 'user-123',
            email: 'test@example.com',
            aud: 'authenticated',
            created_at: '2024-01-01T00:00:00Z',
            app_metadata: {},
            user_metadata: {},
          },
          session: {
            access_token: 'mock-access-token',
            refresh_token: 'mock-refresh-token',
            expires_in: 3600,
            token_type: 'bearer',
            user: {
              id: 'user-123',
              email: 'test@example.com',
              aud: 'authenticated',
              created_at: '2024-01-01T00:00:00Z',
              app_metadata: {},
              user_metadata: {},
            },
          },
        },
        error: null,
      });

      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'password123');

      const { login } = await import('@/lib/actions/auth');

      // Should redirect on success
      await expect(login(formData)).rejects.toThrow('NEXT_REDIRECT: /');

      expect(mockSupabaseClient.auth.signInWithPassword).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
      expect(mockRedirect).toHaveBeenCalledWith('/');
    });

    it('should return error for invalid credentials', async () => {
      // Mock invalid credentials error
      vi.mocked(mockSupabaseClient.auth.signInWithPassword).mockResolvedValue({
        data: { user: null, session: null },
        error: {
          message: 'Invalid login credentials',
          name: 'AuthApiError',
          status: 400,
        },
      });

      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'wrongpassword');

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      expect(result).toEqual({
        success: false,
        message: '이메일 또는 비밀번호가 올바르지 않습니다.',
      });
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for email not confirmed', async () => {
      // Mock email not confirmed error
      vi.mocked(mockSupabaseClient.auth.signInWithPassword).mockResolvedValue({
        data: { user: null, session: null },
        error: {
          message: 'Email not confirmed',
          name: 'AuthApiError',
          status: 400,
        },
      });

      const formData = new FormData();
      formData.append('email', 'unconfirmed@example.com');
      formData.append('password', 'password123');

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      expect(result).toEqual({
        success: false,
        message: '이메일 인증이 완료되지 않았습니다. 이메일을 확인해주세요.',
      });
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for missing email', async () => {
      const formData = new FormData();
      formData.append('email', '');
      formData.append('password', 'password123');

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      expect(result).toEqual({
        success: false,
        message: '이메일을 입력해주세요',
      });
      expect(mockSupabaseClient.auth.signInWithPassword).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for invalid email format', async () => {
      const formData = new FormData();
      formData.append('email', 'invalid-email');
      formData.append('password', 'password123');

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      expect(result).toEqual({
        success: false,
        message: '올바른 이메일 형식이 아닙니다',
      });
      expect(mockSupabaseClient.auth.signInWithPassword).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for missing password', async () => {
      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', '');

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      expect(result).toEqual({
        success: false,
        message: '비밀번호를 입력해주세요',
      });
      expect(mockSupabaseClient.auth.signInWithPassword).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for password shorter than 8 characters', async () => {
      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'short');

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      expect(result).toEqual({
        success: false,
        message: '비밀번호는 최소 8자 이상이어야 합니다',
      });
      expect(mockSupabaseClient.auth.signInWithPassword).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return generic error for unknown auth errors', async () => {
      // Mock unknown error
      vi.mocked(mockSupabaseClient.auth.signInWithPassword).mockResolvedValue({
        data: { user: null, session: null },
        error: {
          message: 'Unknown error occurred',
          name: 'AuthApiError',
          status: 500,
        },
      });

      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'password123');

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      expect(result).toEqual({
        success: false,
        message: '로그인에 실패했습니다. 다시 시도해주세요.',
      });
      expect(mockRedirect).not.toHaveBeenCalled();
    });
  });

  describe('signup()', () => {
    beforeEach(() => {
      // Set default NEXT_PUBLIC_SITE_URL for tests
      process.env.NEXT_PUBLIC_SITE_URL = 'http://localhost:3000';
    });

    it('should successfully signup with valid credentials', async () => {
      // Mock successful signup
      vi.mocked(mockSupabaseClient.auth.signUp).mockResolvedValue({
        data: {
          user: {
            id: 'user-456',
            email: 'newuser@example.com',
            aud: 'authenticated',
            created_at: '2024-01-01T00:00:00Z',
            app_metadata: {},
            user_metadata: {},
          },
          session: null, // No session until email confirmed
        },
        error: null,
      });

      const formData = new FormData();
      formData.append('email', 'newuser@example.com');
      formData.append('password', 'password123');
      formData.append('confirmPassword', 'password123');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: true,
        message:
          '회원가입이 완료되었습니다. 이메일을 확인하여 인증을 완료해주세요.',
      });
      expect(mockSupabaseClient.auth.signUp).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        password: 'password123',
        options: {
          emailRedirectTo: 'http://localhost:3000/api/auth/callback',
        },
      });
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for duplicate email', async () => {
      // Mock duplicate email error
      vi.mocked(mockSupabaseClient.auth.signUp).mockResolvedValue({
        data: { user: null, session: null },
        error: {
          message: 'User already registered',
          name: 'AuthApiError',
          status: 400,
        },
      });

      const formData = new FormData();
      formData.append('email', 'existing@example.com');
      formData.append('password', 'password123');
      formData.append('confirmPassword', 'password123');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '이미 가입된 이메일입니다.',
      });
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for missing email', async () => {
      const formData = new FormData();
      formData.append('email', '');
      formData.append('password', 'password123');
      formData.append('confirmPassword', 'password123');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '이메일을 입력해주세요',
      });
      expect(mockSupabaseClient.auth.signUp).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for invalid email format', async () => {
      const formData = new FormData();
      formData.append('email', 'not-an-email');
      formData.append('password', 'password123');
      formData.append('confirmPassword', 'password123');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '올바른 이메일 형식이 아닙니다',
      });
      expect(mockSupabaseClient.auth.signUp).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for missing password', async () => {
      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', '');
      formData.append('confirmPassword', 'password123');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '비밀번호를 입력해주세요',
      });
      expect(mockSupabaseClient.auth.signUp).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for password shorter than 8 characters', async () => {
      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'short');
      formData.append('confirmPassword', 'short');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '비밀번호는 최소 8자 이상이어야 합니다',
      });
      expect(mockSupabaseClient.auth.signUp).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error for missing confirmPassword', async () => {
      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'password123');
      formData.append('confirmPassword', '');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '비밀번호 확인을 입력해주세요',
      });
      expect(mockSupabaseClient.auth.signUp).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return error when passwords do not match', async () => {
      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'password123');
      formData.append('confirmPassword', 'differentpassword');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '비밀번호가 일치하지 않습니다',
      });
      expect(mockSupabaseClient.auth.signUp).not.toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should return generic error for unknown signup errors', async () => {
      // Mock unknown error
      vi.mocked(mockSupabaseClient.auth.signUp).mockResolvedValue({
        data: { user: null, session: null },
        error: {
          message: 'Internal server error',
          name: 'AuthApiError',
          status: 500,
        },
      });

      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'password123');
      formData.append('confirmPassword', 'password123');

      const { signup } = await import('@/lib/actions/auth');
      const result = await signup(formData);

      expect(result).toEqual({
        success: false,
        message: '회원가입에 실패했습니다. 다시 시도해주세요.',
      });
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should use custom NEXT_PUBLIC_SITE_URL for email redirect', async () => {
      process.env.NEXT_PUBLIC_SITE_URL = 'https://example.com';

      vi.mocked(mockSupabaseClient.auth.signUp).mockResolvedValue({
        data: {
          user: {
            id: 'user-789',
            email: 'test@example.com',
            aud: 'authenticated',
            created_at: '2024-01-01T00:00:00Z',
            app_metadata: {},
            user_metadata: {},
          },
          session: null,
        },
        error: null,
      });

      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'password123');
      formData.append('confirmPassword', 'password123');

      const { signup } = await import('@/lib/actions/auth');
      await signup(formData);

      expect(mockSupabaseClient.auth.signUp).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
        options: {
          emailRedirectTo: 'https://example.com/api/auth/callback',
        },
      });

      // Reset to default
      process.env.NEXT_PUBLIC_SITE_URL = 'http://localhost:3000';
    });
  });

  describe('logout()', () => {
    it('should successfully logout and redirect to home', async () => {
      // Mock successful logout
      vi.mocked(mockSupabaseClient.auth.signOut).mockResolvedValue({
        error: null,
      });

      const { logout } = await import('@/lib/actions/auth');

      // Should redirect on success
      await expect(logout()).rejects.toThrow('NEXT_REDIRECT: /');

      expect(mockSupabaseClient.auth.signOut).toHaveBeenCalled();
      expect(mockRedirect).toHaveBeenCalledWith('/');
    });

    it('should redirect even if logout fails', async () => {
      // Mock logout error
      vi.mocked(mockSupabaseClient.auth.signOut).mockResolvedValue({
        error: {
          message: 'Logout failed',
          name: 'AuthApiError',
          status: 500,
        },
      });

      const { logout } = await import('@/lib/actions/auth');

      // Should still redirect (logout action doesn't check error)
      await expect(logout()).rejects.toThrow('NEXT_REDIRECT: /');

      expect(mockSupabaseClient.auth.signOut).toHaveBeenCalled();
      expect(mockRedirect).toHaveBeenCalledWith('/');
    });
  });

  describe('FormData edge cases', () => {
    it('should handle null values from FormData', async () => {
      const formData = new FormData();
      // Don't append any fields - FormData.get() will return null

      const { login } = await import('@/lib/actions/auth');
      const result = await login(formData);

      // Zod will return an error for null input
      expect(result).toEqual({
        success: false,
        message: 'Invalid input: expected string, received null',
      });
    });

    it('should handle FormData with extra fields', async () => {
      vi.mocked(mockSupabaseClient.auth.signInWithPassword).mockResolvedValue({
        data: {
          user: {
            id: 'user-123',
            email: 'test@example.com',
            aud: 'authenticated',
            created_at: '2024-01-01T00:00:00Z',
            app_metadata: {},
            user_metadata: {},
          },
          session: {
            access_token: 'mock-access-token',
            refresh_token: 'mock-refresh-token',
            expires_in: 3600,
            token_type: 'bearer',
            user: {
              id: 'user-123',
              email: 'test@example.com',
              aud: 'authenticated',
              created_at: '2024-01-01T00:00:00Z',
              app_metadata: {},
              user_metadata: {},
            },
          },
        },
        error: null,
      });

      const formData = new FormData();
      formData.append('email', 'test@example.com');
      formData.append('password', 'password123');
      formData.append('extraField', 'should be ignored');

      const { login } = await import('@/lib/actions/auth');

      await expect(login(formData)).rejects.toThrow('NEXT_REDIRECT: /');

      // Extra field should be ignored
      expect(mockSupabaseClient.auth.signInWithPassword).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });
});
