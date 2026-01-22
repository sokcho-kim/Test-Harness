"""promptfoo CLI 실행 및 결과 파싱"""

import asyncio
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor

import yaml


class PromptfooRunner:
    """promptfoo를 subprocess로 실행하고 결과를 파싱"""

    def __init__(self, project_root: Path | None = None):
        """
        Args:
            project_root: 프로젝트 루트 경로 (node_modules 위치)
        """
        self.project_root = project_root or Path.cwd()
        self._is_windows = sys.platform == "win32"

        # Windows에서는 npm run 사용, 그 외는 직접 실행
        if self._is_windows:
            self.promptfoo_cmd = ["npm", "run", "promptfoo", "--"]
        else:
            bin_path = self.project_root / "node_modules" / ".bin" / "promptfoo"
            self.promptfoo_cmd = [str(bin_path)]

    def _get_together_provider(self, model_id: str) -> dict:
        """Together AI 프로바이더 설정 생성"""
        return {
            "id": f"openai:chat:{model_id}",
            "config": {
                "apiBaseUrl": "https://api.together.xyz/v1",
                "apiKeyEnvar": "TOGETHER_API_KEY",
            }
        }

    def _build_config(
        self,
        prompts: list[dict],
        providers: list[dict],
        tests: list[dict],
        default_test: dict | None = None,
    ) -> dict:
        """promptfoo 설정 파일 생성

        Args:
            prompts: 프롬프트 목록 [{"id": "...", "content": "..."}]
            providers: 프로바이더 목록 (model_id)
            tests: 테스트 케이스 목록
            default_test: 기본 테스트 설정 (assertions 등)

        Returns:
            promptfoo YAML 설정 dict
        """
        # 프롬프트 변환
        prompt_configs = []
        for p in prompts:
            prompt_configs.append({
                "label": p["id"],  # label에 우리 ID 저장 (promptfoo가 보존)
                "raw": p["content"],
            })

        # 프로바이더 변환
        provider_configs = []
        for model_id in providers:
            provider_configs.append(self._get_together_provider(model_id))

        config = {
            "prompts": prompt_configs,
            "providers": provider_configs,
            "tests": tests,
        }

        if default_test:
            config["defaultTest"] = default_test

        return config

    async def run_eval(
        self,
        prompts: list[dict],
        model_ids: list[str],
        tests: list[dict],
        output_path: Path | None = None,
        timeout: int = 300,
        default_test: dict | None = None,
    ) -> dict:
        """promptfoo eval 실행

        Args:
            prompts: [{"id": "prompt_1", "content": "{{question}}에 답해"}]
            model_ids: ["meta-llama/Llama-3.3-70B-Instruct-Turbo"]
            tests: [{"vars": {"question": "서울 인구?"}, "assert": [...]}]
            output_path: 결과 저장 경로
            timeout: 실행 타임아웃 (초)
            default_test: 기본 assertion 등

        Returns:
            promptfoo 평가 결과 dict
        """
        # 설정 생성
        config = self._build_config(prompts, model_ids, tests, default_test)

        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        ) as f:
            yaml.dump(config, f, allow_unicode=True)
            config_path = Path(f.name)

        # 출력 파일 경로
        if output_path is None:
            output_file = tempfile.NamedTemporaryFile(
                suffix=".json",
                delete=False,
            )
            output_path = Path(output_file.name)
            output_file.close()

        try:
            # promptfoo 실행 명령 구성
            cmd = self.promptfoo_cmd + [
                "eval",
                "-c", str(config_path),
                "-o", str(output_path),
                "--no-cache",
                "--no-progress-bar",
            ]

            # Windows에서는 ThreadPoolExecutor로 subprocess.run 실행
            def run_subprocess():
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    cwd=str(self.project_root),
                    env={**os.environ},
                    timeout=timeout,
                    shell=self._is_windows,  # Windows에서만 shell=True
                )

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, run_subprocess)

            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"promptfoo failed (exit {result.returncode}): {error_msg}")

            # 결과 파싱
            with open(output_path, "r", encoding="utf-8") as f:
                results = json.load(f)

            return results

        finally:
            # 임시 파일 정리
            config_path.unlink(missing_ok=True)
            if output_path and output_path.exists():
                # 결과 파일은 호출자가 지정한 경우 유지
                pass

    def parse_results(self, raw_results: dict) -> list[dict]:
        """promptfoo 결과를 내부 형식으로 변환

        Args:
            raw_results: promptfoo 원본 결과

        Returns:
            파싱된 결과 리스트
        """
        parsed = []

        # promptfoo 출력 구조: results.results가 실제 결과 리스트
        results_wrapper = raw_results.get("results", {})
        if isinstance(results_wrapper, dict):
            results = results_wrapper.get("results", [])
        else:
            results = results_wrapper

        for result in results:
            prompt_info = result.get("prompt", {})
            provider_info = result.get("provider", {})
            response = result.get("response", {})

            # assertion 결과 파싱
            assertion_results = []
            for gr in result.get("gradingResult", {}).get("componentResults", []):
                assertion_results.append({
                    "type": gr.get("assertion", {}).get("type"),
                    "passed": gr.get("pass", False),
                    "reason": gr.get("reason"),
                    "score": gr.get("score"),
                })

            parsed.append({
                "prompt_id": prompt_info.get("label"),  # label에서 우리 ID 추출
                "prompt_raw": prompt_info.get("raw"),
                "model_id": provider_info.get("id"),
                "output": response.get("output"),
                "latency_ms": response.get("latencyMs"),
                "input_tokens": response.get("tokenUsage", {}).get("prompt"),
                "output_tokens": response.get("tokenUsage", {}).get("completion"),
                "passed": result.get("success", False),
                "assertion_results": assertion_results,
                "error": result.get("error"),
                "vars": result.get("vars", {}),
            })

        return parsed

    async def run_and_parse(
        self,
        prompts: list[dict],
        model_ids: list[str],
        tests: list[dict],
        **kwargs,
    ) -> list[dict]:
        """실행 + 파싱을 한번에"""
        raw = await self.run_eval(prompts, model_ids, tests, **kwargs)
        return self.parse_results(raw)
