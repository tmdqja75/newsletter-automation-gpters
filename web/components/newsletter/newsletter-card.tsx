'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { deleteNewsletter } from '@/lib/actions/newsletter';
import { Button } from '@/components/ui/button';
import toast from 'react-hot-toast';

interface NewsletterCardProps {
  newsletter: {
    id: string;
    content: {
      title: string;
      tldr: string;
    };
    created_at: string;
    user_topics: {
      id: string;
      topic: string;
    };
    newsletter_requests: {
      status: string;
    };
  };
  onDelete?: () => void;
  onDownload?: (id: string, title: string) => void;
}

export function NewsletterCard({
  newsletter,
  onDelete,
  onDownload,
}: NewsletterCardProps) {
  const [isPending, startTransition] = useTransition();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const status = newsletter.newsletter_requests.status;
  const isCompleted = status === 'completed';
  const isProcessing = status === 'processing';
  const isFailed = status === 'failed';

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300',
    processing:
      'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
    completed:
      'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300',
  };

  const statusLabels = {
    pending: '대기 중',
    processing: '생성 중',
    completed: '완료',
    failed: '실패',
  };

  const handleDelete = async () => {
    startTransition(async () => {
      const result = await deleteNewsletter(newsletter.id);
      if (result.success) {
        toast.success(result.message);
        onDelete?.();
      } else {
        toast.error(result.message);
      }
    });
  };

  const handleShare = async () => {
    const shareUrl = `${window.location.origin}/newsletter/${newsletter.id}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success('링크가 복사되었습니다!');
    } catch (error) {
      toast.error('링크 복사에 실패했습니다.');
    }
  };

  const handleDownload = () => {
    if (onDownload) {
      onDownload(newsletter.id, newsletter.content.title);
    }
  };

  // Generate thumbnail background gradient based on topic
  const getGradient = (topic: string) => {
    const gradients = [
      'from-blue-400 to-blue-600',
      'from-purple-400 to-purple-600',
      'from-pink-400 to-pink-600',
      'from-green-400 to-green-600',
      'from-yellow-400 to-yellow-600',
      'from-red-400 to-red-600',
    ];
    const index = topic.length % gradients.length;
    return gradients[index];
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-lg transition-shadow">
      {/* Thumbnail */}
      <div
        className={`h-32 bg-gradient-to-br ${getGradient(newsletter.user_topics.topic)} flex items-center justify-center`}
      >
        <div className="text-white text-center px-4">
          <h3 className="text-lg font-bold line-clamp-2">
            {newsletter.content.title}
          </h3>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Status Badge */}
        <div className="flex items-center justify-between mb-3">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              statusColors[status as keyof typeof statusColors] ||
              statusColors.pending
            }`}
          >
            {statusLabels[status as keyof typeof statusLabels] || '알 수 없음'}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {new Date(newsletter.created_at).toLocaleDateString('ko-KR', {
              month: 'short',
              day: 'numeric',
            })}
          </span>
        </div>

        {/* Topic */}
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
          주제: {newsletter.user_topics.topic}
        </p>

        {/* TL;DR Preview */}
        {isCompleted && (
          <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2 mb-4">
            {newsletter.content.tldr}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {isCompleted && (
            <>
              <Link href={`/newsletter/${newsletter.id}`} className="flex-1">
                <Button variant="default" className="w-full">
                  보기
                </Button>
              </Link>
              <Button
                variant="outline"
                size="sm"
                onClick={handleShare}
                title="공유"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
                  />
                </svg>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                title="다운로드"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
              </Button>
            </>
          )}

          {isProcessing && (
            <div className="flex-1 flex items-center justify-center gap-2 text-blue-600 dark:text-blue-400">
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm">생성 중...</span>
            </div>
          )}

          {isFailed && (
            <div className="flex-1 text-center text-sm text-red-600 dark:text-red-400">
              생성 실패
            </div>
          )}

          {/* Delete Button */}
          {!showDeleteConfirm ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDeleteConfirm(true)}
              title="삭제"
              className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </Button>
          ) : (
            <div className="flex gap-1">
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                disabled={isPending}
              >
                {isPending ? '삭제 중...' : '확인'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeleteConfirm(false)}
              >
                취소
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
