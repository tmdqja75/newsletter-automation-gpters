'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getNewsletterStatus } from '@/lib/actions/newsletter';

interface NewsletterLoadingProps {
  requestId: string;
}

export function NewsletterLoading({ requestId }: NewsletterLoadingProps) {
  const router = useRouter();
  const [status, setStatus] = useState<string>('pending');
  const [message, setMessage] = useState('뉴스레터를 생성하고 있습니다...');
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // eslint-disable-next-line prefer-const
    let intervalId: NodeJS.Timeout;

    const checkStatus = async () => {
      const result = await getNewsletterStatus(requestId);

      if (result.success) {
        setStatus(result.status || 'pending');

        // Update message based on status
        if (result.status === 'pending') {
          setMessage('뉴스레터 생성 대기 중...');
          setProgress(10);
        } else if (result.status === 'processing') {
          setMessage('리서치 중입니다...');
          setProgress(50);
        } else if (result.status === 'completed' && result.newsletterId) {
          setMessage('뉴스레터 생성 완료!');
          setProgress(100);
          // Redirect to newsletter view
          setTimeout(() => {
            router.push(`/newsletter/${result.newsletterId}`);
          }, 1000);
          clearInterval(intervalId);
        } else if (result.status === 'failed') {
          setMessage(
            `생성 실패: ${result.errorMessage || '알 수 없는 오류가 발생했습니다.'}`
          );
          setProgress(0);
          clearInterval(intervalId);
        }
      }
    };

    // Initial check
    checkStatus();

    // Poll every 3 seconds
    intervalId = setInterval(checkStatus, 3000);

    return () => clearInterval(intervalId);
  }, [requestId, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-gray-800">
        {/* Animated Spinner */}
        <div className="mb-6 flex justify-center">
          <div className="relative h-16 w-16">
            <div className="absolute inset-0 rounded-full border-4 border-gray-200 dark:border-gray-700"></div>
            <div className="absolute inset-0 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
          </div>
        </div>

        {/* Status Message */}
        <h2 className="mb-2 text-xl font-semibold text-gray-900 dark:text-gray-100">
          {status === 'failed' ? '오류 발생' : '생성 중'}
        </h2>
        <p className="mb-6 text-gray-600 dark:text-gray-400">{message}</p>

        {/* Progress Bar */}
        {status !== 'failed' && (
          <div className="mb-4 h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className="h-2 rounded-full bg-blue-600 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        )}

        {/* Additional Info */}
        {status === 'processing' && (
          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
            <p className="text-sm text-blue-700 dark:text-blue-300">
              AI 에이전트가 최신 정보를 수집하고 분석하고 있습니다. 잠시만
              기다려주세요.
            </p>
          </div>
        )}

        {status === 'failed' && (
          <div className="mt-6">
            <button
              onClick={() => router.push('/dashboard')}
              className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
            >
              대시보드로 돌아가기
            </button>
          </div>
        )}

        {/* Expected Sections Preview */}
        {status !== 'failed' && (
          <div className="mt-8 text-left">
            <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">
              생성될 섹션:
            </h3>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>TL;DR 요약</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>핵심 이슈 3-5개</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Deep Dive 분석</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>다음 질문</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>출처 목록</span>
              </li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
