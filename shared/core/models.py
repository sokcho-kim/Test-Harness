"""Test Harness 데이터 모델 정의

References:
- Naver D2: 프롬프트 엔지니어링 도구
- 우아한형제들: AI플랫폼 2.0 LLMOps
- Fastcampus: 테스트 방법론, Semantic Versioning
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field


# =============================================================================
# Enums
# =============================================================================

class AssertionType(str, Enum):
    """Assertion 유형"""
    CONTAINS = "contains"
    NOT_CONTAINS = "not-contains"
    IS_JSON = "is-json"
    REGEX = "regex"
    LLM_RUBRIC = "llm-rubric"
    EQUALS = "equals"
    STARTS_WITH = "starts-with"


class TestRunStatus(str, Enum):
    """테스트 실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PromptStatus(str, Enum):
    """프롬프트 버전 상태 (Fastcampus Part 8)"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class DatasetType(str, Enum):
    """데이터셋 타입 (우아한형제들)"""
    GOLDEN = "golden"           # 검수된 고품질 데이터
    EVALUATION = "evaluation"   # 일반 평가용
    SYNTHETIC = "synthetic"     # 합성 생성 데이터


class SourceType(str, Enum):
    """데이터 소스 타입"""
    MANUAL = "manual"           # 수동 입력
    CSV = "csv"                 # CSV 파일
    JSON = "json"               # JSON 파일
    POSTGRESQL = "postgresql"   # DB 쿼리 (향후 확장)


# =============================================================================
# Base Models
# =============================================================================

class Assertion(BaseModel):
    """테스트 검증 조건"""
    type: AssertionType
    value: str | None = None
    threshold: float | None = None
    description: str | None = None


# =============================================================================
# Prompt Models (Semantic Versioning)
# =============================================================================

class Prompt(BaseModel):
    """프롬프트 (버전 컨테이너)"""
    id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PromptVersion(BaseModel):
    """프롬프트 버전 (Semantic Versioning - Fastcampus Part 8)

    버전 규칙:
    - Major: 주요 기능 변경, 구조 변경
    - Minor: 일부 수정, 성능 개선
    - Patch: 오타, 출력 깨짐 수정
    """
    id: str
    prompt_id: str

    # Semantic Versioning
    major: int = 1
    minor: int = 0
    patch: int = 0

    @computed_field
    @property
    def version(self) -> str:
        """버전 문자열 (예: 1.2.3)"""
        return f"{self.major}.{self.minor}.{self.patch}"

    # 내용
    content: str
    variables: list[str] = Field(default_factory=list)  # 자동 추출된 변수명

    # 상태 관리
    is_active: bool = False
    status: PromptStatus = PromptStatus.DRAFT

    # 변경 관리
    change_note: str | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Dataset Models (3단계 Fallback 매핑)
# =============================================================================

class TestDataset(BaseModel):
    """테스트 데이터셋

    매핑 우선순위:
    1. TestRunRequest.column_mapping (실행 시점)
    2. TestDataset.column_mapping (데이터셋 기본값)
    3. 1:1 Fallback (컬럼명 = 변수명)

    Assertion 우선순위:
    1. Dataset.default_assertions (Base - 전체 적용)
    2. Case.assertions (Override/Add - 개별 적용)
    3. expected_output → contains (Safety Net)
    """
    id: str
    name: str
    description: str | None = None

    # 데이터셋 타입 (우아한형제들)
    dataset_type: DatasetType = DatasetType.EVALUATION

    # 소스 정보 (향후 DB 연결 확장 대비)
    source_type: SourceType = SourceType.MANUAL
    source_file: str | None = None      # 원본 파일명 (참고용)
    source_config: dict | None = None   # DB 연결 시: {"query": "SELECT..."}

    # 컬럼 → 변수 매핑 (2순위)
    # 예: {"user_query": "question", "doc_chunk": "context"}
    column_mapping: dict[str, str] | None = None

    # 기본 Assertion (모든 케이스에 적용)
    # 예: [{"type": "not-contains", "value": "죄송합니다"}, {"type": "is-json"}]
    default_assertions: list[Assertion] = Field(default_factory=list)

    # 품질 관리 (Fastcampus Part 6)
    is_verified: bool = False
    verified_by: str | None = None
    verified_at: datetime | None = None

    # 메타데이터
    tags: list[str] = Field(default_factory=list)
    case_count: int = 0

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TestCase(BaseModel):
    """테스트 케이스 (원본 데이터 보존 - Immutable)"""
    id: str
    dataset_id: str

    # 원본 데이터 그대로 저장 (매핑 전)
    raw_input: dict[str, Any] = Field(default_factory=dict)
    expected_output: str | None = None

    # 케이스별 Assertion (Dataset 기본값에 추가/덮어쓰기)
    # 예: [{"type": "contains", "value": "성남시"}]
    assertions: list[Assertion] | None = None

    # 평가 기준 (Fastcampus Part 6 루브릭)
    # 예: {"정확성": 5, "일관성": 4, "유용성": 5}
    rubric_scores: dict[str, int] | None = None

    # 메타데이터
    metadata: dict | None = None

    # 품질 플래그 (Fastcampus Part 6)
    is_edge_case: bool = False          # 예외 케이스
    is_error_pattern: bool = False      # 오류 패턴

    created_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Application Model (Naver D2)
# =============================================================================

class Application(BaseModel):
    """애플리케이션 = 모델 + 프롬프트(active) + LLM 옵션

    Naver D2 개념: 하나의 LLM 애플리케이션 단위
    """
    id: str
    name: str
    description: str | None = None

    # 구성 요소
    model_id: str
    prompt_id: str  # active 버전 자동 사용

    # LLM 옵션
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop_sequences: list[str] | None = None

    # 메타데이터
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Model Config
# =============================================================================

class ModelConfig(BaseModel):
    """LLM 모델 설정"""
    id: str
    name: str
    provider: str  # "together", "openai", "anthropic", "custom"
    endpoint: str
    api_key_env: str  # 환경변수 이름
    default_params: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Test Run Models
# =============================================================================

class TestRunRequest(BaseModel):
    """테스트 실행 요청"""
    prompt_ids: list[str]           # 테스트할 프롬프트 ID 목록
    dataset_id: str                 # 테스트 데이터셋 ID
    model_ids: list[str]            # 테스트할 모델 ID 목록

    # 실행 시점 매핑 오버라이드 (1순위)
    column_mapping: dict[str, str] | None = None

    # 실행 옵션
    name: str | None = None
    repeat_count: int = 1           # N번 반복 실행 (정량 테스트)

    # Assertion 설정
    assertions: list[Assertion] = Field(default_factory=list)


class TestRun(BaseModel):
    """테스트 실행"""
    id: str
    name: str | None = None

    # 실행 대상
    prompt_ids: list[str]
    dataset_id: str
    model_ids: list[str]

    # 사용된 매핑 (실행 시점에 결정된 최종 매핑)
    resolved_mapping: dict[str, str] | None = None

    # 상태
    status: TestRunStatus = TestRunStatus.PENDING
    progress: int = 0               # 진행률 (0-100)
    total_cases: int = 0
    completed_cases: int = 0

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    error_message: str | None = None


# =============================================================================
# Test Result Models
# =============================================================================

class AssertionResult(BaseModel):
    """개별 Assertion 결과"""
    assertion: Assertion
    passed: bool
    actual_value: str | None = None
    message: str | None = None


class TestResult(BaseModel):
    """개별 테스트 결과"""
    id: str
    test_run_id: str
    prompt_id: str
    prompt_version: str             # 사용된 버전 (예: "1.2.3")
    model_id: str
    test_case_id: str

    # 입출력
    input_mapped: dict[str, Any]    # 매핑된 입력 변수
    input_rendered: str             # 변수 치환된 최종 프롬프트
    output: str

    # 성능 메트릭
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None

    # 평가 결과
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    passed: bool                    # 모든 assertion 통과 여부

    # 에러
    error: str | None = None

    created_at: datetime = Field(default_factory=datetime.now)


class EvaluationSummary(BaseModel):
    """평가 요약"""
    test_run_id: str

    # 전체 통계
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int = 0
    pass_rate: float

    # 성능 통계
    avg_latency_ms: float
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    p50_latency_ms: float | None = None
    p95_latency_ms: float | None = None

    # 그룹별 통계
    by_prompt: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_model: dict[str, dict[str, Any]] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.now)
