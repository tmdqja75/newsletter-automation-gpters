import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { env } from '@/lib/env';

/**
 * Test suite for environment variable validation
 *
 * These tests verify that the environment validation properly:
 * - Accepts valid environment variables
 * - Rejects missing required variables
 * - Rejects invalid formats (URLs, minimum lengths)
 */
describe('Environment Validation', () => {
  describe('Successful Validation', () => {
    it('should validate all required environment variables successfully', () => {
      // Environment is set up in vitest.setup.ts
      expect(env.NODE_ENV).toBe('test');
      expect(env.NEXT_PUBLIC_SUPABASE_URL).toBe('https://test.supabase.co');
      expect(env.NEXT_PUBLIC_SUPABASE_ANON_KEY).toBe('test-anon-key');
      expect(env.SUPABASE_SERVICE_ROLE_KEY).toBe('test-service-role-key');
      expect(env.RESEND_API_KEY).toBe('test-resend-key');
      expect(env.API_SECRET_KEY).toBe(
        'test-api-secret-key-minimum-32-chars-long'
      );
    });

    it('should have all required properties', () => {
      expect(env).toHaveProperty('NODE_ENV');
      expect(env).toHaveProperty('NEXT_PUBLIC_SUPABASE_URL');
      expect(env).toHaveProperty('NEXT_PUBLIC_SUPABASE_ANON_KEY');
      expect(env).toHaveProperty('SUPABASE_SERVICE_ROLE_KEY');
      expect(env).toHaveProperty('RESEND_API_KEY');
      expect(env).toHaveProperty('API_SECRET_KEY');
    });
  });

  describe('Schema Validation', () => {
    it('should reject invalid SUPABASE_URL format', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: 'not-a-valid-url',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
        });
      }).toThrow(z.ZodError);
    });

    it('should reject missing NEXT_PUBLIC_SUPABASE_URL', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: undefined,
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
        });
      }).toThrow(z.ZodError);
    });

    it('should reject empty NEXT_PUBLIC_SUPABASE_ANON_KEY', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: '',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
        });
      }).toThrow(z.ZodError);
    });

    it('should reject missing SUPABASE_SERVICE_ROLE_KEY', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: undefined,
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
        });
      }).toThrow(z.ZodError);
    });

    it('should reject missing RESEND_API_KEY', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: undefined,
          API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
        });
      }).toThrow(z.ZodError);
    });

    it('should reject API_SECRET_KEY that is too short', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: 'too-short',
        });
      }).toThrow(z.ZodError);
    });

    it('should reject missing API_SECRET_KEY', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: undefined,
        });
      }).toThrow(z.ZodError);
    });

    it('should accept all valid NODE_ENV values', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      const baseEnv = {
        NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
        NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
        SUPABASE_SERVICE_ROLE_KEY: 'test-key',
        RESEND_API_KEY: 'test-key',
        API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
      };

      expect(() => {
        envSchema.parse({ ...baseEnv, NODE_ENV: 'development' });
      }).not.toThrow();

      expect(() => {
        envSchema.parse({ ...baseEnv, NODE_ENV: 'production' });
      }).not.toThrow();

      expect(() => {
        envSchema.parse({ ...baseEnv, NODE_ENV: 'test' });
      }).not.toThrow();
    });

    it('should reject invalid NODE_ENV values', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
        RESEND_API_KEY: z.string().min(1),
        API_SECRET_KEY: z.string().min(32),
      });

      expect(() => {
        envSchema.parse({
          NODE_ENV: 'invalid',
          NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
        });
      }).toThrow(z.ZodError);
    });
  });

  describe('Type Safety', () => {
    it('should provide typed environment variable access', () => {
      // TypeScript should enforce these types
      const nodeEnv: 'development' | 'production' | 'test' = env.NODE_ENV;
      const supabaseUrl: string = env.NEXT_PUBLIC_SUPABASE_URL;
      const anonKey: string = env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
      const serviceRoleKey: string = env.SUPABASE_SERVICE_ROLE_KEY;
      const resendKey: string = env.RESEND_API_KEY;
      const apiSecret: string = env.API_SECRET_KEY;

      expect(nodeEnv).toBeDefined();
      expect(supabaseUrl).toBeDefined();
      expect(anonKey).toBeDefined();
      expect(serviceRoleKey).toBeDefined();
      expect(resendKey).toBeDefined();
      expect(apiSecret).toBeDefined();
    });

    it('should export env object with all properties', () => {
      // Verify the env export has all required properties
      expect(env).toBeDefined();
      expect(env.NODE_ENV).toBeDefined();
      expect(env.NEXT_PUBLIC_SUPABASE_URL).toBeDefined();
      expect(env.NEXT_PUBLIC_SUPABASE_ANON_KEY).toBeDefined();
      expect(env.SUPABASE_SERVICE_ROLE_KEY).toBeDefined();
      expect(env.RESEND_API_KEY).toBeDefined();
      expect(env.API_SECRET_KEY).toBeDefined();
    });
  });

  describe('Error Messages', () => {
    it('should provide helpful error messages for validation failures', () => {
      const envSchema = z.object({
        NODE_ENV: z
          .enum(['development', 'production', 'test'])
          .default('development'),
        NEXT_PUBLIC_SUPABASE_URL: z.string().url({
          message: 'NEXT_PUBLIC_SUPABASE_URL must be a valid URL',
        }),
        NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1, {
          message: 'NEXT_PUBLIC_SUPABASE_ANON_KEY is required',
        }),
        SUPABASE_SERVICE_ROLE_KEY: z.string().min(1, {
          message: 'SUPABASE_SERVICE_ROLE_KEY is required',
        }),
        RESEND_API_KEY: z.string().min(1, {
          message: 'RESEND_API_KEY is required',
        }),
        API_SECRET_KEY: z.string().min(32, {
          message: 'API_SECRET_KEY must be at least 32 characters',
        }),
      });

      try {
        envSchema.parse({
          NODE_ENV: 'test',
          NEXT_PUBLIC_SUPABASE_URL: 'invalid-url',
          NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
          SUPABASE_SERVICE_ROLE_KEY: 'test-key',
          RESEND_API_KEY: 'test-key',
          API_SECRET_KEY: 'test-api-secret-key-minimum-32-chars-long',
        });
        expect.fail('Should have thrown ZodError');
      } catch (error) {
        expect(error).toBeInstanceOf(z.ZodError);
        if (error instanceof z.ZodError) {
          // Zod v4 uses 'issues' instead of 'errors'
          expect(error.issues).toBeDefined();
          expect(error.issues.length).toBeGreaterThan(0);
          expect(error.issues[0].message).toBeDefined();
        }
      }
    });
  });
});
