# Test Harness - 아키텍처 수정안 (v2)

> 기존 `plan.md`의 Streamlit 기반 구조에서 **FastAPI + Next.js** 기반으로 변경
> `simple-llm-loadtester` 프로젝트 구조 차용

## 1. 변경 사항 요약

| 항목 | 기존 (plan.md) | 수정안 (v2) |
|------|---------------|-------------|
| **Frontend** | Streamlit | Next.js 14 |
| **Backend** | Streamlit 내장 | FastAPI |
| **구조** | 단일 app.py | 마이크로서비스 (services/) |
| **공유 코드** | core/ | shared/ (CLI/API 공유 가능) |
| **실시간 업데이트** | Streamlit rerun | WebSocket |

### 변경 이유

1. **확장성**: Streamlit은 프로토타이핑에 적합하나, 복잡한 UI/UX 구현에 제한
2. **API 분리**: 다른 시스템에서 호출 가능한 REST API 필요
3. **실시간 처리**: WebSocket 기반 진행률 업데이트
4. **유지보수**: 프론트/백엔드 분리로 독립적 개발 가능

---

## 2. 프로젝트 구조

```
test-harness/
├── services/
│   ├── api/                          # FastAPI 백엔드 (포트 8080)
│   │   ├── src/test_harness_api/
│   │   │   ├── main.py               # FastAPI 애플리케이션
│   │   │   ├── config.py             # 설정 관리
│   │   │   ├── routers/
│   │   │   │   ├── tests.py          # 테스트 실행/관리 API
│   │   │   │   ├── prompts.py        # 프롬프트 CRUD API
│   │   │   │   ├── evaluations.py    # 평가 결과 조회 API
│   │   │   │   ├── models.py         # LLM 모델 목록 API
│   │   │   │   └── websocket.py      # 실시간 진행률 스트리밍
│   │   │   ├── services/
│   │   │   │   ├── test_service.py   # 테스트 실행 비즈니스 로직
│   │   │   │   └── promptfoo_service.py  # promptfoo 연동
│   │   │   └── models/
│   │   │       └── schemas.py        # API 요청/응답 스키마
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── web/                          # Next.js 대시보드 (포트 3000)
│       ├── src/
│       │   ├── app/                  # App Router
│       │   │   ├── page.tsx          # 메인 대시보드
│       │   │   ├── tests/
│       │   │   │   ├── page.tsx      # 테스트 실행 페이지
│       │   │   │   └── [id]/page.tsx # 테스트 상세 결과
│       │   │   ├── prompts/
│       │   │   │   ├── page.tsx      # 프롬프트 목록
│       │   │   │   └── editor/page.tsx # 프롬프트 편집기
│       │   │   ├── compare/
│       │   │   │   └── page.tsx      # Side-by-side 비교
│       │   │   └── history/
│       │   │       └── page.tsx      # 테스트 이력
│       │   ├── components/
│       │   │   ├── PromptEditor.tsx  # 프롬프트 편집 컴포넌트
│       │   │   ├── TestRunner.tsx    # 테스트 실행 UI
│       │   │   ├── ResultTable.tsx   # 결과 테이블
│       │   │   ├── CompareView.tsx   # 비교 뷰
│       │   │   └── AssertionBadge.tsx # Pass/Fail 배지
│       │   ├── hooks/
│       │   │   ├── useTests.ts       # 테스트 API 훅
│       │   │   └── useWebSocket.ts   # WebSocket 연결 훅
│       │   └── lib/
│       │       └── api.ts            # API 클라이언트
│       ├── Dockerfile
│       └── package.json
│
├── shared/                           # 공유 코드 (API/CLI 공통 사용)
│   ├── core/
│   │   ├── models.py                 # Pydantic 데이터 모델
│   │   ├── promptfoo_runner.py       # promptfoo subprocess 실행
│   │   ├── llm_client.py             # LLM API 호출 래퍼
│   │   ├── assertions.py             # 커스텀 assertion 로직
│   │   ├── report_generator.py       # HTML/PDF 보고서 생성
│   │   └── rag_interceptor.py        # RAG Context 로깅
│   │
│   ├── adapters/                     # LLM 서버 어댑터 (팩토리 패턴)
│   │   ├── base.py                   # 추상 어댑터 인터페이스
│   │   ├── openai_compat.py          # OpenAI 호환 API
│   │   │                             # (Together AI, vLLM, 사내 모델)
│   │   ├── anthropic.py              # Claude API
│   │   └── factory.py                # 어댑터 팩토리
│   │
│   └── database/
│       ├── database.py               # SQLite 저장소
│       └── migrations/               # DB 마이그레이션
│
├── vendor/                           # 외주사 원본 코드 (Read-only)
│   └── README.md                     # 외주사 코드 사용 가이드
│
├── configs/
│   ├── promptfooconfig.yaml          # promptfoo 기본 설정
│   ├── prompts/                      # 프롬프트 템플릿
│   │   ├── default.yaml
│   │   └── variants/                 # 프롬프트 변형들
│   └── models.yaml                   # 지원 모델 목록
│
├── data/
│   ├── goldset.json                  # 검증용 Q&A 셋
│   └── test_cases/                   # 테스트 케이스 파일들
│
├── docker-compose.yml                # 전체 서비스 오케스트레이션
├── pyproject.toml                    # 루트 프로젝트 설정
├── .env.example                      # 환경 변수 템플릿
└── README.md
```

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Next.js Web Dashboard                   │   │
│  │  • 프롬프트 편집기    • Side-by-side 비교            │   │
│  │  • 테스트 실행 UI     • 결과 시각화                  │   │
│  │  • 이력 조회          • 보고서 다운로드              │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                      API Layer (FastAPI)                    │
│  ┌─────────────┬─────────────┬─────────────┬────────────┐  │
│  │ /tests      │ /prompts    │ /evaluations│ /ws        │  │
│  │ 테스트 관리 │ 프롬프트    │ 평가 결과   │ 실시간     │  │
│  └─────────────┴─────────────┴─────────────┴────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Business Logic Layer (shared/)            │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ PromptfooRunner  │  │ LLMClient        │                │
│  │ • subprocess     │  │ • API 호출       │                │
│  │ • 결과 파싱      │  │ • 응답 처리      │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Assertions       │  │ ReportGenerator  │                │
│  │ • JSON 검증      │  │ • HTML/PDF 생성  │                │
│  │ • 금지어 체크    │  │                  │                │
│  └──────────────────┘  └──────────────────┘                │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Adapter Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ OpenAI      │  │ Anthropic   │  │ Custom      │         │
│  │ Compatible  │  │ (Claude)    │  │ (사내 모델) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │ Together   │   │ Claude API │   │ 사내 vLLM  │
   │ AI API     │   │            │   │ 서버       │
   └────────────┘   └────────────┘   └────────────┘
