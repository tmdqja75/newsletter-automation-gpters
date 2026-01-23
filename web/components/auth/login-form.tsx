'use client';

import { useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginSchema, type LoginInput } from '@/lib/validation/auth';
import { login } from '@/lib/actions/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import Link from 'next/link';
import toast from 'react-hot-toast';

export function LoginForm() {
  const [isPending, startTransition] = useTransition();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginInput) => {
    const formData = new FormData();
    formData.append('email', data.email);
    formData.append('password', data.password);

    startTransition(async () => {
      try {
        const result = await login(formData);

        // If result exists, it means login failed (success would redirect)
        if (result && !result.success) {
          toast.error(result.message);
        }
        // If no result or success, redirect will happen automatically
      } catch (error) {
        // Check if this is a Next.js redirect (which is expected on success)
        // Next.js redirect errors have a 'digest' property starting with 'NEXT_REDIRECT'
        const isRedirect =
          error &&
          typeof error === 'object' &&
          'digest' in error &&
          typeof error.digest === 'string' &&
          error.digest.startsWith('NEXT_REDIRECT');

        if (isRedirect) {
          // This is a Next.js redirect - re-throw it
          throw error;
        } else {
          // Real error - show error message
          toast.error('로그인 중 오류가 발생했습니다.');
        }
      }
    });
  };

  return (
    <div className="w-full max-w-md space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold">로그인</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          계정에 로그인하세요
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-6">
        <div className="space-y-4">
          <div>
            <Label htmlFor="email">이메일</Label>
            <Input
              id="email"
              type="email"
              placeholder="example@email.com"
              {...register('email')}
              className="mt-1"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600">
                {errors.email.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="password">비밀번호</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              {...register('password')}
              className="mt-1"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">
                {errors.password.message}
              </p>
            )}
          </div>
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={isPending}
          variant="default"
        >
          {isPending ? '로그인 중...' : '로그인'}
        </Button>

        <div className="text-center text-sm">
          <span className="text-gray-600 dark:text-gray-400">
            계정이 없으신가요?{' '}
          </span>
          <Link
            href="/signup"
            className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
          >
            회원가입
          </Link>
        </div>
      </form>
    </div>
  );
}
