'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
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
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <div className="flex flex-col gap-4">
        {/* Search Bar */}
        <div>
          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
            검색
          </label>
          <Input
            type="text"
            placeholder="제목 또는 주제로 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Topic Filter */}
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
              주제 필터
            </label>
            <select
              value={selectedTopic}
              onChange={(e) => handleTopicChange(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
            <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
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
