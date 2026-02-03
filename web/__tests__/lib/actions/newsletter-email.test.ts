import { describe, it, expect, vi, beforeEach } from 'vitest';
import { sendNewsletterEmail } from '@/lib/actions/newsletter';
import { sendUnsentNewsletter } from '@/lib/email/send-newsletter';

vi.mock('@/lib/email/send-newsletter', () => ({
  sendUnsentNewsletter: vi.fn(),
}));

describe('sendNewsletterEmail server action', () => {
  const mockNewsletterId = 'newsletter-123';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should send email successfully', async () => {
    vi.mocked(sendUnsentNewsletter).mockResolvedValueOnce({
      success: true,
      emailId: 'email-123',
    });

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(true);
    expect(result.message).toContain('성공적으로 발송');
    expect(result.emailId).toBe('email-123');
    expect(result.sentAt).toBeDefined();
    expect(sendUnsentNewsletter).toHaveBeenCalledWith(mockNewsletterId);
  });

  it('should handle send failure', async () => {
    vi.mocked(sendUnsentNewsletter).mockResolvedValueOnce({
      success: false,
      error: '이메일 발송에 실패했습니다.',
    });

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(false);
    expect(result.message).toContain('발송에 실패');
  });

  it('should handle network error', async () => {
    vi.mocked(sendUnsentNewsletter).mockRejectedValueOnce(
      new Error('Network error')
    );

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(false);
    expect(result.message).toContain('오류가 발생');
  });

  it('should handle already sent newsletter', async () => {
    vi.mocked(sendUnsentNewsletter).mockResolvedValueOnce({
      success: false,
      alreadySent: true,
    });

    const result = await sendNewsletterEmail(mockNewsletterId);

    expect(result.success).toBe(true);
    expect(result.message).toBe('이미 발송된 뉴스레터입니다.');
  });
});
