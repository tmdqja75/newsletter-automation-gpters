import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createTopic, getTopicById } from '@/lib/actions/topic';

// Mock Supabase client
const mockSelect = vi.fn();
const mockInsert = vi.fn();
const mockEq = vi.fn();
const mockSingle = vi.fn();
const mockFrom = vi.fn();
const mockGetUser = vi.fn();
const mockGte = vi.fn();

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: mockGetUser,
    },
    from: mockFrom,
  })),
  createAdminClient: vi.fn(() => ({
    from: mockFrom,
  })),
}));

describe('Topic Actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup default mock behavior
    mockFrom.mockReturnValue({
      select: mockSelect,
      insert: mockInsert,
    });

    mockSelect.mockReturnValue({
      eq: mockEq,
      single: mockSingle,
    });

    mockEq.mockReturnValue({
      single: mockSingle,
      eq: mockEq,
      gte: mockGte,
    });

    mockGte.mockResolvedValue({
      data: [],
      error: null,
    });

    // Default mockInsert behavior - returns object with both error (for direct use) and select method (for chaining)
    mockInsert.mockReturnValue({
      error: null,
      data: null,
      select: vi.fn().mockReturnValue({
        single: mockSingle,
      }),
    });
  });

  describe('createTopic', () => {
    it('should create a topic successfully', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
        email_confirmed_at: new Date().toISOString(),
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock existing user check
      mockSingle.mockResolvedValueOnce({
        data: { id: mockUser.id },
        error: null,
      });

      // Mock topic creation
      mockSingle.mockResolvedValueOnce({
        data: {
          id: '550e8400-e29b-41d4-a716-446655440001',
          topic_text: 'AI 에이전트 최신 동향',
        },
        error: null,
      });

      // No need to mock questions insertion - default mockInsert returns { error: null }

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(true);
      expect(result.message).toBe('주제가 생성되었습니다.');
      expect(result.topicId).toBe('550e8400-e29b-41d4-a716-446655440001');
    });

    it('should reject topic with less than 5 characters', async () => {
      const formData = new FormData();
      formData.append('topic', 'AI');

      const result = await createTopic(formData);

      expect(result.success).toBe(false);
      expect(result.message).toContain('5자 이상');
    });

    it('should reject topic with profanity', async () => {
      const formData = new FormData();
      formData.append('topic', '씨발 주제입니다');

      const result = await createTopic(formData);

      expect(result.success).toBe(false);
      expect(result.message).toContain('부적절한');
    });

    it('should require authentication', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: { message: 'Not authenticated' },
      });

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(false);
      expect(result.message).toBe('로그인이 필요합니다.');
    });

    it('should create user if not exists', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'newuser@example.com',
        email_confirmed_at: new Date().toISOString(),
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock user not exists
      mockSingle.mockResolvedValueOnce({
        data: null,
        error: { code: 'PGRST116' },
      });

      // No need to mock user creation - default mockInsert returns { error: null }

      // Mock topic creation
      mockSingle.mockResolvedValueOnce({
        data: {
          id: '550e8400-e29b-41d4-a716-446655440001',
          topic_text: 'AI 에이전트 최신 동향',
        },
        error: null,
      });

      // No need to mock questions insertion - default mockInsert returns { error: null }

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(true);
    });

    it('should handle topic creation error', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
        email_confirmed_at: new Date().toISOString(),
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock existing user
      mockSingle.mockResolvedValueOnce({
        data: { id: mockUser.id },
        error: null,
      });

      // Mock topic creation error
      mockSingle.mockResolvedValueOnce({
        data: null,
        error: { message: 'Database error' },
      });

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(false);
      expect(result.message).toBe(
        '주제 생성에 실패했습니다. 다시 시도해주세요.'
      );
    });
  });

  describe('Rate limiting', () => {
    it('should allow topic creation with 0 existing topics', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
        email_confirmed_at: new Date().toISOString(),
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock existing user check
      mockSingle.mockResolvedValueOnce({
        data: { id: mockUser.id },
        error: null,
      });

      // Mock rate limit check - 0 existing topics
      mockGte.mockResolvedValueOnce({
        data: [],
        error: null,
      });

      // Mock topic creation
      mockSingle.mockResolvedValueOnce({
        data: {
          id: '550e8400-e29b-41d4-a716-446655440001',
          topic_text: 'AI 에이전트 최신 동향',
        },
        error: null,
      });

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(true);
      expect(result.message).toBe('주제가 생성되었습니다.');
    });

    it('should allow topic creation with 1 existing topic', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
        email_confirmed_at: new Date().toISOString(),
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock existing user check
      mockSingle.mockResolvedValueOnce({
        data: { id: mockUser.id },
        error: null,
      });

      // Mock rate limit check - 1 existing topic
      mockGte.mockResolvedValueOnce({
        data: [{ id: '550e8400-e29b-41d4-a716-446655440099' }],
        error: null,
      });

      // Mock topic creation
      mockSingle.mockResolvedValueOnce({
        data: {
          id: '550e8400-e29b-41d4-a716-446655440001',
          topic_text: 'AI 에이전트 최신 동향',
        },
        error: null,
      });

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(true);
      expect(result.message).toBe('주제가 생성되었습니다.');
    });

    it('should reject topic creation with 2 existing topics (at limit)', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
        email_confirmed_at: new Date().toISOString(),
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock existing user check
      mockSingle.mockResolvedValueOnce({
        data: { id: mockUser.id },
        error: null,
      });

      // Mock rate limit check - 2 existing topics
      mockGte.mockResolvedValueOnce({
        data: [
          { id: '550e8400-e29b-41d4-a716-446655440098' },
          { id: '550e8400-e29b-41d4-a716-446655440099' },
        ],
        error: null,
      });

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(false);
      expect(result.message).toBe('주당 최대 2개의 주제만 생성할 수 있습니다.');
    });

    it('should allow topic creation if rate limit check fails (fail open)', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
        email_confirmed_at: new Date().toISOString(),
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      // Mock existing user check
      mockSingle.mockResolvedValueOnce({
        data: { id: mockUser.id },
        error: null,
      });

      // Mock rate limit check - database error (fail open)
      mockGte.mockResolvedValueOnce({
        data: null,
        error: { message: 'Database error' },
      });

      // Mock topic creation
      mockSingle.mockResolvedValueOnce({
        data: {
          id: '550e8400-e29b-41d4-a716-446655440001',
          topic_text: 'AI 에이전트 최신 동향',
        },
        error: null,
      });

      const formData = new FormData();
      formData.append('topic', 'AI 에이전트 최신 동향');

      const result = await createTopic(formData);

      expect(result.success).toBe(true);
      expect(result.message).toBe('주제가 생성되었습니다.');
    });
  });

  describe('getTopicById', () => {
    it('should get topic successfully', async () => {
      const mockUser = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'test@example.com',
      };

      mockGetUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      mockSingle.mockResolvedValue({
        data: {
          id: '550e8400-e29b-41d4-a716-446655440001',
          topic_text: 'AI 에이전트 최신 동향',
          topic_description: null,
          created_at: new Date().toISOString(),
        },
        error: null,
      });

      const result = await getTopicById('550e8400-e29b-41d4-a716-446655440001');

      expect(result.success).toBe(true);
      expect(result.topic).toBeDefined();
      expect(result.topic?.topic_text).toBe('AI 에이전트 최신 동향');
    });

    it('should require authentication', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: { message: 'Not authenticated' },
      });

      const result = await getTopicById('550e8400-e29b-41d4-a716-446655440001');

      expect(result.success).toBe(false);
      expect(result.message).toBe('로그인이 필요합니다.');
    });

    it('should handle topic not found', async () => {
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
        error: { code: 'PGRST116', message: 'Not found' },
      });

      const result = await getTopicById('550e8400-e29b-41d4-a716-446655440001');

      expect(result.success).toBe(false);
      expect(result.message).toBe('주제를 찾을 수 없습니다.');
    });
  });
});
