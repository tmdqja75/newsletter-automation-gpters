import NewsletterEmail from '@/emails/newsletter';

export default function EmailPreviewPage() {
  // Sample data for preview
  const sampleData = {
    userEmail: 'user@example.com',
    topic: 'AI 에이전트 최신 동향',
    newsletterId: 'sample-newsletter-id',
    newsletterUrl: 'http://localhost:3000/newsletter/sample-id',
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Email Template Preview
          </h1>
          <p className="text-gray-600">
            This is how the newsletter email will look when sent to users.
          </p>
        </div>

        {/* Email preview container with border to simulate email client */}
        <div className="border-2 border-gray-300 rounded-lg overflow-hidden shadow-lg">
          <div className="bg-gray-200 px-4 py-2 border-b border-gray-300">
            <p className="text-sm text-gray-600">
              <strong>From:</strong> Automata Newsletter{' '}
              &lt;newsletter@automata.com&gt;
            </p>
            <p className="text-sm text-gray-600">
              <strong>To:</strong> {sampleData.userEmail}
            </p>
            <p className="text-sm text-gray-600">
              <strong>Subject:</strong> 이번 주 {sampleData.topic}에 대한
              뉴스레터가 완성되었어요
            </p>
          </div>

          {/* Render the actual email template */}
          <div className="bg-white">
            <NewsletterEmail
              userEmail={sampleData.userEmail}
              topic={sampleData.topic}
              newsletterId={sampleData.newsletterId}
              newsletterUrl={sampleData.newsletterUrl}
            />
          </div>
        </div>

        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h2 className="text-lg font-semibold text-blue-900 mb-2">
            💡 Preview Tips
          </h2>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• This preview shows exactly how the email will render</li>
            <li>
              • The light gray outer background helps the white content stand
              out
            </li>
            <li>• Text is dark for better readability</li>
            <li>
              • Click the button to test the link (it will open in a new tab)
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
