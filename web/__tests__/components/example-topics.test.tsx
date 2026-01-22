import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExampleTopics } from '@/components/example-topics';

describe('ExampleTopics', () => {
  it('should render all example topics', () => {
    const onTopicSelect = vi.fn();
    render(<ExampleTopics onTopicSelect={onTopicSelect} />);

    expect(screen.getByText('AI 에이전트 최신 동향')).toBeInTheDocument();
    expect(screen.getByText('LLM 프롬프팅 기법')).toBeInTheDocument();
    expect(screen.getByText('RAG 시스템 구현 방법')).toBeInTheDocument();
  });

  it('should render the helper text', () => {
    const onTopicSelect = vi.fn();
    render(<ExampleTopics onTopicSelect={onTopicSelect} />);

    expect(screen.getByText('예시 주제를 클릭해보세요')).toBeInTheDocument();
  });

  it('should call onTopicSelect with correct topic when clicked', async () => {
    const user = userEvent.setup();
    const onTopicSelect = vi.fn();
    render(<ExampleTopics onTopicSelect={onTopicSelect} />);

    const firstTopic = screen.getByText('AI 에이전트 최신 동향');
    await user.click(firstTopic);

    expect(onTopicSelect).toHaveBeenCalledWith('AI 에이전트 최신 동향');
    expect(onTopicSelect).toHaveBeenCalledTimes(1);
  });

  it('should call onTopicSelect for each topic independently', async () => {
    const user = userEvent.setup();
    const onTopicSelect = vi.fn();
    render(<ExampleTopics onTopicSelect={onTopicSelect} />);

    await user.click(screen.getByText('AI 에이전트 최신 동향'));
    expect(onTopicSelect).toHaveBeenCalledWith('AI 에이전트 최신 동향');

    await user.click(screen.getByText('LLM 프롬프팅 기법'));
    expect(onTopicSelect).toHaveBeenCalledWith('LLM 프롬프팅 기법');

    await user.click(screen.getByText('RAG 시스템 구현 방법'));
    expect(onTopicSelect).toHaveBeenCalledWith('RAG 시스템 구현 방법');

    expect(onTopicSelect).toHaveBeenCalledTimes(3);
  });

  it('should render buttons with correct type', () => {
    const onTopicSelect = vi.fn();
    render(<ExampleTopics onTopicSelect={onTopicSelect} />);

    const buttons = screen.getAllByRole('button');
    buttons.forEach((button) => {
      expect(button).toHaveAttribute('type', 'button');
    });
  });
});
