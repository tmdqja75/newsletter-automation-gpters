'use client';

import { useState, useTransition } from 'react';
import { submitFeedback, getFeedback } from '@/lib/actions/feedback';
import { Button } from '@/components/ui/button';
import toast from 'react-hot-toast';

interface NewsletterFeedbackProps {
  newsletterId: string;
  existingFeedback?: {
    thumbs_up: boolean;
    structured_feedback: {
      more_depth?: boolean;
      easier_explanation?: boolean;
      different_sources?: boolean;
    } | null;
    comment: string | null;
  } | null;
}

export function NewsletterFeedback({
  newsletterId,
  existingFeedback,
}: NewsletterFeedbackProps) {
  const [isPending, startTransition] = useTransition();
  const [hasSubmitted, setHasSubmitted] = useState(!!existingFeedback);

  // Form state
  const [thumbsUp, setThumbsUp] = useState<boolean | null>(
    existingFeedback?.thumbs_up ?? null
  );
  const [moreDepth, setMoreDepth] = useState(
    existingFeedback?.structured_feedback?.more_depth ?? false
  );
  const [easierExplanation, setEasierExplanation] = useState(
    existingFeedback?.structured_feedback?.easier_explanation ?? false
  );
  const [differentSources, setDifferentSources] = useState(
    existingFeedback?.structured_feedback?.different_sources ?? false
  );
  const [comment, setComment] = useState(existingFeedback?.comment ?? '');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (thumbsUp === null) {
      toast.error('만족도를 선택해주세요');
      return;
    }

    startTransition(async () => {
      const result = await submitFeedback(newsletterId, {
        thumbs_up: thumbsUp,
        structured_feedback:
          moreDepth || easierExplanation || differentSources
            ? {
                more_depth: moreDepth || undefined,
                easier_explanation: easierExplanation || undefined,
                different_sources: differentSources || undefined,
              }
            : null,
        comment: comment.trim() || null,
      });

      if (result.success) {
        toast.success(result.message);
        setHasSubmitted(true);
      } else {
        toast.error(result.message);
      }
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
        피드백을 남겨주세요
      </h3>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Thumbs Up/Down */}
        <div>
          <label className="block text-sm font-medium mb-3 text-gray-700 dark:text-gray-300">
            이번 뉴스레터가 도움이 되었나요? <span className="text-red-600">*</span>
          </label>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setThumbsUp(true)}
              disabled={hasSubmitted}
              className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                thumbsUp === true
                  ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-700'
              } ${hasSubmitted ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <span className="text-4xl block mb-2">👍</span>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                좋아요
              </span>
            </button>
            <button
              type="button"
              onClick={() => setThumbsUp(false)}
              disabled={hasSubmitted}
              className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                thumbsUp === false
                  ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-red-300 dark:hover:border-red-700'
              } ${hasSubmitted ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <span className="text-4xl block mb-2">👎</span>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                아쉬워요
              </span>
            </button>
          </div>
        </div>

        {/* Structured Feedback */}
        <div>
          <label className="block text-sm font-medium mb-3 text-gray-700 dark:text-gray-300">
            어떤 점을 개선하면 좋을까요? (선택사항)
          </label>
          <div className="space-y-2">
            <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer">
              <input
                type="checkbox"
                checked={moreDepth}
                onChange={(e) => setMoreDepth(e.target.checked)}
                disabled={hasSubmitted}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                더 깊게 다뤄주세요
              </span>
            </label>
            <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer">
              <input
                type="checkbox"
                checked={easierExplanation}
                onChange={(e) => setEasierExplanation(e.target.checked)}
                disabled={hasSubmitted}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                더 쉽게 설명해주세요
              </span>
            </label>
            <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer">
              <input
                type="checkbox"
                checked={differentSources}
                onChange={(e) => setDifferentSources(e.target.checked)}
                disabled={hasSubmitted}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                다른 소스를 원해요
              </span>
            </label>
          </div>
        </div>

        {/* Comment */}
        <div>
          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
            추가 의견 (선택사항)
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={hasSubmitted}
            maxLength={500}
            rows={4}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder="자유롭게 의견을 남겨주세요..."
          />
          <div className="flex justify-between items-center mt-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {comment.length} / 500
            </span>
          </div>
        </div>

        {/* Submit Button */}
        {!hasSubmitted && (
          <Button
            type="submit"
            disabled={isPending || thumbsUp === null}
            className="w-full"
          >
            {isPending ? '제출 중...' : '피드백 제출'}
          </Button>
        )}

        {hasSubmitted && (
          <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <p className="text-green-700 dark:text-green-300 font-medium">
              ✓ 피드백이 제출되었습니다. 감사합니다!
            </p>
          </div>
        )}
      </form>
    </div>
  );
}
