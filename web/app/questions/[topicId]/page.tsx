'use client';

import { useEffect, useState, useTransition } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { QuestionCard } from '@/components/question-card';
import { Button } from '@/components/ui/button';
import { getQuestionsByTopicId, saveAnswers } from '@/lib/actions/question';
import { getTopicById } from '@/lib/actions/topic';
import type { Question, Answer } from '@/lib/validation/question';
import { validateAnswerForQuestion } from '@/lib/validation/question';
import toast from 'react-hot-toast';

interface QuestionState {
  question: Question;
  answer?: Answer;
  skipped: boolean;
  error?: string;
}

export default function QuestionsPage() {
  const router = useRouter();
  const params = useParams();
  const topicId = params.topicId as string;

  const [topic, setTopic] = useState<{
    id: string;
    topic_text: string;
  } | null>(null);
  const [questionStates, setQuestionStates] = useState<QuestionState[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    async function loadData() {
      try {
        // Load topic
        const topicResult = await getTopicById(topicId);
        if (!topicResult.success || !topicResult.topic) {
          toast.error(topicResult.message || '주제를 불러오는데 실패했습니다.');
          router.push('/');
          return;
        }
        setTopic(topicResult.topic);

        // Load questions
        const questionsResult = await getQuestionsByTopicId(topicId);
        if (!questionsResult.success || !questionsResult.questions) {
          toast.error(questionsResult.message || '질문을 불러오는데 실패했습니다.');
          return;
        }

        if (questionsResult.questions.length === 0) {
          toast.error('질문을 찾을 수 없습니다.');
          router.push('/');
          return;
        }

        setQuestionStates(
          questionsResult.questions.map((q: Question) => ({
            question: q,
            answer: undefined,
            skipped: false,
            error: undefined,
          }))
        );
      } catch (error) {
        console.error('Error loading questions:', error);
        toast.error('질문을 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [topicId, router]);

  const handleAnswerChange = (index: number, answer: Answer | undefined) => {
    setQuestionStates((prev) =>
      prev.map((state, i) =>
        i === index
          ? {
              ...state,
              answer,
              skipped: false,
              error: undefined,
            }
          : state
      )
    );
  };

  const handleSkip = (index: number) => {
    setQuestionStates((prev) =>
      prev.map((state, i) =>
        i === index
          ? {
              ...state,
              answer: undefined,
              skipped: !state.skipped,
              error: undefined,
            }
          : state
      )
    );
  };

  const validateAllAnswers = (): boolean => {
    let isValid = true;
    const newStates = questionStates.map((state) => {
      const validation = validateAnswerForQuestion(
        state.question,
        state.answer,
        state.skipped
      );
      if (!validation.valid) {
        isValid = false;
      }
      return {
        ...state,
        error: validation.error,
      };
    });

    setQuestionStates(newStates);
    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateAllAnswers()) {
      toast.error('필수 질문에 답변해주세요.');
      return;
    }

    // Check if at least one question is answered
    const answeredCount = questionStates.filter(
      (state) => !state.skipped && state.answer
    ).length;

    if (answeredCount === 0) {
      toast.error('최소 1개 이상의 질문에 답변해주세요.');
      return;
    }

    startTransition(async () => {
      try {
        const answers = questionStates.map((state) => ({
          question_id: state.question.id,
          answer_text:
            state.answer?.type === 'text' ? state.answer.value : null,
          answer_value:
            state.answer?.type === 'radio'
              ? { value: state.answer.value }
              : state.answer?.type === 'checkbox'
                ? { values: state.answer.value }
                : null,
          skipped: state.skipped,
        }));

        const result = await saveAnswers(topicId, answers);

        if (!result.success) {
          toast.error(result.message);
          return;
        }

        toast.success('답변이 저장되었습니다! 리서치를 시작합니다.');
        // TODO: Redirect to research/newsletter generation page
        // For now, redirect to home
        router.push('/');
      } catch (error) {
        console.error('Error saving answers:', error);
        toast.error('답변 저장에 실패했습니다.');
      }
    });
  };

  const answeredCount = questionStates.filter(
    (state) => !state.skipped && state.answer
  ).length;
  const totalCount = questionStates.length;
  const progressPercentage =
    totalCount > 0 ? (answeredCount / totalCount) * 100 : 0;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600"></div>
          <p className="text-gray-600 dark:text-gray-400">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-white dark:bg-black">
      <header className="w-full border-b border-gray-200 px-6 py-4 sm:px-16 dark:border-gray-800">
        <h1 className="text-xl font-semibold text-zinc-950 dark:text-zinc-50">
          Automata
        </h1>
      </header>

      <main className="flex-1 px-6 py-8 sm:px-16">
        <div className="mx-auto max-w-3xl">
          {/* Topic header */}
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              추가 질문
            </h2>
            <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
              <span className="font-medium text-blue-600 dark:text-blue-400">
                {topic?.topic_text}
              </span>
              에 대해 더 알려주세요
            </p>
          </div>

          {/* Progress bar */}
          <div className="mb-8">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">
                답변 진행률
              </span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {answeredCount} / {totalCount}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
              <div
                className="h-full bg-blue-600 transition-all duration-300"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>

          {/* Questions form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {questionStates.map((state, index) => (
              <QuestionCard
                key={state.question.id}
                question={state.question}
                value={state.answer}
                onChange={(answer) => handleAnswerChange(index, answer)}
                onSkip={() => handleSkip(index)}
                skipped={state.skipped}
                error={state.error}
              />
            ))}

            {/* Submit button */}
            <div className="flex justify-end gap-4 pt-6">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/')}
                disabled={isPending}
              >
                취소
              </Button>
              <Button type="submit" disabled={isPending} size="lg">
                {isPending ? '저장 중...' : '제출하기'}
              </Button>
            </div>
          </form>
        </div>
      </main>

      <footer className="flex w-full items-center justify-center px-6 py-8 text-sm text-zinc-500 dark:text-zinc-600">
        © 2026 Automata. AI-powered newsletter service.
      </footer>
    </div>
  );
}
