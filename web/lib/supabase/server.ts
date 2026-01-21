import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { env } from '@/lib/env';

/**
 * Creates a Supabase client for use in Server Components and Server Actions
 * This client runs on the server and manages auth cookies properly
 *
 * Usage in Server Components:
 * ```tsx
 * import { createClient } from '@/lib/supabase/server'
 *
 * export default async function MyPage() {
 *   const supabase = await createClient()
 *   const { data } = await supabase.from('table').select()
 *   // Use data...
 * }
 * ```
 *
 * Usage in Server Actions:
 * ```tsx
 * 'use server'
 * import { createClient } from '@/lib/supabase/server'
 *
 * export async function myAction() {
 *   const supabase = await createClient()
 *   // Perform action...
 * }
 * ```
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          } catch {
            // Cookie setting can fail in Server Components
            // This is expected when rendering pages
            // Middleware will handle the cookie refresh
          }
        },
      },
    }
  );
}

/**
 * Creates a Supabase admin client with service role key
 * Use with caution - bypasses Row Level Security
 *
 * Usage:
 * ```tsx
 * import { createAdminClient } from '@/lib/supabase/server'
 *
 * export async function adminAction() {
 *   const supabase = createAdminClient()
 *   // Perform admin action...
 * }
 * ```
 */
export function createAdminClient() {
  return createServerClient(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.SUPABASE_SERVICE_ROLE_KEY,
    {
      cookies: {
        getAll() {
          return [];
        },
        setAll() {
          // No-op for admin client
        },
      },
    }
  );
}
