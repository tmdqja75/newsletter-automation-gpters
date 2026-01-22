import { z } from 'zod';

/**
 * Client-side environment variables (available in browser)
 * These are prefixed with NEXT_PUBLIC_
 */
const clientEnvSchema = z.object({
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
  NEXT_PUBLIC_SITE_URL: z.string().url().optional(),
});

/**
 * Server-side environment variables (only available on server)
 * These should NEVER be exposed to the browser
 */
const serverEnvSchema = z.object({
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
 * Combined schema for server-side (includes both client and server vars)
 */
const envSchema = clientEnvSchema.merge(serverEnvSchema);

/**
 * Validates and returns typed environment variables
 * Throws error if validation fails
 *
 * On the client side (browser), only validates client-side variables.
 * On the server side (Node.js, tests), validates all variables.
 */
function validateEnv() {
  // Determine if server-only vars are available
  // In the browser, Next.js doesn't include server-only env vars in the bundle
  const hasServerVars =
    process.env.SUPABASE_SERVICE_ROLE_KEY !== undefined ||
    process.env.RESEND_API_KEY !== undefined ||
    process.env.API_SECRET_KEY !== undefined;

  try {
    if (hasServerVars) {
      // Server-side or tests: validate all environment variables
      const parsed = envSchema.parse({
        NODE_ENV: process.env.NODE_ENV,
        NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
        NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
        NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
        SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY,
        RESEND_API_KEY: process.env.RESEND_API_KEY,
        API_SECRET_KEY: process.env.API_SECRET_KEY,
      });
      return parsed;
    } else {
      // Client-side (real browser): only validate client-side variables
      const parsed = clientEnvSchema.parse({
        NODE_ENV: process.env.NODE_ENV,
        NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
        NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
        NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
      });
      // Return with server vars as undefined (they shouldn't be accessed on client anyway)
      return parsed as z.infer<typeof envSchema>;
    }
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
