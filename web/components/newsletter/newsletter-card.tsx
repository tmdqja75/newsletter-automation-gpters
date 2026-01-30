'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { deleteNewsletter } from '@/lib/actions/newsletter';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import toast from 'react-hot-toast';

interface NewsletterCardProps {
  newsletter: {
    id: string;
    request_id?: string;
    status: string; // 'pending' | 'processing' | 'completed' | 'failed'
    content: {
      title: string;
      body: string;
    };
    created_at: string;
    user_topics: {
      id: string;
      topic_text: string;
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

  const status = newsletter.status;
  const isCompleted = status === 'completed';
  const isProcessing = status === 'processing';
  const isFailed = status === 'failed';

  const statusVariants = {
    pending: 'warning',
    processing: 'info',
    completed: 'success',
    failed: 'error',
  } as const;

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
    } catch {
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
    return 'from-slate-700 to-indigo-900';
  };

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white transition-shadow hover:shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
      {/* Thumbnail */}
      <div
        className={`h-32 bg-gradient-to-br ${getGradient(newsletter.user_topics.topic_text)} flex items-center justify-center`}
      >
        <div className="px-4 text-center text-white">
          <h3 className="line-clamp-2 text-lg font-semibold tracking-tight">
            {newsletter.content.title}
          </h3>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Status Badge */}
        <div className="mb-3 flex items-center justify-between">
          <Badge
            variant={
              statusVariants[status as keyof typeof statusVariants] || 'warning'
            }
          >
            {statusLabels[status as keyof typeof statusLabels] || '알 수 없음'}
          </Badge>
          <span className="text-xs text-zinc-500 dark:text-zinc-500">
            {new Date(newsletter.created_at).toLocaleDateString('ko-KR', {
              month: 'short',
              day: 'numeric',
            })}
          </span>
        </div>

        {/* Topic */}
        <p className="mb-2 text-sm font-medium text-zinc-600 dark:text-zinc-400">
          주제: {newsletter.user_topics.topic_text}
        </p>

        {/* Body Preview */}
        {isCompleted && (
          <p className="mb-4 line-clamp-2 text-sm text-zinc-700 dark:text-zinc-300">
            {newsletter.content.body.substring(0, 150)}...
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
                  className="h-4 w-4"
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
                  className="h-4 w-4"
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
            <div className="flex flex-1 items-center justify-center gap-2 text-blue-600 dark:text-blue-400">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
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
              className="text-red-600 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-900/20"
            >
              <svg
                className="h-4 w-4"
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
