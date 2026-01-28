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
