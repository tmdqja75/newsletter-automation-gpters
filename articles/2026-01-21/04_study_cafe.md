# 📚 AI 에이전트 보안, 어디서부터 시작할까요?

안녕하세요, 구독자님! 이번 주 스터디 카페에 오신 걸 환영해요.

이번 주 첫 번째 아티클에서 프롬프트 주입 공격에 대해 다뤘죠? 많은 분들이 "그래서 실제로 어떻게 대응해야 하나요?"라고 물어보셨어요. 완전히 이해돼요. 문제를 알아도 어디서부터 시작해야 할지 막막하니까요.

오늘은 **AI 에이전트 보안을 실무에 적용하는 방법**을 단계별로 함께 살펴볼게요.

## 1단계: 위험 평가부터 시작하세요

보안 조치를 무작정 추가하기 전에, 먼저 **우리 AI 시스템이 어떤 위험에 노출되어 있는지** 파악해야 해요.

다음 질문들을 체크해보세요:

**데이터 접근**
- AI가 어떤 데이터에 접근할 수 있나요?
- 그 중 민감한 정보(개인정보, 금융 데이터, 영업 비밀)는 무엇인가요?
- 데이터가 유출되면 어떤 피해가 발생하나요?

**실행 권한**
- AI가 어떤 작업을 수행할 수 있나요?
- 이메일 발송, 결제 처리, 데이터베이스 수정 등의 권한이 있나요?
- 잘못된 실행이 비즈니스에 어떤 영향을 미치나요?

**외부 입력**
- AI가 처리하는 데이터의 출처는 어디인가요?
- 사용자 입력, 이메일 본문, 웹 페이지 등 신뢰할 수 없는 소스가 있나요?
- 악의적인 입력이 들어올 가능성은 얼마나 되나요?

이런 질문에 답하다 보면, **어디에 가장 큰 위험이 있는지** 자연스럽게 보이기 시작해요.

## 2단계: 권한 최소화 원칙 적용

위험을 파악했다면, 이제 **최소 권한 원칙(Principle of Least Privilege)**을 적용할 차례예요.

### 데이터 접근 제한

AI가 모든 데이터에 접근할 필요는 없어요. 작업에 꼭 필요한 범위로 제한하세요.

**나쁜 예시:**
```python
# AI에게 전체 데이터베이스 접근 권한 부여
agent.add_tool(DatabaseTool(connection_string="full_access"))
```

**좋은 예시:**
```python
# 특정 테이블, 읽기 전용으로 제한
agent.add_tool(DatabaseTool(
    connection_string="read_only",
    allowed_tables=["public_products", "public_reviews"],
    forbidden_columns=["user_email", "payment_info"]
))
```

### 작업 승인 프로세스

중요한 작업은 사람의 승인을 받도록 설계하세요.

**구현 예시:**
```python
class PaymentTool:
    def execute(self, amount, recipient):
        if amount > 1000:
            # 1000달러 이상은 사람의 승인 필요
            approval = request_human_approval(
                action="payment",
                details={"amount": amount, "recipient": recipient}
            )
            if not approval.approved:
                return "Payment cancelled by user"
        
        return process_payment(amount, recipient)
```

이렇게 하면 AI가 실수하거나 악의적인 명령을 받아도, **최악의 시나리오를 방지**할 수 있어요.

## 3단계: 입력 검증과 출력 필터링

프롬프트 주입을 완전히 막을 수는 없지만, **위험을 크게 줄일 수는** 있어요.

### 입력 검증

외부에서 들어오는 데이터는 항상 의심하세요.

```python
def sanitize_external_input(text):
    # 의심스러운 패턴 탐지
    suspicious_patterns = [
        r"ignore previous instructions",
        r"system:\s*you are now",
        r"disregard all prior",
        # 더 많은 패턴 추가...
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Suspicious input detected: {text[:100]}")
            return sanitize_or_reject(text)
    
    return text

# 사용 예시
user_email = fetch_email()
safe_content = sanitize_external_input(user_email.body)
ai_response = agent.process(safe_content)
```

### 출력 필터링

AI의 응답도 검증하세요. 민감한 정보가 포함되어 있지 않은지 확인해야 해요.

```python
def filter_sensitive_output(response):
    # 이메일 주소, 전화번호, 카드 번호 등 탐지
    patterns = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    }
    
    filtered = response
    for data_type, pattern in patterns.items():
        filtered = re.sub(pattern, f'[{data_type.upper()}_REDACTED]', filtered)
    
    return filtered
```

## 4단계: 모니터링과 로깅

보안은 한 번 설정하고 끝나는 게 아니에요. **지속적인 모니터링**이 필요해요.

### 이상 행동 탐지

