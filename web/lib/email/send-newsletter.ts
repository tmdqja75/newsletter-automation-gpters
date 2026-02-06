import { createAdminClient } from '@/lib/supabase/server';
import { sendNewsletterEmail } from '@/lib/email/resend';
import { env } from '@/lib/env';

export interface SendUnsentNewsletterResult {
  success: boolean;
  emailId?: string;
  error?: string;
  alreadySent?: boolean;
}

/**
 * Server-side utility to send a newsletter email using the admin client.
 * Safe to call from cron jobs or any server context without cookie dependency.
 */
export async function sendUnsentNewsletter(
  newsletterId: string
): Promise<SendUnsentNewsletterResult> {
  const supabase = createAdminClient();

  // Fetch newsletter with topic
  const { data: newsletter, error: fetchError } = await supabase
    .from('newsletters')
    .select(
      `
      id,
      user_id,
      topic_id,
      email_sent_at,
      user_topics!inner(topic_text, created_at)
    `
    )
    .eq('id', newsletterId)
    .single<{
      id: string;
      user_id: string;
      topic_id: string;
      email_sent_at: string | null;
      user_topics: {
        topic_text: string;
        created_at: string;
      };
    }>();

  if (fetchError || !newsletter) {
    return { success: false, error: 'Newsletter not found' };
  }

  // Already sent — idempotent short-circuit
  if (newsletter.email_sent_at) {
    return { success: false, alreadySent: true };
  }

  // Check 4-week limit
  const topicCreatedAt = new Date(newsletter.user_topics.created_at);
  const fourWeeksInMs = 4 * 7 * 24 * 60 * 60 * 1000;
  if (Date.now() - topicCreatedAt.getTime() > fourWeeksInMs) {
    return { success: false, error: 'Topic exceeded 4-week limit' };
  }

  // Look up user email via admin API
  const { data: userData, error: userError } =
    await supabase.auth.admin.getUserById(newsletter.user_id);

  if (userError || !userData?.user?.email) {
    return { success: false, error: 'Failed to fetch user email' };
  }

  const siteUrl = env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
  const newsletterUrl = `${siteUrl}/newsletter/${newsletter.id}`;

  // Send via Resend
  const emailResult = await sendNewsletterEmail({
    userEmail: userData.user.email,
    topic: newsletter.user_topics.topic_text,
    newsletterId: newsletter.id,
    newsletterUrl,
  });

  if (!emailResult.success) {
    await supabase.from('email_events').insert({
      newsletter_id: newsletter.id,
      user_id: newsletter.user_id,
      event_type: 'failed',
      email_provider: 'resend',
      metadata: { error: emailResult.error },
    });
    return { success: false, error: emailResult.error };
  }

  // Persist sent timestamp
  await supabase
    .from('newsletters')
    .update({ email_sent_at: new Date().toISOString() })
    .eq('id', newsletter.id);

  // Log success event
  await supabase.from('email_events').insert({
    newsletter_id: newsletter.id,
    user_id: newsletter.user_id,
    event_type: 'sent',
    email_provider: 'resend',
    email_provider_id: emailResult.id,
    metadata: {
      recipient: userData.user.email,
      topic: newsletter.user_topics.topic_text,
    },
  });

  return { success: true, emailId: emailResult.id };
}
