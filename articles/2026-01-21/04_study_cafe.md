# 🎓 오토마타 스터디 카페: 직접 해보는 오픈소스 코딩 에이전트

안녕하세요, 이번 주 수요일도 새로운 소식으로 돌아왔어요!

이번 스터디 카페는 조금 특별해요. 이론과 트렌드는 잠시 내려놓고, 실제로 여러분의 컴퓨터에서 바로 실행할 수 있는 오픈소스 코딩 에이전트 두 가지를 소개하려고 합니다. Mistral의 Devstral 2와 Google의 Gemini CLI인데요, 각각 다른 방식으로 여러분의 개발 워크플로우를 도와줄 수 있답니다. 오늘은 설치부터 활용까지 함께 따라가 보세요!

## Part 1: Mistral Devstral 2 - 강력한 오픈소스 코딩 모델

### 왜 Devstral 2에 주목해야 할까요?

프랑스 AI 스타트업 Mistral AI가 출시한 Devstral 2는 123B 파라미터의 밀집 트랜스포머(Dense Transformer) 모델이에요. 256K 토큰이라는 방대한 컨텍스트 윈도우(Context Window)를 지원하는데, 이게 얼마나 큰지 감이 안 오실 수도 있겠네요. 일반적인 프로젝트의 여러 파일을 통째로 넣어도 될 정도로 넉넉한 용량이랍니다.

더 인상적인 건 실전 성능이에요. SWE-bench Verified에서 72.2%를 기록했는데, 이 벤치마크는 실제 GitHub 이슈를 해결하는 능력을 측정하는 테스트예요. 단순한 코드 생성이 아니라 진짜 소프트웨어 엔지니어링 작업에서 검증받은 셈이죠.

무엇보다 좋은 점은 **완전히 오픈소스**라는 거예요. Hugging Face에서 무료로 이용할 수 있고(시간 제한 있음), RTX 4090 같은 고성능 GPU가 있는 노트북에서도 실행 가능한 경량 버전이 제공됩니다. vLLM이나 Kilo Code 같은 플랫폼도 지원해서 기존 개발 환경에 통합하기도 쉬워요.

### 시작하기: 설치와 설정

세 가지 방법으로 Devstral 2를 사용할 수 있어요:

```bash
# 방법 1: Hugging Face에서 직접 다운로드
huggingface-cli login
huggingface-cli download mistralai/Devstral-2

# 방법 2: vLLM으로 로컬 서버 실행 (고성능 GPU 필요)
vllm serve mistralai/Devstral-2 --gpu-memory-utilization 0.9

# 방법 3: Mistral API 사용 (무료 제한 시간 제공)
pip install mistralai
export MISTRAL_API_KEY="your_key_here"
```

로컬 환경이 부담스럽다면 Mistral API를 추천드려요. 무료 티어로 충분히 테스트해볼 수 있답니다.

### 실전 활용 사례

**버그 수정의 든든한 동료**

에러 메시지가 뜨면 당황스럽죠? Devstral 2에게 에러 메시지와 해당 코드를 함께 보여주면, 원인을 분석하고 수정 방법을 제안해줘요. 256K 토큰 덕분에 여러 파일에 걸친 코드도 한 번에 분석할 수 있어서, "이 함수가 저기서 호출되는데 거기서 문제가 생기는구나" 같은 맥락까지 이해합니다.

**레거시 코드 리팩토링**

오래된 코드를 손봐야 하는데 어디서부터 시작할지 막막하신가요? Devstral 2에게 레거시 코드를 보여주고 현대적인 패턴으로 개선해달라고 요청해보세요. 성능 최적화나 가독성 개선 제안도 받을 수 있어요. 긴 컨텍스트 윈도우는 대규모 코드베이스 작업에 특히 유리합니다.

**테스트 코드 자동 생성**

테스트 코드 작성, 귀찮지만 중요하죠. 함수를 입력하면 엣지 케이스(Edge Case)까지 고려한 포괄적인 테스트 코드를 생성해줘요. 물론 100% 완벽하진 않지만, 시작점으로는 충분히 훌륭합니다.

## Part 2: Google Gemini CLI - AI가 깃든 터미널

### 터미널, 이제 AI와 대화하세요

구글이 Apache 2.0 라이선스로 공개한 Gemini CLI는 터미널 경험을 완전히 바꿔놓아요. 복잡한 bash 명령어를 외우는 대신, 자연어로 원하는 작업을 설명하면 AI가 알아서 명령어를 만들어주는 방식이죠.

특히 주목할 점은 MCP(Model Context Protocol)와 GEMINI.md 시스템 프롬프트(System Prompt) 같은 표준을 지원한다는 거예요. 이건 마치 스마트폰에 앱을 설치하듯이, Gemini CLI에 새로운 기능을 플러그인처럼 추가할 수 있다는 의미랍니다.

### 설치하고 시작하기

설치는 정말 간단해요:

```bash
# GitHub에서 클론
git clone https://github.com/google/gemini-cli
cd gemini-cli

# 설치 (Python 환경 필요)
pip install -e .

# API 키 설정 (Google AI Studio에서 무료 발급)
gemini config set api_key YOUR_API_KEY

# 제대로 설치되었는지 확인
gemini --version
```

API 키는 Google AI Studio에서 몇 분이면 발급받을 수 있어요. 무료 티어도 꽤 관대한 편이에요.

### 실전에서 이렇게 쓰세요

**복잡한 명령어를 자연어로**

"지난 7일간 수정된 Python 파일을 찾아서 라인 수를 세고 싶은데..." 이걸 bash 명령어로 만들려면 find, grep, xargs, wc를 조합해야 하죠. 대신 이렇게 해보세요:

