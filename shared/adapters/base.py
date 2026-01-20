"""LLM 어댑터 기본 인터페이스"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """LLM 응답"""
    content: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str
    raw_response: dict[str, Any] | None = None


class BaseLLMAdapter(ABC):
    """LLM 어댑터 추상 클래스"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """어댑터/프로바이더 이름 반환"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """단일 응답 생성"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """스트리밍 응답 생성"""
        pass

    async def health_check(self) -> bool:
        """연결 상태 확인"""
        return True


class AdapterFactory:
    """어댑터 팩토리"""

    _adapters: dict[str, type[BaseLLMAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_class: type[BaseLLMAdapter]) -> None:
        """어댑터 등록"""
        cls._adapters[name] = adapter_class

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BaseLLMAdapter:
        """어댑터 생성"""
        if name not in cls._adapters:
            raise ValueError(f"Unknown adapter: {name}. Available: {list(cls._adapters.keys())}")
        return cls._adapters[name](**kwargs)

    @classmethod
    def list_adapters(cls) -> list[str]:
        """등록된 어댑터 목록"""
        return list(cls._adapters.keys())
