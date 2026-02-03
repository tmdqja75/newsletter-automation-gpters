import { describe, it, expect } from 'vitest';
import {
  questionSchema,
  radioAnswerSchema,
  checkboxAnswerSchema,
  textAnswerSchema,
  answerSchema,
  userAnswerSchema,
  saveAnswersSchema,
  validateAnswerForQuestion,
  getAnswerTypeFromQuestionType,
  type Question,
  type Answer,
} from '@/lib/validation/question';

describe('Question Validation Schemas', () => {
  describe('questionSchema', () => {
    it('should validate a complete question', () => {
      const validQuestion = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        topic_id: '550e8400-e29b-41d4-a716-446655440001',
        question_text: '이 주제를 알아보는 목적이 무엇인가요?',
        question_type: 'goal' as const,
        options: ['업무', '학습', '투자', '기타'],
        display_order: 1,
        is_required: true,
      };

      const result = questionSchema.safeParse(validQuestion);
      expect(result.success).toBe(true);
    });

    it('should reject invalid question type', () => {
      const invalidQuestion = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        topic_id: '550e8400-e29b-41d4-a716-446655440001',
        question_text: 'Test question',
        question_type: 'invalid_type',
        options: [],
        display_order: 1,
        is_required: false,
      };

      const result = questionSchema.safeParse(invalidQuestion);
      expect(result.success).toBe(false);
    });

    it('should reject empty question text', () => {
      const invalidQuestion = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        topic_id: '550e8400-e29b-41d4-a716-446655440001',
        question_text: '',
        question_type: 'goal' as const,
        options: [],
        display_order: 1,
        is_required: false,
      };

      const result = questionSchema.safeParse(invalidQuestion);
      expect(result.success).toBe(false);
    });
  });

  describe('radioAnswerSchema', () => {
    it('should validate a valid radio answer', () => {
      const validAnswer = {
        type: 'radio' as const,
        value: '업무',
      };

      const result = radioAnswerSchema.safeParse(validAnswer);
      expect(result.success).toBe(true);
    });

    it('should reject empty radio answer', () => {
      const invalidAnswer = {
        type: 'radio' as const,
        value: '',
      };

      const result = radioAnswerSchema.safeParse(invalidAnswer);
      expect(result.success).toBe(false);
    });
  });

  describe('checkboxAnswerSchema', () => {
    it('should validate a valid checkbox answer', () => {
      const validAnswer = {
        type: 'checkbox' as const,
        value: ['공식 문서', '테크 블로그'],
      };

      const result = checkboxAnswerSchema.safeParse(validAnswer);
      expect(result.success).toBe(true);
    });

    it('should reject empty checkbox array', () => {
      const invalidAnswer = {
        type: 'checkbox' as const,
        value: [],
      };

      const result = checkboxAnswerSchema.safeParse(invalidAnswer);
      expect(result.success).toBe(false);
    });
  });

  describe('textAnswerSchema', () => {
    it('should validate a valid text answer', () => {
      const validAnswer = {
        type: 'text' as const,
        value: '에이전트 프레임워크 비교',
      };

      const result = textAnswerSchema.safeParse(validAnswer);
      expect(result.success).toBe(true);
    });

    it('should reject empty text answer', () => {
      const invalidAnswer = {
        type: 'text' as const,
        value: '',
      };

      const result = textAnswerSchema.safeParse(invalidAnswer);
      expect(result.success).toBe(false);
    });

    it('should reject text answer exceeding 500 characters', () => {
      const invalidAnswer = {
        type: 'text' as const,
        value: 'a'.repeat(501),
      };

      const result = textAnswerSchema.safeParse(invalidAnswer);
      expect(result.success).toBe(false);
    });

    it('should accept text answer with exactly 500 characters', () => {
      const validAnswer = {
        type: 'text' as const,
        value: 'a'.repeat(500),
      };

      const result = textAnswerSchema.safeParse(validAnswer);
      expect(result.success).toBe(true);
    });
  });

  describe('answerSchema', () => {
    it('should validate different answer types', () => {
      const radioAnswer = {
        type: 'radio' as const,
        value: '중급',
      };
      const checkboxAnswer = {
        type: 'checkbox' as const,
        value: ['공식 문서'],
      };
      const textAnswer = {
        type: 'text' as const,
        value: 'LangGraph 활용 사례',
      };

      expect(answerSchema.safeParse(radioAnswer).success).toBe(true);
      expect(answerSchema.safeParse(checkboxAnswer).success).toBe(true);
      expect(answerSchema.safeParse(textAnswer).success).toBe(true);
    });
  });

  describe('userAnswerSchema', () => {
    it('should validate a complete user answer', () => {
      const validUserAnswer = {
        question_id: '550e8400-e29b-41d4-a716-446655440000',
        answer_text: '에이전트 프레임워크',
        answer_value: { value: '업무' },
        skipped: false,
      };

      const result = userAnswerSchema.safeParse(validUserAnswer);
      expect(result.success).toBe(true);
    });

    it('should default skipped to false', () => {
      const userAnswer = {
        question_id: '550e8400-e29b-41d4-a716-446655440000',
        answer_text: 'test',
      };

      const result = userAnswerSchema.safeParse(userAnswer);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.skipped).toBe(false);
      }
    });
  });

  describe('saveAnswersSchema', () => {
    it('should validate save answers input', () => {
      const validInput = {
        topic_id: '550e8400-e29b-41d4-a716-446655440000',
        answers: [
          {
            question_id: '550e8400-e29b-41d4-a716-446655440001',
            answer_text: '업무',
            answer_value: { value: '업무' },
            skipped: false,
          },
        ],
      };

      const result = saveAnswersSchema.safeParse(validInput);
      expect(result.success).toBe(true);
    });

    it('should reject empty answers array', () => {
      const invalidInput = {
        topic_id: '550e8400-e29b-41d4-a716-446655440000',
        answers: [],
      };

      const result = saveAnswersSchema.safeParse(invalidInput);
      expect(result.success).toBe(false);
    });
  });

  describe('getAnswerTypeFromQuestionType', () => {
    it('should return radio for goal question', () => {
      expect(getAnswerTypeFromQuestionType('goal')).toBe('radio');
    });

    it('should return radio for difficulty question', () => {
      expect(getAnswerTypeFromQuestionType('difficulty')).toBe('radio');
    });

    it('should return radio for time question', () => {
      expect(getAnswerTypeFromQuestionType('time')).toBe('radio');
    });

    it('should return checkbox for source question', () => {
      expect(getAnswerTypeFromQuestionType('source')).toBe('checkbox');
    });

    it('should return checkbox for scope question', () => {
      expect(getAnswerTypeFromQuestionType('scope')).toBe('checkbox');
    });

    it('should return text for subtopic question', () => {
      expect(getAnswerTypeFromQuestionType('subtopic')).toBe('text');
    });

    it('should return text for custom question', () => {
      expect(getAnswerTypeFromQuestionType('custom')).toBe('text');
    });

    it('should return radio for delivery_day question', () => {
      expect(getAnswerTypeFromQuestionType('delivery_day')).toBe('radio');
    });

    it('should return checkbox for generate_now question', () => {
      expect(getAnswerTypeFromQuestionType('generate_now')).toBe('checkbox');
    });
  });

  describe('validateAnswerForQuestion', () => {
    const createQuestion = (
      type: Question['question_type'],
      required: boolean
    ): Question => ({
      id: '550e8400-e29b-41d4-a716-446655440000',
      topic_id: '550e8400-e29b-41d4-a716-446655440001',
      question_text: 'Test question',
      question_type: type,
      options: type === 'goal' ? ['옵션1', '옵션2'] : undefined,
      display_order: 1,
      is_required: required,
    });

    it('should validate skipped non-required question', () => {
      const question = createQuestion('goal', false);
      const result = validateAnswerForQuestion(question, undefined, true);
      expect(result.valid).toBe(true);
    });

    it('should reject skipped required question', () => {
      const question = createQuestion('goal', true);
      const result = validateAnswerForQuestion(question, undefined, true);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('필수 질문입니다');
    });

    it('should validate correct answer type for question', () => {
      const question = createQuestion('goal', true);
      const answer: Answer = {
        type: 'radio',
        value: '옵션1',
      };
      const result = validateAnswerForQuestion(question, answer, false);
      expect(result.valid).toBe(true);
    });

    it('should reject mismatched answer type', () => {
      const question = createQuestion('goal', true);
      const answer: Answer = {
        type: 'text',
        value: 'some text',
      };
      const result = validateAnswerForQuestion(question, answer, false);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('답변 형식이 올바르지 않습니다');
    });

    it('should validate non-required question without answer', () => {
      const question = createQuestion('subtopic', false);
      const result = validateAnswerForQuestion(question, undefined, false);
      expect(result.valid).toBe(true);
    });

    it('should reject required question without answer', () => {
      const question = createQuestion('goal', true);
      const result = validateAnswerForQuestion(question, undefined, false);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('필수 질문입니다');
    });

    it('should validate delivery_day radio answer', () => {
      const question = createQuestion('delivery_day', true);
      const answer: Answer = { type: 'radio', value: '월요일' };
      const result = validateAnswerForQuestion(question, answer, false);
      expect(result.valid).toBe(true);
    });

    it('should reject delivery_day without answer (required)', () => {
      const question = createQuestion('delivery_day', true);
      const result = validateAnswerForQuestion(question, undefined, false);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('필수 질문입니다');
    });

    it('should validate generate_now checkbox answer', () => {
      const question = createQuestion('generate_now', false);
      const answer: Answer = {
        type: 'checkbox',
        value: ['지금 바로 생성하기'],
      };
      const result = validateAnswerForQuestion(question, answer, false);
      expect(result.valid).toBe(true);
    });

    it('should validate generate_now when skipped (not required)', () => {
      const question = createQuestion('generate_now', false);
      const result = validateAnswerForQuestion(question, undefined, true);
      expect(result.valid).toBe(true);
    });

    it('should reject generate_now with mismatched radio answer type', () => {
      const question = createQuestion('generate_now', false);
      const answer: Answer = { type: 'radio', value: '지금 바로 생성하기' };
      const result = validateAnswerForQuestion(question, answer, false);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('답변 형식이 올바르지 않습니다');
    });
  });

  describe('questionSchema with new types', () => {
    it('should validate delivery_day question type', () => {
      const question = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        topic_id: '550e8400-e29b-41d4-a716-446655440001',
        question_text: '뉴스레터를 매주 받고 싶은 요일을 선택해주세요',
        question_type: 'delivery_day' as const,
        options: [
          '월요일',
          '화요일',
          '수요일',
          '목요일',
          '금요일',
          '토요일',
          '일요일',
        ],
        display_order: 7,
        is_required: true,
      };

      const result = questionSchema.safeParse(question);
      expect(result.success).toBe(true);
    });

    it('should validate generate_now question type', () => {
      const question = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        topic_id: '550e8400-e29b-41d4-a716-446655440001',
        question_text: '지금 바로 생성하고 싶으신가요?',
        question_type: 'generate_now' as const,
        options: ['지금 바로 생성하기'],
        display_order: 8,
        is_required: false,
      };

      const result = questionSchema.safeParse(question);
      expect(result.success).toBe(true);
    });
  });
});
