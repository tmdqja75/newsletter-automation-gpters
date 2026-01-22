'use client';

interface ExampleTopicsProps {
  onTopicSelect: (topic: string) => void;
}

const EXAMPLE_TOPICS = [
  'AI 에이전트 최신 동향',
  'LLM 프롬프팅 기법',
  'RAG 시스템 구현 방법',
];

export function ExampleTopics({ onTopicSelect }: ExampleTopicsProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        예시 주제를 클릭해보세요
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        {EXAMPLE_TOPICS.map((topic) => (
          <button
            key={topic}
            type="button"
            onClick={() => onTopicSelect(topic)}
            className="rounded-full border border-solid border-zinc-200 px-4 py-2 text-sm transition-colors hover:border-zinc-400 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:border-zinc-600 dark:hover:bg-zinc-900"
          >
            {topic}
          </button>
        ))}
      </div>
    </div>
  );
}
