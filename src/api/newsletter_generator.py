"""Newsletter generator with LangSmith integration."""

import os
import sys
from typing import AsyncGenerator, Dict, Any
from datetime import datetime
from pathlib import Path

from deepagents import create_deep_agent
from langsmith import Client as LangSmithClient

from ..config import ANTHROPIC_API_KEY, TAVILY_API_KEY
from ..agents import create_research_subagent, topic_selection_agent, tone_agent
from .models import (
    NewsletterContext,
    ProgressUpdate,
    NewsletterContent,
)
from .supabase_client import get_supabase_client


class NewsletterGenerator:
    """Generates personalized newsletters using LangGraph agents."""

    def __init__(self):
        """Initialize newsletter generator."""
        self.supabase = get_supabase_client()

        # Initialize LangSmith client if API key is set
        self.langsmith_client = None
        langsmith_api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
        if langsmith_api_key:
            self.langsmith_client = LangSmithClient(api_key=langsmith_api_key)

    def _extract_research_context(self, context: NewsletterContext) -> Dict[str, Any]:
        """
        Extract research context from newsletter context.

        Args:
            context: Newsletter context with topic and user answers

        Returns:
            Dictionary with research agent parameters
        """
        research_context = {
            "topic": context.topic_text,
            "topic_description": context.topic_description,
        }

        # Extract subtopics from user answers
        subtopics = []
        preferred_sources = []
        goal = None
        difficulty = None

        for answer in context.user_answers:
            if answer.skipped:
                continue

            # Map question types to research context
            if answer.question_type == "subtopic":
                # Extract subtopic values
                if answer.answer_value and "values" in answer.answer_value:
                    subtopics.extend(answer.answer_value["values"])
                elif answer.answer_text:
                    subtopics.append(answer.answer_text)

            elif answer.question_type == "source":
                # Extract preferred sources
                if answer.answer_value and "values" in answer.answer_value:
                    preferred_sources.extend(answer.answer_value["values"])
                elif answer.answer_text:
                    preferred_sources.append(answer.answer_text)

            elif answer.question_type == "goal":
                # Extract goal
                if answer.answer_value and "value" in answer.answer_value:
                    goal = answer.answer_value["value"]
                elif answer.answer_text:
                    goal = answer.answer_text.lower()

            elif answer.question_type == "difficulty":
                # Extract difficulty
                if answer.answer_value and "value" in answer.answer_value:
                    difficulty = answer.answer_value["value"]
                elif answer.answer_text:
                    difficulty = answer.answer_text.lower()

        # Add to research context if present
        if subtopics:
            research_context["subtopics"] = subtopics
        if preferred_sources:
            research_context["preferred_sources"] = preferred_sources
        if goal:
            research_context["goal"] = goal
        if difficulty or context.user_preferences.get("difficulty"):
            research_context["difficulty"] = difficulty or context.user_preferences.get("difficulty")

        return research_context

    def _build_personalized_prompt(self, context: NewsletterContext) -> str:
        """
        Build a personalized prompt for the agent based on user context.

        Args:
            context: Newsletter context with topic and answers

        Returns:
            Prompt string in Korean
        """
        # Build user context section
        user_context_parts = [f"**주제**: {context.topic_text}"]

        if context.topic_description:
            user_context_parts.append(f"**상세 설명**: {context.topic_description}")

        # Add user preferences
        if context.user_preferences:
            prefs = context.user_preferences
            if prefs.get("difficulty"):
                difficulty_map = {
                    "beginner": "초급",
                    "intermediate": "중급",
                    "advanced": "고급",
                }
                user_context_parts.append(
                    f"**난이도**: {difficulty_map.get(prefs['difficulty'], prefs['difficulty'])}"
                )
            if prefs.get("length"):
                length_map = {
                    "short": "짧게 (3분)",
                    "medium": "중간 (5-10분)",
                    "long": "길게 (15분+)",
                }
                user_context_parts.append(
                    f"**읽기 시간**: {length_map.get(prefs['length'], prefs['length'])}"
                )

        # Add user answers to personalization questions
        if context.user_answers:
            user_context_parts.append("\n**사용자 맞춤 정보**:")
            for answer in context.user_answers:
                if not answer.skipped and (answer.answer_text or answer.answer_value):
                    user_context_parts.append(f"- {answer.question_text}")
                    if answer.answer_text:
                        user_context_parts.append(f"  답변: {answer.answer_text}")
                    elif answer.answer_value:
                        # Handle different answer types
                        if "value" in answer.answer_value:
                            user_context_parts.append(f"  답변: {answer.answer_value['value']}")
                        elif "values" in answer.answer_value:
                            values = ", ".join(answer.answer_value["values"])
                            user_context_parts.append(f"  답변: {values}")

        user_context = "\n".join(user_context_parts)

        # Build the prompt
        prompt = f"""개인화된 리서치 뉴스레터를 작성해주세요.

## 사용자 컨텍스트
{user_context}

## 작업 순서
1. **research-agent 사용**: 위 주제와 관련된 최신 뉴스, 기술 블로그, 논문 등을 수집하세요
   - 사용자의 관심사와 수준에 맞는 자료를 우선적으로 선택하세요
   - 다양한 출처(공식 블로그, 기술 뉴스, HackerNews 등)를 활용하세요

2. **topic-selector 사용**: 수집한 자료에서 핵심 주제들을 선정하세요
   - 사용자의 관심사에 가장 관련 있는 내용을 우선 선택하세요
   - 각 주제는 구체적이고 명확해야 합니다

3. **뉴스레터 작성**: 완전한 마크다운 문서 형식으로 뉴스레터를 작성하세요
   - 제목, 본문, 링크 등을 포함한 완전한 문서를 작성하세요
   - 마크다운 문법을 사용하세요 (제목: #, ##, 링크: [텍스트](URL), 등)
   - 사용자의 수준과 관심사에 맞게 설명하세요
   - 코드 예제가 필요하면 코드 블록(```)을 사용하세요

4. **tone-editor 사용**: 작성한 뉴스레터를 검토하고 다음을 확인하세요
   - 한국어 "해요체" 사용
   - 기술 용어는 한글(영어) 병기
   - 사용자 수준에 맞는 설명
   - 모든 출처 링크가 포함되었는지 확인

5. **최종 결과 반환**: 완성된 마크다운 뉴스레터를 반환하세요

**중요**:
- 모든 주장에는 반드시 출처를 명시하세요
- 링크 없는 단정적 주장을 피하세요
- 불확실한 내용은 "확인 필요" 또는 "추측" 표시하세요
- 최종 결과는 바로 사용자에게 보여줄 수 있는 완전한 마크다운 문서여야 합니다
"""

        return prompt

    async def generate_newsletter(
        self, user_id: str, topic_id: str
    ) -> Dict[str, Any]:
        """
        Generate newsletter synchronously.

        Args:
            user_id: User UUID
            topic_id: Topic UUID

        Returns:
            Dict with request_id and newsletter_id

        Raises:
            ValueError: If generation fails
        """
        # Validate API keys
        if not ANTHROPIC_API_KEY or not TAVILY_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY and TAVILY_API_KEY must be set")

        # Create newsletter request
        request_id = await self.supabase.create_newsletter_request(user_id, topic_id)

        # Update status to processing
        await self.supabase.update_request_status(request_id, "processing")

        try:
            # Fetch context from Supabase
            context = await self.supabase.get_topic_and_answers(topic_id)

            # Build prompt
            prompt = self._build_personalized_prompt(context)

            # Extract research context for personalization
            research_context = self._extract_research_context(context)

            # Create personalized research agent
            research_agent = create_research_subagent(research_context)

            # Create agent
            agent = create_deep_agent(
                system_prompt="You are an expert research newsletter writer. Follow the user's instructions carefully and produce high-quality, well-researched content.",
                tools=[],  # No tools needed, subagents have them
                subagents=[research_agent, topic_selection_agent, tone_agent],
            )

            # Configure LangSmith metadata
            config: Dict[str, Any] = {
                "configurable": {"thread_id": f"newsletter-{request_id}"}
            }

            # Add LangSmith metadata if available
            if self.langsmith_client:
                config["metadata"] = {
                    "user_id": user_id,
                    "topic_id": topic_id,
                    "request_id": request_id,
                    "topic_text": context.topic_text,
                    "user_preferences": context.user_preferences,
                }

            # Run agent
            final_content = None
            langsmith_run_id = None

            for event in agent.stream(
                {"messages": [{"role": "user", "content": prompt}]}, config=config
            ):
                for key, value in event.items():
                    if key == "model" and "messages" in value:
                        for msg in value["messages"]:
                            if hasattr(msg, "content") and msg.content:
                                final_content = msg.content

                    # Extract LangSmith run ID if available
                    if key == "__metadata__" and "run_id" in value:
                        langsmith_run_id = value["run_id"]

            if not final_content:
                raise ValueError("Agent did not produce any content")

            # Parse the content (for now, assume it's structured text)
            # TODO: Implement proper parsing of agent response to NewsletterContent
            newsletter_content = self._parse_agent_response(final_content, context)

            # Save newsletter to database
            newsletter_id = await self.supabase.save_newsletter(
                request_id=request_id,
                user_id=user_id,
                topic_id=topic_id,
                content=newsletter_content,
            )

            # Update request status to completed
            agent_metadata = {"langsmith_run_id": langsmith_run_id} if langsmith_run_id else {}
            await self.supabase.update_request_status(
                request_id, "completed", agent_metadata=agent_metadata
            )

            return {
                "request_id": request_id,
                "newsletter_id": newsletter_id,
                "status": "completed",
            }

        except Exception as e:
            # Update request status to failed
            await self.supabase.update_request_status(
                request_id, "failed", error_message=str(e)
            )
            raise

    async def generate_newsletter_stream(
        self, user_id: str, topic_id: str
    ) -> AsyncGenerator[ProgressUpdate, None]:
        """
        Generate newsletter with streaming progress updates.

        Args:
            user_id: User UUID
            topic_id: Topic UUID

        Yields:
            ProgressUpdate objects with progress information
        """
        yield ProgressUpdate(
            step="init", progress=0, message="초기화 중...", details={"status": "starting"}
        )

        # Validate API keys
        if not ANTHROPIC_API_KEY or not TAVILY_API_KEY:
            yield ProgressUpdate(
                step="error",
                progress=0,
                message="API 키가 설정되지 않았습니다",
                details={"error": "Missing API keys"},
            )
            return

        # Create newsletter request
        request_id = await self.supabase.create_newsletter_request(user_id, topic_id)

        yield ProgressUpdate(
            step="init",
            progress=5,
            message="뉴스레터 요청이 생성되었습니다",
            details={"request_id": request_id},
        )

        # Update status to processing
        await self.supabase.update_request_status(request_id, "processing")

        try:
            # Fetch context
            yield ProgressUpdate(
                step="init", progress=10, message="사용자 맞춤 정보를 가져오는 중..."
            )

            context = await self.supabase.get_topic_and_answers(topic_id)

            yield ProgressUpdate(
                step="research",
                progress=20,
                message=f"'{context.topic_text}' 주제로 자료를 수집하는 중...",
                details={"topic": context.topic_text},
            )

            # Build prompt
            prompt = self._build_personalized_prompt(context)

            # Extract research context for personalization
            research_context = self._extract_research_context(context)

            # Create personalized research agent
            research_agent = create_research_subagent(research_context)

            # Create agent
            agent = create_deep_agent(
                system_prompt="You are an expert research newsletter writer. Follow the user's instructions carefully and produce high-quality, well-researched content.",
                tools=[],
                subagents=[research_agent, topic_selection_agent, tone_agent],
            )

            config: Dict[str, Any] = {
                "configurable": {"thread_id": f"newsletter-{request_id}"}
            }

            if self.langsmith_client:
                config["metadata"] = {
                    "user_id": user_id,
                    "topic_id": topic_id,
                    "request_id": request_id,
                    "topic_text": context.topic_text,
                }

            # Stream agent execution
            final_content = None
            langsmith_run_id = None
            current_step = "research"
            progress = 20

            for event in agent.stream(
                {"messages": [{"role": "user", "content": prompt}]}, config=config
            ):
                for key, value in event.items():
                    if key == "model" and "messages" in value:
                        for msg in value["messages"]:
                            # Detect step changes based on content
                            if hasattr(msg, "content") and msg.content:
                                final_content = msg.content

                                content_lower = str(msg.content).lower()
                                if "research" in content_lower or "수집" in content_lower:
                                    if current_step != "research":
                                        current_step = "research"
                                        progress = 30
                                        yield ProgressUpdate(
                                            step="research",
                                            progress=progress,
                                            message="자료 수집 중...",
                                        )
                                elif "topic" in content_lower or "선정" in content_lower:
                                    if current_step != "topic_selection":
                                        current_step = "topic_selection"
                                        progress = 50
                                        yield ProgressUpdate(
                                            step="topic_selection",
                                            progress=progress,
                                            message="핵심 이슈를 선정하는 중...",
                                        )
                                elif "작성" in content_lower or "writing" in content_lower:
                                    if current_step != "writing":
                                        current_step = "writing"
                                        progress = 70
                                        yield ProgressUpdate(
                                            step="writing",
                                            progress=progress,
                                            message="뉴스레터를 작성하는 중...",
                                        )
                                elif "편집" in content_lower or "edit" in content_lower:
                                    if current_step != "editing":
                                        current_step = "editing"
                                        progress = 85
                                        yield ProgressUpdate(
                                            step="editing",
                                            progress=progress,
                                            message="톤앤매너를 조정하는 중...",
                                        )

                    if key == "__metadata__" and "run_id" in value:
                        langsmith_run_id = value["run_id"]

            if not final_content:
                yield ProgressUpdate(
                    step="error",
                    progress=0,
                    message="에이전트가 콘텐츠를 생성하지 못했습니다",
                )
                await self.supabase.update_request_status(
                    request_id, "failed", error_message="No content generated"
                )
                return

            yield ProgressUpdate(
                step="saving", progress=90, message="뉴스레터를 저장하는 중..."
            )

            # Parse and save newsletter
            newsletter_content = self._parse_agent_response(final_content, context)
            newsletter_id = await self.supabase.save_newsletter(
                request_id=request_id,
                user_id=user_id,
                topic_id=topic_id,
                content=newsletter_content,
            )

            # Update request status
            agent_metadata = {"langsmith_run_id": langsmith_run_id} if langsmith_run_id else {}
            await self.supabase.update_request_status(
                request_id, "completed", agent_metadata=agent_metadata
            )

            yield ProgressUpdate(
                step="complete",
                progress=100,
                message="뉴스레터가 성공적으로 생성되었습니다!",
                details={
                    "request_id": request_id,
                    "newsletter_id": newsletter_id,
                },
            )

        except Exception as e:
            await self.supabase.update_request_status(
                request_id, "failed", error_message=str(e)
            )
            yield ProgressUpdate(
                step="error",
                progress=0,
                message=f"오류 발생: {str(e)}",
                details={"error": str(e)},
            )

    def _parse_agent_response(
        self, content: str, context: NewsletterContext
    ) -> NewsletterContent:
        """
        Parse agent response into simplified NewsletterContent.

        Extracts the markdown body and calculates reading metrics.

        Args:
            content: Agent response text (complete markdown document)
            context: Newsletter context

        Returns:
            Simplified NewsletterContent with title and body
        """
        # Extract title from first line if it starts with #, otherwise generate one
        lines = content.strip().split("\n")
        title = f"{context.topic_text}에 대한 최신 동향 ({datetime.now().strftime('%Y.%m.%d')})"

        if lines and lines[0].startswith("#"):
            # Remove markdown header syntax
            title = lines[0].lstrip("#").strip()

        # Calculate word count and reading time
        word_count = len(content.split())
        estimated_reading_time = max(1, word_count // 200)  # 200 words per minute

        return NewsletterContent(
            title=title,
            body=content,
            word_count=word_count,
            estimated_reading_time=estimated_reading_time,
        )


# Global instance
_generator: NewsletterGenerator | None = None


def get_newsletter_generator() -> NewsletterGenerator:
    """Get or create newsletter generator singleton."""
    global _generator
    if _generator is None:
        _generator = NewsletterGenerator()
    return _generator
