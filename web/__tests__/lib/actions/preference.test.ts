import { describe, it, expect, beforeEach, vi } from 'vitest';
import { saveDeliveryPreference } from '@/lib/actions/preference';

const mockGetUser = vi.fn();
const mockFrom = vi.fn();
const mockSelect = vi.fn();
const mockEq = vi.fn();
const mockMaybeSingle = vi.fn();
const mockUpdate = vi.fn();
const mockInsert = vi.fn();

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: mockGetUser,
    },
    from: mockFrom,
  })),
}));

describe('saveDeliveryPreference', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFrom.mockReturnValue({
      select: mockSelect,
      update: mockUpdate,
      insert: mockInsert,
    });
    mockSelect.mockReturnValue({ eq: mockEq });
    mockEq.mockReturnValue({ maybeSingle: mockMaybeSingle });
    mockUpdate.mockReturnValue({
      eq: vi.fn().mockResolvedValue({ error: null }),
    });
  });

  it('should return error when not authenticated', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: null },
      error: { message: 'Not authenticated' },
    });

    const result = await saveDeliveryPreference('월요일');

    expect(result.success).toBe(false);
    expect(result.message).toBe('로그인이 필요합니다.');
  });

  it('should return error for invalid day name', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'user-1' } },
      error: null,
    });

    const result = await saveDeliveryPreference('잘못된요일');

    expect(result.success).toBe(false);
    expect(result.message).toBe('올바르지 않은 요일입니다.');
  });

  it('should update existing preference when row exists', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'user-1' } },
      error: null,
    });
    mockMaybeSingle.mockResolvedValue({ data: { id: 'pref-1' } });

    const mockUpdateEq = vi.fn().mockResolvedValue({ error: null });
    mockUpdate.mockReturnValue({ eq: mockUpdateEq });

    const result = await saveDeliveryPreference('월요일');

    expect(result.success).toBe(true);
    expect(result.message).toBe('발송 주기가 저장되었습니다.');
    expect(mockUpdate).toHaveBeenCalledWith({
      send_frequency: 'weekly',
      preferred_send_day: 1,
      preferred_send_time: '09:00:00',
    });
    expect(mockUpdateEq).toHaveBeenCalledWith('user_id', 'user-1');
  });

  it('should insert new preference when row does not exist', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'user-1' } },
      error: null,
    });
    mockMaybeSingle.mockResolvedValue({ data: null });
    mockInsert.mockResolvedValue({ error: null });

    const result = await saveDeliveryPreference('수요일');

    expect(result.success).toBe(true);
    expect(mockInsert).toHaveBeenCalledWith({
      user_id: 'user-1',
      send_frequency: 'weekly',
      preferred_send_day: 3,
      preferred_send_time: '09:00:00',
    });
  });

  it('should return error when update fails', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'user-1' } },
      error: null,
    });
    mockMaybeSingle.mockResolvedValue({ data: { id: 'pref-1' } });

    const mockUpdateEq = vi
      .fn()
      .mockResolvedValue({ error: { message: 'DB error' } });
    mockUpdate.mockReturnValue({ eq: mockUpdateEq });

    const result = await saveDeliveryPreference('금요일');

    expect(result.success).toBe(false);
    expect(result.message).toBe('발송 주기 저장에 실패했습니다.');
  });

  it('should return error when insert fails', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'user-1' } },
      error: null,
    });
    mockMaybeSingle.mockResolvedValue({ data: null });
    mockInsert.mockResolvedValue({ error: { message: 'DB error' } });

    const result = await saveDeliveryPreference('토요일');

    expect(result.success).toBe(false);
    expect(result.message).toBe('발송 주기 저장에 실패했습니다.');
  });

  it('should map all days correctly', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'user-1' } },
      error: null,
    });
    mockMaybeSingle.mockResolvedValue({ data: null });
    mockInsert.mockResolvedValue({ error: null });

    const dayMap: Record<string, number> = {
      월요일: 1,
      화요일: 2,
      수요일: 3,
      목요일: 4,
      금요일: 5,
      토요일: 6,
      일요일: 0,
    };

    for (const [dayName, expectedInt] of Object.entries(dayMap)) {
      mockInsert.mockClear();
      const result = await saveDeliveryPreference(dayName);
      expect(result.success).toBe(true);
      expect(mockInsert).toHaveBeenCalledWith(
        expect.objectContaining({ preferred_send_day: expectedInt })
      );
    }
  });
});
