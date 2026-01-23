'use server';

import { createClient } from '@/lib/supabase/server';
import { saveAnswersSchema, type UserAnswer } from '@/lib/validation/question';

export async function getQuestionsByTopicId(topicId: string) {
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

  // Verify topic belongs to user
  const { data: topic, error: topicError } = await supabase
    .from('user_topics')
    .select('id')
    .eq('id', topicId)
    .eq('user_id', user.id)
    .single();

  if (topicError || !topic) {
    return {
      success: false,
      message: '주제를 찾을 수 없습니다.',
    };
  }

  // Fetch questions for this topic, ordered by display_order
  const { data: questions, error: questionsError } = await supabase
    .from('personalization_questions')
    .select('*')
    .eq('topic_id', topicId)
    .order('display_order', { ascending: true });

  if (questionsError) {
    console.error('Error fetching questions:', questionsError);
    return {
      success: false,
      message: '질문을 불러오는데 실패했습니다.',
    };
  }

  return {
    success: true,
    questions: questions || [],
  };
}

export async function saveAnswers(topicId: string, answers: UserAnswer[]) {
  // Validate input
  const result = saveAnswersSchema.safeParse({ topic_id: topicId, answers });
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

  // Verify topic belongs to user
  const { data: topic, error: topicError } = await supabase
    .from('user_topics')
    .select('id')
    .eq('id', topicId)
    .eq('user_id', user.id)
    .single();

  if (topicError || !topic) {
    return {
      success: false,
      message: '주제를 찾을 수 없습니다.',
    };
  }

  // Prepare answers for insertion
  const answersToInsert = result.data.answers
    .filter((answer) => !answer.skipped) // Don't save skipped questions
    .map((answer) => ({
      question_id: answer.question_id,
      user_id: user.id,
      answer_text: answer.answer_text || null,
      answer_value: answer.answer_value || null,
    }));

  if (answersToInsert.length === 0) {
    return {
      success: false,
      message: '최소 1개 이상의 질문에 답변해주세요.',
    };
  }

  // Use upsert to handle both insert and update cases
  const { error: answersError } = await supabase
    .from('user_answers')
    .upsert(answersToInsert, {
      onConflict: 'user_id,question_id',
    });

  if (answersError) {
    console.error('Error saving answers:', answersError);
    return {
      success: false,
      message: '답변 저장에 실패했습니다. 다시 시도해주세요.',
    };
  }

  return {
    success: true,
    message: '답변이 저장되었습니다.',
  };
}

export async function getUserAnswers(topicId: string) {
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

  // Fetch user's answers for questions related to this topic
  const { data: answers, error: answersError } = await supabase
    .from('user_answers')
    .select(
      `
      *,
      personalization_questions!inner(topic_id)
    `
    )
    .eq('user_id', user.id)
    .eq('personalization_questions.topic_id', topicId);

  if (answersError) {
    console.error('Error fetching user answers:', answersError);
    return {
      success: false,
      message: '답변을 불러오는데 실패했습니다.',
    };
  }

  return {
    success: true,
    answers: answers || [],
  };
}
