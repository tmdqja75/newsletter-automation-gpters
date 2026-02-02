'use client';

import {
  FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
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
  const [isFocused, setIsFocused] = useState(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  // Korean placeholders for the newsletter research topic
  const placeholders = useMemo(
    () => [
      '어떤 주제로 리서치해 드릴까요?',
      'AI 에이전트 최신 동향',
      'LLM 프롬프팅 기법',
      'RAG 시스템 구현 방법',
    ],
    []
  );

  // Animation config
  const CHAR_DELAY = 75; // ms between characters while typing
  const IDLE_DELAY_AFTER_FINISH = 2200; // ms to wait after a full sentence is shown

  // Refs to hold active timers so they can be cleaned up
  const intervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // clear any stale timers (helps with StrictMode double-invoke in dev)
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    const current = placeholders[placeholderIndex];
    if (!current) {
      return;
    }

    const chars = Array.from(current);
    let charIndex = 0;

    // Use requestAnimationFrame to avoid setState during effect initialization
    requestAnimationFrame(() => {
      setDisplayedText('');
      setIsTyping(true);
    });

    // type character-by-character using a derived slice to avoid any chance of appending undefined
    intervalRef.current = window.setInterval(() => {
      if (charIndex < chars.length) {
        const next = chars.slice(0, charIndex + 1).join('');
        setDisplayedText(next);
        charIndex += 1;
      } else {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setIsTyping(false);

        // after a brief pause, advance to the next placeholder
        timeoutRef.current = window.setTimeout(() => {
          setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
        }, IDLE_DELAY_AFTER_FINISH);
      }
    }, CHAR_DELAY);

    // Cleanup on unmount or when placeholderIndex changes
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [placeholderIndex, placeholders]);

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
            <div
              className={`flex items-center gap-4 rounded-full border border-gray-300 bg-black p-6 shadow-lg transition-all duration-300 ease-out ${
                isFocused
                  ? 'scale-[1.02] border-gray-600 shadow-xl'
                  : 'shadow-lg'
              }`}
            >
              <div className="relative flex-shrink-0">
                <div className="h-16 w-16 scale-100 overflow-hidden rounded-full transition-all duration-300">
                  <Image
                    src="https://media.giphy.com/media/26gsuUjoEBmLrNBxC/giphy.gif"
                    alt="Animated orb"
                    width={64}
                    height={64}
                    className="h-full w-full object-cover"
                    unoptimized
                  />
                </div>
              </div>

              <div className="h-12 w-px bg-gray-600" />

              <div className="w-[500px] flex-1">
                <input
                  data-testid="topic-input"
                  type="text"
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setIsFocused(false)}
                  placeholder={`${displayedText}${isTyping ? '|' : ''}`}
                  aria-label="어떤 주제로 리서치해 드릴까요?"
                  className="w-full border-none bg-transparent text-xl font-light text-white placeholder-gray-400 outline-none"
                  disabled={isPending}
                  maxLength={maxChars}
                />
              </div>
            </div>
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
