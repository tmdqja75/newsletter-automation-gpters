import { notFound } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { getNewsletterForPublicView } from '@/lib/actions/newsletter';
import { getFeedback } from '@/lib/actions/feedback';
import { NewsletterContent } from '@/components/newsletter/newsletter-content';
import { NewsletterShare } from '@/components/newsletter/newsletter-share';
import { NewsletterFeedback } from '@/components/newsletter/newsletter-feedback';
import Link from 'next/link';

interface PageProps {
  params: Promise<{
    newsletterId: string;
  }>;
}

export default async function NewsletterPage({ params }: PageProps) {
  const { newsletterId } = await params;

  // Fetch newsletter (public access)
  const result = await getNewsletterForPublicView(newsletterId);

  if (!result.success || !result.newsletter) {
    notFound();
  }

  const newsletter = result.newsletter;

  // Check if user is authenticated and is the owner
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isOwner = user?.id === newsletter.user_id;

  // Get existing feedback if user is owner
  let existingFeedback = null;
  if (isOwner) {
    const feedbackResult = await getFeedback(newsletterId);
    if (feedbackResult.success) {
      existingFeedback = feedbackResult.feedback;
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link
            href={isOwner ? '/dashboard' : '/'}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            ← {isOwner ? '대시보드로 돌아가기' : '홈으로 돌아가기'}
          </Link>
          {isOwner && (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <span>내 뉴스레터</span>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Topic Info */}
        <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                주제: {newsletter.user_topics.topic}
              </h2>
              {newsletter.user_topics.description && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {newsletter.user_topics.description}
                </p>
              )}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {new Date(newsletter.created_at).toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </div>
          </div>
        </div>

        {/* Newsletter Content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 mb-6">
          <NewsletterContent content={newsletter.content} />
        </div>

        {/* Share and Feedback Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Share Component */}
          <NewsletterShare
            newsletterId={newsletterId}
            title={newsletter.content.title}
          />

          {/* Feedback Component (only for owner) */}
          {isOwner && (
            <NewsletterFeedback
              newsletterId={newsletterId}
              existingFeedback={existingFeedback}
            />
          )}
        </div>

        {/* Public View Notice */}
        {!isOwner && (
          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 text-center">
            <p className="text-sm text-blue-700 dark:text-blue-300">
              이 뉴스레터는 공개 링크로 공유되었습니다. 자신의 뉴스레터를
              생성하려면{' '}
              <Link href="/" className="underline font-medium">
                여기를 클릭하세요
              </Link>
              .
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 mt-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>© 2026 Automata. AI-powered personalized newsletters.</p>
        </div>
      </footer>
    </div>
  );
}
