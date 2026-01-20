"""SQLite 데이터베이스 관리"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    """SQLite 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """데이터베이스 연결"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _create_tables(self) -> None:
        """테이블 생성"""
        assert self._connection is not None

        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                variables TEXT DEFAULT '[]',
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS test_cases (
                id TEXT PRIMARY KEY,
                name TEXT,
                input TEXT NOT NULL,
                expected_output TEXT,
                assertions TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS test_runs (
                id TEXT PRIMARY KEY,
                name TEXT,
                prompts TEXT NOT NULL,
                models TEXT NOT NULL,
                test_cases TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS test_results (
                id TEXT PRIMARY KEY,
                test_run_id TEXT NOT NULL,
                prompt_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                test_case_id TEXT NOT NULL,
                input_rendered TEXT NOT NULL,
                output TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                assertion_results TEXT DEFAULT '[]',
                passed INTEGER NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (test_run_id) REFERENCES test_runs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs(status);
            CREATE INDEX IF NOT EXISTS idx_test_runs_created ON test_runs(created_at);
            CREATE INDEX IF NOT EXISTS idx_test_results_run ON test_results(test_run_id);
        """)
        await self._connection.commit()

    async def execute(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> aiosqlite.Cursor:
        """SQL 실행"""
        assert self._connection is not None
        if params:
            return await self._connection.execute(query, params)
        return await self._connection.execute(query)

    async def commit(self) -> None:
        """커밋"""
        assert self._connection is not None
        await self._connection.commit()

    async def fetchone(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> aiosqlite.Row | None:
        """단일 행 조회"""
        cursor = await self.execute(query, params)
        return await cursor.fetchone()

    async def fetchall(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[aiosqlite.Row]:
        """전체 행 조회"""
        cursor = await self.execute(query, params)
        return await cursor.fetchall()
