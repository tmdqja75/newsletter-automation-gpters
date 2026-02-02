"""Supabase client for newsletter generation."""

import os
from typing import Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from .models import (
    NewsletterContext,
    UserAnswer,
    NewsletterContent,
)


class SupabaseClient:
    """Client for interacting with Supabase database."""

    def __init__(self):
        """Initialize Supabase client with service role key."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )

        self.client: Client = create_client(supabase_url, supabase_key)

    async def get_topic_and_answers(self, topic_id: str) -> NewsletterContext:
        """
        Fetch topic and user answers from Supabase.

        Args:
            topic_id: UUID of the topic

        Returns:
            NewsletterContext with topic and answers

        Raises:
            ValueError: If topic not found
        """
        # Fetch topic
        topic_response = (
            self.client.table("user_topics")
            .select("id, user_id, topic_text, topic_description, metadata")
            .eq("id", topic_id)
            .execute()
        )

        if not topic_response.data:
            raise ValueError(f"Topic {topic_id} not found")

        topic = topic_response.data[0]
        user_id = topic["user_id"]

        # Fetch questions for this topic
        questions_response = (
            self.client.table("personalization_questions")
            .select("*")
            .eq("topic_id", topic_id)
            .order("display_order")
            .execute()
        )

        questions = {q["id"]: q for q in questions_response.data}

        # Fetch user answers
        answers_response = (
            self.client.table("user_answers")
            .select("*")
            .eq("user_id", user_id)
            .in_("question_id", list(questions.keys()))
            .execute()
        )

        # Build user answers list
        user_answers = []
        for answer_data in answers_response.data:
            question_id = answer_data["question_id"]
            question = questions.get(question_id)

            if question:
                user_answers.append(
                    UserAnswer(
                        question_id=question_id,
                        question_text=question["question_text"],
                        question_type=question["question_type"],
                        answer_text=answer_data.get("answer_text"),
                        answer_value=answer_data.get("answer_value"),
                        skipped=False,  # If in DB, not skipped
                    )
                )

        # Fetch user preferences (optional)
        prefs_response = (
            self.client.table("user_preferences")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        user_preferences = {}
        if prefs_response.data:
            prefs = prefs_response.data[0]
            user_preferences = {
                "difficulty": prefs.get("preferred_difficulty", "intermediate"),
                "length": prefs.get("preferred_length", "medium"),
                "source_whitelist": prefs.get("source_whitelist", []),
                "source_blacklist": prefs.get("source_blacklist", []),
            }

        return NewsletterContext(
            topic_id=topic["id"],
            topic_text=topic["topic_text"],
            topic_description=topic.get("topic_description"),
            user_answers=user_answers,
            user_preferences=user_preferences,
        )

    async def create_newsletter_request(
        self, user_id: str, topic_id: str
    ) -> str:
        """
        Create a newsletter generation request in the database.

        Args:
            user_id: User UUID
            topic_id: Topic UUID

        Returns:
            request_id (UUID)
        """
        response = (
            self.client.table("newsletter_requests")
            .insert(
                {
                    "user_id": user_id,
                    "topic_id": topic_id,
                    "status": "pending",
                    "requested_at": datetime.utcnow().isoformat(),
                }
            )
            .execute()
        )

        if not response.data:
            raise ValueError("Failed to create newsletter request")

        return response.data[0]["id"]

    async def update_request_status(
        self,
        request_id: str,
        status: str,
        error_message: Optional[str] = None,
        agent_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update newsletter request status.

        Args:
            request_id: Request UUID
            status: New status ('pending', 'processing', 'completed', 'failed')
            error_message: Error message if failed
            agent_metadata: LangSmith run metadata
        """
        update_data: Dict[str, Any] = {"status": status}

        if status == "processing":
            update_data["processing_started_at"] = datetime.utcnow().isoformat()
        elif status in ("completed", "failed"):
            update_data["processing_completed_at"] = datetime.utcnow().isoformat()

        if error_message:
            update_data["error_message"] = error_message

        if agent_metadata:
            update_data["agent_metadata"] = agent_metadata

        self.client.table("newsletter_requests").update(update_data).eq(
            "id", request_id
        ).execute()

    async def save_newsletter(
        self,
        request_id: str,
        user_id: str,
        topic_id: str,
        content: NewsletterContent,
    ) -> str:
        """
        Save generated newsletter to database.

        Args:
            request_id: Newsletter request UUID
            user_id: User UUID
            topic_id: Topic UUID
            content: Newsletter content

        Returns:
            newsletter_id (UUID)
        """
        newsletter_data = {
            "request_id": request_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "title": content.title,
            "body": content.body,
            "word_count": content.word_count,
            "estimated_reading_time": content.estimated_reading_time,
            "is_published": False,  # Not published yet
            "created_at": datetime.utcnow().isoformat(),
        }

        response = (
            self.client.table("newsletters").insert(newsletter_data).execute()
        )

        if not response.data:
            raise ValueError("Failed to save newsletter")

        return response.data[0]["id"]

    async def get_newsletter_request_status(
        self, request_id: str
    ) -> Dict[str, Any]:
        """
        Get newsletter request status.

        Args:
            request_id: Request UUID

        Returns:
            Request data with status
        """
        response = (
            self.client.table("newsletter_requests")
            .select("*")
            .eq("id", request_id)
            .execute()
        )

        if not response.data:
            raise ValueError(f"Request {request_id} not found")

        return response.data[0]

    async def get_newsletter_by_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get newsletter by request ID.

        Args:
            request_id: Request UUID

        Returns:
            Newsletter data if exists, None otherwise
        """
        response = (
            self.client.table("newsletters")
            .select("*")
            .eq("request_id", request_id)
            .execute()
        )

        return response.data[0] if response.data else None


# Global instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
