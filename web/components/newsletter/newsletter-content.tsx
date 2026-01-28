'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface NewsletterContentProps {
  content: {
    title: string;
    tldr: string;
    core_issues: Array<{
      title: string;
      summary: string;
      links: Array<{ url: string; title: string }>;
    }>;
    deep_dive: {
      title: string;
      content: string;
      additional_readings: Array<{
        url: string;
        title: string;
        description?: string;
      }>;
    };
    next_questions: string[];
    sources: Array<{
      url: string;
      title: string;
      domain: string;
      accessed_at: string;
    }>;
    word_count?: number;
    estimated_reading_time?: number;
  };
}

export function NewsletterContent({ content }: NewsletterContentProps) {
  return (
    <article className="prose prose-slate dark:prose-invert max-w-none">
      {/* Title */}
      <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100">
        {content.title}
      </h1>

      {/* Reading time */}
      {content.estimated_reading_time && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          예상 읽기 시간: {content.estimated_reading_time}분
        </p>
      )}

      {/* TL;DR Section */}
      <section className="mb-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <h2 className="text-xl font-semibold mb-3 text-blue-900 dark:text-blue-100">
          📝 TL;DR
        </h2>
        <div className="text-gray-700 dark:text-gray-300">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content.tldr}
          </ReactMarkdown>
        </div>
      </section>

      {/* Core Issues Section */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold mb-6 text-gray-900 dark:text-gray-100">
          핵심 이슈
        </h2>
        {content.core_issues.map((issue, index) => (
          <div
            key={index}
            className="mb-6 pb-6 border-b border-gray-200 dark:border-gray-700 last:border-b-0"
          >
            <h3 className="text-xl font-semibold mb-3 text-gray-900 dark:text-gray-100">
              {index + 1}. {issue.title}
            </h3>
            <div className="text-gray-700 dark:text-gray-300 mb-4">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code
                        className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {issue.summary}
              </ReactMarkdown>
            </div>
            {issue.links.length > 0 && (
              <div className="space-y-2">
                {issue.links.map((link, linkIndex) => (
                  <a
                    key={linkIndex}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-blue-600 dark:text-blue-400 mt-1">
                        🔗
                      </span>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900 dark:text-gray-100">
                          {link.title}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                          {link.url}
                        </p>
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
      </section>

      {/* Deep Dive Section */}
      <section className="mb-8 p-6 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
          🔍 Deep Dive: {content.deep_dive.title}
        </h2>
        <div className="text-gray-700 dark:text-gray-300 mb-6">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code
                    className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm"
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
            }}
          >
            {content.deep_dive.content}
          </ReactMarkdown>
        </div>
        {content.deep_dive.additional_readings.length > 0 && (
          <div>
            <h4 className="font-semibold mb-3 text-gray-900 dark:text-gray-100">
              추가 읽을거리
            </h4>
            <div className="space-y-3">
              {content.deep_dive.additional_readings.map((reading, index) => (
                <a
                  key={index}
                  href={reading.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors border border-gray-200 dark:border-gray-700"
                >
                  <p className="font-medium text-gray-900 dark:text-gray-100 mb-1">
                    {reading.title}
                  </p>
                  {reading.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                      {reading.description}
                    </p>
                  )}
                  <p className="text-xs text-gray-500 dark:text-gray-500 truncate">
                    {reading.url}
                  </p>
                </a>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Next Questions Section */}
      {content.next_questions.length > 0 && (
        <section className="mb-8">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
            💡 다음에 파볼 질문
          </h2>
          <ul className="space-y-2">
            {content.next_questions.map((question, index) => (
              <li
                key={index}
                className="flex items-start gap-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800"
              >
                <span className="text-yellow-600 dark:text-yellow-400 font-bold">
                  ?
                </span>
                <span className="text-gray-700 dark:text-gray-300">
                  {question}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Sources Section */}
      {content.sources.length > 0 && (
        <section className="mb-8">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
            📚 출처
          </h2>
          <ul className="space-y-2 text-sm">
            {content.sources.map((source, index) => (
              <li
                key={index}
                className="flex items-start gap-2 text-gray-600 dark:text-gray-400"
              >
                <span className="font-medium text-gray-500 dark:text-gray-500">
                  [{index + 1}]
                </span>
                <div className="flex-1">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {source.title}
                  </a>
                  <span className="text-gray-500 dark:text-gray-500 ml-2">
                    ({source.domain})
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
