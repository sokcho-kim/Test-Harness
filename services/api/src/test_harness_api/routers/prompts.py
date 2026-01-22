"""프롬프트 관리 API (Semantic Versioning)"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..dependencies import get_prompt_service
from ..services.prompt_service import PromptService

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class PromptCreate(BaseModel):
    """프롬프트 생성 요청"""
    name: str
    content: str
    description: str | None = None
    tags: list[str] | None = None
    created_by: str | None = None


class PromptUpdate(BaseModel):
    """프롬프트 수정 요청 (메타데이터만)"""
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class VersionCreate(BaseModel):
    """새 버전 생성 요청"""
    content: str
    change_type: str = "minor"  # "major", "minor", "patch"
    change_note: str | None = None
    created_by: str | None = None
    auto_activate: bool = False


# =============================================================================
# 프롬프트 CRUD
# =============================================================================

@router.get("")
async def list_prompts(
    limit: int = 50,
    offset: int = 0,
    tag: str | None = None,
    service: PromptService = Depends(get_prompt_service),
):
    """프롬프트 목록 조회"""
    return await service.list_prompts(limit=limit, offset=offset, tag=tag)


@router.post("")
async def create_prompt(
    request: PromptCreate,
    service: PromptService = Depends(get_prompt_service),
):
    """프롬프트 생성 (v1.0.0 자동 생성)"""
    result = await service.create_prompt(
        name=request.name,
        content=request.content,
        description=request.description,
        tags=request.tags,
        created_by=request.created_by,
    )
    return result


@router.get("/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    service: PromptService = Depends(get_prompt_service),
):
    """프롬프트 조회 (active 버전 포함)"""
    result = await service.get_prompt(prompt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return result


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    request: PromptUpdate,
    service: PromptService = Depends(get_prompt_service),
):
    """프롬프트 메타데이터 수정 (내용 수정은 새 버전 생성)"""
    result = await service.update_prompt(
        prompt_id=prompt_id,
        name=request.name,
        description=request.description,
        tags=request.tags,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return result


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    service: PromptService = Depends(get_prompt_service),
):
    """프롬프트 삭제 (모든 버전 포함)"""
    success = await service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted", "id": prompt_id}


# =============================================================================
# 버전 관리 (Semantic Versioning)
# =============================================================================

@router.get("/{prompt_id}/versions")
async def list_versions(
    prompt_id: str,
    service: PromptService = Depends(get_prompt_service),
):
    """프롬프트의 모든 버전 조회"""
    # 프롬프트 존재 확인
    prompt = await service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    versions = await service.list_versions(prompt_id)
    return {
        "prompt_id": prompt_id,
        "versions": versions,
        "total": len(versions),
    }


@router.post("/{prompt_id}/versions")
async def create_version(
    prompt_id: str,
    request: VersionCreate,
    service: PromptService = Depends(get_prompt_service),
):
    """새 버전 생성 (Semantic Versioning)

    change_type:
    - major: 주요 기능 변경, 구조 변경 (1.0.0 → 2.0.0)
    - minor: 일부 수정, 성능 개선 (1.0.0 → 1.1.0)
    - patch: 오타, 출력 깨짐 수정 (1.0.0 → 1.0.1)
    """
    if request.change_type not in ["major", "minor", "patch"]:
        raise HTTPException(
            status_code=400,
            detail="change_type must be 'major', 'minor', or 'patch'"
        )

    result = await service.create_version(
        prompt_id=prompt_id,
        content=request.content,
        change_type=request.change_type,
        change_note=request.change_note,
        created_by=request.created_by,
        auto_activate=request.auto_activate,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return result


@router.get("/{prompt_id}/versions/{version_id}")
async def get_version(
    prompt_id: str,
    version_id: str,
    service: PromptService = Depends(get_prompt_service),
):
    """특정 버전 조회"""
    result = await service.get_version(version_id)
    if not result or result["prompt_id"] != prompt_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return result


@router.put("/{prompt_id}/versions/{version_id}/activate")
async def activate_version(
    prompt_id: str,
    version_id: str,
    service: PromptService = Depends(get_prompt_service),
):
    """특정 버전 활성화 (기존 active 비활성화)"""
    # 버전 존재 확인
    version = await service.get_version(version_id)
    if not version or version["prompt_id"] != prompt_id:
        raise HTTPException(status_code=404, detail="Version not found")

    await service.activate_version(prompt_id, version_id)

    return {
        "message": "Version activated",
        "prompt_id": prompt_id,
        "version_id": version_id,
        "version": version["version"],
    }


@router.get("/{prompt_id}/active")
async def get_active_version(
    prompt_id: str,
    service: PromptService = Depends(get_prompt_service),
):
    """현재 active 버전 조회"""
    result = await service.get_active_version(prompt_id)
    if not result:
        raise HTTPException(status_code=404, detail="No active version found")
    return result
