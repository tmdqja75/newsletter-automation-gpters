import { describe, it, expect, vi, beforeEach } from 'vitest';
import { sendNewsletterEmail } from '@/lib/email/resend';

// Mock Resend
vi.mock('resend', () => ({
  Resend: vi.fn().mockImplementation(() => ({
    emails: {
      send: vi.fn(),
    },
  })),
}));

// Mock React Email render
vi.mock('@react-email/render', () => ({
  render: vi.fn(() => '<html>Test Email HTML</html>'),
}));

// Mock env
vi.mock('@/lib/env', () => ({
  env: {
    RESEND_API_KEY: 'test-api-key',
  },
}));

describe('sendNewsletterEmail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should send email successfully', async () => {
    const { Resend } = await import('resend');
    const mockSend = vi.fn().mockResolvedValue({
      data: { id: 'email-123' },
      error: null,
    });

    (Resend as any).mockImplementation(() => ({
      emails: {
        send: mockSend,
      },
    }));

    const result = await sendNewsletterEmail({
      userEmail: 'user@example.com',
      topic: 'AI 에이전트',
      newsletterId: 'newsletter-123',
      newsletterUrl: 'https://example.com/newsletters/newsletter-123',
    });

    expect(result.success).toBe(true);
    expect(result.id).toBe('email-123');
    expect(result.error).toBeUndefined();
    expect(mockSend).toHaveBeenCalledWith({
      from: 'Automata Newsletter <newsletter@automata.com>',
      to: ['user@example.com'],
      subject: '이번 주 AI 에이전트에 대한 뉴스레터가 완성되었어요',
      html: '<html>Test Email HTML</html>',
    });
  });

  it('should handle Resend API error', async () => {
    const { Resend } = await import('resend');
    const mockSend = vi.fn().mockResolvedValue({
      data: null,
      error: { message: 'API error' },
    });

    (Resend as any).mockImplementation(() => ({
      emails: {
        send: mockSend,
      },
    }));

    const result = await sendNewsletterEmail({
      userEmail: 'user@example.com',
      topic: 'AI 에이전트',
      newsletterId: 'newsletter-123',
      newsletterUrl: 'https://example.com/newsletters/newsletter-123',
    });

    expect(result.success).toBe(false);
    expect(result.id).toBe('');
    expect(result.error).toBe('API error');
  });

  it('should handle missing email ID in response', async () => {
    const { Resend } = await import('resend');
    const mockSend = vi.fn().mockResolvedValue({
      data: {},
      error: null,
    });

    (Resend as any).mockImplementation(() => ({
      emails: {
        send: mockSend,
      },
    }));

    const result = await sendNewsletterEmail({
      userEmail: 'user@example.com',
      topic: 'AI 에이전트',
      newsletterId: 'newsletter-123',
      newsletterUrl: 'https://example.com/newsletters/newsletter-123',
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe('No email ID returned from Resend');
  });

  it('should handle thrown errors', async () => {
    const { Resend } = await import('resend');
    const mockSend = vi.fn().mockRejectedValue(new Error('Network error'));

    (Resend as any).mockImplementation(() => ({
      emails: {
        send: mockSend,
      },
    }));

    const result = await sendNewsletterEmail({
      userEmail: 'user@example.com',
      topic: 'AI 에이전트',
      newsletterId: 'newsletter-123',
      newsletterUrl: 'https://example.com/newsletters/newsletter-123',
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe('Network error');
  });

  it('should handle non-Error thrown values', async () => {
    const { Resend } = await import('resend');
    const mockSend = vi.fn().mockRejectedValue('String error');

    (Resend as any).mockImplementation(() => ({
      emails: {
        send: mockSend,
      },
    }));

    const result = await sendNewsletterEmail({
      userEmail: 'user@example.com',
      topic: 'AI 에이전트',
      newsletterId: 'newsletter-123',
      newsletterUrl: 'https://example.com/newsletters/newsletter-123',
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe('Unknown error');
  });
});