```

---

## 4. 핵심 컴포넌트 설계

### 4.1 Pydantic 데이터 모델 (shared/core/models.py)

```python
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class AssertionType(str, Enum):
    CONTAINS = "contains"
    NOT_CONTAINS = "not-contains"
    IS_JSON = "is-json"
    REGEX = "regex"
    LLM_RUBRIC = "llm-rubric"

class Assertion(BaseModel):
    type: AssertionType
    value: str | None = None
    threshold: float | None = None

class Prompt(BaseModel):
    id: str
    name: str
    content: str
    variables: list[str] = []
    created_at: datetime
    updated_at: datetime

class TestCase(BaseModel):
    id: str
    input: dict[str, str]          # 변수 바인딩
    expected_output: str | None     # 기대 출력 (선택)
    assertions: list[Assertion]

class ModelConfig(BaseModel):
    id: str
    name: str
    provider: str                   # "together", "openai", "anthropic", "custom"
    endpoint: str
    api_key_env: str               # 환경변수 이름

class TestRun(BaseModel):
    id: str
    prompts: list[str]             # 테스트할 프롬프트 ID 목록
    models: list[str]              # 테스트할 모델 ID 목록
    test_cases: list[str]          # 테스트 케이스 ID 목록
    status: str                    # "pending", "running", "completed", "failed"
    created_at: datetime
    completed_at: datetime | None

class AssertionResult(BaseModel):
    assertion: Assertion
    passed: bool
    actual_value: str | None
    message: str | None

class TestResult(BaseModel):
    test_run_id: str
    prompt_id: str
    model_id: str
    test_case_id: str
    output: str
    latency_ms: float
    token_count: int
    assertion_results: list[AssertionResult]
    passed: bool                   # 모든 assertion 통과 여부
    created_at: datetime

