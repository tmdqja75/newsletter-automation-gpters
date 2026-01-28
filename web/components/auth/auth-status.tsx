'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { logout } from '@/lib/actions/auth';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import type { User } from '@supabase/supabase-js';

export function AuthStatus() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createClient();

    // Get initial session
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"></div>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          로딩 중...
        </span>
      </div>
    );
  }

  if (user) {
    return (
      <div className="flex items-center gap-4">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm">
            대시보드
          </Button>
        </Link>
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {user.email}
        </span>
        <form action={logout}>
          <Button type="submit" variant="outline" size="sm">
            로그아웃
          </Button>
        </form>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Link href="/login">
        <Button variant="outline" size="sm">
          로그인
        </Button>
      </Link>
      <Link href="/signup">
        <Button variant="default" size="sm">
          회원가입
        </Button>
      </Link>
    </div>
  );
}
