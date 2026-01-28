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
export async function getUserNewsletters(
  options: GetUserNewslettersOptions = {}
) {
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

  // Build query - start from newsletter_requests to include processing status
  let query = supabase
    .from('newsletter_requests')
    .select(
      `
      id,
      status,
      created_at,
      requested_at,
      topic_id,
      user_topics!inner(id, topic_text, topic_description),
      newsletters(id, title, body, created_at)
    `,
      { count: 'exact' }
    )
    .eq('user_id', user.id)
    .in('status', ['completed', 'processing']); // Only show completed and processing

  // Apply filters
  if (topicId) {
    query = query.eq('topic_id', topicId);
  }

  if (search) {
    query = query.or(
      `newsletters.title.ilike.%${search}%,user_topics.topic_text.ilike.%${search}%`
    );
  }

  // Apply sorting
  query = query.order('created_at', {
    ascending: sortBy === 'oldest',
  });

  // Apply pagination
  query = query.range(offset, offset + limit - 1);

  const { data: requests, error: newslettersError, count } = await query;

  if (newslettersError) {
    console.error('Error fetching newsletters:', newslettersError);
    return {
      success: false,
      message: '뉴스레터 목록을 불러오는데 실패했습니다.',
      newsletters: [],
      total: 0,
    };
  }

  // Transform to match frontend expectations
  const transformedNewsletters = (requests || []).map((req: any) => {
    const newsletter = Array.isArray(req.newsletters)
      ? req.newsletters[0]
      : req.newsletters;

    return {
      id: newsletter?.id || req.id, // Use newsletter ID if available, otherwise request ID
      request_id: req.id,
      user_id: user.id,
      topic_id: req.topic_id,
      status: req.status,
      title: newsletter?.title || '생성 중...',
      body: newsletter?.body || '',
      created_at: newsletter?.created_at || req.created_at,
      user_topics: req.user_topics,
      content: {
        title: newsletter?.title || '생성 중...',
        body: newsletter?.body || '',
      },
    };
  });

  return {
    success: true,
    newsletters: transformedNewsletters,
    total: count || 0,
  };
}

/**
 * Delete a newsletter or newsletter request.
 *
 * @param id - Newsletter ID or Request ID
 * @returns Result with success status
 */
export async function deleteNewsletter(id: string) {
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

  // First try to find as a newsletter
  const { data: newsletter } = await supabase
    .from('newsletters')
    .select('id, user_id, request_id')
    .eq('id', id)
    .eq('user_id', user.id)
    .single();

  if (newsletter) {
    // Delete from newsletter_requests (cascades to newsletters)
    const { error: deleteError } = await supabase
      .from('newsletter_requests')
      .delete()
      .eq('id', newsletter.request_id);

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

  // If not found as newsletter, try as a request (processing status)
  const { data: request, error: requestError } = await supabase
    .from('newsletter_requests')
    .select('id, user_id')
    .eq('id', id)
    .eq('user_id', user.id)
    .single();

  if (requestError || !request) {
    return {
      success: false,
      message: '뉴스레터를 찾을 수 없습니다.',
    };
  }

  // Delete the request
  const { error: deleteError } = await supabase
    .from('newsletter_requests')
    .delete()
    .eq('id', id);

  if (deleteError) {
    console.error('Error deleting newsletter request:', deleteError);
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
      user_topics!inner(topic_text, topic_description)
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

  // Transform flat structure to match frontend expectations
  const transformedNewsletter = {
    ...newsletter,
    content: {
      title: newsletter.title,
      body: newsletter.body,
    },
  };

  return {
    success: true,
    newsletter: transformedNewsletter,
  };
}