class EvaluationSummary(BaseModel):
    test_run_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    avg_latency_ms: float
    by_prompt: dict[str, dict]     # 프롬프트별 통계
    by_model: dict[str, dict]      # 모델별 통계
```

### 4.2 어댑터 인터페이스 (shared/adapters/base.py)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMResponse(BaseModel):
    content: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model: str
    raw_response: dict | None = None

class BaseLLMAdapter(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """어댑터 이름 반환"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """단일 응답 생성"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """스트리밍 응답 생성"""
        pass

class AdapterFactory:
    _adapters: dict[str, type[BaseLLMAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_class: type[BaseLLMAdapter]):
        cls._adapters[name] = adapter_class

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseLLMAdapter:
        if name not in cls._adapters:
            raise ValueError(f"Unknown adapter: {name}")
        return cls._adapters[name](**kwargs)
```

### 4.3 Promptfoo Runner (shared/core/promptfoo_runner.py)

```python
import subprocess
import json
import tempfile
from pathlib import Path

class PromptfooRunner:
    """promptfoo CLI를 subprocess로 실행하고 결과를 파싱"""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path

    async def run_eval(
        self,
        prompts: list[dict],
        providers: list[dict],
        tests: list[dict],
        output_path: str | None = None
    ) -> dict:
        """
        promptfoo eval 실행

        Args:
            prompts: 프롬프트 목록
            providers: 모델/프로바이더 설정
            tests: 테스트 케이스 목록
            output_path: 결과 저장 경로

        Returns:
            promptfoo 평가 결과 (JSON)
        """
        # 임시 설정 파일 생성
        config = {
            "prompts": prompts,
            "providers": providers,
            "tests": tests
        }

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        ) as f:
            import yaml
            yaml.dump(config, f)
            temp_config = f.name

        try:
            # promptfoo 실행
            result = subprocess.run(
                [
                    "npx", "promptfoo", "eval",
                    "-c", temp_config,
                    "--output", output_path or "output.json",
                    "--no-cache"
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode != 0:
                raise RuntimeError(f"promptfoo failed: {result.stderr}")

            # 결과 파싱
            output_file = output_path or "output.json"
            with open(output_file, 'r') as f:
                return json.load(f)

        finally:
            Path(temp_config).unlink(missing_ok=True)

    def parse_results(self, raw_results: dict) -> list[TestResult]:
        """promptfoo 결과를 내부 모델로 변환"""
        # 구현...
        pass
```

---

## 5. API 엔드포인트 설계

### 5.1 테스트 API (/tests)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/tests/run` | 새 테스트 실행 |
| GET | `/tests` | 테스트 목록 조회 |
| GET | `/tests/{id}` | 테스트 상세 조회 |
| GET | `/tests/{id}/results` | 테스트 결과 조회 |
| DELETE | `/tests/{id}` | 테스트 삭제 |
| GET | `/tests/{id}/export` | 결과 내보내기 (HTML/PDF/CSV) |

### 5.2 프롬프트 API (/prompts)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/prompts` | 프롬프트 목록 |
| POST | `/prompts` | 프롬프트 생성 |
| GET | `/prompts/{id}` | 프롬프트 조회 |
| PUT | `/prompts/{id}` | 프롬프트 수정 |
| DELETE | `/prompts/{id}` | 프롬프트 삭제 |
| POST | `/prompts/{id}/duplicate` | 프롬프트 복제 |

### 5.3 WebSocket (/ws)

| Endpoint | 설명 |
|----------|------|
| `/ws/tests/{id}/progress` | 테스트 실행 진행률 스트리밍 |

**메시지 포맷:**
```json
{
  "type": "progress",
  "data": {
    "current": 5,
    "total": 10,
    "current_test": "test_case_1",
    "current_model": "gpt-4",
    "status": "running"
  }
}
```

---

## 6. UI 화면 설계

### 6.1 메인 대시보드 (/)
- 최근 테스트 실행 목록
- 전체 Pass/Fail 통계
- 빠른 테스트 실행 버튼

### 6.2 테스트 실행 (/tests)
- 프롬프트 선택 (다중 선택)
- 모델 선택 (다중 선택)
- 테스트 케이스 선택
- Assertion 설정
- "테스트 실행" 버튼
- 실시간 진행률 표시

