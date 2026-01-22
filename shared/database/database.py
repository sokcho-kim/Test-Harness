"""SQLite 데이터베이스 관리

스키마 버전: 3.0
- prompt_versions 테이블 추가 (Semantic Versioning)
- test_datasets 테이블 추가 (3단계 Fallback 매핑)
- applications 테이블 추가 (Naver D2 개념)
- test_cases에 dataset_id 추가
- test_runs에 resolved_mapping 추가
- test_datasets에 default_assertions 추가 (v3)
- test_cases에 assertions 추가 (v3)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    """SQLite 데이터베이스 관리 클래스"""

    SCHEMA_VERSION = 3

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
            -- =================================================================
            -- 프롬프트 테이블 (버전 컨테이너)
            -- =================================================================
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- =================================================================
            -- 프롬프트 버전 테이블 (Semantic Versioning)
            -- =================================================================
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id TEXT PRIMARY KEY,
                prompt_id TEXT NOT NULL,
                major INTEGER NOT NULL DEFAULT 1,
                minor INTEGER NOT NULL DEFAULT 0,
                patch INTEGER NOT NULL DEFAULT 0,
                content TEXT NOT NULL,
                variables TEXT DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                change_note TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt
                ON prompt_versions(prompt_id);
            CREATE INDEX IF NOT EXISTS idx_prompt_versions_active
                ON prompt_versions(prompt_id, is_active) WHERE is_active = 1;

            -- =================================================================
            -- 테스트 데이터셋 테이블 (3단계 Fallback 매핑 + Assertion)
            -- =================================================================
            CREATE TABLE IF NOT EXISTS test_datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                dataset_type TEXT NOT NULL DEFAULT 'evaluation',
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_file TEXT,
                source_config TEXT,
                column_mapping TEXT,
                default_assertions TEXT DEFAULT '[]',
                is_verified INTEGER NOT NULL DEFAULT 0,
                verified_by TEXT,
                verified_at TEXT,
                tags TEXT DEFAULT '[]',
                case_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_test_datasets_type
                ON test_datasets(dataset_type);

            -- =================================================================
            -- 테스트 케이스 테이블 (Immutable 원본 데이터 + Assertion)
            -- =================================================================
            CREATE TABLE IF NOT EXISTS test_cases (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                raw_input TEXT NOT NULL,
                expected_output TEXT,
                assertions TEXT,
                rubric_scores TEXT,
                metadata TEXT,
                is_edge_case INTEGER NOT NULL DEFAULT 0,
                is_error_pattern INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dataset_id) REFERENCES test_datasets(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_test_cases_dataset
                ON test_cases(dataset_id);

            -- =================================================================
            -- 애플리케이션 테이블 (Model + Prompt + Options)
            -- =================================================================
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                model_id TEXT NOT NULL,
                prompt_id TEXT NOT NULL,
                temperature REAL NOT NULL DEFAULT 0.7,
                max_tokens INTEGER NOT NULL DEFAULT 1024,
                top_p REAL,
                frequency_penalty REAL,
                presence_penalty REAL,
                stop_sequences TEXT,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id)
            );

            -- =================================================================
            -- 테스트 실행 테이블
            -- =================================================================
            CREATE TABLE IF NOT EXISTS test_runs (
                id TEXT PRIMARY KEY,
                name TEXT,
                prompt_ids TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                model_ids TEXT NOT NULL,
                resolved_mapping TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                progress INTEGER NOT NULL DEFAULT 0,
                total_cases INTEGER NOT NULL DEFAULT 0,
                completed_cases INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                FOREIGN KEY (dataset_id) REFERENCES test_datasets(id)
            );

            CREATE INDEX IF NOT EXISTS idx_test_runs_status
                ON test_runs(status);
            CREATE INDEX IF NOT EXISTS idx_test_runs_created
                ON test_runs(created_at DESC);

            -- =================================================================
            -- 테스트 결과 테이블
            -- =================================================================
            CREATE TABLE IF NOT EXISTS test_results (
                id TEXT PRIMARY KEY,
                test_run_id TEXT NOT NULL,
                prompt_id TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                model_id TEXT NOT NULL,
                test_case_id TEXT NOT NULL,
                input_mapped TEXT NOT NULL,
                input_rendered TEXT NOT NULL,
                output TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                assertion_results TEXT DEFAULT '[]',
                passed INTEGER NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (test_run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
                FOREIGN KEY (test_case_id) REFERENCES test_cases(id)
            );

            CREATE INDEX IF NOT EXISTS idx_test_results_run
                ON test_results(test_run_id);
            CREATE INDEX IF NOT EXISTS idx_test_results_passed
                ON test_results(test_run_id, passed);

            -- =================================================================
            -- 스키마 버전 테이블
            -- =================================================================
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL,
                applied_at TEXT NOT NULL
            );
        """)
        await self._connection.commit()

        # 스키마 마이그레이션 (v3: Assertion 컬럼 추가)
        await self._migrate_to_v3()

    async def _migrate_to_v3(self) -> None:
        """v3 마이그레이션: Assertion 컬럼 추가"""
        assert self._connection is not None

        # test_datasets에 default_assertions 컬럼 추가
        try:
            await self._connection.execute(
                "ALTER TABLE test_datasets ADD COLUMN default_assertions TEXT DEFAULT '[]'"
            )
        except Exception:
            pass  # 이미 존재

        # test_cases에 assertions 컬럼 추가
        try:
            await self._connection.execute(
                "ALTER TABLE test_cases ADD COLUMN assertions TEXT"
            )
        except Exception:
            pass  # 이미 존재

        await self._connection.commit()

    # =========================================================================
    # 기본 CRUD 메서드
    # =========================================================================

    async def execute(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> aiosqlite.Cursor:
        """SQL 실행"""
        assert self._connection is not None
        if params:
            return await self._connection.execute(query, params)
        return await self._connection.execute(query)

    async def executemany(
        self, query: str, params_list: list[tuple[Any, ...]]
    ) -> aiosqlite.Cursor:
        """SQL 다중 실행"""
        assert self._connection is not None
        return await self._connection.executemany(query, params_list)

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

    # =========================================================================
    # 헬퍼 메서드
    # =========================================================================

    @staticmethod
    def serialize_json(data: Any) -> str:
        """JSON 직렬화"""
        return json.dumps(data, ensure_ascii=False, default=str)

    @staticmethod
    def deserialize_json(data: str | None) -> Any:
        """JSON 역직렬화"""
        if data is None:
            return None
        return json.loads(data)

    @staticmethod
    def now_iso() -> str:
        """현재 시간 ISO 문자열"""
        return datetime.now().isoformat()
