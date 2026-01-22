import { z } from 'zod';

/**
 * Environment variable validation schema
 * Based on env.d.ts declarations
 */
const envSchema = z.object({
  // Node environment
  NODE_ENV: z
    .enum(['development', 'production', 'test'])
    .default('development'),

  // Supabase (client-side)
  NEXT_PUBLIC_SUPABASE_URL: z.string().url({
    message: 'NEXT_PUBLIC_SUPABASE_URL must be a valid URL',
  }),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1, {
    message: 'NEXT_PUBLIC_SUPABASE_ANON_KEY is required',
  }),

  // Supabase (server-side)
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1, {
    message: 'SUPABASE_SERVICE_ROLE_KEY is required',
  }),

  // Email service
  RESEND_API_KEY: z.string().min(1, {
    message: 'RESEND_API_KEY is required',
  }),

  // Internal API secret
  API_SECRET_KEY: z.string().min(32, {
    message: 'API_SECRET_KEY must be at least 32 characters',
  }),
});

/**
 * Validates and returns typed environment variables
 * Throws error if validation fails
 */
function validateEnv() {
  try {
    const parsed = envSchema.parse({
      NODE_ENV: process.env.NODE_ENV,
      NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
      NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
      SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY,
      RESEND_API_KEY: process.env.RESEND_API_KEY,
      API_SECRET_KEY: process.env.API_SECRET_KEY,
    });

    return parsed;
  } catch (error) {
    if (error instanceof z.ZodError) {
      const missingVars = error.issues
        ? error.issues.map((err) => err.path.join('.')).join(', ')
        : 'unknown';
      throw new Error(
        `Environment validation failed. Missing or invalid variables: ${missingVars}\n\n` +
          `Please check your .env.local file and ensure all required variables are set.\n` +
          `See web/.env.example for reference.`
      );
    }
    throw error;
  }
}

/**
 * Validated environment variables
 * Use this instead of process.env for type safety
 */
export const env = validateEnv();

/**
 * Type-safe environment variable access
 */
export type Env = z.infer<typeof envSchema>;
