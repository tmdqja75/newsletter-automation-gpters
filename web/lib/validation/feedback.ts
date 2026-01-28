import { z } from 'zod';

// Structured feedback options
export const structuredFeedbackSchema = z.object({
  more_depth: z.boolean().optional(),
  easier_explanation: z.boolean().optional(),
  different_sources: z.boolean().optional(),
});

// Main feedback schema
export const feedbackSchema = z.object({
  newsletter_id: z.string().uuid('올바른 뉴스레터 ID가 아닙니다'),
  thumbs_up: z.boolean(),
  structured_feedback: structuredFeedbackSchema.optional(),
  comment: z
    .string()
    .max(500, '코멘트는 최대 500자까지 입력 가능합니다')
    .optional()
    .nullable(),
});

// Feedback submission schema (for server actions)
export const submitFeedbackSchema = z.object({
  newsletter_id: z.string().uuid(),
  thumbs_up: z.boolean(),
  structured_feedback: structuredFeedbackSchema.optional().nullable(),
  comment: z
    .string()
    .max(500, '코멘트는 최대 500자까지 입력 가능합니다')
    .optional()
    .nullable(),
});

// Feedback response schema (from database)
export const feedbackResponseSchema = z.object({
  id: z.string().uuid(),
  newsletter_id: z.string().uuid(),
  user_id: z.string().uuid(),
  thumbs_up: z.boolean(),
  structured_feedback: structuredFeedbackSchema.nullable(),
  comment: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string().optional(),
});

// Export types
export type StructuredFeedback = z.infer<typeof structuredFeedbackSchema>;
export type Feedback = z.infer<typeof feedbackSchema>;
export type SubmitFeedbackInput = z.infer<typeof submitFeedbackSchema>;
export type FeedbackResponse = z.infer<typeof feedbackResponseSchema>;

// Helper function to validate feedback
export function validateFeedback(
  data: unknown
): { valid: boolean; data?: SubmitFeedbackInput; error?: string } {
  try {
    const validated = submitFeedbackSchema.parse(data);
    return { valid: true, data: validated };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { valid: false, error: error.issues[0]?.message };
    }
    return { valid: false, error: '피드백 형식이 올바르지 않습니다' };
  }
}
