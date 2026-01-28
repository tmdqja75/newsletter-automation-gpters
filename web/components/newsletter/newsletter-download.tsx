'use client';

import { Button } from '@/components/ui/button';
import { downloadAsMarkdown } from '@/lib/utils/download';
import toast from 'react-hot-toast';

interface NewsletterDownloadProps {
  content: any;
  title: string;
}

export function NewsletterDownload({
  content,
  title,
}: NewsletterDownloadProps) {
  const handleDownload = () => {
    try {
      const filename = `${title
        .replace(/[^a-zA-Z0-9가-힣]/g, '-')
        .toLowerCase()}.md`;
      downloadAsMarkdown(content, filename);
      toast.success('다운로드가 시작되었습니다.');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('다운로드에 실패했습니다.');
    }
  };

  return (
    <Button variant="outline" onClick={handleDownload} className="w-full">
      <svg
        className="w-4 h-4 mr-2"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
        />
      </svg>
      다운로드 (Markdown)
    </Button>
  );
}
