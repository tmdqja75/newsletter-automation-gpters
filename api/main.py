import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import json

from src.api.newsletter_generator import get_newsletter_generator
from src.api.supabase_client import get_supabase_client
from src.api.models import (
    GenerationRequest,
    NewsletterRequestResponse,
    NewsletterStatusResponse,
    NewsletterResponse,
    NewsletterContent,
)

app = FastAPI(title="Newsletter Automation API")

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "newsletter-automation-api"}


@app.post("/api/newsletter/generate", response_model=NewsletterRequestResponse)
async def generate_newsletter(request: GenerationRequest):
    """
    Trigger newsletter generation (non-streaming).

    Args:
        request: Generation request with user_id and topic_id

    Returns:
        Request ID and initial status
    """
    try:
        generator = get_newsletter_generator()
        result = await generator.generate_newsletter(
            user_id=request.user_id, topic_id=request.topic_id
        )

        return NewsletterRequestResponse(
            request_id=result["request_id"],
            status=result["status"],
            message="뉴스레터 생성이 완료되었습니다.",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@app.post("/api/newsletter/generate/stream")
async def generate_newsletter_stream(request: GenerationRequest):
    """
    Trigger newsletter generation with SSE streaming.

    Args:
        request: Generation request with user_id and topic_id

    Returns:
        Server-Sent Events stream with progress updates
    """

    async def event_generator():
        """Generate SSE events for newsletter generation progress."""
        try:
            generator = get_newsletter_generator()

            async for update in generator.generate_newsletter_stream(
                user_id=request.user_id, topic_id=request.topic_id
            ):
                # Convert ProgressUpdate to JSON and yield as SSE event
                data = update.model_dump_json()
                yield {"data": data}

        except Exception as e:
            # Send error event
            error_data = json.dumps(
                {
                    "step": "error",
                    "progress": 0,
                    "message": f"오류 발생: {str(e)}",
                    "details": {"error": str(e)},
                }
            )
            yield {"data": error_data}

    return EventSourceResponse(event_generator())


@app.get(
    "/api/newsletter/status/{request_id}", response_model=NewsletterStatusResponse
)
async def get_newsletter_status(request_id: str):
    """
    Get newsletter generation request status.

    Args:
        request_id: Newsletter request UUID

    Returns:
        Request status and details
    """
    try:
        supabase = get_supabase_client()
        request_data = await supabase.get_newsletter_request_status(request_id)

        # Check if newsletter exists
        newsletter = await supabase.get_newsletter_by_request(request_id)
        newsletter_id = newsletter["id"] if newsletter else None

        return NewsletterStatusResponse(
            request_id=request_data["id"],
            status=request_data["status"],
            message=request_data.get("error_message"),
            newsletter_id=newsletter_id,
            error_message=request_data.get("error_message"),
            processing_started_at=request_data.get("processing_started_at"),
            processing_completed_at=request_data.get("processing_completed_at"),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@app.get("/api/newsletter/{newsletter_id}", response_model=NewsletterResponse)
async def get_newsletter(newsletter_id: str):
    """
    Get generated newsletter by ID.

    Args:
        newsletter_id: Newsletter UUID

    Returns:
        Complete newsletter content
    """
    try:
        supabase = get_supabase_client()

        # Fetch newsletter from database
        response = (
            supabase.client.table("newsletters")
            .select("*")
            .eq("id", newsletter_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="뉴스레터를 찾을 수 없습니다.")

        newsletter_data = response.data[0]

        # Parse content from JSONB fields
        content = NewsletterContent(
            title=newsletter_data["title"],
            tldr=newsletter_data["tldr"],
            core_issues=newsletter_data["core_issues"],
            deep_dive=newsletter_data["deep_dive"],
            next_questions=newsletter_data.get("next_questions", []),
            sources=newsletter_data["sources"],
            word_count=newsletter_data.get("word_count"),
            estimated_reading_time=newsletter_data.get("estimated_reading_time"),
        )

        return NewsletterResponse(
            id=newsletter_data["id"],
            request_id=newsletter_data["request_id"],
            user_id=newsletter_data["user_id"],
            topic_id=newsletter_data["topic_id"],
            content=content,
            published_at=newsletter_data.get("published_at"),
            is_published=newsletter_data.get("is_published", False),
            created_at=newsletter_data["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
