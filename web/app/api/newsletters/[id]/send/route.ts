import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { sendNewsletterEmail } from '@/lib/email/resend';
import { env } from '@/lib/env';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const supabase = await createClient();

    // Verify authentication
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized', message: '로그인이 필요합니다.' },
        { status: 401 }
      );
    }

    // Fetch newsletter with ownership check
    const { data: newsletter, error: fetchError } = await supabase
      .from('newsletters')
      .select(
        `
        id,
        user_id,
        topic_id,
        title,
        body,
        email_sent_at,
        user_topics!inner(topic_text)
      `
      )
      .eq('id', id)
      .eq('user_id', user.id)
      .single();

    if (fetchError || !newsletter) {
      return NextResponse.json(
        { error: 'Not found', message: '뉴스레터를 찾을 수 없습니다.' },
        { status: 404 }
      );
    }

    // Check if already sent
    if (newsletter.email_sent_at) {
      return NextResponse.json(
        {
          error: 'Already sent',
          message: '이미 발송된 뉴스레터입니다.',
          sentAt: newsletter.email_sent_at,
        },
        { status: 400 }
      );
    }

    // Construct newsletter URL
    const siteUrl = env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
    const newsletterUrl = `${siteUrl}/newsletters/${newsletter.id}`;

    // Send email via Resend
    const emailResult = await sendNewsletterEmail({
      userEmail: user.email!,
      topic: (newsletter.user_topics as any).topic_text,
      newsletterId: newsletter.id,
      newsletterUrl,
    });

    if (!emailResult.success) {
      // Log failed attempt
      await supabase.from('email_events').insert({
        newsletter_id: newsletter.id,
        user_id: user.id,
        event_type: 'failed',
        email_provider: 'resend',
        metadata: {
          error: emailResult.error,
        },
      });

      return NextResponse.json(
        {
          error: 'Email send failed',
          message: '이메일 발송에 실패했습니다.',
          details: emailResult.error,
        },
        { status: 500 }
      );
    }

    // Update newsletter with sent timestamp
    const { error: updateError } = await supabase
      .from('newsletters')
      .update({ email_sent_at: new Date().toISOString() })
      .eq('id', newsletter.id);

    if (updateError) {
      console.error('Failed to update email_sent_at:', updateError);
    }

    // Log successful send
    const { error: logError } = await supabase.from('email_events').insert({
      newsletter_id: newsletter.id,
      user_id: user.id,
      event_type: 'sent',
      email_provider: 'resend',
      email_provider_id: emailResult.id,
      metadata: {
        recipient: user.email,
        topic: (newsletter.user_topics as any).topic_text,
      },
    });

    if (logError) {
      console.error('Failed to log email event:', logError);
    }

    return NextResponse.json({
      success: true,
      message: '이메일이 성공적으로 발송되었습니다.',
      emailId: emailResult.id,
      sentAt: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Email send error:', error);
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: '서버 오류가 발생했습니다.',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
