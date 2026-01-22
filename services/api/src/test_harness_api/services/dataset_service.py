"""데이터셋 서비스 (Import + 3단계 Fallback 매핑)"""

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any

from shared.core.models import DatasetType, SourceType
from shared.core.mapping import MappingResolver
from shared.database.database import Database


class DatasetService:
    """데이터셋 CRUD 및 Import"""

    def __init__(self, db: Database):
        self.db = db

    # =========================================================================
    # 데이터셋 CRUD
    # =========================================================================

    async def create_dataset(
        self,
        name: str,
        description: str | None = None,
        dataset_type: str = "evaluation",
        column_mapping: dict[str, str] | None = None,
        default_assertions: list[dict] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """데이터셋 생성 (빈 상태)"""
        dataset_id = f"dataset_{uuid.uuid4().hex[:8]}"
        now = self.db.now_iso()

        await self.db.execute(
            """
            INSERT INTO test_datasets
            (id, name, description, dataset_type, source_type, column_mapping, default_assertions, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                name,
                description,
                dataset_type,
                SourceType.MANUAL.value,
                self.db.serialize_json(column_mapping) if column_mapping else None,
                self.db.serialize_json(default_assertions or []),
                self.db.serialize_json(tags or []),
                now,
                now,
            ),
        )
        await self.db.commit()

        return await self.get_dataset(dataset_id)

    async def get_dataset(self, dataset_id: str) -> dict | None:
        """데이터셋 조회"""
        row = await self.db.fetchone(
            "SELECT * FROM test_datasets WHERE id = ?",
            (dataset_id,)
        )
        if not row:
            return None

        return self._row_to_dict(row)

    async def list_datasets(
        self,
        limit: int = 50,
        offset: int = 0,
        dataset_type: str | None = None,
    ) -> dict:
        """데이터셋 목록 조회"""
        # 조건 구성
        where = []
        params = []

        if dataset_type:
            where.append("dataset_type = ?")
            params.append(dataset_type)

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""

        # 카운트
        count_row = await self.db.fetchone(
            f"SELECT COUNT(*) as cnt FROM test_datasets {where_clause}",
            tuple(params) if params else None
        )
        total = count_row["cnt"] if count_row else 0

        # 목록
        params.extend([limit, offset])
        rows = await self.db.fetchall(
            f"""
            SELECT * FROM test_datasets
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params)
        )

        return {
            "datasets": [self._row_to_dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def update_dataset(
        self,
        dataset_id: str,
        name: str | None = None,
        description: str | None = None,
        dataset_type: str | None = None,
        column_mapping: dict[str, str] | None = None,
        default_assertions: list[dict] | None = None,
        tags: list[str] | None = None,
        is_verified: bool | None = None,
        verified_by: str | None = None,
    ) -> dict | None:
        """데이터셋 수정"""
        existing = await self.get_dataset(dataset_id)
        if not existing:
            return None

        now = self.db.now_iso()
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if dataset_type is not None:
            updates.append("dataset_type = ?")
            params.append(dataset_type)
        if column_mapping is not None:
            updates.append("column_mapping = ?")
            params.append(self.db.serialize_json(column_mapping))
        if default_assertions is not None:
            updates.append("default_assertions = ?")
            params.append(self.db.serialize_json(default_assertions))
        if tags is not None:
            updates.append("tags = ?")
            params.append(self.db.serialize_json(tags))
        if is_verified is not None:
            updates.append("is_verified = ?")
            params.append(1 if is_verified else 0)
            if is_verified and verified_by:
                updates.append("verified_by = ?")
                params.append(verified_by)
                updates.append("verified_at = ?")
                params.append(now)

        if updates:
            updates.append("updated_at = ?")
            params.append(now)
            params.append(dataset_id)

            await self.db.execute(
                f"UPDATE test_datasets SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )
            await self.db.commit()

        return await self.get_dataset(dataset_id)

    async def delete_dataset(self, dataset_id: str) -> bool:
        """데이터셋 삭제 (모든 케이스 포함)"""
        existing = await self.get_dataset(dataset_id)
        if not existing:
            return False

        await self.db.execute("DELETE FROM test_datasets WHERE id = ?", (dataset_id,))
        await self.db.commit()
        return True

    # =========================================================================
    # 테스트 케이스 관리
    # =========================================================================

    async def add_case(
        self,
        dataset_id: str,
        raw_input: dict[str, Any],
        expected_output: str | None = None,
        assertions: list[dict] | None = None,
        metadata: dict | None = None,
        is_edge_case: bool = False,
        is_error_pattern: bool = False,
    ) -> dict:
        """테스트 케이스 추가"""
        case_id = f"case_{uuid.uuid4().hex[:8]}"
        now = self.db.now_iso()

        await self.db.execute(
            """
            INSERT INTO test_cases
            (id, dataset_id, raw_input, expected_output, assertions, metadata, is_edge_case, is_error_pattern, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                dataset_id,
                self.db.serialize_json(raw_input),
                expected_output,
                self.db.serialize_json(assertions) if assertions else None,
                self.db.serialize_json(metadata) if metadata else None,
                1 if is_edge_case else 0,
                1 if is_error_pattern else 0,
                now,
            ),
        )

        # case_count 업데이트
        await self._update_case_count(dataset_id)
        await self.db.commit()

        return await self.get_case(case_id)

    async def get_case(self, case_id: str) -> dict | None:
        """테스트 케이스 조회"""
        row = await self.db.fetchone(
            "SELECT * FROM test_cases WHERE id = ?",
            (case_id,)
        )
        if not row:
            return None

        return {
            "id": row["id"],
            "dataset_id": row["dataset_id"],
            "raw_input": self.db.deserialize_json(row["raw_input"]),
            "expected_output": row["expected_output"],
            "assertions": self.db.deserialize_json(row["assertions"]),
            "rubric_scores": self.db.deserialize_json(row["rubric_scores"]),
            "metadata": self.db.deserialize_json(row["metadata"]),
            "is_edge_case": bool(row["is_edge_case"]),
            "is_error_pattern": bool(row["is_error_pattern"]),
            "created_at": row["created_at"],
        }

    async def list_cases(
        self,
        dataset_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """데이터셋의 테스트 케이스 목록"""
        count_row = await self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM test_cases WHERE dataset_id = ?",
            (dataset_id,)
        )
        total = count_row["cnt"] if count_row else 0

        rows = await self.db.fetchall(
            """
            SELECT * FROM test_cases
            WHERE dataset_id = ?
            ORDER BY created_at
            LIMIT ? OFFSET ?
            """,
            (dataset_id, limit, offset)
        )

        cases = []
        for row in rows:
            cases.append({
                "id": row["id"],
                "raw_input": self.db.deserialize_json(row["raw_input"]),
                "expected_output": row["expected_output"],
                "assertions": self.db.deserialize_json(row["assertions"]),
                "is_edge_case": bool(row["is_edge_case"]),
                "is_error_pattern": bool(row["is_error_pattern"]),
            })

        return {
            "dataset_id": dataset_id,
            "cases": cases,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def delete_case(self, case_id: str) -> bool:
        """테스트 케이스 삭제"""
        case = await self.get_case(case_id)
        if not case:
            return False

        await self.db.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
        await self._update_case_count(case["dataset_id"])
        await self.db.commit()
        return True

    # =========================================================================
    # CSV Import
    # =========================================================================

    async def import_csv(
        self,
        dataset_id: str,
        csv_content: str,
        column_mapping: dict[str, str] | None = None,
        expected_output_column: str = "expected_output",
        metadata_prefix: str = "_",
    ) -> dict:
        """CSV 파일 내용을 테스트 케이스로 임포트

        Args:
            dataset_id: 대상 데이터셋 ID
            csv_content: CSV 파일 내용 (문자열)
            column_mapping: 컬럼 매핑 (선택, 지정하면 데이터셋에 저장)
            expected_output_column: 기대 출력 컬럼명
            metadata_prefix: 메타데이터 컬럼 접두사 (기본: _)

        Returns:
            임포트 결과 (추가된 케이스 수 등)
        """
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # CSV 파싱
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return {"imported": 0, "errors": [], "message": "No data in CSV"}

        # 매핑 설정 저장
        if column_mapping:
            await self.db.execute(
                """
                UPDATE test_datasets
                SET column_mapping = ?, source_type = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    self.db.serialize_json(column_mapping),
                    SourceType.CSV.value,
                    self.db.now_iso(),
                    dataset_id,
                ),
            )

        imported = 0
        errors = []

        for i, row in enumerate(rows):
            try:
                # raw_input 구성 (expected_output과 metadata 제외)
                raw_input = {}
                metadata = {}
                expected_output = None

                for key, value in row.items():
                    if key == expected_output_column:
                        expected_output = value
                    elif key.startswith(metadata_prefix):
                        # 메타데이터 (접두사 제거)
                        meta_key = key[len(metadata_prefix):]
                        metadata[meta_key] = value
                    else:
                        raw_input[key] = value

                # 특수 메타데이터 플래그 처리
                is_edge_case = metadata.pop("is_edge_case", "").lower() in ("true", "1", "yes")
                is_error_pattern = metadata.pop("is_error_pattern", "").lower() in ("true", "1", "yes")

                # 케이스 추가
                await self.add_case(
                    dataset_id=dataset_id,
                    raw_input=raw_input,
                    expected_output=expected_output,
                    metadata=metadata if metadata else None,
                    is_edge_case=is_edge_case,
                    is_error_pattern=is_error_pattern,
                )
                imported += 1

            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)})

        return {
            "imported": imported,
            "errors": errors,
            "total_rows": len(rows),
            "message": f"Imported {imported}/{len(rows)} cases",
        }

    async def import_json(
        self,
        dataset_id: str,
        json_data: list[dict],
        column_mapping: dict[str, str] | None = None,
    ) -> dict:
        """JSON 배열을 테스트 케이스로 임포트"""
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        if column_mapping:
            await self.db.execute(
                """
                UPDATE test_datasets
                SET column_mapping = ?, source_type = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    self.db.serialize_json(column_mapping),
                    SourceType.JSON.value,
                    self.db.now_iso(),
                    dataset_id,
                ),
            )

        imported = 0
        errors = []

        for i, item in enumerate(json_data):
            try:
                raw_input = item.get("input", item.get("raw_input", {}))
                expected_output = item.get("expected_output", item.get("expected"))
                metadata = item.get("metadata")
                is_edge_case = item.get("is_edge_case", False)
                is_error_pattern = item.get("is_error_pattern", False)

                # input이 dict가 아니면 변환
                if not isinstance(raw_input, dict):
                    raw_input = {"input": raw_input}

                await self.add_case(
                    dataset_id=dataset_id,
                    raw_input=raw_input,
                    expected_output=expected_output,
                    metadata=metadata,
                    is_edge_case=is_edge_case,
                    is_error_pattern=is_error_pattern,
                )
                imported += 1

            except Exception as e:
                errors.append({"index": i, "error": str(e)})

        return {
            "imported": imported,
            "errors": errors,
            "total_items": len(json_data),
            "message": f"Imported {imported}/{len(json_data)} cases",
        }

    # =========================================================================
    # Export
    # =========================================================================

    async def export_csv(self, dataset_id: str) -> str:
        """데이터셋을 CSV로 내보내기"""
        cases = await self.list_cases(dataset_id, limit=10000)

        if not cases["cases"]:
            return ""

        # 모든 컬럼 수집
        all_columns = set()
        for case in cases["cases"]:
            all_columns.update(case["raw_input"].keys())

        columns = sorted(all_columns) + ["expected_output", "_is_edge_case", "_is_error_pattern"]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for case in cases["cases"]:
            row = {**case["raw_input"]}
            row["expected_output"] = case.get("expected_output", "")
            row["_is_edge_case"] = "true" if case.get("is_edge_case") else "false"
            row["_is_error_pattern"] = "true" if case.get("is_error_pattern") else "false"
            writer.writerow(row)

        return output.getvalue()

    async def export_json(self, dataset_id: str) -> list[dict]:
        """데이터셋을 JSON으로 내보내기"""
        cases = await self.list_cases(dataset_id, limit=10000)
        return cases["cases"]

    # =========================================================================
    # 헬퍼
    # =========================================================================

    def _row_to_dict(self, row) -> dict:
        """Row를 dict로 변환"""
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "dataset_type": row["dataset_type"],
            "source_type": row["source_type"],
            "source_file": row["source_file"],
            "column_mapping": self.db.deserialize_json(row["column_mapping"]),
            "default_assertions": self.db.deserialize_json(row["default_assertions"]),
            "is_verified": bool(row["is_verified"]),
            "verified_by": row["verified_by"],
            "verified_at": row["verified_at"],
            "tags": self.db.deserialize_json(row["tags"]),
            "case_count": row["case_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def _update_case_count(self, dataset_id: str):
        """케이스 수 업데이트"""
        count_row = await self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM test_cases WHERE dataset_id = ?",
            (dataset_id,)
        )
        count = count_row["cnt"] if count_row else 0

        await self.db.execute(
            "UPDATE test_datasets SET case_count = ?, updated_at = ? WHERE id = ?",
            (count, self.db.now_iso(), dataset_id)
        )
