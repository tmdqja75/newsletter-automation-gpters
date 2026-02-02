declare global {
  namespace NodeJS {
    interface ProcessEnv {
      // Server-only
      SUPABASE_SERVICE_ROLE_KEY: string;
      RESEND_API_KEY: string;
      API_SECRET_KEY: string;

      // Client-exposed
      NEXT_PUBLIC_SUPABASE_URL: string;
      NEXT_PUBLIC_SUPABASE_ANON_KEY: string;
      NEXT_PUBLIC_SITE_URL?: string;

      // Node.js
      NODE_ENV: 'development' | 'production' | 'test';
    }
  }
}

export {};
