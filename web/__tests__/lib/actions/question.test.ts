import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getQuestionsByTopicId,
  saveAnswers,
  getUserAnswers,
} from '@/lib/actions/question';

// Mock Supabase client
const mockSelect = vi.fn();
const mockInsert = vi.fn();
const mockUpsert = vi.fn();
const mockEq = vi.fn();
const mockSingle = vi.fn();
const mockOrder = vi.fn();
const mockFrom = vi.fn();
const mockGetUser = vi.fn();

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: mockGetUser,
    },
    from: mockFrom,
  })),
}));

describe('Question Actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFrom.mockReturnValue({
      select: mockSelect,
      insert: mockInsert,
      upsert: mockUpsert,
    });
    mockSelect.mockReturnValue({
      eq: mockEq,
    });
    mockEq.mockReturnValue({
      single: mockSingle,
      eq: mockEq,
      order: mockOrder,
    });
    mockOrder.mockReturnValue({
      data: [],
      error: null,
    });
  });

  describe('getQuestionsByTopicId', () => {
    it('should get questions successfully', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      const mockQuestions = [
        {
          id: '550e8400-e29b-41d4-a716-446655440001',
          topic_id: '550e8400-e29b-41d4-a716-446655440002',
          question_text: '이 주제를 알아보는 목적이 무엇인가요?',
          question_type: 'goal',
          options: ['업무', '학습', '투자', '기타'],
          display_order: 1,
          is_required: true,
        },
      ];

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock topic verification
      mockSingle.mockResolvedValueOnce({
        data: { id: '550e8400-e29b-41d4-a716-446655440002' },
        error: null,
      });

      // Mock questions fetch
      mockOrder.mockResolvedValueOnce({
        data: mockQuestions,
        error: null,
      });

      const result = await getQuestionsByTopicId(
        '550e8400-e29b-41d4-a716-446655440002'
      );

      expect(result.success).toBe(true);
      expect(result.questions).toHaveLength(1);
      expect(result.questions?.[0]?.question_text).toBe(
        '이 주제를 알아보는 목적이 무엇인가요?'
      );
    });

    it('should require authentication', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: { message: 'Not authenticated' },
      });

      const result = await getQuestionsByTopicId(
        '550e8400-e29b-41d4-a716-446655440002'
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe('로그인이 필요합니다.');
    });

    it('should verify topic belongs to user', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      mockSingle.mockResolvedValueOnce({
        data: null,
        error: { code: 'PGRST116' },
      });

      const result = await getQuestionsByTopicId(
        '550e8400-e29b-41d4-a716-446655440002'
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe('주제를 찾을 수 없습니다.');
    });
  });

  describe('saveAnswers', () => {
    it('should save answers successfully', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock topic verification
      mockSingle.mockResolvedValueOnce({
        data: { id: '550e8400-e29b-41d4-a716-446655440002' },
        error: null,
      });

      // Mock answers upsert
      mockUpsert.mockReturnValueOnce({
        data: null,
        error: null,
      });

      const answers = [
        {
          question_id: '550e8400-e29b-41d4-a716-446655440001',
          answer_text: '업무',
          answer_value: { value: '업무' },
          skipped: false,
        },
      ];

      const result = await saveAnswers(
        '550e8400-e29b-41d4-a716-446655440002',
        answers
      );

      expect(result.success).toBe(true);
      expect(result.message).toBe('답변이 저장되었습니다.');
    });

    it('should require authentication', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: { message: 'Not authenticated' },
      });

      const answers = [
        {
          question_id: '550e8400-e29b-41d4-a716-446655440001',
          answer_text: '업무',
          answer_value: { value: '업무' },
          skipped: false,
        },
      ];

      const result = await saveAnswers(
        '550e8400-e29b-41d4-a716-446655440002',
        answers
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe('로그인이 필요합니다.');
    });

    it('should filter out skipped questions', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      mockSingle.mockResolvedValueOnce({
        data: { id: '550e8400-e29b-41d4-a716-446655440002' },
        error: null,
      });

      const answers = [
        {
          question_id: '550e8400-e29b-41d4-a716-446655440001',
          answer_text: '업무',
          answer_value: { value: '업무' },
          skipped: false,
        },
        {
          question_id: '550e8400-e29b-41d4-a716-446655440003',
          answer_text: null,
          answer_value: null,
          skipped: true,
        },
      ];

      mockUpsert.mockImplementationOnce((data) => {
        expect(data).toHaveLength(1);
        return { data: null, error: null };
      });

      const result = await saveAnswers(
        '550e8400-e29b-41d4-a716-446655440002',
        answers
      );

      expect(result.success).toBe(true);
    });

    it('should reject if all questions are skipped', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      mockSingle.mockResolvedValueOnce({
        data: { id: '550e8400-e29b-41d4-a716-446655440002' },
        error: null,
      });

      const answers = [
        {
          question_id: '550e8400-e29b-41d4-a716-446655440001',
          answer_text: null,
          answer_value: null,
          skipped: true,
        },
      ];

      const result = await saveAnswers(
        '550e8400-e29b-41d4-a716-446655440002',
        answers
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe('최소 1개 이상의 질문에 답변해주세요.');
    });

    it('should handle database error', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      mockSingle.mockResolvedValueOnce({
        data: { id: '550e8400-e29b-41d4-a716-446655440002' },
        error: null,
      });

      mockUpsert.mockReturnValueOnce({
        data: null,
        error: { message: 'Database error' },
      });

      const answers = [
        {
          question_id: '550e8400-e29b-41d4-a716-446655440001',
          answer_text: '업무',
          answer_value: { value: '업무' },
          skipped: false,
        },
      ];

      const result = await saveAnswers(
        '550e8400-e29b-41d4-a716-446655440002',
        answers
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe(
        '답변 저장에 실패했습니다. 다시 시도해주세요.'
      );
    });
  });

  describe('getUserAnswers', () => {
    it('should get user answers successfully', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      const mockAnswers = [
        {
          id: '550e8400-e29b-41d4-a716-446655440003',
          question_id: '550e8400-e29b-41d4-a716-446655440001',
          user_id: mockUser.id,
          answer_text: '업무',
          answer_value: { value: '업무' },
          personalization_questions: {
            topic_id: '550e8400-e29b-41d4-a716-446655440002',
          },
        },
      ];

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock the chained eq calls for getUserAnswers
      const mockSecondEq = vi.fn().mockReturnValue({
        data: mockAnswers,
        error: null,
      });

      mockEq.mockReturnValueOnce({
        eq: mockSecondEq,
      });

      const result = await getUserAnswers(
        '550e8400-e29b-41d4-a716-446655440002'
      );

      expect(result.success).toBe(true);
      expect(result.answers).toHaveLength(1);
    });

    it('should require authentication', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: { message: 'Not authenticated' },
      });

      const result = await getUserAnswers(
        '550e8400-e29b-41d4-a716-446655440002'
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe('로그인이 필요합니다.');
    });
  });
});
