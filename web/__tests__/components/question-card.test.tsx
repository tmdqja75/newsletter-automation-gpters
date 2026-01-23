import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuestionCard } from '@/components/question-card';
import type { Question } from '@/lib/validation/question';

describe('QuestionCard', () => {
  const mockOnChange = vi.fn();
  const mockOnSkip = vi.fn();

  const createQuestion = (
    type: Question['question_type'],
    required: boolean = false,
    options: string[] = []
  ): Question => ({
    id: '550e8400-e29b-41d4-a716-446655440000',
    topic_id: '550e8400-e29b-41d4-a716-446655440001',
    question_text: '테스트 질문입니다',
    question_type: type,
    options,
    display_order: 1,
    is_required: required,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Radio Question', () => {
    it('should render radio question with options', () => {
      const question = createQuestion('goal', true, [
        '업무',
        '학습',
        '투자',
        '기타',
      ]);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(screen.getByText('테스트 질문입니다')).toBeInTheDocument();
      expect(screen.getByText('*')).toBeInTheDocument(); // Required indicator
      expect(screen.getByText('업무')).toBeInTheDocument();
      expect(screen.getByText('학습')).toBeInTheDocument();
      expect(screen.getByText('투자')).toBeInTheDocument();
      expect(screen.getByText('기타')).toBeInTheDocument();
    });

    it('should call onChange when radio option is selected', async () => {
      const user = userEvent.setup();
      const question = createQuestion('goal', true, ['업무', '학습']);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      const radioOption = screen.getByLabelText('업무');
      await user.click(radioOption);

      expect(mockOnChange).toHaveBeenCalledWith({
        type: 'radio',
        value: '업무',
      });
    });

    it('should show selected radio option', () => {
      const question = createQuestion('goal', true, ['업무', '학습']);

      render(
        <QuestionCard
          question={question}
          value={{ type: 'radio', value: '업무' }}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      const radioOption = screen.getByLabelText('업무') as HTMLInputElement;
      expect(radioOption.checked).toBe(true);
    });
  });

  describe('Checkbox Question', () => {
    it('should render checkbox question with options', () => {
      const question = createQuestion('source', false, [
        '공식 문서',
        '학술 논문',
        '테크 블로그',
      ]);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(screen.getByText('공식 문서')).toBeInTheDocument();
      expect(screen.getByText('학술 논문')).toBeInTheDocument();
      expect(screen.getByText('테크 블로그')).toBeInTheDocument();
    });

    it('should call onChange when checkbox is selected', async () => {
      const user = userEvent.setup();
      const question = createQuestion('source', false, [
        '공식 문서',
        '학술 논문',
      ]);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      const checkbox = screen.getByLabelText('공식 문서');
      await user.click(checkbox);

      expect(mockOnChange).toHaveBeenCalledWith({
        type: 'checkbox',
        value: ['공식 문서'],
      });
    });

    it('should handle multiple checkbox selections', async () => {
      const user = userEvent.setup();
      const question = createQuestion('source', false, [
        '공식 문서',
        '학술 논문',
      ]);

      render(
        <QuestionCard
          question={question}
          value={{ type: 'checkbox', value: ['공식 문서'] }}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      const checkbox = screen.getByLabelText('학술 논문');
      await user.click(checkbox);

      expect(mockOnChange).toHaveBeenCalledWith({
        type: 'checkbox',
        value: ['공식 문서', '학술 논문'],
      });
    });

    it('should handle checkbox deselection', async () => {
      const user = userEvent.setup();
      const question = createQuestion('source', false, [
        '공식 문서',
        '학술 논문',
      ]);

      render(
        <QuestionCard
          question={question}
          value={{ type: 'checkbox', value: ['공식 문서', '학술 논문'] }}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      const checkbox = screen.getByLabelText('공식 문서');
      await user.click(checkbox);

      expect(mockOnChange).toHaveBeenCalledWith({
        type: 'checkbox',
        value: ['학술 논문'],
      });
    });
  });

  describe('Text Question', () => {
    it('should render text input question', () => {
      const question = createQuestion('subtopic', false);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(
        screen.getByPlaceholderText('답변을 입력해주세요')
      ).toBeInTheDocument();
      expect(screen.getByText('0/500')).toBeInTheDocument();
    });

    it('should call onChange when text is entered', async () => {
      const user = userEvent.setup();
      const question = createQuestion('subtopic', false);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      const input = screen.getByPlaceholderText('답변을 입력해주세요');
      await user.type(input, '에이전트 프레임워크');

      expect(mockOnChange).toHaveBeenCalled();
    });

    it('should show character count', () => {
      const question = createQuestion('subtopic', false);

      render(
        <QuestionCard
          question={question}
          value={{ type: 'text', value: '에이전트 프레임워크' }}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(screen.getByText('10/500')).toBeInTheDocument();
    });
  });

  describe('Skip Functionality', () => {
    it('should show skip button for non-required questions', () => {
      const question = createQuestion('subtopic', false);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(screen.getByText('스킵')).toBeInTheDocument();
    });

    it('should not show skip button for required questions', () => {
      const question = createQuestion('goal', true, ['업무', '학습']);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(screen.queryByText('스킵')).not.toBeInTheDocument();
    });

    it('should call onSkip when skip button is clicked', async () => {
      const user = userEvent.setup();
      const question = createQuestion('subtopic', false);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      const skipButton = screen.getByText('스킵');
      await user.click(skipButton);

      expect(mockOnSkip).toHaveBeenCalled();
      expect(mockOnChange).toHaveBeenCalledWith(undefined);
    });

    it('should show skipped state', () => {
      const question = createQuestion('subtopic', false);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={true}
        />
      );

      expect(screen.getByText(/이 질문을 건너뛰었습니다/)).toBeInTheDocument();
      expect(screen.getByText('답변하기')).toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
    it('should display error message', () => {
      const question = createQuestion('goal', true, ['업무', '학습']);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
          error="필수 질문입니다"
        />
      );

      expect(screen.getByText('필수 질문입니다')).toBeInTheDocument();
    });

    it('should not display error when skipped', () => {
      const question = createQuestion('goal', false, ['업무', '학습']);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={true}
          error="필수 질문입니다"
        />
      );

      expect(screen.queryByText('필수 질문입니다')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible labels for radio inputs', () => {
      const question = createQuestion('goal', true, ['업무', '학습']);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(screen.getByLabelText('업무')).toBeInTheDocument();
      expect(screen.getByLabelText('학습')).toBeInTheDocument();
    });

    it('should have accessible labels for checkbox inputs', () => {
      const question = createQuestion('source', false, [
        '공식 문서',
        '학술 논문',
      ]);

      render(
        <QuestionCard
          question={question}
          onChange={mockOnChange}
          onSkip={mockOnSkip}
          skipped={false}
        />
      );

      expect(screen.getByLabelText('공식 문서')).toBeInTheDocument();
      expect(screen.getByLabelText('학술 논문')).toBeInTheDocument();
    });
  });
});
