'use client';

import { useState, useEffect, useCallback } from 'react';
import { useInView } from 'react-intersection-observer';
import Link from 'next/link';
import { getUserNewsletters } from '@/lib/actions/newsletter';
import { NewsletterCard } from '@/components/newsletter/newsletter-card';
import { NewsletterFilters } from '@/components/newsletter/newsletter-filters';
import { downloadAsMarkdown } from '@/lib/utils/download';
import toast from 'react-hot-toast';

export default function DashboardPage() {
  const [newsletters, setNewsletters] = useState<any[]>([]);
  const [topics, setTopics] = useState<Array<{ id: string; topic: string }>>(
    []
  );
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
              { id: n.user_topics.id, topic: n.user_topics.topic_text },
            ])
          ).values()
        );
        setTopics((prev) => {
          const merged = [...prev, ...uniqueTopics];
          return Array.from(new Map(merged.map((t) => [t.id, t])).values());
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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadNewsletters(0, false);
  }, [search, selectedTopic, sortBy, loadNewsletters]);

  // Load more when scrolling
  useEffect(() => {
    if (inView && hasMore && !loadingMore && !loading) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadNewsletters(newsletters.length, true);
    }
  }, [
    inView,
    hasMore,
    loadingMore,
    loading,
    newsletters.length,
    loadNewsletters,
  ]);

  const handleDelete = () => {
    // Reload newsletters after delete
    loadNewsletters(0, false);
  };

  const handleDownload = async (id: string, title: string) => {
    try {
      // Find the newsletter in the current list
      const newsletter = newsletters.find((n) => n.id === id);
      if (!newsletter) {
        toast.error('뉴스레터를 찾을 수 없습니다.');
        return;
      }

      // Generate filename from title
      const filename = `${title
        .replace(/[^a-zA-Z0-9가-힣]/g, '-')
        .toLowerCase()}.md`;

      downloadAsMarkdown(newsletter.content, filename);
      toast.success('다운로드가 시작되었습니다.');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('다운로드에 실패했습니다.');
    }
  };

  if (loading && newsletters.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
          <p className="text-gray-600 dark:text-gray-400">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6">
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
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            새 뉴스레터 생성하기 →
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Page Title */}
        <div className="mb-6">
          <h1 className="mb-2 text-3xl font-bold text-gray-900 dark:text-gray-100">
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
          <div className="rounded-lg border border-gray-200 bg-white py-12 text-center dark:border-gray-700 dark:bg-gray-800">
            <div className="mx-auto max-w-md">
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
                <button className="mt-6 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700">
                  뉴스레터 생성하기
                </button>
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
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
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
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
