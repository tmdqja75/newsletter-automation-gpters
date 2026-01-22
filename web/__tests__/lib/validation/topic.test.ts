import { describe, it, expect } from 'vitest';
import { topicSchema, validateTopic } from '@/lib/validation/topic';

describe('Topic Validation', () => {
  describe('topicSchema', () => {
    it('should accept valid topics with 5-100 characters', () => {
      const validTopics = [
        'AI 에이전트',
        'AI 에이전트 최신 동향',
        'LLM 프롬프팅 기법',
        'RAG 시스템 구현 방법',
        '에이전트 기반 코딩 도구(2026 트렌드)',
      ];

      validTopics.forEach((topic) => {
        const result = topicSchema.safeParse(topic);
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data).toBe(topic);
        }
      });
    });

    it('should reject topics shorter than 5 characters', () => {
      const shortTopics = ['AI', 'LLM', 'RAG', 'GPT'];

      shortTopics.forEach((topic) => {
        const result = topicSchema.safeParse(topic);
        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0]?.message).toBe(
            '주제는 최소 5자 이상이어야 합니다.'
          );
        }
      });
    });

    it('should reject topics longer than 100 characters', () => {
      const longTopic = 'a'.repeat(101);
      const result = topicSchema.safeParse(longTopic);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.message).toBe(
          '주제는 최대 100자까지 입력할 수 있습니다.'
        );
      }
    });

    it('should accept topics with exactly 5 characters', () => {
      const result = topicSchema.safeParse('AI기술학');
      expect(result.success).toBe(true);
    });

    it('should accept topics with exactly 100 characters', () => {
      const exactlyHundred = 'a'.repeat(100);
      const result = topicSchema.safeParse(exactlyHundred);
      expect(result.success).toBe(true);
    });

    it('should reject topics containing profanity', () => {
      const profaneTopics = [
        '개새끼 같은 AI',
        'AI 에이전트 개새끼',
      ];

      profaneTopics.forEach((topic) => {
        const result = topicSchema.safeParse(topic);
        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0]?.message).toBe(
            '부적절한 내용이 포함되어 있습니다.'
          );
        }
      });
    });
  });

  describe('validateTopic', () => {
    it('should return success for valid topics', () => {
      const result = validateTopic('AI 에이전트 최신 동향');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe('AI 에이전트 최신 동향');
      }
    });

    it('should return error for invalid topics', () => {
      const result = validateTopic('AI');
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues).toHaveLength(1);
        expect(result.error.issues[0]?.message).toBe(
          '주제는 최소 5자 이상이어야 합니다.'
        );
      }
    });

    it('should return error for profane topics', () => {
      const result = validateTopic('개새끼 같은 주제입니다');
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.message).toBe(
          '부적절한 내용이 포함되어 있습니다.'
        );
      }
    });
  });
});
