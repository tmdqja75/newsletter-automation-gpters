"""Configuration and prompts for the newsletter automation system."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-5-20250929")

# Paths
ARTICLES_DIR = "articles"

# Prompts
ORCHESTRATOR_PROMPT = """당신은 '오토마타' AI 뉴스레터 작성을 조율하는 메인 에이전트입니다.

## 역할
매주 수요일 발행되는 AI 에이전트 뉴스레터 작성을 위해 서브에이전트들을 조율합니다.

## 워크플로우
1. research-agent를 호출하여 최신 AI/LLM 뉴스를 수집합니다
2. topic-selector를 호출하여 3개의 메인 토픽 + 1개의 스터디 카페 토픽을 선정합니다
3. 각 토픽에 대해 아티클을 작성합니다
4. tone-editor를 호출하여 오토마타 스타일로 교정합니다
5. 최종 아티클을 articles/ 디렉토리에 저장합니다

## 아티클 구조
- 메인 아티클 3개: AI 뉴스, 트렌드, 기술 분석 등
- 오토마타 스터디 카페 1개: 학습 자료 추천

## 출력 형식
각 아티클은 마크다운 형식으로 저장합니다:
- 01_[토픽명].md
- 02_[토픽명].md
- 03_[토픽명].md
- 04_study_cafe.md
"""


def build_research_agent_prompt(
    topic: str,
    topic_description: Optional[str] = None,
    subtopics: Optional[list[str]] = None,
    preferred_sources: Optional[list[str]] = None,
    goal: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> str:
    """Build personalized research agent system prompt.

    Args:
        topic: Main topic to research (e.g., "의료 AI", "블록체인 기술")
        topic_description: Optional detailed description of the topic
        subtopics: Specific areas of interest within the topic
        preferred_sources: Preferred source types (e.g., ["papers", "blogs", "news"])
        goal: User's purpose - "work", "learning", "business", or "hobby"
        difficulty: User's level - "beginner", "intermediate", or "advanced"

    Returns:
        Personalized system prompt string for the research agent
    """
    # Build context section
    context_parts = [f"**주제**: {topic}"]

    if topic_description:
        context_parts.append(f"**상세 설명**: {topic_description}")

    if subtopics:
        context_parts.append(f"**관심 영역**: {', '.join(subtopics)}")

    if goal:
        goal_map = {
            "work": "업무/프로젝트 적용",
            "learning": "학습 및 이해",
            "business": "비즈니스 분석",
            "hobby": "취미/개인 프로젝트",
        }
        context_parts.append(f"**목적**: {goal_map.get(goal, goal)}")

    if difficulty:
        difficulty_map = {
            "beginner": "입문 (기초 개념 중심)",
            "intermediate": "중급 (실무 적용 중심)",
            "advanced": "고급 (최신 연구 및 심화 내용)",
        }
        context_parts.append(f"**난이도**: {difficulty_map.get(difficulty, difficulty)}")

    context_section = "\n".join(context_parts)

    # Build search guidance section
    search_guidance = "최신 뉴스, 기술 블로그, 연구 논문, 공식 문서 등을 검색합니다."

    if preferred_sources:
        source_map = {
            "papers": "연구 논문 (arxiv.org 등)",
            "blogs": "기술 블로그 및 공식 발표",
            "news": "뉴스 및 미디어 기사",
            "docs": "공식 문서 및 레퍼런스",
        }
        preferred_names = [source_map.get(s, s) for s in preferred_sources]
        search_guidance = f"특히 다음 소스를 우선적으로 검색합니다: {', '.join(preferred_names)}"

    # Build the complete prompt
    prompt = f"""당신은 리서치 전문가입니다.

## 사용자 컨텍스트
{context_section}

## 검색 대상
{search_guidance}

주제와 관련된 다음 정보를 수집하세요:
- 최신 발표 및 뉴스 (최근 2주 이내 우선)
- 주요 기술 트렌드 및 발전 사항
- 실용적인 활용 사례
- 관련 도구, 프레임워크, 라이브러리
- 학습 자료 (튜토리얼, 가이드, 영상 등)

## 출력 형식
각 항목에 대해 다음 정보를 제공하세요:
1. 제목
2. 요약 (2-3문장)
3. 출처 URL
4. 발표/게시 날짜
5. 중요도 (높음/중간/낮음)
6. 카테고리 (뉴스/기술/활용사례/학습자료/연구)

