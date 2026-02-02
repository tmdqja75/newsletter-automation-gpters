'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface NewsletterContentProps {
  content: {
    title: string;
    body: string;
    word_count?: number;
    estimated_reading_time?: number;
  };
}

export function NewsletterContent({ content }: NewsletterContentProps) {
  const normalizedBody = normalizeMarkdown(content.body);

  return (
    <article className="prose prose-zinc dark:prose-invert max-w-none">
      {/* Title */}
      <h1 className="mb-4 text-3xl font-bold text-zinc-950 dark:text-zinc-50">
        {content.title}
      </h1>

      {/* Reading time */}
      {content.estimated_reading_time && (
        <p className="mb-6 text-sm text-zinc-500 dark:text-zinc-400">
          예상 읽기 시간: {content.estimated_reading_time}분
        </p>
      )}

      {/* Markdown Body */}
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          hr() {
            return <hr className="my-8 border-zinc-200 dark:border-zinc-800" />;
          },
          h2(props) {
            return (
              <h2
                className="mt-8 scroll-m-20 text-2xl font-semibold text-zinc-950 dark:text-zinc-50"
                {...props}
              />
            );
          },
          h3(props) {
            return (
              <h3
                className="mt-6 scroll-m-20 text-xl font-semibold text-zinc-950 dark:text-zinc-50"
                {...props}
              />
            );
          },
          code(props) {
            const { inline, className, children, ...rest } = props as any;
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                {...rest}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code
                className="rounded bg-zinc-100 px-1.5 py-0.5 text-sm dark:bg-zinc-800"
                {...rest}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {normalizedBody}
      </ReactMarkdown>
    </article>
  );
}

function normalizeMarkdown(body: string) {
  if (!body) {
    return '';
  }

  let normalized = body.replace(/\r\n/g, '\n');

  // If the markdown was stored with escaped newlines, decode them.
  if (normalized.includes('\\n')) {
    normalized = normalized
      .replace(/\\r\\n/g, '\n')
      .replace(/\\n/g, '\n');
  }

  return normalized;
}
