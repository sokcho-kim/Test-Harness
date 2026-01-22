"""3단계 Fallback 매핑 및 Assertion 병합 처리

매핑 우선순위:
1. TestRunRequest.column_mapping (실행 시점 오버라이드)
2. TestDataset.column_mapping (데이터셋 기본값)
3. 1:1 Fallback (컬럼명 = 변수명, Convention over Configuration)

Assertion 병합 우선순위:
1. Dataset.default_assertions (Base - 전체 케이스 적용)
2. Case.assertions (Override/Add - 개별 케이스)
3. expected_output → contains (Safety Net - 자동 생성)

References:
- Gemini 분석: 플랫폼 설계 관점 유연성
"""

import re
from dataclasses import dataclass
from typing import Any

from .models import Assertion, AssertionType


@dataclass
class MappingValidationResult:
    """매핑 검증 결과"""
    is_valid: bool
    missing_variables: list[str]    # 프롬프트에 필요하지만 매핑되지 않은 변수
    unused_columns: list[str]       # 데이터에 있지만 사용되지 않는 컬럼
    warnings: list[str]             # 경고 메시지


class MappingResolver:
    """3단계 Fallback 매핑 처리"""

    @staticmethod
    def resolve_mapping(
        run_mapping: dict[str, str] | None,
        dataset_mapping: dict[str, str] | None,
        raw_columns: list[str]
    ) -> dict[str, str]:
        """매핑 결정 (우선순위: run > dataset > 1:1)

        Args:
            run_mapping: 실행 시점 매핑 (1순위)
            dataset_mapping: 데이터셋 기본 매핑 (2순위)
            raw_columns: 원본 데이터 컬럼 목록

        Returns:
            최종 매핑 딕셔너리 {원본컬럼: 변수명}
        """
        if run_mapping:
            return run_mapping
        if dataset_mapping:
            return dataset_mapping
        # 1:1 fallback (Convention over Configuration)
        return {col: col for col in raw_columns}

    @staticmethod
    def apply_mapping(raw_row: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
        """원본 데이터를 프롬프트 변수에 맞게 변환

        Args:
            raw_row: 원본 데이터 {"user_query": "안녕", "doc_chunk": "내용..."}
            mapping: 매핑 정보 {"user_query": "question", "doc_chunk": "context"}

        Returns:
            변환된 데이터 {"question": "안녕", "context": "내용..."}
        """
        if not mapping:
            return raw_row

        result = {}
        for origin_key, mapped_key in mapping.items():
            if origin_key in raw_row:
                result[mapped_key] = raw_row[origin_key]

        return result

    @staticmethod
    def validate_mapping(
        mapping: dict[str, str],
        prompt_variables: list[str],
        data_columns: list[str]
    ) -> MappingValidationResult:
        """매핑 검증

        Args:
            mapping: 적용할 매핑
            prompt_variables: 프롬프트에 필요한 변수 목록
            data_columns: 데이터에 존재하는 컬럼 목록

        Returns:
            검증 결과
        """
        mapped_vars = set(mapping.values())
        required_vars = set(prompt_variables)
        available_cols = set(data_columns)
        mapping_cols = set(mapping.keys())

        # 누락된 변수 (프롬프트에 필요하지만 매핑 안됨)
        missing_variables = list(required_vars - mapped_vars)

        # 사용되지 않는 컬럼 (데이터에 있지만 매핑 안됨)
        unused_columns = list(available_cols - mapping_cols)

        # 경고 메시지
        warnings = []

        # 매핑에 지정됐지만 데이터에 없는 컬럼
        invalid_cols = mapping_cols - available_cols
        if invalid_cols:
            warnings.append(f"매핑에 지정된 컬럼이 데이터에 없음: {list(invalid_cols)}")

        is_valid = len(missing_variables) == 0

        return MappingValidationResult(
            is_valid=is_valid,
            missing_variables=missing_variables,
            unused_columns=unused_columns,
            warnings=warnings
        )

    @staticmethod
    def suggest_mapping(
        data_columns: list[str],
        prompt_variables: list[str]
    ) -> dict[str, str]:
        """자동 매핑 추천 (컬럼명 유사도 기반)

        간단한 규칙:
        1. 정확히 일치하면 매핑
        2. 소문자 비교로 일치하면 매핑
        3. 일반적인 별칭 매핑 (question ↔ query, context ↔ document 등)

        Args:
            data_columns: 데이터 컬럼 목록
            prompt_variables: 프롬프트 변수 목록

        Returns:
            추천 매핑
        """
        # 일반적인 별칭 매핑
        ALIASES = {
            "question": ["query", "q", "user_query", "input", "user_input"],
            "context": ["document", "doc", "doc_chunk", "chunk", "passage", "text"],
            "answer": ["response", "output", "expected", "expected_output", "gold"],
        }

        suggested = {}
        data_cols_lower = {col.lower(): col for col in data_columns}
        remaining_vars = set(prompt_variables)

        for var in prompt_variables:
            var_lower = var.lower()

            # 1. 정확히 일치
            if var in data_columns:
                suggested[var] = var
                remaining_vars.discard(var)
                continue

            # 2. 소문자 비교
            if var_lower in data_cols_lower:
                suggested[data_cols_lower[var_lower]] = var
                remaining_vars.discard(var)
                continue

            # 3. 별칭 매핑
            if var_lower in ALIASES:
                for alias in ALIASES[var_lower]:
                    if alias in data_cols_lower:
                        suggested[data_cols_lower[alias]] = var
                        remaining_vars.discard(var)
                        break

        return suggested


class PromptVariableExtractor:
    """프롬프트에서 변수 추출"""

    # 지원하는 변수 문법
    PATTERNS = [
        r"\{\{(\w+)\}\}",       # Jinja2 스타일: {{variable}}
        r"\{\$(\w+)\}",         # The Prompt Test 스타일: {$variable}
        r"\{(\w+)\}",           # 단순 스타일: {variable}
    ]

    @classmethod
    def extract(cls, content: str) -> list[str]:
        """프롬프트 내용에서 변수 추출

        Args:
            content: 프롬프트 내용

        Returns:
            변수명 목록 (중복 제거, 순서 유지)
        """
        variables = []
        seen = set()

        for pattern in cls.PATTERNS:
            matches = re.findall(pattern, content)
            for var in matches:
                if var not in seen:
                    variables.append(var)
                    seen.add(var)

        return variables

    @classmethod
    def render(
        cls,
        template: str,
        variables: dict[str, Any],
        strict: bool = False
    ) -> str:
        """변수를 치환하여 프롬프트 렌더링

        Args:
            template: 프롬프트 템플릿
            variables: 변수 딕셔너리
            strict: True면 누락된 변수 시 에러 발생

        Returns:
            렌더링된 프롬프트
        """
        result = template

        for pattern in cls.PATTERNS:
            def replace(match):
                var_name = match.group(1)
                if var_name in variables:
                    return str(variables[var_name])
                elif strict:
                    raise ValueError(f"변수 '{var_name}'이 제공되지 않았습니다")
                else:
                    return match.group(0)  # 원본 유지

            result = re.sub(pattern, replace, result)

        return result


class AssertionMerger:
    """3단계 Assertion 병합 처리

    병합 우선순위:
    1. Dataset.default_assertions (Base - 전체 케이스 적용)
    2. Case.assertions (Override/Add - 개별 케이스)
    3. expected_output → contains (Safety Net - 자동 생성)

    병합 전략:
    - 같은 type의 assertion이 있으면 Case 것으로 Override
    - 다른 type의 assertion은 Add
    - expected_output이 있고 contains assertion이 없으면 자동 생성
    """

    @staticmethod
    def merge_assertions(
        dataset_assertions: list[Assertion] | list[dict] | None,
        case_assertions: list[Assertion] | list[dict] | None,
        expected_output: str | None = None,
    ) -> list[dict]:
        """Assertion 병합

        Args:
            dataset_assertions: 데이터셋 기본 assertions (1순위 Base)
            case_assertions: 케이스별 assertions (2순위 Override/Add)
            expected_output: 예상 출력 (3순위 Safety Net)

        Returns:
            병합된 promptfoo 형식 assertions 리스트
        """
        # 1. Assertion을 dict로 정규화
        def normalize(assertions: list | None) -> list[dict]:
            if not assertions:
                return []
            result = []
            for a in assertions:
                if isinstance(a, Assertion):
                    result.append(a.model_dump(exclude_none=True))
                elif isinstance(a, dict):
                    result.append(a)
            return result

        dataset_list = normalize(dataset_assertions)
        case_list = normalize(case_assertions)

        # 2. Dataset assertions를 기본으로 시작
        merged: dict[str, dict] = {}
        for a in dataset_list:
            key = AssertionMerger._get_assertion_key(a)
            merged[key] = a

        # 3. Case assertions로 Override/Add
        for a in case_list:
            key = AssertionMerger._get_assertion_key(a)
            merged[key] = a  # 같은 key면 덮어쓰기 (Override)

        # 4. Safety Net: expected_output → contains
        if expected_output:
            contains_key = f"contains:{expected_output}"
            # 이미 같은 값의 contains가 있는지 확인
            has_contains = any(
                a.get("type") == "contains" and a.get("value") == expected_output
                for a in merged.values()
            )
            if not has_contains:
                merged[contains_key] = {
                    "type": "contains",
                    "value": expected_output,
                }

        # 5. promptfoo 형식으로 변환
        return [AssertionMerger._to_promptfoo_format(a) for a in merged.values()]

    @staticmethod
    def _get_assertion_key(assertion: dict) -> str:
        """Assertion 고유 키 생성 (중복 판단용)

        - type + value 조합으로 키 생성
        - llm-rubric은 type만으로 판단 (하나만 허용)
        """
        a_type = assertion.get("type", "")
        a_value = assertion.get("value", "")

        # llm-rubric은 type만으로 고유 (케이스당 하나)
        if a_type == "llm-rubric":
            return "llm-rubric"

        return f"{a_type}:{a_value}"

    @staticmethod
    def _to_promptfoo_format(assertion: dict) -> dict:
        """내부 형식을 promptfoo 형식으로 변환

        내부 형식: {"type": "contains", "value": "...", "threshold": 0.8}
        promptfoo: {"type": "contains", "value": "..."}

        특수 처리:
        - llm-rubric → rubricPrompt 필드 사용
        - threshold → score 조건 추가
        """
        a_type = assertion.get("type", "")
        result = {"type": a_type}

        # type별 처리
        if a_type == "llm-rubric":
            # llm-rubric은 value를 rubricPrompt로 사용
            result["value"] = assertion.get("value", "")
        elif a_type in ("contains", "not-contains", "equals", "starts-with", "regex"):
            result["value"] = assertion.get("value", "")
        elif a_type == "is-json":
            pass  # value 불필요

        # threshold가 있으면 score 조건 추가
        if "threshold" in assertion and assertion["threshold"] is not None:
            result["threshold"] = assertion["threshold"]

        return result
