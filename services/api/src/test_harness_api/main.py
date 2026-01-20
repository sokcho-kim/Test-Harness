"""Test Harness API Server"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import tests, prompts, evaluations, websocket


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """애플리케이션 생명주기 관리"""
    # Startup
    print("Starting Test Harness API...")
    yield
    # Shutdown
    print("Shutting down Test Harness API...")


app = FastAPI(
    title="Test Harness API",
    description="LLM 프롬프트 테스트 및 평가 API",
    version="0.1.0",
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
app.include_router(tests.router, prefix="/tests", tags=["tests"])
app.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
app.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/")
async def root():
    """API 루트"""
    return {
        "name": "Test Harness API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
