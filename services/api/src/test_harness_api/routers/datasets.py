"""데이터셋 관리 API (Import + 3단계 Fallback 매핑)"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from typing import Any

from ..dependencies import get_dataset_service
from ..services.dataset_service import DatasetService

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class AssertionRequest(BaseModel):
    """Assertion 요청"""
    type: str  # contains, not-contains, is-json, regex, llm-rubric, equals, starts-with
    value: str | None = None
    threshold: float | None = None
    description: str | None = None


class DatasetCreate(BaseModel):
    """데이터셋 생성 요청"""
    name: str
    description: str | None = None
    dataset_type: str = "evaluation"  # golden, evaluation, synthetic
    column_mapping: dict[str, str] | None = None
    default_assertions: list[AssertionRequest] | None = None  # 기본 assertions
    tags: list[str] | None = None


class DatasetUpdate(BaseModel):
    """데이터셋 수정 요청"""
    name: str | None = None
    description: str | None = None
    dataset_type: str | None = None
    column_mapping: dict[str, str] | None = None
    default_assertions: list[AssertionRequest] | None = None  # 기본 assertions
    tags: list[str] | None = None
    is_verified: bool | None = None
    verified_by: str | None = None


class CaseCreate(BaseModel):
    """테스트 케이스 생성 요청"""
    raw_input: dict[str, Any]
    expected_output: str | None = None
    assertions: list[AssertionRequest] | None = None  # 케이스별 assertions
    metadata: dict | None = None
    is_edge_case: bool = False
    is_error_pattern: bool = False


class JsonImportRequest(BaseModel):
    """JSON Import 요청"""
    data: list[dict]
    column_mapping: dict[str, str] | None = None


# =============================================================================
# 데이터셋 CRUD
# =============================================================================

@router.get("")
async def list_datasets(
    limit: int = 50,
    offset: int = 0,
    dataset_type: str | None = None,
    service: DatasetService = Depends(get_dataset_service),
):
    """데이터셋 목록 조회

    dataset_type: golden(검수된), evaluation(일반), synthetic(합성)
    """
    return await service.list_datasets(
        limit=limit,
        offset=offset,
        dataset_type=dataset_type,
    )


@router.post("")
async def create_dataset(
    request: DatasetCreate,
    service: DatasetService = Depends(get_dataset_service),
):
    """데이터셋 생성 (빈 상태)

    default_assertions: 모든 케이스에 적용될 기본 assertions
    예: [{"type": "not-contains", "value": "죄송합니다"}, {"type": "is-json"}]
    """
    # AssertionRequest → dict 변환
    default_assertions = None
    if request.default_assertions:
        default_assertions = [a.model_dump(exclude_none=True) for a in request.default_assertions]

    return await service.create_dataset(
        name=request.name,
        description=request.description,
        dataset_type=request.dataset_type,
        column_mapping=request.column_mapping,
        default_assertions=default_assertions,
        tags=request.tags,
    )


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """데이터셋 조회"""
    result = await service.get_dataset(dataset_id)
    if not result:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return result


@router.put("/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    request: DatasetUpdate,
    service: DatasetService = Depends(get_dataset_service),
):
    """데이터셋 수정

    default_assertions: 모든 케이스에 적용될 기본 assertions
    """
    # AssertionRequest → dict 변환
    default_assertions = None
    if request.default_assertions is not None:
        default_assertions = [a.model_dump(exclude_none=True) for a in request.default_assertions]

    result = await service.update_dataset(
        dataset_id=dataset_id,
        name=request.name,
        description=request.description,
        dataset_type=request.dataset_type,
        column_mapping=request.column_mapping,
        default_assertions=default_assertions,
        tags=request.tags,
        is_verified=request.is_verified,
        verified_by=request.verified_by,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return result


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """데이터셋 삭제 (모든 케이스 포함)"""
    success = await service.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset deleted", "id": dataset_id}


# =============================================================================
# 테스트 케이스 관리
# =============================================================================

@router.get("/{dataset_id}/cases")
async def list_cases(
    dataset_id: str,
    limit: int = 100,
    offset: int = 0,
    service: DatasetService = Depends(get_dataset_service),
):
    """데이터셋의 테스트 케이스 목록"""
    # 데이터셋 존재 확인
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return await service.list_cases(dataset_id, limit=limit, offset=offset)


@router.post("/{dataset_id}/cases")
async def add_case(
    dataset_id: str,
    request: CaseCreate,
    service: DatasetService = Depends(get_dataset_service),
):
    """테스트 케이스 추가

    assertions: 이 케이스에만 적용될 assertions (dataset 기본값에 추가/덮어쓰기)
    예: [{"type": "contains", "value": "서울"}, {"type": "llm-rubric", "value": "정확한 답변인가?"}]
    """
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # AssertionRequest → dict 변환
    assertions = None
    if request.assertions:
        assertions = [a.model_dump(exclude_none=True) for a in request.assertions]

    return await service.add_case(
        dataset_id=dataset_id,
        raw_input=request.raw_input,
        expected_output=request.expected_output,
        assertions=assertions,
        metadata=request.metadata,
        is_edge_case=request.is_edge_case,
        is_error_pattern=request.is_error_pattern,
    )


@router.get("/{dataset_id}/cases/{case_id}")
async def get_case(
    dataset_id: str,
    case_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """테스트 케이스 조회"""
    case = await service.get_case(case_id)
    if not case or case["dataset_id"] != dataset_id:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.delete("/{dataset_id}/cases/{case_id}")
async def delete_case(
    dataset_id: str,
    case_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """테스트 케이스 삭제"""
    case = await service.get_case(case_id)
    if not case or case["dataset_id"] != dataset_id:
        raise HTTPException(status_code=404, detail="Case not found")

    await service.delete_case(case_id)
    return {"message": "Case deleted", "id": case_id}


# =============================================================================
# Import
# =============================================================================

@router.post("/{dataset_id}/import/csv")
async def import_csv(
    dataset_id: str,
    file: UploadFile = File(...),
    column_mapping: str | None = Form(None),  # JSON 문자열
    expected_output_column: str = Form("expected_output"),
    metadata_prefix: str = Form("_"),
    service: DatasetService = Depends(get_dataset_service),
):
    """CSV 파일 Import

    CSV 규칙:
    - expected_output_column 지정 컬럼 → expected_output
    - metadata_prefix로 시작하는 컬럼 → metadata (접두사 제거)
    - 나머지 컬럼 → raw_input

    예시 CSV:
    ```
    question,context,expected_output,_category,_is_edge_case
    "질문1","문맥1","답변1","factual","false"
    ```
    """
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # 파일 읽기
    content = await file.read()
    try:
        csv_content = content.decode("utf-8")
    except UnicodeDecodeError:
        csv_content = content.decode("cp949")  # 한글 Windows

    # 매핑 파싱
    mapping = None
    if column_mapping:
        try:
            import json
            mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid column_mapping JSON")

    result = await service.import_csv(
        dataset_id=dataset_id,
        csv_content=csv_content,
        column_mapping=mapping,
        expected_output_column=expected_output_column,
        metadata_prefix=metadata_prefix,
    )

    return result


@router.post("/{dataset_id}/import/json")
async def import_json(
    dataset_id: str,
    request: JsonImportRequest,
    service: DatasetService = Depends(get_dataset_service),
):
    """JSON 배열 Import

    JSON 형식:
    ```json
    {
      "data": [
        {"input": {"question": "..."}, "expected_output": "..."},
        {"raw_input": {"q": "..."}, "expected": "...", "metadata": {...}}
      ],
      "column_mapping": {"q": "question"}  // 선택
    }
    ```
    """
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result = await service.import_json(
        dataset_id=dataset_id,
        json_data=request.data,
        column_mapping=request.column_mapping,
    )

    return result


# =============================================================================
# Export
# =============================================================================

@router.get("/{dataset_id}/export")
async def export_dataset(
    dataset_id: str,
    format: str = "json",
    service: DatasetService = Depends(get_dataset_service),
):
    """데이터셋 Export

    format: json, csv
    """
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if format == "csv":
        csv_content = await service.export_csv(dataset_id)
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={dataset_id}.csv"
            }
        )
    elif format == "json":
        json_data = await service.export_json(dataset_id)
        return JSONResponse(
            content={
                "dataset_id": dataset_id,
                "name": dataset["name"],
                "cases": json_data,
            }
        )
    else:
        raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")


# =============================================================================
# 매핑 관련
# =============================================================================

@router.get("/{dataset_id}/mapping/suggest")
async def suggest_mapping(
    dataset_id: str,
    prompt_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """매핑 추천 (컬럼명-변수명 유사도 기반)

    프롬프트 변수와 데이터셋 컬럼을 비교하여 자동 매핑 제안
    """
    from shared.core.mapping import MappingResolver
    from ..dependencies import get_prompt_service

    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # 프롬프트 서비스 가져오기
    prompt_service = await get_prompt_service()
    prompt = await prompt_service.get_prompt(prompt_id)
    if not prompt or not prompt.get("active_version"):
        raise HTTPException(status_code=404, detail="Prompt or active version not found")

    # 첫 번째 케이스에서 컬럼 추출
    cases = await service.list_cases(dataset_id, limit=1)
    if not cases["cases"]:
        raise HTTPException(status_code=400, detail="Dataset has no cases")

    data_columns = list(cases["cases"][0]["raw_input"].keys())
    prompt_variables = prompt["active_version"]["variables"]

    # 매핑 추천
    suggested = MappingResolver.suggest_mapping(data_columns, prompt_variables)

    # 검증
    validation = MappingResolver.validate_mapping(
        suggested, prompt_variables, data_columns
    )

    return {
        "suggested_mapping": suggested,
        "data_columns": data_columns,
        "prompt_variables": prompt_variables,
        "is_complete": validation.is_valid,
        "missing_variables": validation.missing_variables,
        "unused_columns": validation.unused_columns,
    }
