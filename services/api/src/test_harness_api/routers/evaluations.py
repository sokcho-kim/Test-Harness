"""평가 결과 API"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/{test_run_id}/summary")
async def get_evaluation_summary(test_run_id: str):
    """평가 요약 조회"""
    # TODO: DB에서 조회 및 계산
    return {
        "test_run_id": test_run_id,
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "pass_rate": 0.0,
        "avg_latency_ms": 0.0,
        "by_prompt": {},
        "by_model": {},
    }


@router.get("/{test_run_id}/compare")
async def compare_results(test_run_id: str):
    """Side-by-side 비교용 데이터"""
    # TODO: 비교 데이터 생성
    return {
        "test_run_id": test_run_id,
        "comparisons": [],
    }
