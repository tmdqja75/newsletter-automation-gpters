'use client';

import { useState, useEffect, useCallback } from 'react';
import { useInView } from 'react-intersection-observer';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getUserNewsletters } from '@/lib/actions/newsletter';
import { NewsletterCard } from '@/components/newsletter/newsletter-card';
import { NewsletterFilters } from '@/components/newsletter/newsletter-filters';

export default function DashboardPage() {
  const router = useRouter();
  const [newsletters, setNewsletters] = useState<any[]>([]);
  const [topics, setTopics] = useState<Array<{ id: string; topic: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest');

  const { ref, inView } = useInView({
    threshold: 0,
  });

  const loadNewsletters = useCallback(
    async (offset: number = 0, append: boolean = false) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }

      const result = await getUserNewsletters({
        limit: 12,
        offset,
        search: search || undefined,
        topicId: selectedTopic || undefined,
        sortBy,
      });

      if (result.success) {
        if (append) {
          setNewsletters((prev) => [...prev, ...result.newsletters]);
        } else {
          setNewsletters(result.newsletters);
        }

        // Extract unique topics
        const uniqueTopics = Array.from(
          new Map(
            result.newsletters.map((n: any) => [
              n.user_topics.id,
              { id: n.user_topics.id, topic: n.user_topics.topic },
            ])
          ).values()
        );
        setTopics((prev) => {
          const merged = [...prev, ...uniqueTopics];
          return Array.from(
            new Map(merged.map((t) => [t.id, t])).values()
          );
        });

        setHasMore(result.newsletters.length === 12);
      }

      setLoading(false);
      setLoadingMore(false);
    },
    [search, selectedTopic, sortBy]
  );

  // Initial load
  useEffect(() => {
    loadNewsletters(0, false);
  }, [search, selectedTopic, sortBy]);

  // Load more when scrolling
  useEffect(() => {
    if (inView && hasMore && !loadingMore && !loading) {
      loadNewsletters(newsletters.length, true);
    }
  }, [inView, hasMore, loadingMore, loading, newsletters.length]);

  const handleDelete = () => {
    // Reload newsletters after delete
    loadNewsletters(0, false);
  };

  const handleDownload = async (id: string, title: string) => {
    // TODO: Implement download functionality
    console.log('Download:', id, title);
  };

  if (loading && newsletters.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-xl font-bold text-gray-900 dark:text-gray-100"
            >
              Automata
            </Link>
          </div>
          <Link
            href="/"
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            새 뉴스레터 생성하기 →
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Page Title */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            내 뉴스레터
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            생성한 뉴스레터를 확인하고 관리하세요
          </p>
        </div>

        {/* Filters */}
        <NewsletterFilters
          topics={topics}
          onSearchChange={setSearch}
          onTopicChange={setSelectedTopic}
          onSortChange={setSortBy}
        />

        {/* Newsletter Grid */}
        {newsletters.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="max-w-md mx-auto">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
                아직 생성한 뉴스레터가 없습니다
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                관심 있는 주제로 첫 뉴스레터를 생성해보세요!
              </p>
              <Link href="/">
                <button className="mt-6 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
                  뉴스레터 생성하기
                </button>
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {newsletters.map((newsletter) => (
                <NewsletterCard
                  key={newsletter.id}
                  newsletter={newsletter}
                  onDelete={handleDelete}
                  onDownload={handleDownload}
                />
              ))}
            </div>

            {/* Infinite Scroll Trigger */}
            {hasMore && (
              <div ref={ref} className="py-8 text-center">
                {loadingMore && (
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-gray-600 dark:text-gray-400">
                      더 불러오는 중...
                    </span>
                  </div>
                )}
              </div>
            )}

            {!hasMore && newsletters.length > 0 && (
              <div className="py-8 text-center text-gray-500 dark:text-gray-400">
                모든 뉴스레터를 불러왔습니다
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
