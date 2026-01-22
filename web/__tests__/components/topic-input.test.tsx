import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TopicInput } from '@/components/topic-input';
import toast from 'react-hot-toast';

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('TopicInput', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render input field with placeholder', () => {
    render(<TopicInput value="" onChange={mockOnChange} />);

    const input = screen.getByPlaceholderText('어떤 주제로 리서치해 드릴까요?');
    expect(input).toBeInTheDocument();
  });

  it('should render submit button', () => {
    render(<TopicInput value="" onChange={mockOnChange} />);

    expect(screen.getByText('리서치 시작하기')).toBeInTheDocument();
  });

  it('should display character counter', () => {
    render(<TopicInput value="" onChange={mockOnChange} />);

    expect(screen.getByText('0 / 100')).toBeInTheDocument();
  });

  it('should update character counter when value changes', () => {
    const { rerender } = render(
      <TopicInput value="" onChange={mockOnChange} />
    );

    expect(screen.getByText('0 / 100')).toBeInTheDocument();

    rerender(<TopicInput value="AI 에이전트" onChange={mockOnChange} />);
    expect(screen.getByText('7 / 100')).toBeInTheDocument();
  });

  it('should call onChange when typing in input', async () => {
    const user = userEvent.setup();
    render(<TopicInput value="" onChange={mockOnChange} />);

    const input = screen.getByPlaceholderText('어떤 주제로 리서치해 드릴까요?');
    await user.type(input, 'AI 에이전트');

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('should disable submit button when value is empty', () => {
    render(<TopicInput value="" onChange={mockOnChange} />);

    const submitButton = screen.getByText('리서치 시작하기');
    expect(submitButton).toBeDisabled();
  });

  it('should enable submit button when value is not empty', () => {
    render(<TopicInput value="AI 에이전트" onChange={mockOnChange} />);

    const submitButton = screen.getByText('리서치 시작하기');
    expect(submitButton).not.toBeDisabled();
  });

  it('should show error toast for invalid input (too short)', async () => {
    const user = userEvent.setup();
    render(<TopicInput value="AI" onChange={mockOnChange} />);

    await user.click(screen.getByText('리서치 시작하기'));

    expect(toast.error).toHaveBeenCalledWith(
      '주제는 최소 5자 이상이어야 합니다.'
    );
  });

  it('should show error toast for profane input', async () => {
    const user = userEvent.setup();
    render(<TopicInput value="개새끼 같은 주제" onChange={mockOnChange} />);

    await user.click(screen.getByText('리서치 시작하기'));

    expect(toast.error).toHaveBeenCalledWith(
      '부적절한 내용이 포함되어 있습니다.'
    );
  });

  it('should show success toast for valid input', async () => {
    const user = userEvent.setup();
    render(
      <TopicInput value="AI 에이전트 최신 동향" onChange={mockOnChange} />
    );

    await user.click(screen.getByText('리서치 시작하기'));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        '주제가 성공적으로 제출되었습니다!'
      );
    });
  });

  it('should show loading state during submission', async () => {
    const user = userEvent.setup();
    render(
      <TopicInput value="AI 에이전트 최신 동향" onChange={mockOnChange} />
    );

    const submitButton = screen.getByText('리서치 시작하기');
    await user.click(submitButton);

    expect(screen.getByText('제출 중...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('리서치 시작하기')).toBeInTheDocument();
    });
  });

  it('should disable input and button during submission', async () => {
    const user = userEvent.setup();
    render(
      <TopicInput value="AI 에이전트 최신 동향" onChange={mockOnChange} />
    );

    const input = screen.getByPlaceholderText('어떤 주제로 리서치해 드릴까요?');
    const submitButton = screen.getByText('리서치 시작하기');

    await user.click(submitButton);

    expect(input).toBeDisabled();
    expect(screen.getByText('제출 중...')).toBeDisabled();

    await waitFor(() => {
      expect(input).not.toBeDisabled();
    });
  });

  it('should enforce max length of 100 characters', () => {
    render(<TopicInput value="" onChange={mockOnChange} />);

    const input = screen.getByPlaceholderText(
      '어떤 주제로 리서치해 드릴까요?'
    ) as HTMLInputElement;
    expect(input.maxLength).toBe(100);
  });

  it('should highlight character counter when over limit', () => {
    const overLimitValue = 'a'.repeat(101);
    render(<TopicInput value={overLimitValue} onChange={mockOnChange} />);

    const counter = screen.getByText('101 / 100');
    expect(counter).toHaveClass('text-red-500');
  });
});
