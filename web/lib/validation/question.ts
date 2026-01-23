import { z } from 'zod';

// Question types from database schema
export const questionTypeEnum = z.enum([
  'goal',
  'difficulty',
  'scope',
  'time',
  'source',
  'subtopic',
  'custom',
]);

// Base question schema
export const questionSchema = z.object({
  id: z.string().uuid(),
  topic_id: z.string().uuid(),
  question_text: z.string().min(1, '질문이 비어있습니다'),
  question_type: questionTypeEnum,
  options: z.array(z.string()).optional(),
  display_order: z.number().int().min(0),
  is_required: z.boolean(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

// Answer validation for different question types
export const radioAnswerSchema = z.object({
  type: z.literal('radio'),
  value: z.string().min(1, '선택지를 선택해주세요'),
});

export const checkboxAnswerSchema = z.object({
  type: z.literal('checkbox'),
  value: z.array(z.string()).min(1, '최소 1개 이상 선택해주세요'),
});

export const textAnswerSchema = z.object({
  type: z.literal('text'),
  value: z
    .string()
    .min(1, '답변을 입력해주세요')
    .max(500, '답변은 최대 500자까지 입력 가능합니다'),
});

// Union type for all answer types
export const answerSchema = z.discriminatedUnion('type', [
  radioAnswerSchema,
  checkboxAnswerSchema,
  textAnswerSchema,
]);

// Single answer submission
export const userAnswerSchema = z.object({
  question_id: z.string().uuid(),
  answer_text: z.string().nullable().optional(),
  answer_value: z.record(z.unknown()).nullable().optional(),
  skipped: z.boolean().default(false),
});

// Bulk answer submission
export const saveAnswersSchema = z.object({
  topic_id: z.string().uuid(),
  answers: z.array(userAnswerSchema).min(1, '최소 1개 이상의 답변이 필요합니다'),
});

// Question with answer (for form state)
export const questionWithAnswerSchema = questionSchema.extend({
  answer: answerSchema.optional(),
  skipped: z.boolean().default(false),
});

// Export types
export type QuestionType = z.infer<typeof questionTypeEnum>;
export type Question = z.infer<typeof questionSchema>;
export type RadioAnswer = z.infer<typeof radioAnswerSchema>;
export type CheckboxAnswer = z.infer<typeof checkboxAnswerSchema>;
export type TextAnswer = z.infer<typeof textAnswerSchema>;
export type Answer = z.infer<typeof answerSchema>;
export type UserAnswer = z.infer<typeof userAnswerSchema>;
export type SaveAnswersInput = z.infer<typeof saveAnswersSchema>;
export type QuestionWithAnswer = z.infer<typeof questionWithAnswerSchema>;

// Helper function to get answer type from question type
export function getAnswerTypeFromQuestionType(
  questionType: QuestionType,
): 'radio' | 'checkbox' | 'text' {
  switch (questionType) {
    case 'goal':
    case 'difficulty':
    case 'time':
      return 'radio';
    case 'source':
    case 'scope':
      return 'checkbox';
    case 'subtopic':
    case 'custom':
      return 'text';
    default:
      return 'text';
  }
}

// Validate answer based on question type
export function validateAnswerForQuestion(
  question: Question,
  answer: Answer | undefined,
  skipped: boolean,
): { valid: boolean; error?: string } {
  // If skipped and not required, it's valid
  if (skipped && !question.is_required) {
    return { valid: true };
  }

  // Required questions must have an answer
  if (question.is_required && (!answer || skipped)) {
    return { valid: false, error: '필수 질문입니다' };
  }

  // If not required and no answer, it's valid
  if (!answer && !question.is_required) {
    return { valid: true };
  }

  // Validate answer type matches question type
  const expectedType = getAnswerTypeFromQuestionType(question.question_type);
  if (answer && answer.type !== expectedType) {
    return { valid: false, error: '답변 형식이 올바르지 않습니다' };
  }

  // Validate answer value
  try {
    answerSchema.parse(answer);
    return { valid: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { valid: false, error: error.errors[0]?.message };
    }
    return { valid: false, error: '답변이 올바르지 않습니다' };
  }
}
