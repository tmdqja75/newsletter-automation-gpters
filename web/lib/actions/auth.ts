'use server';

import { createClient } from '@/lib/supabase/server';
import { loginSchema, signupSchema } from '@/lib/validation/auth';
import { redirect } from 'next/navigation';

export async function login(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;

  // Validate input
  const result = loginSchema.safeParse({ email, password });
  if (!result.success) {
    const firstError = result.error.issues[0];
    return { success: false, message: firstError.message };
  }

  const supabase = await createClient();

  const { error } = await supabase.auth.signInWithPassword({
    email: result.data.email,
    password: result.data.password,
  });

  if (error) {
    // Handle specific error cases
    if (error.message.includes('Email not confirmed')) {
      return {
        success: false,
        message: '이메일 인증이 완료되지 않았습니다. 이메일을 확인해주세요.',
      };
    }
    if (error.message.includes('Invalid login credentials')) {
      return {
        success: false,
        message: '이메일 또는 비밀번호가 올바르지 않습니다.',
      };
    }
    return {
      success: false,
      message: '로그인에 실패했습니다. 다시 시도해주세요.',
    };
  }

  redirect('/');
}

export async function signup(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const confirmPassword = formData.get('confirmPassword') as string;

  // Validate input
  const result = signupSchema.safeParse({ email, password, confirmPassword });
  if (!result.success) {
    const firstError = result.error.issues[0];
    return { success: false, message: firstError.message };
  }

  const supabase = await createClient();

  // Get the origin for email confirmation redirect
  const origin = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

  const { error } = await supabase.auth.signUp({
    email: result.data.email,
    password: result.data.password,
    options: {
      emailRedirectTo: `${origin}/api/auth/callback`,
    },
  });

  if (error) {
    // Handle specific error cases
    if (error.message.includes('User already registered')) {
      return {
        success: false,
        message: '이미 가입된 이메일입니다.',
      };
    }
    return {
      success: false,
      message: '회원가입에 실패했습니다. 다시 시도해주세요.',
    };
  }

  return {
    success: true,
    message:
      '회원가입이 완료되었습니다. 이메일을 확인하여 인증을 완료해주세요.',
  };
}

export async function logout() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect('/');
}
