"""OpenAI 호환 API 어댑터 (Together AI, vLLM, 사내 모델 등)"""

import time
from typing import AsyncIterator, Any

import httpx

from .base import BaseLLMAdapter, LLMResponse, AdapterFactory


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """OpenAI 호환 API 어댑터"""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        timeout: float = 60.0,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "openai-compatible"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """단일 응답 생성"""
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs,
        }

        start_time = time.perf_counter()
        response = await client.post(
            f"{self.endpoint}/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        latency_ms = (time.perf_counter() - start_time) * 1000

        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["message"]["content"],
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            model=data.get("model", model),
            raw_response=data,
        )

    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """스트리밍 응답 생성"""
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        async with client.stream(
            "POST",
            f"{self.endpoint}/chat/completions",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    if content := delta.get("content"):
                        yield content

    async def close(self) -> None:
        """클라이언트 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None


# 어댑터 등록
AdapterFactory.register("openai", OpenAICompatibleAdapter)
AdapterFactory.register("together", OpenAICompatibleAdapter)
AdapterFactory.register("vllm", OpenAICompatibleAdapter)