AI의 행동 패턴을 추적하고, 평소와 다른 행동을 탐지하세요.

```python
class AIMonitor:
    def __init__(self):
        self.baseline = self.establish_baseline()
    
    def check_anomaly(self, action):
        # 비정상적으로 많은 데이터 요청
        if action.data_volume > self.baseline.avg_data_volume * 3:
            alert("Unusual data access pattern detected")
        
        # 평소와 다른 시간대의 활동
        if self.is_unusual_time(action.timestamp):
            alert("Activity detected at unusual time")
        
        # 짧은 시간에 많은 요청
        if self.count_recent_actions() > self.baseline.avg_actions * 5:
            alert("Unusually high activity rate")
```

### 상세한 로깅

모든 중요한 작업을 로그로 남기세요. 문제가 생겼을 때 추적할 수 있어야 해요.

```python
def log_ai_action(action, context):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action.type,
        "input": sanitize_for_logging(action.input),
        "output": sanitize_for_logging(action.output),
        "data_accessed": action.data_accessed,
        "user_context": context.user_id,
        "model_version": context.model_version,
    }
    
    security_logger.info(json.dumps(log_entry))
    
    # 민감한 작업은 별도로 감사 로그 기록
    if action.type in ["payment", "data_export", "permission_change"]:
        audit_logger.critical(json.dumps(log_entry))
```

## 5단계: 정기적인 보안 검토

보안은 한 번 설정하면 끝이 아니에요. **정기적으로 검토하고 개선**해야 해요.

### 분기별 체크리스트

**접근 권한 검토**
- 현재 AI가 가진 권한이 여전히 필요한가요?
- 새로운 기능 추가로 인해 권한이 과도하게 확장되지 않았나요?

**로그 분석**
- 지난 3개월간 이상 행동 패턴이 있었나요?
- 실패한 작업이나 거부된 요청에서 패턴이 보이나요?

**보안 업데이트**
- AI 모델 제공자의 보안 권고사항을 확인했나요?
- 사용 중인 라이브러리와 프레임워크가 최신 버전인가요?

**테스트**
- 프롬프트 주입 테스트를 정기적으로 수행하고 있나요?
- 새로운 공격 벡터에 대한 방어 테스트를 했나요?

## 실용적인 시작 팁

"이 모든 걸 다 해야 하나요?"라고 걱정하실 수도 있어요. 괜찮아요. **작은 것부터 시작**하세요.

**이번 주에 할 수 있는 것:**
1. AI가 접근하는 데이터 목록을 작성하세요
2. 가장 민감한 데이터 3가지를 식별하세요
3. 그 데이터에 대한 접근을 제한하세요

**이번 달에 할 수 있는 것:**
1. 중요한 작업에 승인 프로세스를 추가하세요
2. 기본적인 입력 검증을 구현하세요
3. 주요 작업에 대한 로깅을 시작하세요

**다음 분기에 할 수 있는 것:**
1. 모니터링 대시보드를 만드세요
2. 정기적인 보안 검토 프로세스를 수립하세요
3. 팀과 함께 보안 인시던트 대응 계획을 수립하세요

## 완벽하지 않아도 괜찮아요

마지막으로 가장 중요한 이야기를 할게요. **완벽한 보안은 존재하지 않아요.** 100% 안전한 시스템을 만들려고 하다가 아예 시작하지 못하는 것보다, **실용적인 수준의 보안으로 시작**하는 것이 훨씬 낫죠.

보안은 여정이에요. 오늘 구독자님의 시스템이 어제보다 조금 더 안전해졌다면, 그것으로 충분해요. 계속 개선해나가면 돼요.

다음 스터디 카페에서는 구독자님들이 실제로 구현한 보안 전략과 마주친 챌린지를 공유할 예정이에요. 궁금한 점이나 공유하고 싶은 경험이 있다면 언제든 댓글로 남겨주세요!

---

**핵심 요약**
- AI 에이전트 보안은 위험 평가부터 시작하여 단계적으로 접근
- 최소 권한 원칙을 적용하고, 중요한 작업에는 승인 프로세스 추가
- 입력 검증과 출력 필터링으로 프롬프트 주입 위험 감소
- 모니터링과 로깅을 통해 이상 행동을 조기에 탐지
- 완벽한 보안은 불가능하므로 실용적 수준에서 시작하여 지속적으로 개선

**추천 리소스**
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [AI Security Best Practices by Google](https://cloud.google.com/security/ai)
- [Anthropic's Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)

**다음 스터디 카페 예고**
- 실전 프롬프트 주입 테스트 케이스와 방어 전략
- 커뮤니티가 공유하는 AI 보안 인시던트 사례
- AI 에이전트 권한 관리 패턴 라이브러리