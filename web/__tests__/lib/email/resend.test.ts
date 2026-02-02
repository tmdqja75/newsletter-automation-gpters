import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock send function factory
const createMockSend = () => vi.fn();
let mockSend = createMockSend();

// Mock Resend
vi.mock('resend', () => {
  return {
    Resend: vi.fn().mockImplementation(function (this: any) {
      this.emails = {
        get send() {
          return mockSend;
        },
      };
    }),
  };
});

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

// Import after mocks are set up
import { sendNewsletterEmail } from '@/lib/email/resend';

describe('sendNewsletterEmail', () => {
  beforeEach(() => {
    mockSend = createMockSend();
    vi.clearAllMocks();
  });

  it('should send email successfully', async () => {
    mockSend.mockResolvedValue({
      data: { id: 'email-123' },
      error: null,
    });

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
    mockSend.mockResolvedValue({
      data: null,
      error: { message: 'API error' },
    });

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
    mockSend.mockResolvedValue({
      data: {},
      error: null,
    });

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
    mockSend.mockRejectedValue(new Error('Network error'));

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
    mockSend.mockRejectedValue('String error');

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
