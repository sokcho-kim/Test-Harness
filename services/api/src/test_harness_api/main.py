"""Test Harness API Server"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import tests, prompts, datasets, evaluations, websocket
from .dependencies import get_database, close_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """애플리케이션 생명주기 관리"""
    # Startup
    print("Starting Test Harness API...")
    # 데이터베이스 연결 (테이블 자동 생성)
    await get_database()
    print("Database connected.")

    yield

    # Shutdown
    print("Shutting down Test Harness API...")
    await close_database()
    print("Database closed.")


app = FastAPI(
    title="Test Harness API",
    description="""
LLM 프롬프트 테스트 및 평가 API

## 주요 기능

- **프롬프트 관리**: Semantic Versioning 기반 버전 관리
- **데이터셋 관리**: CSV/JSON Import, 3단계 Fallback 매핑
- **테스트 실행**: 프롬프트 × 모델 × 데이터셋 조합 테스트
- **평가**: promptfoo 기반 Assertion 평가

## References

- Naver D2: 프롬프트 엔지니어링 도구
- 우아한형제들: AI플랫폼 2.0 LLMOps
- Fastcampus: 테스트 방법론, Semantic Versioning
""",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
app.include_router(tests.router, prefix="/tests", tags=["tests"])
app.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/")
async def root():
    """API 루트"""
    return {
        "name": "Test Harness API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
