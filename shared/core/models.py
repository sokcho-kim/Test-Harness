"""Test Harness 데이터 모델 정의"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssertionType(str, Enum):
    """Assertion 유형"""
    CONTAINS = "contains"
    NOT_CONTAINS = "not-contains"
    IS_JSON = "is-json"
    REGEX = "regex"
    LLM_RUBRIC = "llm-rubric"
    EQUALS = "equals"
    STARTS_WITH = "starts-with"


class Assertion(BaseModel):
    """테스트 검증 조건"""
    type: AssertionType
    value: str | None = None
    threshold: float | None = None
    description: str | None = None


class Prompt(BaseModel):
    """프롬프트 템플릿"""
    id: str
    name: str
    content: str
    variables: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TestCase(BaseModel):
    """테스트 케이스"""
    id: str
    name: str | None = None
    input: dict[str, str] = Field(default_factory=dict)  # 변수 바인딩
    expected_output: str | None = None  # 기대 출력 (선택)
    assertions: list[Assertion] = Field(default_factory=list)


class ModelConfig(BaseModel):
    """LLM 모델 설정"""
    id: str
    name: str
    provider: str  # "together", "openai", "anthropic", "custom"
    endpoint: str
    api_key_env: str  # 환경변수 이름
    default_params: dict[str, Any] = Field(default_factory=dict)


class TestRunStatus(str, Enum):
    """테스트 실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestRun(BaseModel):
    """테스트 실행"""
    id: str
    name: str | None = None
    prompts: list[str]  # 테스트할 프롬프트 ID 목록
    models: list[str]  # 테스트할 모델 ID 목록
    test_cases: list[str]  # 테스트 케이스 ID 목록
    status: TestRunStatus = TestRunStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error_message: str | None = None


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
    model_id: str
    test_case_id: str
    input_rendered: str  # 변수 치환된 최종 프롬프트
    output: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    passed: bool  # 모든 assertion 통과 여부
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class EvaluationSummary(BaseModel):
    """평가 요약"""
    test_run_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int = 0
    pass_rate: float
    avg_latency_ms: float
    by_prompt: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_model: dict[str, dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
