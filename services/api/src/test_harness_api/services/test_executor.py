"""테스트 실행 Executor - promptfoo 기반 실제 테스트 실행"""

import asyncio
from pathlib import Path
from typing import Any

from shared.core.models import TestRunStatus
from shared.core.promptfoo_runner import PromptfooRunner
from shared.core.mapping import MappingResolver, PromptVariableExtractor, AssertionMerger
from shared.database.database import Database

from .test_service import TestService
from .prompt_service import PromptService
from .dataset_service import DatasetService


class TestExecutor:
    """테스트 실행 Executor

    TestRun을 받아 promptfoo로 실제 테스트 실행 후 결과 저장
    """

    def __init__(
        self,
        db: Database,
        project_root: Path | None = None,
    ):
        self.db = db
        self.test_service = TestService(db)
        self.prompt_service = PromptService(db)
        self.dataset_service = DatasetService(db)
        self.runner = PromptfooRunner(project_root=project_root)

    async def execute(
        self,
        test_run_id: str,
        timeout: int = 600,
        on_progress: callable = None,
    ) -> dict:
        """테스트 실행

        Args:
            test_run_id: 테스트 실행 ID
            timeout: 전체 타임아웃 (초)
            on_progress: 진행률 콜백 (current, total, status)

        Returns:
            실행 결과 요약
        """
        # 1. 테스트 실행 정보 로드
        test_run = await self.test_service.get_test_run(test_run_id)
        if not test_run:
            raise ValueError(f"Test run not found: {test_run_id}")

        # 2. 상태를 running으로 변경
        await self.test_service.update_test_run_status(
            test_run_id,
            TestRunStatus.RUNNING.value,
        )

        try:
            # 3. 프롬프트 정보 로드
            prompts = []
            prompt_map = {}  # promptfoo id → our prompt_id
            for prompt_id in test_run["prompt_ids"]:
                prompt = await self.prompt_service.get_prompt(prompt_id)
                if not prompt or not prompt.get("active_version"):
                    raise ValueError(f"Prompt or active version not found: {prompt_id}")

                pf_id = f"{prompt_id}_v{prompt['active_version']['version']}"
                prompts.append({
                    "id": pf_id,
                    "content": prompt["active_version"]["content"],
                })
                prompt_map[pf_id] = {
                    "prompt_id": prompt_id,
                    "version": prompt["active_version"]["version"],
                }

            # 4. 데이터셋 정보 및 케이스 로드
            dataset_id = test_run["dataset_id"]

            # 데이터셋 기본 assertions 로드
            dataset = await self.dataset_service.get_dataset(dataset_id)
            if not dataset:
                raise ValueError(f"Dataset not found: {dataset_id}")
            dataset_assertions = dataset.get("default_assertions", [])

            cases_result = await self.dataset_service.list_cases(
                dataset_id,
                limit=10000,  # 전체 로드
            )
            cases = cases_result["cases"]

            if not cases:
                raise ValueError(f"Dataset has no cases: {dataset_id}")

            # 5. 매핑 + Assertion 병합하여 테스트 케이스 생성
            resolved_mapping = test_run["resolved_mapping"]
            tests = []

            for case in cases:
                mapped_input = MappingResolver.apply_mapping(
                    case["raw_input"],
                    resolved_mapping,
                )

                # 히든 필드로 case_id 추적 (프롬프트에서 사용 안됨)
                vars_with_meta = {
                    **mapped_input,
                    "__case_id__": case["id"],
                }

                # 3단계 Assertion 병합
                # 1. Dataset.default_assertions (Base)
                # 2. Case.assertions (Override/Add)
                # 3. expected_output → contains (Safety Net)
                merged_assertions = AssertionMerger.merge_assertions(
                    dataset_assertions=dataset_assertions,
                    case_assertions=case.get("assertions"),
                    expected_output=case.get("expected_output"),
                )

                test_config = {"vars": vars_with_meta}
                if merged_assertions:
                    test_config["assert"] = merged_assertions

                tests.append(test_config)

            # 6. 모델 목록
            model_ids = test_run["model_ids"]

            # 7. promptfoo 실행
            if on_progress:
                on_progress(0, len(tests) * len(prompts) * len(model_ids), "running")

            raw_results = await self.runner.run_eval(
                prompts=prompts,
                model_ids=model_ids,
                tests=tests,
                timeout=timeout,
            )
            parsed_results = self.runner.parse_results(raw_results)

            # 8. 결과 저장
            saved_count = 0
            for result in parsed_results:
                # promptfoo ID에서 원래 정보 추출
                pf_prompt_id = result.get("prompt_id")
                prompt_info = prompt_map.get(pf_prompt_id, {})

                # vars에서 case_id 추출 (히든 필드)
                vars_data = result.get("vars", {})
                case_id = vars_data.pop("__case_id__", "unknown")

                # 모델 ID 정리 (openai:chat:model → model)
                model_id = result.get("model_id", "")
                if model_id.startswith("openai:chat:"):
                    model_id = model_id.replace("openai:chat:", "")

                await self.test_service.save_test_result(
                    test_run_id=test_run_id,
                    prompt_id=prompt_info.get("prompt_id", "unknown"),
                    prompt_version=prompt_info.get("version", "unknown"),
                    model_id=model_id,
                    test_case_id=case_id,
                    input_mapped=vars_data,
                    input_rendered=result.get("prompt_raw", ""),
                    output=result.get("output", ""),
                    latency_ms=result.get("latency_ms", 0),
                    passed=result.get("passed", False),
                    assertion_results=result.get("assertion_results", []),
                    input_tokens=result.get("input_tokens"),
                    output_tokens=result.get("output_tokens"),
                    error=result.get("error"),
                )
                saved_count += 1

                if on_progress:
                    on_progress(saved_count, len(parsed_results), "running")

            # 9. 완료 상태로 변경
            await self.test_service.update_test_run_status(
                test_run_id,
                TestRunStatus.COMPLETED.value,
            )

            return {
                "test_run_id": test_run_id,
                "status": "completed",
                "total_results": saved_count,
                "passed": sum(1 for r in parsed_results if r.get("passed")),
                "failed": sum(1 for r in parsed_results if not r.get("passed")),
            }

        except Exception as e:
            # 실패 상태로 변경
            await self.test_service.update_test_run_status(
                test_run_id,
                TestRunStatus.FAILED.value,
                error_message=str(e),
            )
            raise


async def execute_test_run(
    db: Database,
    test_run_id: str,
    project_root: Path | None = None,
    timeout: int = 600,
) -> dict:
    """편의 함수: 테스트 실행"""
    executor = TestExecutor(db, project_root=project_root)
    return await executor.execute(test_run_id, timeout=timeout)
