/**
 * Test script to send a newsletter email
 * Usage: npx tsx scripts/test-email.ts
 */

import { config } from 'dotenv';
import { resolve } from 'path';
import { Resend } from 'resend';
import { render } from '@react-email/render';
import NewsletterEmail from '../emails/newsletter';

// Load environment variables from .env.local
config({ path: resolve(__dirname, '../.env.local') });

async function testEmailSend() {
  console.log('🚀 Testing email send functionality...\n');

  // Check if API key is set
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    console.error('❌ Error: RESEND_API_KEY is not set or using dummy value');
    console.log('\n📝 To get a real API key:');
    console.log('1. Go to https://resend.com');
    console.log('2. Sign up or log in');
    console.log('3. Create an API key');
    console.log('4. Update RESEND_API_KEY in .env.local\n');
    process.exit(1);
  }

  console.log('🔑 API Key loaded:', apiKey.substring(0, 10) + '...');

  const resend = new Resend(apiKey);

  // Test data
  const testData = {
    userEmail: 'tmdqja75@gmail.com',
    topic: 'AI 에이전트 최신 동향',
    newsletterId: 'test-newsletter-123',
    newsletterUrl:
      'http://localhost:3000/newsletter/e696ee66-d179-491b-9b0d-cd657bac9996',
  };

  try {
    console.log('📧 Sending test email to:', testData.userEmail);
    console.log('📋 Topic:', testData.topic);
    console.log('🔗 Newsletter URL:', testData.newsletterUrl);
    console.log();

    // Render email HTML
    const emailHtml = await render(
      NewsletterEmail({
        userEmail: testData.userEmail,
        topic: testData.topic,
        newsletterId: testData.newsletterId,
        newsletterUrl: testData.newsletterUrl,
      })
    );

    // Send email via Resend
    const { data, error } = await resend.emails.send({
      from: 'Automata Newsletter <onboarding@resend.dev>', // Use verified domain
      to: [testData.userEmail],
      subject: `이번 주 ${testData.topic}에 대한 뉴스레터가 완성되었어요`,
      html: emailHtml,
    });

    if (error) {
      console.error('❌ Error sending email:', error);
      process.exit(1);
    }

    console.log('✅ Email sent successfully!');
    console.log('📬 Email ID:', data?.id);
    console.log('\n💡 Check your inbox at tmdqja75@gmail.com');
    console.log("   (Don't forget to check spam folder)");
  } catch (error) {
    console.error('❌ Unexpected error:', error);
    process.exit(1);
  }
}

testEmailSend();
