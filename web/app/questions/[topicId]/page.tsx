'use client';

import { useEffect, useState, useTransition } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { QuestionCard } from '@/components/question-card';
import { Button } from '@/components/ui/button';
import { Container } from '@/components/ui/container';
import { Progress } from '@/components/ui/progress';
import { AuthStatus } from '@/components/auth/auth-status';
import { getQuestionsByTopicId, saveAnswers } from '@/lib/actions/question';
import { getTopicById } from '@/lib/actions/topic';
import { saveDeliveryPreference } from '@/lib/actions/preference';
import { env } from '@/lib/env';
import { createClient } from '@/lib/supabase/client';
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
  const [generating, setGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationMessage, setGenerationMessage] = useState('');
  const [scheduled, setScheduled] = useState(false);
  const [scheduledDay, setScheduledDay] = useState('');

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
          toast.error(
            questionsResult.message || '질문을 불러오는데 실패했습니다.'
          );
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

        toast.success('답변이 저장되었습니다!');

        // Extract delivery preference answers
        const deliveryDayState = questionStates.find(
          (s) => s.question.question_type === 'delivery_day'
        );
        const generateNowState = questionStates.find(
          (s) => s.question.question_type === 'generate_now'
        );

        const selectedDay =
          deliveryDayState?.answer?.type === 'radio'
            ? deliveryDayState.answer.value
            : null;
        const shouldGenerateNow =
          generateNowState?.answer?.type === 'checkbox' &&
          generateNowState.answer.value.includes('지금 바로 생성하기');

        // Save delivery preference regardless of generate_now
        if (selectedDay) {
          const prefResult = await saveDeliveryPreference(selectedDay);
          if (!prefResult.success) {
            toast.error(prefResult.message);
            return;
          }
        }

        if (!shouldGenerateNow) {
          // Scheduled flow: show confirmation screen
          setScheduledDay(selectedDay || '');
          setScheduled(true);
          return;
        }

        // Immediate generation flow (SSE streaming)
        const supabase = createClient();
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (!user) {
          toast.error('로그인이 필요합니다.');
          return;
        }

        setGenerating(true);
        setGenerationProgress(0);
        setGenerationMessage('리서치를 준비하는 중...');

        const apiUrl = env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

        try {
          const response = await fetch(
            `${apiUrl}/api/newsletter/generate/stream`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                user_id: user.id,
                topic_id: topicId,
              }),
            }
          );

          if (!response.ok) {
            throw new Error('Failed to start generation');
          }

          const reader = response.body?.getReader();
          const decoder = new TextDecoder();

          if (reader) {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              const chunk = decoder.decode(value);
              const lines = chunk.split('\n');

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = JSON.parse(line.slice(6));
                  setGenerationProgress(data.progress);
                  setGenerationMessage(data.message);

                  if (data.step === 'complete' && data.details?.newsletter_id) {
                    const newsletterId = data.details.newsletter_id;

                    // Send email before redirecting
                    setGenerationMessage('이메일 발송 중...');
                    try {
                      const sendRes = await fetch(
                        `/api/newsletters/${newsletterId}/send`,
                        { method: 'POST' }
                      );
                      if (
                        sendRes.ok ||
                        (sendRes.status === 400 &&
                          (await sendRes.json()).error === 'Already sent')
                      ) {
                        toast.success('이메일이 발송되었습니다!');
                      } else {
                        toast.error('이메일 발송에 실패했습니다.');
                      }
                    } catch {
                      toast.error('이메일 발송에 실패했습니다.');
                    }

                    router.push(`/newsletter/${newsletterId}`);
                    return;
                  } else if (data.step === 'error') {
                    toast.error(data.message);
                    setGenerating(false);
                    return;
                  }
                }
              }
            }
          }
        } catch (error) {
          console.error('Error generating newsletter:', error);
          toast.error('뉴스레터 생성 중 오류가 발생했습니다.');
          setGenerating(false);
        }
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

  useEffect(() => {
    if (!scheduled) return;
    const timer = setTimeout(() => {
      router.push('/dashboard');
    }, 3000);
    return () => clearTimeout(timer);
  }, [scheduled, router]);

  if (scheduled) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white dark:bg-black">
        <Container className="text-center" maxWidth="md">
          <div className="mb-8">
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
              <svg
                className="h-8 w-8 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="mb-3 text-3xl font-bold text-zinc-950 sm:text-4xl dark:text-zinc-50">
              예약 완료!
            </h2>
            <p className="text-lg text-zinc-600 dark:text-zinc-400">
              매주{' '}
              <span className="font-semibold text-zinc-950 dark:text-zinc-50">
                {scheduledDay}
              </span>
              마다 뉴스레터를 배송해 드릴게요!
            </p>
          </div>

          <p className="mb-8 text-sm text-zinc-500 dark:text-zinc-400">
            발송 시간은 오전 9시로 고정됩니다.
            <br />
            잠시 후 대시보드로 이동합니다...
          </p>

          <Button
            type="button"
            variant="outline"
            onClick={() => router.push('/dashboard')}
          >
            대시보드로 이동
          </Button>
        </Container>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white dark:bg-black">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-zinc-200 border-t-zinc-950 dark:border-zinc-800 dark:border-t-zinc-50"></div>
          <p className="text-lg text-zinc-600 dark:text-zinc-400">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (generating) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white dark:bg-black">
        <Container className="text-center" maxWidth="md">
          <div className="mb-8">
            <div className="mx-auto mb-6 h-16 w-16 animate-spin rounded-full border-4 border-zinc-200 border-t-zinc-950 dark:border-zinc-800 dark:border-t-zinc-50"></div>
            <h2 className="mb-3 text-3xl font-bold text-zinc-950 sm:text-4xl dark:text-zinc-50">
              리서치 중입니다...
            </h2>
            <p className="text-lg text-zinc-600 dark:text-zinc-400">
              {generationMessage}
            </p>
          </div>

          <div className="mb-8">
            <Progress
              value={generationProgress}
              showPercentage={true}
              className="mx-auto max-w-md"
            />
          </div>

          <p className="mb-8 text-sm text-zinc-500 dark:text-zinc-400">
            AI가 최신 자료를 수집하고 분석하고 있습니다.
            <br />
            잠시만 기다려주세요.
          </p>

          <Button
            type="button"
            variant="outline"
            onClick={() => {
              // Use full navigation so it works even if streaming blocks client routing.
              window.location.assign('/dashboard');
            }}
          >
            대시보드로 이동
          </Button>
        </Container>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-white dark:bg-black">
      <header className="w-full py-4">
        <Container className="flex items-center justify-between" maxWidth="2xl">
          <h1 className="text-xl font-semibold text-zinc-950 dark:text-zinc-50">
            Automata
          </h1>
          <AuthStatus />
        </Container>
      </header>

      <main className="flex-1 py-12">
        <Container maxWidth="md">
          {/* Topic header */}
          <div className="mb-12">
            <h2 className="text-4xl leading-tight font-bold tracking-tight text-zinc-950 sm:text-5xl dark:text-zinc-50">
              추가 질문
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-zinc-600 dark:text-zinc-400">
              <span className="font-medium text-zinc-950 dark:text-zinc-50">
                {topic?.topic_text}
              </span>
              에 대해 더 알려주세요
            </p>
          </div>

          {/* Progress bar */}
          <div className="mb-12">
            <Progress
              value={progressPercentage}
              label={`답변 진행률: ${answeredCount} / ${totalCount}`}
              showPercentage={false}
            />
          </div>

          {/* Questions form */}
          <form onSubmit={handleSubmit} className="space-y-8">
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
            <div className="flex justify-end gap-4 pt-8">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/')}
                disabled={isPending}
              >
                취소
              </Button>
              <Button
                type="submit"
                disabled={isPending}
                size="lg"
                className="rounded-full"
              >
                {isPending ? '저장 중...' : '제출하기'}
              </Button>
            </div>
          </form>
        </Container>
      </main>

      <footer className="w-full py-8">
        <Container
          className="flex items-center justify-center text-sm text-zinc-500 dark:text-zinc-600"
          maxWidth="2xl"
        >
          © 2026 Automata. AI-powered newsletter service.
        </Container>
      </footer>
    </div>
  );
}
