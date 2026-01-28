"""Pydantic models for API wrapper."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# Request Models
# =============================================================================


class GenerationRequest(BaseModel):
    """Request to generate a newsletter."""

    user_id: str = Field(..., description="User ID from Supabase auth")
    topic_id: str = Field(..., description="Topic ID from user_topics table")


class UserAnswer(BaseModel):
    """User answer to a personalization question."""

    question_id: str
    question_text: str
    question_type: str  # 'goal', 'difficulty', 'scope', 'time', 'source', 'subtopic', 'custom'
    answer_text: Optional[str] = None
    answer_value: Optional[Dict[str, Any]] = None
    skipped: bool = False


class NewsletterContext(BaseModel):
    """Context data for newsletter generation."""

    topic_id: str
    topic_text: str
    topic_description: Optional[str] = None
    user_answers: List[UserAnswer] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Progress Models
# =============================================================================


class ProgressUpdate(BaseModel):
    """Progress update for streaming."""

    step: str = Field(
        ...,
        description="Current step: init, research, topic_selection, writing, editing, complete, error",
    )
    progress: int = Field(..., ge=0, le=100, description="Progress percentage 0-100")
    message: str = Field(..., description="Korean message to display to user")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional details about the step"
    )


# =============================================================================
# Newsletter Content Models (matches Supabase schema)
# =============================================================================


class NewsletterContent(BaseModel):
    """Simplified newsletter content with markdown body."""

    title: str = Field(..., description="Newsletter title")
    body: str = Field(..., description="Complete newsletter content in markdown")
    word_count: Optional[int] = Field(None, description="Word count")
    estimated_reading_time: Optional[int] = Field(
        None, description="Estimated reading time in minutes"
    )


# =============================================================================
# Response Models
# =============================================================================


class NewsletterRequestResponse(BaseModel):
    """Response when creating a newsletter request."""

    request_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    message: str


class NewsletterStatusResponse(BaseModel):
    """Response for checking newsletter generation status."""

    request_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    newsletter_id: Optional[str] = None
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None


class NewsletterResponse(BaseModel):
    """Response with complete newsletter."""

    id: str
    request_id: str
    user_id: str
    topic_id: str
    content: NewsletterContent
    published_at: Optional[datetime] = None
    is_published: bool = False
    created_at: datetime
