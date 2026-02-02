import { Resend } from 'resend';
import { render } from '@react-email/render';
import NewsletterEmail from '@/emails/newsletter';
import { env } from '@/lib/env';

const resend = new Resend(env.RESEND_API_KEY);

export interface NewsletterEmailData {
  userEmail: string;
  topic: string;
  newsletterId: string;
  newsletterUrl: string;
}

export interface SendEmailResult {
  id: string;
  success: boolean;
  error?: string;
}

/**
 * Send newsletter email using Resend
 */
export async function sendNewsletterEmail(
  data: NewsletterEmailData
): Promise<SendEmailResult> {
  try {
    const emailHtml = await render(
      NewsletterEmail({
        userEmail: data.userEmail,
        topic: data.topic,
        newsletterId: data.newsletterId,
        newsletterUrl: data.newsletterUrl,
      })
    );

    const { data: emailData, error } = await resend.emails.send({
      from: 'Automata Newsletter <newsletter@automata.com>',
      to: [data.userEmail],
      subject: `이번 주 ${data.topic}에 대한 뉴스레터가 완성되었어요`,
      html: emailHtml,
    });

    if (error) {
      console.error('Resend email error:', error);
      return {
        id: '',
        success: false,
        error: error.message || 'Failed to send email',
      };
    }

    if (!emailData?.id) {
      return {
        id: '',
        success: false,
        error: 'No email ID returned from Resend',
      };
    }

    return {
      id: emailData.id,
      success: true,
    };
  } catch (error) {
    console.error('Email send error:', error);
    return {
      id: '',
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
