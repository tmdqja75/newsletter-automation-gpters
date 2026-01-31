'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

interface NewsletterFiltersProps {
  topics: Array<{ id: string; topic: string }>;
  onSearchChange: (search: string) => void;
  onTopicChange: (topicId: string) => void;
  onSortChange: (sort: 'newest' | 'oldest') => void;
}

export function NewsletterFilters({
  topics,
  onSearchChange,
  onTopicChange,
  onSortChange,
}: NewsletterFiltersProps) {
  const [search, setSearch] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest');

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(search);
    }, 500);

    return () => clearTimeout(timer);
  }, [search, onSearchChange]);

  const handleTopicChange = (topicId: string) => {
    setSelectedTopic(topicId);
    onTopicChange(topicId);
  };

  const handleSortChange = (newSort: 'newest' | 'oldest') => {
    setSortBy(newSort);
    onSortChange(newSort);
  };

  const handleClearFilters = () => {
    setSearch('');
    setSelectedTopic('');
    setSortBy('newest');
    onSearchChange('');
    onTopicChange('');
    onSortChange('newest');
  };

  const hasActiveFilters = search || selectedTopic;

  return (
    <div className="mb-8 rounded-lg border border-zinc-200 bg-zinc-50 p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex flex-col gap-4">
        {/* Search Bar */}
        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
            검색
          </label>
          <input
            type="text"
            placeholder="제목 또는 주제로 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-full border border-solid border-zinc-200 px-6 py-4 text-base transition-colors outline-none placeholder:text-zinc-400 focus:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:placeholder:text-zinc-600 dark:focus:border-zinc-600"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Topic Filter */}
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              주제 필터
            </label>
            <select
              value={selectedTopic}
              onChange={(e) => handleTopicChange(e.target.value)}
              className="w-full rounded-full border border-solid border-zinc-200 px-6 py-4 text-base transition-colors outline-none focus:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100 dark:focus:border-zinc-600"
            >
              <option value="">모든 주제</option>
              {topics.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.topic}
                </option>
              ))}
            </select>
          </div>

          {/* Sort */}
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              정렬
            </label>
            <div className="flex gap-2">
              <Button
                variant={sortBy === 'newest' ? 'default' : 'outline'}
                onClick={() => handleSortChange('newest')}
                className="flex-1"
              >
                최신순
              </Button>
              <Button
                variant={sortBy === 'oldest' ? 'default' : 'outline'}
                onClick={() => handleSortChange('oldest')}
                className="flex-1"
              >
                오래된순
              </Button>
            </div>
          </div>
        </div>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <div className="flex justify-end">
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              필터 초기화
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