```bash
gemini "find all Python files modified in the last 7 days and count lines of code"
```

Gemini CLI가 정확한 명령어를 생성해주고, 실행 전에 확인까지 받아요. 안전하면서도 편리하죠.

**코드베이스 탐색과 이해**

새로운 프로젝트에 합류했을 때 가장 힘든 게 코드 구조 파악이에요. Gemini CLI에게 물어보세요:

```bash
gemini analyze "What does this project do and how is it structured?"
```

프로젝트의 디렉토리 구조, 주요 모듈, 의존성을 분석해서 쉬운 말로 설명해줍니다.

**MCP로 무한 확장**

MCP 프로토콜의 진가는 확장성에 있어요. 예를 들어 Jira와 연동해서 "이번 스프린트의 티켓을 분석해줘"라고 할 수도 있고, Slack과 연결해서 알림을 보낼 수도 있어요. 데이터베이스 쿼리, 클라우드 리소스 관리 등 가능성은 무궁무진합니다.

## Part 3: 실전 프로젝트 - 자동 코드 리뷰 파이프라인

두 도구를 결합하면 어떤 시너지가 날까요? 간단한 자동 코드 리뷰 시스템을 만들어봅시다:

### 워크플로우 설계

1. **Gemini CLI로 변경사항 추출**: git diff를 분석해서 어떤 파일이 어떻게 바뀌었는지 구조화된 정보로 정리
2. **Devstral 2로 품질 검사**: 변경된 코드를 분석해서 잠재적 버그, 성능 이슈, 보안 취약점 탐지
3. **개선 제안 생성**: 단순히 문제를 지적하는 게 아니라, 구체적인 코드 예시와 함께 개선 방안 제시
4. **자동 PR 코멘트**: GitHub API를 통해 풀 리퀘스트에 리뷰 코멘트 자동 작성

이건 멀티 에이전트 시스템(Multi-Agent System)의 아주 간단한 예시예요. 각 에이전트가 자신의 강점을 발휘하는 단계를 맡고, 전체적으로는 혼자서는 불가능한 복잡한 작업을 완수하는 거죠.

### 실제로 만들어보기

구현은 생각보다 간단해요. Python 스크립트 하나면 충분합니다:

- Gemini CLI를 subprocess로 호출해서 git diff 분석
- Devstral 2 API로 코드 품질 체크
- GitHub API로 결과를 PR에 코멘트로 추가

물론 프로덕션 레벨로 만들려면 에러 핸들링, 레이트 리미팅(Rate Limiting), 비용 관리 등을 고려해야겠지만, 프로토타입은 하루면 충분히 만들 수 있어요.

## 더 깊이 파고들고 싶다면

### 추천 오픈소스 프로젝트

**Claude Code**: Anthropic이 공개한 터미널 기반 에이전트예요. 자율적으로 소프트웨어를 구축할 수 있는 수준까지 발전했답니다.

**Continue.dev**: VS Code와 JetBrains IDE에 직접 통합되는 AI 에이전트예요. 에디터를 떠나지 않고 AI의 도움을 받을 수 있어요.

**Aider**: CLI 기반의 AI 페어 프로그래밍(Pair Programming) 도구예요. 대화하듯이 코드를 함께 작성할 수 있답니다.

### 학습 자료

**Anthropic의 "Demystifying evals for AI agents" 가이드**: 에이전트의 성능을 어떻게 평가할지 고민 중이라면 필독 자료예요. 실용적인 평가 방법론을 배울 수 있어요.

**MCP 공식 문서**: Model Context Protocol을 이해하고 싶다면 여기서 시작하세요. 커스텀 스킬을 개발하는 방법도 배울 수 있어요.

**SWE-bench 벤치마크**: 코딩 에이전트의 성능을 측정하는 표준 벤치마크예요. 어떤 모델이 실제로 얼마나 잘하는지 객관적으로 비교할 수 있답니다.

### 커뮤니티에 참여하세요

**HackerNews**: AI 에이전트 관련 최신 토론이 활발해요. 때로는 개발자 본인이 직접 댓글로 설명을 추가하기도 해요.

**Reddit r/LocalLLaMA**: 로컬 환경에서 LLM을 실행하는 팁과 트릭이 가득해요. 하드웨어 최적화, 양자화(Quantization) 기법 등 실용적인 정보를 얻을 수 있어요.

**GitHub Discussions**: 각 프로젝트의 GitHub 저장소에는 이슈 트래커와 토론 게시판이 있어요. 버그 리포트나 기능 제안도 좋지만, 다른 사용자들의 질문과 답변을 읽는 것만으로도 많이 배울 수 있답니다.

## 마무리하며

오픈소스 코딩 에이전트의 세계는 놀라운 속도로 발전하고 있어요. 완전 자율적인 AI 개발자는 아직 먼 미래의 이야기지만, 지금 당장 사용할 수 있는 도구들도 여러분의 생산성을 크게 향상시킬 수 있어요.

가장 중요한 건 직접 해보는 거예요. 오늘 소개한 도구 중 하나를 골라서 설치해보세요. 작은 프로젝트에 적용해보고, 무엇이 잘 되고 무엇이 부족한지 직접 경험해보세요. 그 과정에서 여러분만의 워크플로우가 만들어질 거예요.

다음 주에도 더 유익한 소식으로 찾아올게요!

---

**참고 자료**
- [Mistral Devstral 2 공식 페이지](https://mistral.ai/news/devstral-2/)
- [Google Gemini CLI GitHub](https://github.com/google/gemini-cli)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
