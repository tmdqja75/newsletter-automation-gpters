import { createAdminClient } from '@/lib/supabase/server';
import { sendUnsentNewsletter } from '@/lib/email/send-newsletter';

export async function GET(request: Request) {
  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const supabase = createAdminClient();

  // --- Phase 1: Send any published newsletters that haven't been emailed yet ---
  const { data: unsent } = await supabase
    .from('newsletters')
    .select('id')
    .eq('is_published', true)
    .is('email_sent_at', null);

  let emailSent = 0;
  let emailAlreadySent = 0;
  let emailFailed = 0;

  if (unsent && unsent.length > 0) {
    const sendResults = await Promise.allSettled(
      unsent.map((n: { id: string }) => sendUnsentNewsletter(n.id))
    );

    for (const result of sendResults) {
      if (result.status === 'fulfilled') {
        if (result.value.success) {
          emailSent++;
        } else if (result.value.alreadySent) {
          emailAlreadySent++;
        } else {
          emailFailed++;
        }
      } else {
        emailFailed++;
      }
    }
  }

  // --- Phase 2: Trigger generation for users scheduled for tomorrow ---
  // Calculate tomorrow's day of week (0=Sun, 1=Mon, ..., 6=Sat)
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowDayOfWeek = tomorrow.getDay();

  // Find users whose delivery day is tomorrow with weekly frequency
  const { data: preferences, error: prefError } = await supabase
    .from('user_preferences')
    .select('user_id')
    .eq('preferred_send_day', tomorrowDayOfWeek)
    .eq('send_frequency', 'weekly')
    .eq('email_enabled', true);

  if (prefError) {
    console.error('Error fetching preferences:', prefError);
    return Response.json(
      { error: 'Failed to fetch preferences' },
      { status: 500 }
    );
  }

  if (!preferences || preferences.length === 0) {
    return Response.json({
      message: 'No users scheduled for tomorrow',
      emails: {
        sent: emailSent,
        alreadySent: emailAlreadySent,
        failed: emailFailed,
      },
    });
  }

  const userIds = preferences.map((p) => p.user_id);

  // Find active topics for these users
  const { data: topics, error: topicsError } = await supabase
    .from('user_topics')
    .select('id, user_id')
    .in('user_id', userIds)
    .eq('is_active', true);

  if (topicsError) {
    console.error('Error fetching topics:', topicsError);
    return Response.json({ error: 'Failed to fetch topics' }, { status: 500 });
  }

  if (!topics || topics.length === 0) {
    return Response.json({
      message: 'No active topics found',
      emails: {
        sent: emailSent,
        alreadySent: emailAlreadySent,
        failed: emailFailed,
      },
    });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Trigger generation for each user's topic
  const results = await Promise.allSettled(
    topics.map(async (topic) => {
      const response = await fetch(`${apiUrl}/api/newsletter/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: topic.user_id,
          topic_id: topic.id,
        }),
      });

      if (!response.ok) {
        throw new Error(
          `Generation failed for topic ${topic.id}: ${response.status}`
        );
      }

      return response.json();
    })
  );

  const fulfilled = results.filter((r) => r.status === 'fulfilled').length;
  const rejected = results.filter((r) => r.status === 'rejected').length;

  return Response.json({
    message: 'Cron completed',
    emails: {
      sent: emailSent,
      alreadySent: emailAlreadySent,
      failed: emailFailed,
    },
    scheduled_day: tomorrowDayOfWeek,
    users_found: userIds.length,
    topics_triggered: topics.length,
    fulfilled,
    rejected,
  });
}
