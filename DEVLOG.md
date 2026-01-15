# 오토마타 뉴스레터 자동화 에이전트 - 개발 로그

Claude Code와 함께 진행한 개발 작업 기록입니다.

---

## 2026-01-15 (Day 1)

### 1. 프로젝트 기획 및 deepagents 패키지 조사

```
매주 수요일 발행하는 "오토마타" (Automata) 뉴스레터 작성을 자동화하는 langgraph deepagent를 만들어보려고 해
아직 코드는 작성하지 말고, 이 에이전트를 파이썬으로 만들기 위해 어떻게 해야 하는지 같이 생각해보자
```

**Claude 작업:**
- deepagents 패키지에 대한 웹 검색 및 공식 문서 분석
- GitHub 레포지토리에서 코드 예제 및 API 사용법 파악
- `create_deep_agent()` 함수, subagents 정의 방법, middleware 아키텍처 학습

---

### 2. 요구사항 정리 및 톤앤매너 분석

```
[검색 도구] Tavily API (Recommended)
[승인 프로세스] Human-in-the-loop
[톤앤매너] 기존 아티클 샘플 있음 - URL로 공유
```

**Claude 작업:**
- 사용자 요구사항 수집 (검색 도구, 승인 프로세스, 톤앤매너)
- 기존 뉴스레터 URL(maily.so/automata) 분석
- 톤앤매너 가이드 도출: 친근한 해요체, 기술 용어 한영 병기, 400-600 단어/섹션

---

### 3. 구현 계획 수립

```
[구현 계획 승인 요청]
```

**Claude 작업:**
- 상세 구현 계획서 작성 (`.claude/plans/` 디렉토리에 저장)
- 에이전트 아키텍처 설계:
  - Main Orchestrator Agent
  - Research Subagent (Tavily, HackerNews 검색)
  - Topic Selection Agent (Human-in-the-Loop)
  - Tone & Manner Agent (한국어 스타일 교정)
- 디렉토리 구조 및 워크플로우 정의

---

### 4. 프로젝트 환경 설정

```
poetry 대신 uv를 사용해서 프로젝트 세팅해줘
```

**Claude 작업:**
- `pyproject.toml` 생성 (deepagents, tavily-python, python-dotenv 의존성)
- `.env.example` 생성 (ANTHROPIC_API_KEY, TAVILY_API_KEY)
- `.gitignore` 생성
- `README.md` 작성
- uv 패키지 매니저로 의존성 설치: `uv sync`

**생성된 파일:**
- `pyproject.toml` - 프로젝트 설정 및 의존성
- `.env.example` - 환경변수 템플릿
- `.gitignore` - Git 무시 파일
- `README.md` - 프로젝트 문서

---

### 5. 에이전트 코드 구현

```
[계획 승인 후 구현 진행]
```

**Claude 작업:**
- `src/config.py` - 설정 및 프롬프트 정의 (ORCHESTRATOR_PROMPT, RESEARCH_PROMPT 등)
- `src/agents/__init__.py` - 서브에이전트 정의
  - `research_subagent` - AI/LLM 뉴스 리서치
  - `topic_selection_agent` - 토픽 선정 및 우선순위 결정
  - `tone_agent` - 오토마타 톤앤매너 교정
- `src/tools/search_tools.py` - Tavily 검색 도구
- `src/utils/merge_articles.py` - 아티클 병합 유틸리티
- `src/main.py` - 메인 오케스트레이터
- `run.py` - CLI 실행 진입점

**생성된 디렉토리 구조:**
```
src/
├── __init__.py
├── config.py
├── main.py
├── agents/
│   ├── __init__.py
│   ├── research.py
│   ├── topic_selector.py
│   └── tone_editor.py
├── tools/
│   ├── __init__.py
│   └── search_tools.py
└── utils/
    ├── __init__.py
    └── merge_articles.py
```

---

### 6. 실행 오류 디버깅

```
when I start @run.py file, it outputs the following and gets stuck forever. Figure out the cause and fix it.
🚀 오토마타 뉴스레터 생성 시작
📅 발행 예정일: 2026-01-21
----------------------------------------
```

**Claude 작업:**
- `run.py` 코드 분석 및 실행 흐름 추적
- 에이전트 스트리밍 로직 디버깅
- 문제 원인 파악: deepagents 에이전트 초기화 및 스트리밍 대기 이슈
- 타임아웃 및 진행 상황 출력 메시지 추가
- `sys.stdout.flush()` 추가로 실시간 출력 보장

---

### 7. 에이전트 테스트 및 검증

```
[테스트 파일 작성 및 실행]
```

**Claude 작업:**
- `test_agent.py` - 에이전트 단위 테스트
- `test_simple_newsletter.py` - 간단한 뉴스레터 생성 테스트
- 실제 뉴스레터 생성 테스트 실행

**생성된 파일:**
- `test_agent.py` - 에이전트 테스트 코드
- `test_simple_newsletter.py` - 통합 테스트

---

## 2026-01-16 (Day 2)

### 8. 전체 뉴스레터 생성 테스트

```
[전체 워크플로우 실행]
```

**Claude 작업:**
- 4개 아티클 자동 생성 완료
  - `01_deepseek_revolution.md` - DeepSeek V3.2-V4 소식
  - `02_multi_agent_era.md` - 멀티 에이전트 시스템 트렌드
  - `03_next_ai_paradigm.md` - Test-Time Reasoning 패러다임
  - `04_study_cafe.md` - 오픈소스 코딩 에이전트 추천
- `newsletter.md` - 최종 병합된 뉴스레터 생성

**생성된 파일:**
- `articles/2026-01-21/01_deepseek_revolution.md`
- `articles/2026-01-21/02_multi_agent_era.md`
- `articles/2026-01-21/03_next_ai_paradigm.md`
- `articles/2026-01-21/04_study_cafe.md`
- `articles/2026-01-21/newsletter.md`

---

## 기술 스택

- **Framework**: deepagents (LangGraph 기반)
- **LLM**: Claude Sonnet 4.5 (deepagents 기본값)
- **Web Search**: Tavily API
- **Package Manager**: uv
- **Language**: Python 3.12

---

## 주요 기능

1. **AI 뉴스 자동 리서치**
   - Tavily API를 통한 최신 AI/LLM 뉴스 수집
   - HackerNews 트렌드 모니터링

2. **멀티 에이전트 아키텍처**
   - Research Agent: 뉴스 수집 및 분석
   - Topic Selection Agent: 토픽 선정 (Human-in-the-Loop 지원)
   - Tone Agent: 한국어 톤앤매너 교정

3. **자동 아티클 생성**
   - 4개 섹션 (메인 토픽 3개 + 스터디 카페 1개)
   - 400-600 단어/섹션
   - 마크다운 형식 출력

4. **뉴스레터 병합**
   - 개별 아티클을 하나의 뉴스레터로 자동 병합
   - 목차 자동 생성
   - 헤더/푸터 템플릿 적용

5. **CLI 인터페이스**
   - `--date`: 특정 날짜 지정
   - `--preview`: 기존 아티클 미리보기
   - `--merge`: 아티클 병합만 수행
   - `--quick`: 빠른 테스트 모드
