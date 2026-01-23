'use client';

import { useState, FormEvent, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { validateTopic } from '@/lib/validation/topic';
import { createTopic } from '@/lib/actions/topic';

interface TopicInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function TopicInput({ value, onChange }: TopicInputProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const validation = validateTopic(value);

    if (!validation.success) {
      const errorMessage =
        validation.error.issues[0]?.message || '유효하지 않은 주제입니다.';
      toast.error(errorMessage);
      return;
    }

    startTransition(async () => {
      try {
        const formData = new FormData();
        formData.append('topic', value);

        const result = await createTopic(formData);

        if (!result.success) {
          toast.error(result.message);
          return;
        }

        // Navigate to questions page
        router.push(`/questions/${result.topicId}`);
      } catch (error) {
        toast.error('제출 중 오류가 발생했습니다.');
        console.error('Submission error:', error);
      }
    });
  };

  const charCount = value.length;
  const maxChars = 100;
  const isOverLimit = charCount > maxChars;

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <div className="relative">
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="어떤 주제로 리서치해 드릴까요?"
              className="w-full rounded-full border border-solid border-zinc-200 px-6 py-4 text-base transition-colors outline-none placeholder:text-zinc-400 focus:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:placeholder:text-zinc-600 dark:focus:border-zinc-600"
              disabled={isPending}
              maxLength={maxChars}
            />
          </div>
          <div className="flex items-center justify-between px-2">
            <span
              className={`text-sm ${
                isOverLimit
                  ? 'text-red-500 dark:text-red-400'
                  : 'text-zinc-500 dark:text-zinc-500'
              }`}
            >
              {charCount} / {maxChars}
            </span>
          </div>
        </div>

        <button
          type="submit"
          disabled={isPending || value.length === 0}
          className="bg-foreground text-background flex h-12 w-full items-center justify-center gap-2 rounded-full px-5 transition-colors hover:bg-[#383838] disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-[#ccc]"
        >
          {isPending ? '제출 중...' : '리서치 시작하기'}
        </button>
      </div>
    </form>
  );
}
