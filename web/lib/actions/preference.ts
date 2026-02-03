'use server';

import { createClient } from '@/lib/supabase/server';

const DAY_NAME_TO_INT: Record<string, number> = {
  월요일: 1,
  화요일: 2,
  수요일: 3,
  목요일: 4,
  금요일: 5,
  토요일: 6,
  일요일: 0,
};

export async function saveDeliveryPreference(deliveryDay: string) {
  const supabase = await createClient();

  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return { success: false, message: '로그인이 필요합니다.' };
  }

  const dayInt = DAY_NAME_TO_INT[deliveryDay];
  if (dayInt === undefined) {
    return { success: false, message: '올바르지 않은 요일입니다.' };
  }

  // Check if preference row already exists
  const { data: existing } = await supabase
    .from('user_preferences')
    .select('id')
    .eq('user_id', user.id)
    .maybeSingle();

  if (existing) {
    const { error } = await supabase
      .from('user_preferences')
      .update({
        send_frequency: 'weekly',
        preferred_send_day: dayInt,
        preferred_send_time: '09:00:00',
      })
      .eq('user_id', user.id);

    if (error) {
      console.error('Error updating delivery preference:', error);
      return { success: false, message: '발송 주기 저장에 실패했습니다.' };
    }
  } else {
    const { error } = await supabase.from('user_preferences').insert({
      user_id: user.id,
      send_frequency: 'weekly',
      preferred_send_day: dayInt,
      preferred_send_time: '09:00:00',
    });

    if (error) {
      console.error('Error inserting delivery preference:', error);
      return { success: false, message: '발송 주기 저장에 실패했습니다.' };
    }
  }

  return { success: true, message: '발송 주기가 저장되었습니다.' };
}