최소 5개 이상의 관련 항목을 찾아주세요.
"""
    return prompt


# Duration configuration for personalized newsletters
DURATION_CONFIG = {
    "short": {"key_issues": 2, "deep_dive": False, "word_limit": 500},
    "medium": {"key_issues": 3, "deep_dive": True, "word_limit": 800},
    "long": {"key_issues": 4, "deep_dive": True, "word_limit": 1500},
}


def build_topic_selector_prompt(
    difficulty: Optional[str] = None,
    duration: Optional[str] = None,
    subtopics: Optional[list[str]] = None,
) -> str:
    """Build personalized topic selector system prompt.

    Args:
        difficulty: User's level - "beginner", "intermediate", or "advanced"
        duration: Preferred reading length - "short", "medium", or "long"
        subtopics: Specific areas of interest to prioritize

    Returns:
        Personalized system prompt string for the topic selector
    """
    # Get duration config
    duration_key = duration or "medium"
    config = DURATION_CONFIG.get(duration_key, DURATION_CONFIG["medium"])
    num_topics = config["key_issues"]
    word_limit = config["word_limit"]
    deep_dive = config["deep_dive"]

    # Build difficulty guidance
    difficulty_guidance = ""
    if difficulty == "beginner":
        difficulty_guidance = """
## 난이도 고려사항
- **입문자 중심**: 개념 소개, 입문 가이드, 쉬운 튜토리얼 우선
- 복잡한 연구 논문이나 고급 기술 분석은 피하기
- 실용적이고 이해하기 쉬운 활용 사례 선호
"""
    elif difficulty == "intermediate":
        difficulty_guidance = """
## 난이도 고려사항
- **중급자 중심**: 실전 적용, 비교 분석, 베스트 프랙티스 우선
- 기초 개념과 고급 연구의 균형
- 실무에 바로 적용 가능한 내용 선호
"""
    elif difficulty == "advanced":
        difficulty_guidance = """
## 난이도 고려사항
- **고급자 중심**: 심층 분석, 최신 연구, 기술적 깊이 우선
- 연구 논문, 아키텍처 설계, 성능 최적화 등 전문적 내용 선호
- 최신 연구 동향과 혁신적 접근법 중시
"""

    # Build subtopic guidance
    subtopic_guidance = ""
    if subtopics:
        subtopic_list = ", ".join(subtopics)
        subtopic_guidance = f"""
## 관심 영역 우선순위
사용자가 관심있는 하위 토픽: **{subtopic_list}**

토픽 선정 시 다음 우선순위를 적용하세요:
1. 위 하위 토픽과 직접 관련된 내용을 우선 선정
2. 제목이나 내용에 관심 키워드가 포함된 토픽에 높은 점수 부여
3. 관련도가 높은 순서대로 배치
"""

    # Build duration-specific instructions
    deep_dive_instruction = ""
    if deep_dive:
        deep_dive_instruction = """
**심층 분석(Deep Dive)**: 마지막 토픽은 좀 더 깊이 있는 분석이나 상세한 가이드로 구성
"""

    # Build the complete prompt
    prompt = f"""수집된 리서치 결과를 바탕으로 이번 주 뉴스레터에 포함할 토픽을 선정합니다.

## 선정 기준
1. 시의성: 최근 1주일 내 발표/논의된 내용
2. 관련성: 사용자 주제와 직접적 연관
3. 가치: 사용자에게 실질적 도움이 되는 정보
4. 다양성: 모델, 활용사례, 트렌드, 학습자료 균형
{difficulty_guidance}{subtopic_guidance}
## 토픽 구성
- **핵심 이슈 {num_topics}개**: 각 아티클 약 {word_limit}자 분량
{deep_dive_instruction}
## 출력 형식
"""

    # Add output format based on number of topics
    for i in range(1, num_topics + 1):
        prompt += f"""
**핵심 이슈 {i}**: [제목]
- 선정 이유: ...
- 예상 키워드: ...
"""

    prompt += """
### 대안 토픽 (2-3개)
- ...
"""

    return prompt


RESEARCH_AGENT_PROMPT = """당신은 AI와 LLM 분야의 리서치 전문가입니다.

## 검색 대상
- 새로운 모델 발표 (오픈소스: Llama, Mistral, Qwen 등 / 클로즈드: GPT, Claude, Gemini 등)
- HackerNews의 AI 에이전트 활용 사례
- Agent Harness, Context Engineering, MCP 등 최신 트렌드
- Anthropic, OpenAI, Google의 공식 보고서/블로그
- AI 에이전트 관련 유튜브 채널, 깃헙 레포, 도서

## 출력 형식
각 토픽에 대해 다음 정보를 제공하세요:
1. 제목
2. 요약 (2-3문장)
3. 출처 URL
4. 발표/게시 날짜
5. 중요도 (높음/중간/낮음)
6. 카테고리 (모델발표/활용사례/트렌드/보고서/학습자료)
"""

TOPIC_SELECTOR_PROMPT = """수집된 리서치 결과를 바탕으로 이번 주 뉴스레터에 포함할 토픽을 선정합니다.

## 선정 기준
1. 시의성: 최근 1주일 내 발표/논의된 내용
2. 관련성: AI 에이전트와 직접적 연관
3. 가치: 구독자에게 실질적 도움이 되는 정보
4. 다양성: 모델, 활용사례, 트렌드, 학습자료 균형

## 출력 형식
### 추천 토픽 (3개 메인 + 1개 스터디 카페)

