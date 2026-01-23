'use server';

import { createClient } from '@/lib/supabase/server';
import { topicSchema } from '@/lib/validation/topic';
import { defaultQuestions } from '@/lib/default-questions';

export async function createTopic(formData: FormData) {
  const topicText = formData.get('topic') as string;

  // Validate input
  const result = topicSchema.safeParse({ topic: topicText });
  if (!result.success) {
    const firstError = result.error.issues[0];
    return { success: false, message: firstError.message };
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

  // Check if user exists in users table, if not create
  const { data: existingUser } = await supabase
    .from('users')
    .select('id')
    .eq('id', user.id)
    .single();

  if (!existingUser) {
    const { error: userCreateError } = await supabase.from('users').insert({
      id: user.id,
      email: user.email!,
      is_email_verified: user.email_confirmed_at !== null,
    });

    if (userCreateError) {
      console.error('Error creating user:', userCreateError);
      return {
        success: false,
        message: '사용자 정보 생성에 실패했습니다.',
      };
    }
  }

  // Create topic
  const { data: topic, error: topicError } = await supabase
    .from('user_topics')
    .insert({
      user_id: user.id,
      topic_text: result.data.topic,
      is_active: true,
    })
    .select('id, topic_text')
    .single();

  if (topicError) {
    console.error('Error creating topic:', topicError);
    return {
      success: false,
      message: '주제 생성에 실패했습니다. 다시 시도해주세요.',
    };
  }

  // Insert default personalization questions for this topic
  const questionsToInsert = defaultQuestions.map((q) => ({
    topic_id: topic.id,
    question_text: q.question_text,
    question_type: q.question_type,
    options: q.options,
    display_order: q.display_order,
    is_required: q.is_required,
  }));

  const { error: questionsError } = await supabase
    .from('personalization_questions')
    .insert(questionsToInsert);

  if (questionsError) {
    console.error('Error creating questions:', questionsError);
    // Don't fail the entire operation if questions fail
    // The topic is already created, so return success
    // but log the error for debugging
  }

  return {
    success: true,
    message: '주제가 생성되었습니다.',
    topicId: topic.id,
  };
}

export async function getTopicById(topicId: string) {
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

  // Fetch topic
  const { data: topic, error: topicError } = await supabase
    .from('user_topics')
    .select('id, topic_text, topic_description, created_at')
    .eq('id', topicId)
    .eq('user_id', user.id)
    .single();

  if (topicError) {
    console.error('Error fetching topic:', topicError);
    return {
      success: false,
      message: '주제를 찾을 수 없습니다.',
    };
  }

  return {
    success: true,
    topic,
  };
}
