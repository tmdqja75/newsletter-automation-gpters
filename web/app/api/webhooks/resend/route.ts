import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

/**
 * Resend webhook event types
 * Reference: https://resend.com/docs/dashboard/webhooks/event-types
 */
type ResendEventType =
  | 'email.sent'
  | 'email.delivered'
  | 'email.delivery_delayed'
  | 'email.complained'
  | 'email.bounced'
  | 'email.opened'
  | 'email.clicked';

interface ResendWebhookEvent {
  type: ResendEventType;
  created_at: string;
  data: {
    email_id: string;
    from: string;
    to: string[];
    subject: string;
    created_at: string;
    // Additional fields depending on event type
    link?: {
      url: string;
    };
    bounce?: {
      type: string;
    };
  };
}

/**
 * Map Resend event types to our database event types
 */
function mapEventType(resendEventType: ResendEventType): string {
  const eventMap: Record<ResendEventType, string> = {
    'email.sent': 'sent',
    'email.delivered': 'delivered',
    'email.delivery_delayed': 'sent', // Keep as sent, could add delayed status
    'email.complained': 'complained',
    'email.bounced': 'bounced',
    'email.opened': 'opened',
    'email.clicked': 'clicked',
  };

  return eventMap[resendEventType] || 'sent';
}

/**
 * Webhook handler for Resend email events
 * Tracks: sent, delivered, opened, clicked, bounced, complained
 */
export async function POST(request: NextRequest) {
  try {
    const event: ResendWebhookEvent = await request.json();

    // TODO: Verify webhook signature for security
    // const signature = request.headers.get('resend-signature');
    // if (!verifySignature(signature, event)) {
    //   return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
    // }

    const supabase = await createClient();

    // Extract email ID from event
    const emailId = event.data.email_id;
    const eventType = mapEventType(event.type);

    // Find newsletter by email provider ID
    const { data: emailEvent } = await supabase
      .from('email_events')
      .select('newsletter_id, user_id')
      .eq('email_provider', 'resend')
      .eq('email_provider_id', emailId)
      .single();

    if (!emailEvent) {
      console.warn(
        `No email event found for Resend email ID: ${emailId}, creating new event`
      );

      // If we can't find the original event, we still log this event
      // but without newsletter/user association
      await supabase.from('email_events').insert({
        event_type: eventType,
        email_provider: 'resend',
        email_provider_id: emailId,
        metadata: {
          resend_event: event,
          note: 'Original send event not found',
        },
      });

      return NextResponse.json({ received: true });
    }

    // Prepare event metadata
    const metadata: Record<string, any> = {
      resend_event_type: event.type,
      created_at: event.created_at,
      from: event.data.from,
      to: event.data.to,
      subject: event.data.subject,
    };

    // Add event-specific data
    if (event.type === 'email.clicked' && event.data.link) {
      metadata.clicked_url = event.data.link.url;
    }

    if (event.type === 'email.bounced' && event.data.bounce) {
      metadata.bounce_type = event.data.bounce.type;
    }

    // Extract user agent and IP from headers if available
    const userAgent = request.headers.get('user-agent');
    const ip = request.headers.get('x-forwarded-for') || request.ip;

    // Insert new event
    const { error: insertError } = await supabase.from('email_events').insert({
      newsletter_id: emailEvent.newsletter_id,
      user_id: emailEvent.user_id,
      event_type: eventType,
      email_provider: 'resend',
      email_provider_id: emailId,
      clicked_url: event.type === 'email.clicked' ? event.data.link?.url : null,
      user_agent: userAgent,
      ip_address: ip,
      metadata,
    });

    if (insertError) {
      console.error('Failed to insert email event:', insertError);
      return NextResponse.json(
        { error: 'Failed to log event' },
        { status: 500 }
      );
    }

    console.log(
      `Logged email event: ${eventType} for newsletter ${emailEvent.newsletter_id}`
    );

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('Webhook processing error:', error);
    return NextResponse.json(
      {
        error: 'Webhook processing failed',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
