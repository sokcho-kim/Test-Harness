"""FastAPI 의존성 주입"""

from functools import lru_cache
from pathlib import Path

from shared.database.database import Database
from .services.prompt_service import PromptService
from .services.dataset_service import DatasetService


# =============================================================================
# Database
# =============================================================================

_db: Database | None = None


async def get_database() -> Database:
    """데이터베이스 인스턴스 반환"""
    global _db
    if _db is None:
        # 기본 경로 (환경 변수로 오버라이드 가능)
        db_path = Path("data/test_harness.db")
        _db = Database(db_path)
        await _db.connect()
    return _db


async def close_database():
    """데이터베이스 연결 종료"""
    global _db
    if _db is not None:
        await _db.close()
        _db = None


# =============================================================================
# Services
# =============================================================================

async def get_prompt_service() -> PromptService:
    """프롬프트 서비스 인스턴스"""
    db = await get_database()
    return PromptService(db)


async def get_dataset_service() -> DatasetService:
    """데이터셋 서비스 인스턴스"""
    db = await get_database()
    return DatasetService(db)
