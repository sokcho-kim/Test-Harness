"""테스트 실행 및 관리 API (3단계 Fallback 매핑)"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from ..dependencies import get_database
from ..services.test_service import TestService
from ..services.test_executor import TestExecutor

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class TestRunRequest(BaseModel):
    """테스트 실행 요청"""
    prompt_ids: list[str]           # 테스트할 프롬프트 ID 목록
    dataset_id: str                 # 테스트 데이터셋 ID
    model_ids: list[str]            # 테스트할 모델 ID 목록

    # 실행 시점 매핑 오버라이드 (1순위)
    column_mapping: dict[str, str] | None = None

    name: str | None = None


class MappingPreviewRequest(BaseModel):
    """매핑 미리보기 요청"""
    prompt_id: str
    dataset_id: str
    column_mapping: dict[str, str] | None = None
    sample_count: int = 3


# =============================================================================
# Dependencies
# =============================================================================

async def get_test_service() -> TestService:
    """테스트 서비스 인스턴스"""
    db = await get_database()
    return TestService(db)


# =============================================================================
# 테스트 실행
# =============================================================================

@router.post("/run")
async def create_test_run(
    request: TestRunRequest,
    service: TestService = Depends(get_test_service),
):
    """새 테스트 실행 생성

    3단계 Fallback 매핑:
    1. column_mapping (실행 시점 오버라이드)
    2. dataset.column_mapping (데이터셋 기본값)
    3. 1:1 Fallback (컬럼명 = 변수명)

    매핑 예시:
    ```json
    {
      "column_mapping": {
        "user_query": "question",
        "doc_chunk": "context"
      }
    }
    ```
    """
    try:
        result = await service.create_test_run(
            prompt_ids=request.prompt_ids,
            dataset_id=request.dataset_id,
            model_ids=request.model_ids,
            column_mapping=request.column_mapping,
            name=request.name,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_test_runs(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    service: TestService = Depends(get_test_service),
):
    """테스트 실행 목록 조회

    status: pending, running, completed, failed, cancelled
    """
    return await service.list_test_runs(limit=limit, offset=offset, status=status)


@router.get("/{test_id}")
async def get_test_run(
    test_id: str,
    service: TestService = Depends(get_test_service),
):
    """테스트 실행 상세 조회"""
    result = await service.get_test_run(test_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test run not found")
    return result


@router.get("/{test_id}/results")
async def get_test_results(
    test_id: str,
    limit: int = 100,
    offset: int = 0,
    service: TestService = Depends(get_test_service),
):
    """테스트 결과 조회"""
    # 테스트 존재 확인
    test_run = await service.get_test_run(test_id)
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")

    return await service.get_test_results(test_id, limit=limit, offset=offset)


@router.delete("/{test_id}")
async def delete_test_run(
    test_id: str,
    service: TestService = Depends(get_test_service),
):
    """테스트 실행 삭제 (결과 포함)"""
    success = await service.delete_test_run(test_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test run not found")
    return {"message": "Test run deleted", "id": test_id}


# =============================================================================
# 테스트 실행 (Execute)
# =============================================================================

@router.post("/{test_id}/execute")
async def execute_test_run(
    test_id: str,
    background_tasks: BackgroundTasks,
    sync: bool = False,
    timeout: int = 600,
):
    """테스트 실행 시작

    pending 상태의 테스트를 실제로 실행합니다.
    promptfoo를 통해 LLM 호출 및 Assertion 평가를 수행합니다.

    Args:
        test_id: 테스트 실행 ID
        sync: True면 동기 실행 (완료까지 대기), False면 백그라운드 실행
        timeout: 타임아웃 (초, 기본 600초 = 10분)

    Returns:
        sync=True: 실행 결과
        sync=False: 실행 시작 메시지
    """
    db = await get_database()
    service = TestService(db)

    # 테스트 존재 확인
    test_run = await service.get_test_run(test_id)
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")

    # 이미 실행 중이거나 완료된 경우
    if test_run["status"] not in ["pending", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Test run is already {test_run['status']}"
        )

    # 프로젝트 루트 경로 (node_modules 위치)
    # tests.py → routers → test_harness_api → src → api → services → Test-Harness
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent

    executor = TestExecutor(db, project_root=project_root)

    if sync:
        # 동기 실행: 완료까지 대기
        try:
            result = await executor.execute(test_id, timeout=timeout)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # 백그라운드 실행
        async def run_in_background():
            try:
                await executor.execute(test_id, timeout=timeout)
            except Exception as e:
                # 에러는 이미 test_run에 기록됨
                pass

        background_tasks.add_task(run_in_background)
        return {
            "message": "Test execution started",
            "test_id": test_id,
            "status": "running",
        }


# =============================================================================
# 매핑 미리보기
# =============================================================================

@router.post("/preview-mapping")
async def preview_mapping(
    request: MappingPreviewRequest,
    service: TestService = Depends(get_test_service),
):
    """매핑 결과 미리보기

    실행 전에 매핑이 올바르게 적용되는지 확인.
    샘플 케이스에 대해 렌더링된 프롬프트를 보여줌.

    응답 예시:
    ```json
    {
      "resolved_mapping": {"user_query": "question"},
      "mapping_source": "run_override",
      "validation": {
        "is_valid": true,
        "missing_variables": [],
        "unused_columns": ["extra_col"]
      },
      "samples": [
        {
          "raw_input": {"user_query": "질문"},
          "mapped_input": {"question": "질문"},
          "rendered_prompt": "질문에 대해 답변해주세요.",
          "error": null
        }
      ]
    }
    ```
    """
    try:
        result = await service.preview_mapping(
            prompt_id=request.prompt_id,
            dataset_id=request.dataset_id,
            column_mapping=request.column_mapping,
            sample_count=request.sample_count,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Export (TODO)
# =============================================================================

@router.get("/{test_id}/export")
async def export_test_results(
    test_id: str,
    format: str = "json",
    service: TestService = Depends(get_test_service),
):
    """테스트 결과 내보내기

    format: json, csv, html, pdf
    """
    test_run = await service.get_test_run(test_id)
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")

    if format not in ["json", "csv", "html", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format")

    # TODO: 실제 내보내기 구현
    return {
        "message": f"Export as {format}",
        "test_id": test_id,
        "status": "not_implemented"
    }
