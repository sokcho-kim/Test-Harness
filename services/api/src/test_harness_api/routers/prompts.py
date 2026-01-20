"""프롬프트 관리 API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class PromptCreate(BaseModel):
    """프롬프트 생성 요청"""
    name: str
    content: str
    variables: list[str] = []
    description: str | None = None


class PromptUpdate(BaseModel):
    """프롬프트 수정 요청"""
    name: str | None = None
    content: str | None = None
    variables: list[str] | None = None
    description: str | None = None


@router.get("")
async def list_prompts(limit: int = 50, offset: int = 0):
    """프롬프트 목록 조회"""
    # TODO: DB에서 조회
    return {
        "prompts": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


@router.post("")
async def create_prompt(prompt: PromptCreate):
    """프롬프트 생성"""
    # TODO: DB에 저장
    return {
        "id": "prompt_001",
        "message": "Prompt created",
        **prompt.model_dump(),
    }


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str):
    """프롬프트 조회"""
    # TODO: DB에서 조회
    raise HTTPException(status_code=404, detail="Prompt not found")


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: str, prompt: PromptUpdate):
    """프롬프트 수정"""
    # TODO: DB에서 수정
    return {
        "id": prompt_id,
        "message": "Prompt updated",
    }


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """프롬프트 삭제"""
    # TODO: DB에서 삭제
    return {"message": "Prompt deleted", "id": prompt_id}


@router.post("/{prompt_id}/duplicate")
async def duplicate_prompt(prompt_id: str, new_name: str | None = None):
    """프롬프트 복제"""
    # TODO: 복제 로직 구현
    return {
        "original_id": prompt_id,
        "new_id": "prompt_002",
        "message": "Prompt duplicated",
    }
