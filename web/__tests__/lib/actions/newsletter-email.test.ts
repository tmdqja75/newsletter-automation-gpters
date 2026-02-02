import { describe, it, expect, vi, beforeEach } from 'vitest';
import { sendNewsletterEmail } from '@/lib/actions/newsletter';

// Mock env
vi.mock('@/lib/env', () => ({
  env: {
    NEXT_PUBLIC_SITE_URL: 'https://example.com',
  },
}));

// Mock fetch
global.fetch = vi.fn();

describe('sendNewsletterEmail server action', () => {
  const mockNewsletterId = 'newsletter-123';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should send email successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        message: '이메일이 성공적으로 발송되었습니다.',
        emailId: 'email-123',
        sentAt: '2026-01-01T00:00:00Z',
      }),
    });

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(true);
    expect(result.message).toContain('성공적으로 발송');
    expect(result.emailId).toBe('email-123');
    expect(result.sentAt).toBe('2026-01-01T00:00:00Z');
    expect(global.fetch).toHaveBeenCalledWith(
      `https://example.com/api/newsletters/${mockNewsletterId}/send`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  });

  it('should handle API error', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        message: '이메일 발송에 실패했습니다.',
      }),
    });

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(false);
    expect(result.message).toContain('발송에 실패');
  });

  it('should handle network error', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(false);
    expect(result.message).toContain('오류가 발생');
  });

  it('should use default message when API message is missing', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        emailId: 'email-123',
      }),
    });

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(true);
    expect(result.message).toBe('이메일이 성공적으로 발송되었습니다.');
  });
});
