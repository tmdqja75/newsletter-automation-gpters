'use server';

import { createClient } from '@/lib/supabase/server';
import {
  submitFeedbackSchema,
  type SubmitFeedbackInput,
} from '@/lib/validation/feedback';

interface FeedbackResult {
  success: boolean;
  message: string;
  feedback?: any;
}

/**
 * Submit feedback for a newsletter.
 *
 * @param newsletterId - Newsletter UUID
 * @param feedbackData - Feedback data (thumbs_up, structured_feedback, comment)
 * @returns Result with success status
 */
export async function submitFeedback(
  newsletterId: string,
  feedbackData: Omit<SubmitFeedbackInput, 'newsletter_id'>
): Promise<FeedbackResult> {
  // Validate input
  const result = submitFeedbackSchema.safeParse({
    newsletter_id: newsletterId,
    ...feedbackData,
  });

  if (!result.success) {
    const firstError = result.error.issues[0];
    return {
      success: false,
      message: firstError.message || '피드백 형식이 올바르지 않습니다.',
    };
  }

  const supabase = await createClient();

  // Check authentication
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return {
      success: false,
      message: '로그인이 필요합니다.',
    };
  }

  // Verify newsletter exists and belongs to user
  const { data: newsletter, error: newsletterError } = await supabase
    .from('newsletters')
    .select('id, user_id')
    .eq('id', newsletterId)
    .eq('user_id', user.id)
    .single();

  if (newsletterError || !newsletter) {
    return {
      success: false,
      message: '뉴스레터를 찾을 수 없습니다.',
    };
  }

  // Check if feedback already exists
  const { data: existingFeedback } = await supabase
    .from('newsletter_feedback')
    .select('id')
    .eq('newsletter_id', newsletterId)
    .eq('user_id', user.id)
    .single();

  // Prepare feedback data for insertion/update
  const feedbackToSave = {
    newsletter_id: newsletterId,
    user_id: user.id,
    thumbs_up: result.data.thumbs_up,
    structured_feedback: result.data.structured_feedback || null,
    comment: result.data.comment || null,
  };

  if (existingFeedback) {
    // Update existing feedback
    const { error: updateError } = await supabase
      .from('newsletter_feedback')
      .update({
        thumbs_up: feedbackToSave.thumbs_up,
        structured_feedback: feedbackToSave.structured_feedback,
        comment: feedbackToSave.comment,
        updated_at: new Date().toISOString(),
      })
      .eq('id', existingFeedback.id);

    if (updateError) {
      console.error('Error updating feedback:', updateError);
      return {
        success: false,
        message: '피드백 수정에 실패했습니다. 다시 시도해주세요.',
      };
    }

    return {
      success: true,
      message: '피드백이 수정되었습니다.',
    };
  } else {
    // Insert new feedback
    const { error: insertError } = await supabase
      .from('newsletter_feedback')
      .insert(feedbackToSave);

    if (insertError) {
      console.error('Error inserting feedback:', insertError);
      return {
        success: false,
        message: '피드백 저장에 실패했습니다. 다시 시도해주세요.',
      };
    }

    return {
      success: true,
      message: '피드백이 저장되었습니다. 감사합니다!',
    };
  }
}

/**
 * Get user's feedback for a newsletter.
 *
 * @param newsletterId - Newsletter UUID
 * @returns User's feedback if exists
 */
export async function getFeedback(
  newsletterId: string
): Promise<FeedbackResult> {
  const supabase = await createClient();

  // Check authentication
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return {
      success: false,
      message: '로그인이 필요합니다.',
    };
  }

  // Fetch user's feedback for this newsletter
  const { data: feedback, error: feedbackError } = await supabase
    .from('newsletter_feedback')
    .select('*')
    .eq('newsletter_id', newsletterId)
    .eq('user_id', user.id)
    .single();

  if (feedbackError) {
    // No feedback found is not an error
    if (feedbackError.code === 'PGRST116') {
      return {
        success: true,
        feedback: null,
        message: '피드백이 없습니다.',
      };
    }

    console.error('Error fetching feedback:', feedbackError);
    return {
      success: false,
      message: '피드백을 불러오는데 실패했습니다.',
    };
  }

  return {
    success: true,
    feedback,
  };
}
