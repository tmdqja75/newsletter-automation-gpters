import { z } from 'zod';
import { containsProfanity } from './profanity';

export const topicSchema = z
  .string()
  .min(5, {
    message: '주제는 최소 5자 이상이어야 합니다.',
  })
  .max(100, {
    message: '주제는 최대 100자까지 입력할 수 있습니다.',
  })
  .refine((text) => !containsProfanity(text), {
    message: '부적절한 내용이 포함되어 있습니다.',
  });

export type TopicInput = z.infer<typeof topicSchema>;

/**
 * Validates a topic input string
 * @param topic - The topic string to validate
 * @returns Validation result with success status and data/error
 */
export function validateTopic(topic: string) {
  return topicSchema.safeParse(topic);
}
