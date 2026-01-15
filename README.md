# 오토마타 뉴스레터 자동화

LangGraph deepagents를 활용한 AI 뉴스레터 자동 작성 시스템

## 설치

```bash
uv sync
```

## 환경 설정

```bash
cp .env.example .env
# .env 파일에서 API 키 설정:
# - ANTHROPIC_API_KEY
# - TAVILY_API_KEY
```

## 실행

```bash
# 다음 수요일 발행용 뉴스레터 생성
uv run python run.py

# 특정 날짜용 뉴스레터 생성
uv run python run.py --date 2026-01-22

# 기존 아티클 미리보기
uv run python run.py --preview 2026-01-15

# 기존 아티클 병합만 수행
uv run python run.py --merge 2026-01-15
```

## 개발

```bash
# 개발 의존성 포함 설치
uv sync --all-extras
```
