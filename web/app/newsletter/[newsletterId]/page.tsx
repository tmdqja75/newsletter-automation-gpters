import { notFound } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { getNewsletterForPublicView } from '@/lib/actions/newsletter';
import { getFeedback } from '@/lib/actions/feedback';
import { NewsletterContent } from '@/components/newsletter/newsletter-content';
import { NewsletterShare } from '@/components/newsletter/newsletter-share';
import { NewsletterFeedback } from '@/components/newsletter/newsletter-feedback';
import { NewsletterDownload } from '@/components/newsletter/newsletter-download';
import { Container } from '@/components/ui/container';
import { Card } from '@/components/ui/card';
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
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Header */}
      <header className="w-full py-4">
        <Container className="flex items-center justify-between" maxWidth="lg">
          <Link
            href={isOwner ? '/dashboard' : '/'}
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            ← {isOwner ? '대시보드로 돌아가기' : '홈으로 돌아가기'}
          </Link>
          {isOwner && (
            <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
              <span>내 뉴스레터</span>
            </div>
          )}
        </Container>
      </header>

      {/* Main Content */}
      <main className="w-full py-12">
        <Container maxWidth="lg">
          {/* Topic Info */}
          <Card className="mb-8">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="mb-1 text-lg font-semibold text-zinc-950 dark:text-zinc-50">
                  주제: {newsletter.user_topics.topic_text}
                </h2>
                {newsletter.user_topics.topic_description && (
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {newsletter.user_topics.topic_description}
                  </p>
                )}
              </div>
              <div className="text-sm text-zinc-500 dark:text-zinc-400">
                {new Date(newsletter.created_at).toLocaleDateString('ko-KR', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </div>
            </div>
          </Card>

          {/* Newsletter Content */}
          <Card className="mb-8 p-8">
            <NewsletterContent content={newsletter.content} />
          </Card>

          {/* Share and Feedback Section */}
          <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2">
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

          {/* Download Section */}
          <div className="mx-auto max-w-md">
            <NewsletterDownload
              content={newsletter.content}
              title={newsletter.content.title}
            />
          </div>

          {/* Public View Notice */}
          {!isOwner && (
            <div className="mt-8 rounded-lg border border-blue-200 bg-blue-50 p-4 text-center dark:border-blue-900 dark:bg-blue-950">
              <p className="text-sm text-blue-700 dark:text-blue-300">
                이 뉴스레터는 공개 링크로 공유되었습니다. 자신의 뉴스레터를
                생성하려면{' '}
                <Link href="/" className="font-medium underline">
                  여기를 클릭하세요
                </Link>
                .
              </p>
            </div>
          )}
        </Container>
      </main>

      {/* Footer */}
      <footer className="w-full py-8">
        <Container
          className="flex items-center justify-center text-sm text-zinc-500 dark:text-zinc-600"
          maxWidth="lg"
        >
          © 2026 Automata. AI-powered newsletter service.
        </Container>
      </footer>
    </div>
  );
}
