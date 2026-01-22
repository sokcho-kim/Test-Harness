"""프롬프트 서비스 (CRUD + Semantic Versioning)"""

import re
import uuid
from datetime import datetime

from shared.core.models import Prompt, PromptVersion, PromptStatus
from shared.core.mapping import PromptVariableExtractor
from shared.database.database import Database


class PromptService:
    """프롬프트 CRUD 및 버전 관리"""

    def __init__(self, db: Database):
        self.db = db

    # =========================================================================
    # 프롬프트 CRUD
    # =========================================================================

    async def create_prompt(
        self,
        name: str,
        content: str,
        description: str | None = None,
        tags: list[str] | None = None,
        created_by: str | None = None,
    ) -> dict:
        """프롬프트 생성 (v1.0.0 자동 생성)"""
        prompt_id = f"prompt_{uuid.uuid4().hex[:8]}"
        version_id = f"ver_{uuid.uuid4().hex[:8]}"
        now = self.db.now_iso()

        # 변수 자동 추출
        variables = PromptVariableExtractor.extract(content)

        # 프롬프트 생성
        await self.db.execute(
            """
            INSERT INTO prompts (id, name, description, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                prompt_id,
                name,
                description,
                self.db.serialize_json(tags or []),
                now,
                now,
            ),
        )

        # 첫 번째 버전 생성 (v1.0.0, active)
        await self.db.execute(
            """
            INSERT INTO prompt_versions
            (id, prompt_id, major, minor, patch, content, variables, is_active, status, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                prompt_id,
                1, 0, 0,
                content,
                self.db.serialize_json(variables),
                1,  # is_active
                PromptStatus.ACTIVE.value,
                created_by,
                now,
            ),
        )

        await self.db.commit()

        return {
            "id": prompt_id,
            "name": name,
            "description": description,
            "tags": tags or [],
            "active_version": {
                "id": version_id,
                "version": "1.0.0",
                "content": content,
                "variables": variables,
            },
            "created_at": now,
        }

    async def get_prompt(self, prompt_id: str) -> dict | None:
        """프롬프트 조회 (active 버전 포함)"""
        row = await self.db.fetchone(
            "SELECT * FROM prompts WHERE id = ?",
            (prompt_id,)
        )
        if not row:
            return None

        # active 버전 조회
        active_version = await self.db.fetchone(
            """
            SELECT * FROM prompt_versions
            WHERE prompt_id = ? AND is_active = 1
            """,
            (prompt_id,)
        )

        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "tags": self.db.deserialize_json(row["tags"]),
            "active_version": self._version_to_dict(active_version) if active_version else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def list_prompts(
        self,
        limit: int = 50,
        offset: int = 0,
        tag: str | None = None,
    ) -> dict:
        """프롬프트 목록 조회"""
        # 카운트
        count_row = await self.db.fetchone("SELECT COUNT(*) as cnt FROM prompts")
        total = count_row["cnt"] if count_row else 0

        # 목록 조회
        rows = await self.db.fetchall(
            """
            SELECT p.*, pv.id as ver_id, pv.major, pv.minor, pv.patch, pv.content, pv.variables
            FROM prompts p
            LEFT JOIN prompt_versions pv ON p.id = pv.prompt_id AND pv.is_active = 1
            ORDER BY p.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )

        prompts = []
        for row in rows:
            prompts.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "tags": self.db.deserialize_json(row["tags"]),
                "active_version": f"{row['major']}.{row['minor']}.{row['patch']}" if row["ver_id"] else None,
                "updated_at": row["updated_at"],
            })

        return {
            "prompts": prompts,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def update_prompt(
        self,
        prompt_id: str,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> dict | None:
        """프롬프트 메타데이터 수정"""
        existing = await self.get_prompt(prompt_id)
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
        if tags is not None:
            updates.append("tags = ?")
            params.append(self.db.serialize_json(tags))

        if updates:
            updates.append("updated_at = ?")
            params.append(now)
            params.append(prompt_id)

            await self.db.execute(
                f"UPDATE prompts SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )
            await self.db.commit()

        return await self.get_prompt(prompt_id)

    async def delete_prompt(self, prompt_id: str) -> bool:
        """프롬프트 삭제 (모든 버전 포함)"""
        existing = await self.get_prompt(prompt_id)
        if not existing:
            return False

        # CASCADE로 버전도 삭제됨
        await self.db.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        await self.db.commit()
        return True

    # =========================================================================
    # 버전 관리 (Semantic Versioning)
    # =========================================================================

    async def list_versions(self, prompt_id: str) -> list[dict]:
        """프롬프트의 모든 버전 조회"""
        rows = await self.db.fetchall(
            """
            SELECT * FROM prompt_versions
            WHERE prompt_id = ?
            ORDER BY major DESC, minor DESC, patch DESC
            """,
            (prompt_id,)
        )
        return [self._version_to_dict(row) for row in rows]

    async def get_version(self, version_id: str) -> dict | None:
        """특정 버전 조회"""
        row = await self.db.fetchone(
            "SELECT * FROM prompt_versions WHERE id = ?",
            (version_id,)
        )
        return self._version_to_dict(row) if row else None

    async def create_version(
        self,
        prompt_id: str,
        content: str,
        change_type: str = "minor",  # "major", "minor", "patch"
        change_note: str | None = None,
        created_by: str | None = None,
        auto_activate: bool = False,
    ) -> dict | None:
        """새 버전 생성

        Args:
            prompt_id: 프롬프트 ID
            content: 새 내용
            change_type: 버전 업 타입 (major/minor/patch)
            change_note: 변경 사유
            created_by: 작성자
            auto_activate: 즉시 활성화 여부

        Returns:
            생성된 버전 정보
        """
        # 최신 버전 조회
        latest = await self.db.fetchone(
            """
            SELECT major, minor, patch FROM prompt_versions
            WHERE prompt_id = ?
            ORDER BY major DESC, minor DESC, patch DESC
            LIMIT 1
            """,
            (prompt_id,)
        )

        if not latest:
            return None

        # 버전 번호 계산
        major, minor, patch = latest["major"], latest["minor"], latest["patch"]
        if change_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif change_type == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        version_id = f"ver_{uuid.uuid4().hex[:8]}"
        now = self.db.now_iso()
        variables = PromptVariableExtractor.extract(content)

        await self.db.execute(
            """
            INSERT INTO prompt_versions
            (id, prompt_id, major, minor, patch, content, variables, is_active, status, change_note, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                prompt_id,
                major, minor, patch,
                content,
                self.db.serialize_json(variables),
                0,  # is_active (기본 비활성)
                PromptStatus.DRAFT.value,
                change_note,
                created_by,
                now,
            ),
        )

        # 프롬프트 updated_at 갱신
        await self.db.execute(
            "UPDATE prompts SET updated_at = ? WHERE id = ?",
            (now, prompt_id)
        )

        await self.db.commit()

        # 자동 활성화
        if auto_activate:
            await self.activate_version(prompt_id, version_id)

        return await self.get_version(version_id)

    async def activate_version(self, prompt_id: str, version_id: str) -> bool:
        """특정 버전 활성화 (기존 active 비활성화)"""
        # 기존 active 비활성화
        await self.db.execute(
            """
            UPDATE prompt_versions
            SET is_active = 0, status = ?
            WHERE prompt_id = ? AND is_active = 1
            """,
            (PromptStatus.DEPRECATED.value, prompt_id)
        )

        # 새 버전 활성화
        await self.db.execute(
            """
            UPDATE prompt_versions
            SET is_active = 1, status = ?
            WHERE id = ? AND prompt_id = ?
            """,
            (PromptStatus.ACTIVE.value, version_id, prompt_id)
        )

        now = self.db.now_iso()
        await self.db.execute(
            "UPDATE prompts SET updated_at = ? WHERE id = ?",
            (now, prompt_id)
        )

        await self.db.commit()
        return True

    async def get_active_version(self, prompt_id: str) -> dict | None:
        """active 버전 조회"""
        row = await self.db.fetchone(
            """
            SELECT * FROM prompt_versions
            WHERE prompt_id = ? AND is_active = 1
            """,
            (prompt_id,)
        )
        return self._version_to_dict(row) if row else None

    # =========================================================================
    # 헬퍼
    # =========================================================================

    def _version_to_dict(self, row) -> dict:
        """Row를 dict로 변환"""
        return {
            "id": row["id"],
            "prompt_id": row["prompt_id"],
            "version": f"{row['major']}.{row['minor']}.{row['patch']}",
            "major": row["major"],
            "minor": row["minor"],
            "patch": row["patch"],
            "content": row["content"],
            "variables": self.db.deserialize_json(row["variables"]),
            "is_active": bool(row["is_active"]),
            "status": row["status"],
            "change_note": row["change_note"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
        }
