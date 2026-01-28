'use server';

import { createClient } from '@/lib/supabase/server';
import { env } from '@/lib/env';

interface GenerateNewsletterResult {
  success: boolean;
  message: string;
  requestId?: string;
  newsletterId?: string;
}

/**
 * Generate newsletter for a topic.
 *
 * This triggers the FastAPI backend to generate a personalized newsletter
 * using the LangGraph agents.
 *
 * @param topicId - Topic UUID
 * @returns Result with request ID
 */
export async function generateNewsletter(
  topicId: string
): Promise<GenerateNewsletterResult> {
  try {
    // Get authenticated user
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return {
        success: false,
        message: '로그인이 필요합니다.',
      };
    }

    // Get API URL from environment
    const apiUrl = env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    // Call FastAPI to generate newsletter
    const response = await fetch(`${apiUrl}/api/newsletter/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: user.id,
        topic_id: topicId,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        message: error.detail || '뉴스레터 생성 요청에 실패했습니다.',
      };
    }

    const data = await response.json();

    return {
      success: true,
      message: data.message || '뉴스레터 생성이 시작되었습니다.',
      requestId: data.request_id,
    };
  } catch (error) {
    console.error('Error generating newsletter:', error);
    return {
      success: false,
      message: '뉴스레터 생성 중 오류가 발생했습니다.',
    };
  }
}

/**
 * Check newsletter generation status.
 *
 * @param requestId - Newsletter request UUID
 * @returns Status information
 */
export async function getNewsletterStatus(requestId: string) {
  try {
    const apiUrl = env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    const response = await fetch(
      `${apiUrl}/api/newsletter/status/${requestId}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        message: error.detail || '상태 조회에 실패했습니다.',
      };
    }

    const data = await response.json();

    return {
      success: true,
      status: data.status,
      newsletterId: data.newsletter_id,
      errorMessage: data.error_message,
    };
  } catch (error) {
    console.error('Error checking newsletter status:', error);
    return {
      success: false,
      message: '상태 조회 중 오류가 발생했습니다.',
    };
  }
}

/**
 * Get generated newsletter by ID.
 *
 * @param newsletterId - Newsletter UUID
 * @returns Newsletter content
 */
export async function getNewsletter(newsletterId: string) {
  try {
    const apiUrl = env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    const response = await fetch(`${apiUrl}/api/newsletter/${newsletterId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        message: error.detail || '뉴스레터 조회에 실패했습니다.',
      };
    }

    const data = await response.json();

    return {
      success: true,
      newsletter: data,
    };
  } catch (error) {
    console.error('Error fetching newsletter:', error);
    return {
      success: false,
      message: '뉴스레터 조회 중 오류가 발생했습니다.',
    };
  }
}

interface GetUserNewslettersOptions {
  limit?: number;
  offset?: number;
  search?: string;
  topicId?: string;
  sortBy?: 'newest' | 'oldest';
}

/**
 * Get user's newsletters with pagination, filtering, and sorting.
 *
 * @param options - Query options
 * @returns List of newsletters
 */
export async function getUserNewsletters(options: GetUserNewslettersOptions = {}) {
  const {
    limit = 12,
    offset = 0,
    search,
    topicId,
    sortBy = 'newest',
  } = options;

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
      newsletters: [],
      total: 0,
    };
  }

  // Build query
  let query = supabase
    .from('newsletters')
    .select(
      `
      *,
      user_topics!inner(id, topic, description),
      newsletter_requests!inner(status)
    `,
      { count: 'exact' }
    )
    .eq('user_id', user.id);

  // Apply filters
  if (topicId) {
    query = query.eq('topic_id', topicId);
  }

  if (search) {
    query = query.or(
      `content->title.ilike.%${search}%,user_topics.topic.ilike.%${search}%`
    );
  }

  // Apply sorting
  query = query.order('created_at', {
    ascending: sortBy === 'oldest',
  });

  // Apply pagination
  query = query.range(offset, offset + limit - 1);

  const { data: newsletters, error: newslettersError, count } = await query;

  if (newslettersError) {
    console.error('Error fetching newsletters:', newslettersError);
    return {
      success: false,
      message: '뉴스레터 목록을 불러오는데 실패했습니다.',
      newsletters: [],
      total: 0,
    };
  }

  return {
    success: true,
    newsletters: newsletters || [],
    total: count || 0,
  };
}

/**
 * Delete a newsletter.
 *
 * @param newsletterId - Newsletter UUID
 * @returns Result with success status
 */
export async function deleteNewsletter(newsletterId: string) {
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

  // Verify newsletter belongs to user
  const { data: newsletter, error: verifyError } = await supabase
    .from('newsletters')
    .select('id, user_id')
    .eq('id', newsletterId)
    .eq('user_id', user.id)
    .single();

  if (verifyError || !newsletter) {
    return {
      success: false,
      message: '뉴스레터를 찾을 수 없습니다.',
    };
  }

  // Delete the newsletter
  const { error: deleteError } = await supabase
    .from('newsletters')
    .delete()
    .eq('id', newsletterId);

  if (deleteError) {
    console.error('Error deleting newsletter:', deleteError);
    return {
      success: false,
      message: '뉴스레터 삭제에 실패했습니다. 다시 시도해주세요.',
    };
  }

  return {
    success: true,
    message: '뉴스레터가 삭제되었습니다.',
  };
}

/**
 * Get newsletter for public viewing (no authentication required).
 *
 * @param newsletterId - Newsletter UUID
 * @returns Newsletter content for public view
 */
export async function getNewsletterForPublicView(newsletterId: string) {
  const supabase = await createClient();

  // Fetch newsletter without authentication check
  const { data: newsletter, error: newsletterError } = await supabase
    .from('newsletters')
    .select(
      `
      *,
      user_topics!inner(topic, description)
    `
    )
    .eq('id', newsletterId)
    .single();

  if (newsletterError || !newsletter) {
    return {
      success: false,
      message: '뉴스레터를 찾을 수 없습니다.',
    };
  }

  return {
    success: true,
    newsletter,
  };
}
