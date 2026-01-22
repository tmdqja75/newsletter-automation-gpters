import { describe, it, expect } from 'vitest';
import { containsProfanity, cleanProfanity } from '@/lib/validation/profanity';

describe('Profanity Filter', () => {
  describe('containsProfanity', () => {
    it('should return false for clean text', () => {
      expect(containsProfanity('AI 에이전트 최신 동향')).toBe(false);
      expect(containsProfanity('LLM 프롬프팅 기법')).toBe(false);
      expect(containsProfanity('RAG 시스템 구현 방법')).toBe(false);
    });

    it('should return false for empty or whitespace-only text', () => {
      expect(containsProfanity('')).toBe(false);
      expect(containsProfanity('   ')).toBe(false);
      expect(containsProfanity('\n\t')).toBe(false);
    });

    it('should return true for text containing Korean profanity', () => {
      // Note: badwords-ko will filter common Korean profanity
      // Testing with a known profane word that badwords-ko detects
      const textWithProfanity = '이건 개새끼 같은 내용이야';
      expect(containsProfanity(textWithProfanity)).toBe(true);
    });

    it('should handle mixed content correctly', () => {
      const mixedText = 'AI 에이전트는 좋지만 개새끼는 나빠';
      expect(containsProfanity(mixedText)).toBe(true);
    });
  });

  describe('cleanProfanity', () => {
    it('should return the same text if no profanity is detected', () => {
      const cleanText = 'AI 에이전트 최신 동향';
      expect(cleanProfanity(cleanText)).toBe(cleanText);
    });

    it('should return empty string for empty input', () => {
      expect(cleanProfanity('')).toBe('');
    });

    it('should replace profanity with asterisks', () => {
      const textWithProfanity = '이건 개새끼 같은 내용이야';
      const cleaned = cleanProfanity(textWithProfanity);
      expect(cleaned).toContain('***');
      expect(cleaned).not.toContain('개새끼');
    });

    it('should preserve clean parts of mixed content', () => {
      const mixedText = 'AI 에이전트는 개새끼';
      const cleaned = cleanProfanity(mixedText);
      expect(cleaned).toContain('AI 에이전트는');
      expect(cleaned).toContain('***');
    });
  });
});
