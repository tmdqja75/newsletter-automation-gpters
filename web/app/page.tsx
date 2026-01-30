'use client';

import { useState } from 'react';
import { AuthStatus } from '@/components/auth/auth-status';
import { TopicInput } from '@/components/topic-input';
import { ExampleTopics } from '@/components/example-topics';
import { Container } from '@/components/ui/container';
import { ShaderAnimation } from '@/components/ui/shader-animation';

export default function Home() {
  const [topic, setTopic] = useState('');

  const handleTopicSelect = (selectedTopic: string) => {
    setTopic(selectedTopic);
  };

  return (
    <div className="relative flex min-h-screen flex-col">
      <ShaderAnimation />
      <header className="relative z-10 w-full py-4">
        <Container className="flex items-center justify-between" maxWidth="2xl">
          <h1 className="text-xl font-semibold text-white">Automata</h1>
          <AuthStatus />
        </Container>
      </header>

      <main className="relative z-10 flex flex-1 flex-col items-center justify-center gap-12 py-16">
        <Container
          className="flex flex-col items-center gap-6 text-center"
          maxWidth="md"
        >
          <h2 className="text-4xl leading-tight font-bold tracking-tight text-white sm:text-5xl">
            개인화된 리서치 뉴스레터
          </h2>
          <p className="max-w-2xl text-lg leading-relaxed text-zinc-300">
            관심 있는 주제를 입력하면, AI가 리서치하여 개인화된 뉴스레터를
            이메일로 전달해드립니다.
          </p>
        </Container>

        <TopicInput value={topic} onChange={setTopic} />

        <ExampleTopics onTopicSelect={handleTopicSelect} />
      </main>

      <footer className="relative z-10 w-full py-8">
        <Container
          className="flex items-center justify-center text-sm text-zinc-400"
          maxWidth="2xl"
        >
          © 2026 Automata. AI-powered newsletter service.
        </Container>
      </footer>
    </div>
  );
}