### 6.3 Side-by-side 비교 (/compare)
- 좌우 분할 뷰
- 프롬프트 A vs 프롬프트 B
- 동일 입력에 대한 출력 비교
- Diff 하이라이팅
- Assertion 결과 배지 (Pass/Fail)

### 6.4 프롬프트 편집기 (/prompts/editor)
- Monaco Editor 기반
- 변수 하이라이팅 (`{{variable}}`)
- 즉시 미리보기
- 버전 히스토리

### 6.5 테스트 이력 (/history)
- 테스트 실행 기록 목록
- 필터링 (날짜, 프롬프트, 모델)
- 결과 트렌드 그래프

---

## 7. 기술 스택 상세

### Backend (Python 3.10+)

| 패키지 | 용도 |
|--------|------|
| FastAPI | Web Framework |
| Pydantic v2 | 데이터 검증 |
| uvicorn | ASGI 서버 |
| httpx | 비동기 HTTP 클라이언트 |
| websockets | WebSocket 지원 |
| structlog | 구조화 로깅 |
| SQLite + aiosqlite | 데이터 저장 |
| PyYAML | YAML 설정 파싱 |
| weasyprint | PDF 생성 |

### Frontend (TypeScript)

| 패키지 | 용도 |
|--------|------|
| Next.js 14 | React 프레임워크 |
| TanStack Query | 서버 상태 관리 |
| Tailwind CSS | 스타일링 |
| shadcn/ui | UI 컴포넌트 |
| Monaco Editor | 코드 편집기 |
| Recharts | 차트/그래프 |
| react-diff-viewer | Diff 비교 |

### Evaluation

| 도구 | 용도 |
|------|------|
| promptfoo | 프롬프트 평가 프레임워크 |

---

## 8. 환경 변수

```env
# .env.example

# API Server
API_HOST=0.0.0.0
API_PORT=8080

# Database
DATABASE_URL=sqlite:///./data/test_harness.db

# LLM Providers
TOGETHER_API_KEY=your_together_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# 사내 모델 (OpenAI 호환)
INTERNAL_LLM_ENDPOINT=http://internal-vllm:8000/v1
INTERNAL_LLM_API_KEY=your_internal_key

# promptfoo
PROMPTFOO_CACHE_PATH=./cache/promptfoo
```

---

## 9. Docker Compose

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: services/api/Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./configs:/app/configs
      - ./vendor:/app/vendor:ro
    environment:
      - DATABASE_URL=sqlite:///./data/test_harness.db
    env_file:
      - .env

  web:
    build:
      context: .
      dockerfile: services/web/Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8080
    depends_on:
      - api
```

---

## 10. 마이그레이션 계획

### Phase 1: 핵심 구조 (1주차)
- [ ] 프로젝트 디렉토리 구조 생성
- [ ] shared/core/models.py 구현
- [ ] shared/adapters 구현 (OpenAI Compatible)
- [ ] 기본 FastAPI 서버 설정

### Phase 2: promptfoo 연동 (2주차)
- [ ] PromptfooRunner 구현
- [ ] 결과 파싱 로직
- [ ] 테스트 실행 API

### Phase 3: Web UI (3주차)
- [ ] Next.js 프로젝트 설정
- [ ] 테스트 실행 페이지
- [ ] Side-by-side 비교 뷰
- [ ] 프롬프트 편집기

### Phase 4: 고급 기능 (4주차)
- [ ] WebSocket 실시간 업데이트
- [ ] 보고서 생성 (HTML/PDF)
- [ ] RAG 인터셉터
- [ ] Docker Compose 설정

---

## 11. 기존 plan.md와의 호환성

| plan.md 기능 | v2 구현 방식 |
|--------------|-------------|
| Wrapper Layer | `vendor/` 디렉토리 + 환경 변수 주입 유지 |
| promptfoo 실행 | `PromptfooRunner` (subprocess) |
| Multi-Prompt Side-by-Side | `/compare` 페이지 |
| RAG 인터셉터 | `shared/core/rag_interceptor.py` |
| 자동 검사기 | promptfoo assertions + 커스텀 |
| Report Exporter | `shared/core/report_generator.py` |

---

## 12. 참고 자료

- [simple-llm-loadtester](../../../simple-llm-loadtester) - 프로젝트 구조 참조
- [promptfoo 공식 문서](https://promptfoo.dev/docs/intro)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Next.js 공식 문서](https://nextjs.org/docs)
