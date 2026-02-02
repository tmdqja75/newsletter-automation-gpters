import {
  Body,
  Button,
  Container,
  Head,
  Heading,
  Html,
  Preview,
  Section,
  Text,
} from '@react-email/components';

interface NewsletterEmailProps {
  userEmail?: string;
  topic?: string;
  newsletterId?: string;
  newsletterUrl: string;
}

export default function NewsletterEmail({
  topic = '예시 주제',
  newsletterUrl,
}: NewsletterEmailProps) {
  const previewText = `이번 주 ${topic}에 대한 뉴스레터가 완성되었어요`;

  return (
    <Html>
      <Head />
      <Preview>{previewText}</Preview>
      <Body style={main}>
        <Container style={container}>
          <Section style={section}>
            <Heading style={h1}>Automata</Heading>
            <Text style={text}>안녕하세요,</Text>
            <Text style={text}>
              이번 주 <strong>{topic}</strong>에 대한 뉴스레터가 완성되었어요.
            </Text>
            <Text style={text}>아래 버튼을 눌러 읽을 수 있습니다.</Text>
            <Section style={buttonContainer}>
              <Button style={button} href={newsletterUrl}>
                뉴스레터 읽기
              </Button>
            </Section>
            <Text style={footer}>
              © 2026 Automata. AI-powered personalized research newsletter.
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

const main = {
  backgroundColor: '#f9fafb',
  fontFamily:
    '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Ubuntu,sans-serif',
};

const container = {
  margin: '0 auto',
  padding: '20px 0 48px',
  maxWidth: '560px',
};

const section = {
  padding: '32px',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  backgroundColor: '#ffffff',
  boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
};

const h1 = {
  color: '#000000',
  fontSize: '24px',
  fontWeight: '700',
  margin: '0 0 24px',
  padding: '0',
  lineHeight: '1.25',
};

const text = {
  color: '#1f2937',
  fontSize: '16px',
  lineHeight: '1.6',
  margin: '0 0 16px',
};

const buttonContainer = {
  margin: '32px 0',
  textAlign: 'center' as const,
};

const button = {
  backgroundColor: '#000000',
  borderRadius: '9999px',
  color: '#ffffff',
  fontSize: '16px',
  fontWeight: '600',
  textDecoration: 'none',
  textAlign: 'center' as const,
  display: 'inline-block',
  padding: '12px 32px',
};

const footer = {
  color: '#6b7280',
  fontSize: '14px',
  lineHeight: '1.5',
  margin: '32px 0 0',
  textAlign: 'center' as const,
};
