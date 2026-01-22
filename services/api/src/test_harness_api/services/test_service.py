"""테스트 실행 서비스 (3단계 Fallback 매핑)"""

import uuid
from datetime import datetime
from typing import Any

from shared.core.models import TestRunStatus
from shared.core.mapping import MappingResolver, PromptVariableExtractor
from shared.database.database import Database

from .prompt_service import PromptService
from .dataset_service import DatasetService


class TestService:
    """테스트 실행 및 결과 관리"""

    def __init__(self, db: Database):
        self.db = db
        self.prompt_service = PromptService(db)
        self.dataset_service = DatasetService(db)

    # =========================================================================
    # 테스트 실행
    # =========================================================================

    async def create_test_run(
        self,
        prompt_ids: list[str],
        dataset_id: str,
        model_ids: list[str],
        column_mapping: dict[str, str] | None = None,
        name: str | None = None,
    ) -> dict:
        """테스트 실행 생성

        3단계 Fallback 매핑:
        1. column_mapping (실행 시점)
        2. dataset.column_mapping (데이터셋 기본값)
        3. 1:1 Fallback (컬럼명 = 변수명)
        """
        # 데이터셋 조회
        dataset = await self.dataset_service.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # 케이스 조회
        cases_result = await self.dataset_service.list_cases(dataset_id, limit=1)
        if not cases_result["cases"]:
            raise ValueError(f"Dataset has no cases: {dataset_id}")

        # 컬럼 목록
        raw_columns = list(cases_result["cases"][0]["raw_input"].keys())

        # 매핑 결정 (3단계 Fallback)
        resolved_mapping = MappingResolver.resolve_mapping(
            run_mapping=column_mapping,
            dataset_mapping=dataset.get("column_mapping"),
            raw_columns=raw_columns,
        )

        # 프롬프트 변수 검증
        for prompt_id in prompt_ids:
            prompt = await self.prompt_service.get_prompt(prompt_id)
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_id}")
            if not prompt.get("active_version"):
                raise ValueError(f"No active version for prompt: {prompt_id}")

            variables = prompt["active_version"]["variables"]
            validation = MappingResolver.validate_mapping(
                resolved_mapping, variables, raw_columns
            )

            if not validation.is_valid:
                raise ValueError(
                    f"Prompt '{prompt_id}' requires variables {validation.missing_variables} "
                    f"but mapping doesn't provide them. Available columns: {raw_columns}"
                )

        # 테스트 실행 생성
        test_run_id = f"run_{uuid.uuid4().hex[:8]}"
        now = self.db.now_iso()
        total_cases = cases_result["total"]

        await self.db.execute(
            """
            INSERT INTO test_runs
            (id, name, prompt_ids, dataset_id, model_ids, resolved_mapping, status, total_cases, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_run_id,
                name,
                self.db.serialize_json(prompt_ids),
                dataset_id,
                self.db.serialize_json(model_ids),
                self.db.serialize_json(resolved_mapping),
                TestRunStatus.PENDING.value,
                total_cases * len(prompt_ids) * len(model_ids),
                now,
            ),
        )
        await self.db.commit()

        return await self.get_test_run(test_run_id)

    async def get_test_run(self, test_run_id: str) -> dict | None:
        """테스트 실행 조회"""
        row = await self.db.fetchone(
            "SELECT * FROM test_runs WHERE id = ?",
            (test_run_id,)
        )
        if not row:
            return None

        return self._run_to_dict(row)

    async def list_test_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> dict:
        """테스트 실행 목록 조회"""
        where = []
        params = []

        if status:
            where.append("status = ?")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""

        count_row = await self.db.fetchone(
            f"SELECT COUNT(*) as cnt FROM test_runs {where_clause}",
            tuple(params) if params else None
        )
        total = count_row["cnt"] if count_row else 0

        params.extend([limit, offset])
        rows = await self.db.fetchall(
            f"""
            SELECT * FROM test_runs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params)
        )

        return {
            "test_runs": [self._run_to_dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def delete_test_run(self, test_run_id: str) -> bool:
        """테스트 실행 삭제"""
        existing = await self.get_test_run(test_run_id)
        if not existing:
            return False

        await self.db.execute("DELETE FROM test_runs WHERE id = ?", (test_run_id,))
        await self.db.commit()
        return True

    # =========================================================================
    # 테스트 결과
    # =========================================================================

    async def get_test_results(
        self,
        test_run_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """테스트 결과 조회"""
        count_row = await self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM test_results WHERE test_run_id = ?",
            (test_run_id,)
        )
        total = count_row["cnt"] if count_row else 0

        rows = await self.db.fetchall(
            """
            SELECT * FROM test_results
            WHERE test_run_id = ?
            ORDER BY created_at
            LIMIT ? OFFSET ?
            """,
            (test_run_id, limit, offset)
        )

        return {
            "test_run_id": test_run_id,
            "results": [self._result_to_dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def save_test_result(
        self,
        test_run_id: str,
        prompt_id: str,
        prompt_version: str,
        model_id: str,
        test_case_id: str,
        input_mapped: dict,
        input_rendered: str,
        output: str,
        latency_ms: float,
        passed: bool,
        assertion_results: list[dict] | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        error: str | None = None,
    ) -> dict:
        """테스트 결과 저장"""
        result_id = f"result_{uuid.uuid4().hex[:8]}"
        now = self.db.now_iso()

        await self.db.execute(
            """
            INSERT INTO test_results
            (id, test_run_id, prompt_id, prompt_version, model_id, test_case_id,
             input_mapped, input_rendered, output, latency_ms, input_tokens, output_tokens,
             assertion_results, passed, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                test_run_id,
                prompt_id,
                prompt_version,
                model_id,
                test_case_id,
                self.db.serialize_json(input_mapped),
                input_rendered,
                output,
                latency_ms,
                input_tokens,
                output_tokens,
                self.db.serialize_json(assertion_results or []),
                1 if passed else 0,
                error,
                now,
            ),
        )

        # 진행률 업데이트
        await self.db.execute(
            """
            UPDATE test_runs
            SET completed_cases = completed_cases + 1,
                progress = CAST((completed_cases + 1) * 100.0 / total_cases AS INTEGER)
            WHERE id = ?
            """,
            (test_run_id,)
        )

        await self.db.commit()

        return {
            "id": result_id,
            "test_run_id": test_run_id,
            "passed": passed,
        }

    async def update_test_run_status(
        self,
        test_run_id: str,
        status: str,
        error_message: str | None = None,
    ):
        """테스트 실행 상태 업데이트"""
        now = self.db.now_iso()
        updates = ["status = ?"]
        params = [status]

        if status == TestRunStatus.RUNNING.value:
            updates.append("started_at = ?")
            params.append(now)
        elif status in [TestRunStatus.COMPLETED.value, TestRunStatus.FAILED.value]:
            updates.append("completed_at = ?")
            params.append(now)

        if error_message:
            updates.append("error_message = ?")
            params.append(error_message)

        params.append(test_run_id)

        await self.db.execute(
            f"UPDATE test_runs SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        await self.db.commit()

    # =========================================================================
    # 매핑 미리보기
    # =========================================================================

    async def preview_mapping(
        self,
        prompt_id: str,
        dataset_id: str,
        column_mapping: dict[str, str] | None = None,
        sample_count: int = 3,
    ) -> dict:
        """매핑 결과 미리보기

        실행 전에 매핑이 올바르게 적용되는지 확인
        """
        # 프롬프트 조회
        prompt = await self.prompt_service.get_prompt(prompt_id)
        if not prompt or not prompt.get("active_version"):
            raise ValueError("Prompt or active version not found")

        # 데이터셋 조회
        dataset = await self.dataset_service.get_dataset(dataset_id)
        if not dataset:
            raise ValueError("Dataset not found")

        # 샘플 케이스 조회
        cases_result = await self.dataset_service.list_cases(dataset_id, limit=sample_count)
        if not cases_result["cases"]:
            raise ValueError("Dataset has no cases")

        # 매핑 결정
        raw_columns = list(cases_result["cases"][0]["raw_input"].keys())
        resolved_mapping = MappingResolver.resolve_mapping(
            run_mapping=column_mapping,
            dataset_mapping=dataset.get("column_mapping"),
            raw_columns=raw_columns,
        )

        # 검증
        prompt_variables = prompt["active_version"]["variables"]
        validation = MappingResolver.validate_mapping(
            resolved_mapping, prompt_variables, raw_columns
        )

        # 샘플 렌더링
        template = prompt["active_version"]["content"]
        samples = []

        for case in cases_result["cases"]:
            mapped_input = MappingResolver.apply_mapping(case["raw_input"], resolved_mapping)
            try:
                rendered = PromptVariableExtractor.render(template, mapped_input, strict=True)
                error = None
            except ValueError as e:
                rendered = None
                error = str(e)

            samples.append({
                "case_id": case["id"],
                "raw_input": case["raw_input"],
                "mapped_input": mapped_input,
                "rendered_prompt": rendered,
                "error": error,
            })

        return {
            "prompt_id": prompt_id,
            "prompt_version": prompt["active_version"]["version"],
            "dataset_id": dataset_id,
            "resolved_mapping": resolved_mapping,
            "mapping_source": (
                "run_override" if column_mapping else
                "dataset_default" if dataset.get("column_mapping") else
                "auto_1to1"
            ),
            "validation": {
                "is_valid": validation.is_valid,
                "missing_variables": validation.missing_variables,
                "unused_columns": validation.unused_columns,
                "warnings": validation.warnings,
            },
            "samples": samples,
        }

    # =========================================================================
    # 헬퍼
    # =========================================================================

    def _run_to_dict(self, row) -> dict:
        """Row를 dict로 변환"""
        return {
            "id": row["id"],
            "name": row["name"],
            "prompt_ids": self.db.deserialize_json(row["prompt_ids"]),
            "dataset_id": row["dataset_id"],
            "model_ids": self.db.deserialize_json(row["model_ids"]),
            "resolved_mapping": self.db.deserialize_json(row["resolved_mapping"]),
            "status": row["status"],
            "progress": row["progress"],
            "total_cases": row["total_cases"],
            "completed_cases": row["completed_cases"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "error_message": row["error_message"],
        }

    def _result_to_dict(self, row) -> dict:
        """Row를 dict로 변환"""
        return {
            "id": row["id"],
            "test_run_id": row["test_run_id"],
            "prompt_id": row["prompt_id"],
            "prompt_version": row["prompt_version"],
            "model_id": row["model_id"],
            "test_case_id": row["test_case_id"],
            "input_mapped": self.db.deserialize_json(row["input_mapped"]),
            "input_rendered": row["input_rendered"],
            "output": row["output"],
            "latency_ms": row["latency_ms"],
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "assertion_results": self.db.deserialize_json(row["assertion_results"]),
            "passed": bool(row["passed"]),
            "error": row["error"],
            "created_at": row["created_at"],
        }
