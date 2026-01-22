"""Together AI Adapter Helper"""

import os
from .openai_compat import OpenAICompatibleAdapter


TOGETHER_API_ENDPOINT = "https://api.together.xyz/v1"

# Together AI 인기 모델 목록
TOGETHER_MODELS = {
    # Meta Llama 3
    "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "llama-3.1-8b": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "llama-3.1-70b": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "llama-3.1-405b": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",

    # Mistral
    "mixtral-8x7b": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "mixtral-8x22b": "mistralai/Mixtral-8x22B-Instruct-v0.1",

    # Qwen
    "qwen-2.5-72b": "Qwen/Qwen2.5-72B-Instruct-Turbo",
    "qwen-2.5-7b": "Qwen/Qwen2.5-7B-Instruct-Turbo",

    # DeepSeek
    "deepseek-v3": "deepseek-ai/DeepSeek-V3",
    "deepseek-r1": "deepseek-ai/DeepSeek-R1",
}


def create_together_adapter(
    api_key: str | None = None,
    timeout: float = 120.0,
) -> OpenAICompatibleAdapter:
    """Together AI 어댑터 생성

    Args:
        api_key: API 키 (없으면 환경변수에서 읽음)
        timeout: 요청 타임아웃 (초)

    Returns:
        OpenAICompatibleAdapter 인스턴스
    """
    key = api_key or os.getenv("TOGETHER_API_KEY")
    if not key:
        raise ValueError("TOGETHER_API_KEY not found in environment")

    return OpenAICompatibleAdapter(
        endpoint=TOGETHER_API_ENDPOINT,
        api_key=key,
        timeout=timeout,
    )


def get_model_id(short_name: str) -> str:
    """단축 이름으로 전체 모델 ID 반환

    Examples:
        get_model_id("llama-3.3-70b") → "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    """
    return TOGETHER_MODELS.get(short_name, short_name)


def list_available_models() -> dict[str, str]:
    """사용 가능한 모델 목록"""
    return TOGETHER_MODELS.copy()