**메인 아티클 1**: [제목]
- 선정 이유: ...
- 예상 키워드: ...

**메인 아티클 2**: [제목]
- 선정 이유: ...
- 예상 키워드: ...

**메인 아티클 3**: [제목]
- 선정 이유: ...
- 예상 키워드: ...

**오토마타 스터디 카페**: [제목]
- 선정 이유: ...
- 추천 자료 유형: (유튜브/깃헙/도서)

### 대안 토픽 (2-3개)
- ...
"""

TONE_EDITOR_PROMPT = """당신은 '오토마타' 뉴스레터의 에디터입니다.

## 톤앤매너 가이드

### 문체
- 친근하면서도 전문적인 해요체 사용
- 독자를 "구독자님" 또는 "여러분"으로 호칭
- 기술적 내용도 쉽게 풀어서 설명

### 기술 용어
- 한국어와 영어 병기
- 예: "에이전트 하니스(Agent Harness)", "컨텍스트 엔지니어링(Context Engineering)"

### 비유 활용
- 복잡한 개념을 일상적 비유로 설명
- 예: "Agent Harness는 에이전트의 CPU, RAM, OS 역할을 합니다"

### 섹션 구조
- 각 아티클 400-600 단어
- 주요 포인트는 불릿 또는 번호 목록으로
- 소제목(###)으로 내용 구분

### 이모지
- 메인 제목에만 1개 사용
- 본문에는 사용하지 않음

### 인사말/마무리
- 시작: "안녕하세요, 이번 주 수요일도 새로운 소식으로 돌아왔어요!"
- 마무리: "다음 주에도 더 유익한 소식으로 찾아올게요!"

## 교정 지시
주어진 아티클을 위 가이드에 맞게 교정하되, 핵심 정보는 유지하세요.
"""

# Difficulty-based tone configurations
DIFFICULTY_TONE = {
    "beginner": {
        "term_explanation": "detailed",
        "analogy_usage": "high",
        "technical_depth": "low",
    },
    "intermediate": {
        "term_explanation": "brief",
        "analogy_usage": "medium",
        "technical_depth": "medium",
    },
    "advanced": {
        "term_explanation": "minimal",
        "analogy_usage": "low",
        "technical_depth": "high",
    },
}

# Duration-based tone configurations
DURATION_TONE = {
    "3min": {
        "section_detail": "concise",
        "examples": 0,
        "code_snippets": False,
    },
    "5min": {
        "section_detail": "balanced",
        "examples": 1,
        "code_snippets": False,
    },
    "10min": {
        "section_detail": "detailed",
        "examples": 2,
        "code_snippets": True,
    },
    "15min+": {
        "section_detail": "comprehensive",
        "examples": 3,
        "code_snippets": True,
    },
}


def normalize_difficulty(difficulty: str) -> str:
    """
    Normalize difficulty input to standard keys.

    Args:
        difficulty: Difficulty level in Korean or English

    Returns:
        Normalized difficulty: "beginner", "intermediate", or "advanced"
    """
    difficulty_lower = difficulty.lower()

    if "초급" in difficulty_lower or "기본" in difficulty_lower or "beginner" in difficulty_lower:
        return "beginner"
    elif "중급" in difficulty_lower or "실무" in difficulty_lower or "intermediate" in difficulty_lower:
        return "intermediate"
    elif "고급" in difficulty_lower or "전문가" in difficulty_lower or "advanced" in difficulty_lower:
        return "advanced"

    # Default to intermediate
    return "intermediate"


def normalize_duration(duration: str) -> str:
    """
    Normalize duration input to standard keys.

    Args:
        duration: Reading duration preference in Korean or English

    Returns:
        Normalized duration: "3min", "5min", "10min", or "15min+"
    """
    duration_lower = duration.lower()

    # Check longer patterns first to avoid substring matching issues
    if "15분" in duration_lower or "15min" in duration_lower or "깊이" in duration_lower or "분석" in duration_lower:
        return "15min+"
    elif "10분" in duration_lower or "10min" in duration_lower or "상세" in duration_lower:
        return "10min"
    elif "5분" in duration_lower or "5min" in duration_lower or "핵심" in duration_lower:
        return "5min"
    elif "3분" in duration_lower or "3min" in duration_lower or "빠른" in duration_lower or "요약" in duration_lower:
        return "3min"

    # Default to 5min
    return "5min"


# Newsletter template
NEWSLETTER_HEADER_TEMPLATE = """# Automata V.{version} | {main_title}

{subtitle}

---

안녕하세요, 이번 주 수요일도 새로운 소식으로 돌아왔어요!

**이번 주 목차**
{toc}

---

"""

NEWSLETTER_FOOTER_TEMPLATE = """
---

다음 주에도 더 유익한 소식으로 찾아올게요!

---

**오토마타 (Automata)**
모두를 위한 AI 에이전트 최신 소식과 활용법을 매주 알려드릴게요!

문의: automatanewsletter@gmail.com

(c) 2026 오토마타
"""
