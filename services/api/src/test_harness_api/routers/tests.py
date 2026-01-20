"""테스트 실행 및 관리 API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TestRunRequest(BaseModel):
    """테스트 실행 요청"""
    prompts: list[str]  # 프롬프트 ID 목록
    models: list[str]  # 모델 ID 목록
    test_cases: list[str]  # 테스트 케이스 ID 목록
    name: str | None = None


@router.post("/run")
async def run_test(request: TestRunRequest):
    """새 테스트 실행"""
    # TODO: 테스트 실행 로직 구현
    return {
        "id": "test_run_001",
        "status": "pending",
        "message": "Test run created",
    }


@router.get("")
async def list_tests(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
):
    """테스트 목록 조회"""
    # TODO: DB에서 조회
    return {
        "tests": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{test_id}")
async def get_test(test_id: str):
    """테스트 상세 조회"""
    # TODO: DB에서 조회
    raise HTTPException(status_code=404, detail="Test not found")


@router.get("/{test_id}/results")
async def get_test_results(test_id: str):
    """테스트 결과 조회"""
    # TODO: DB에서 조회
    return {
        "test_run_id": test_id,
        "results": [],
    }


@router.delete("/{test_id}")
async def delete_test(test_id: str):
    """테스트 삭제"""
    # TODO: DB에서 삭제
    return {"message": "Test deleted", "id": test_id}


@router.get("/{test_id}/export")
async def export_test(test_id: str, format: str = "json"):
    """테스트 결과 내보내기"""
    # TODO: 내보내기 구현 (json, csv, html, pdf)
    if format not in ["json", "csv", "html", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format")
    return {"message": f"Export as {format}", "test_id": test_id}
