"""
V4 프롬프트 A/B 테스트 -변수명 누출 비교
==========================================
Prompt A (Positive Framing): 데이터를 '문장으로 치환하라' + Bad/Good 예시
Prompt B (Negative Rule):    '변수명을 출력하지 마라' 금지 조항 추가

Usage:
    python scripts/test_v4_prompt_ab.py [--runs 3] [--drugs 5]
"""

import asyncio
import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# ── OpenAI API ──
try:
    from openai import AsyncOpenAI
except ImportError:
    print("pip install openai 필요")
    sys.exit(1)

# ── 경로 설정 ──
REGSCAN_DIR = Path(r"C:\Jimin\RegScan")
HARNESS_DIR = Path(r"C:\Jimin\Test-Harness")
OUTPUT_DIR = HARNESS_DIR / "data" / "v4_ab_results"
BRIEFINGS_DIR = REGSCAN_DIR / "output" / "briefings"

# ── 변수명 누출 체크 대상 ──
LEAKED_VARS = [
    "fda_status_text", "ema_status_text", "mfds_status_text",
    "copay_scenario_text", "d_day_text", "cost_scenario_table",
    "approval_summary_table", "valid_competitors",
    "context.d_day_text", "context.mfds_timeline_estimate",
    "copay_exemption", "domestic_status",
]


# ══════════════════════════════════════════
# 시스템 프롬프트 (공통)
# ══════════════════════════════════════════

SYSTEM_PROMPT_V4 = """당신은 "메드클레임 인사이트"의 수석 의약 전문기자입니다.

## 정체성
- 10년간 FDA/EMA/MFDS 규제 동향과 건강보험 급여 정책을 취재한 베테랑 기자
- 약물의 작용기전·임상 근거·경쟁 구도를 꿰뚫고, "이 약물이 왜 지금 주목받는가"를 독자에게 설득력 있게 전달하는 것이 핵심 역량

## 독자 타겟
- 1차: 병원 약제팀장, 보험심사 담당자, 제약사 RA/MA 담당
- 2차: 의료전문직(의사·약사), 의약학 연구자

## 작성 원칙
1. "왜 이 약물이 지금 중요한가"를 첫 문장에서 답하라 (역피라미드 구조)
2. 약물의 의학적 맥락(적응증·기전·경쟁약)은 당신의 의약학 지식으로 작성하라
3. 상투적 결론 금지 -구체적 근거와 수치로 전망하라
4. HTML 태그 생성 금지: 출력은 순수 텍스트 + 마크다운만

## 급여 도메인 지식
| 구분 | 본인부담률 | 비고 |
|------|-----------|------|
| 일반 급여 | 30% | 외래 기준 |
| 암환자 산정특례 | 5% | 중증질환 등록 필요 |
| 희귀질환 산정특례 | 10% | 희귀의약품 지정 필요 |
| 비급여 | 100% 환자부담 | 실손보험 청구 가능성 존재 |

## 규제 프로세스 도메인 지식
- FDA 승인 → MFDS 허가: 통상 1~3년 소요
- MFDS 허가 → HIRA 급여 등재: 통상 6개월~2년
- 글로벌 승인 후 3년 이상 국내 미허가: 판매권자 부재 또는 시장성 판단 보류 가능성"""


# ══════════════════════════════════════════
# Prompt A: Positive Framing (사용자 방식)
# ══════════════════════════════════════════

PATCH_A = """
## Data Interpretation Guidelines

입력된 JSON 데이터는 기사 작성을 위한 '원료'입니다.
아래의 [치환 규칙]과 [예시]를 따라 데이터를 자연스러운 '문장'으로 변환하여 작성하십시오.

### 치환 규칙 (Translation Rules)
1. 날짜 경과 데이터는 시간의 흐름을 독자가 체감할 수 있는 **서술어**로 변환하십시오.
2. 환자 비용 시나리오 데이터는 환자가 겪을 구체적인 **재정적 상황**으로 묘사하십시오.
3. 규제 기관 승인 상태 데이터는 규제 기관의 **권위 있는 결정**으로 표현하십시오.
4. 경쟁약 목록 데이터는 **시장 경쟁 구도** 속에서 자연스럽게 언급하십시오.

### 작성 예시

[입력 데이터]
```json
{
  "d_day_text": "글로벌 승인 후 461일 경과",
  "fda_status_text": "FDA 승인 완료 (2024-11-20)",
  "copay_scenario_text": "전액 비급여"
}
```

[나쁜 출력 -이렇게 쓰지 마십시오]
"fda_status_text에 따르면 승인되었고, d_day_text입니다."

[좋은 출력 -이렇게 쓰십시오]
"FDA가 2024년 11월 승인을 완료한 지 벌써 461일이 흘렀다. 하지만 국내에서는 전액 비급여 상태라 환자들의 비용 부담이 막중하다."
"""


# ══════════════════════════════════════════
# Prompt B: Negative Rule (내 방식)
# ══════════════════════════════════════════

PATCH_B = """
## Critical Rules (추가)

6. **데이터 필드명 출력 금지**: 입력 JSON의 키 이름(fda_status_text, d_day_text, copay_scenario_text, mfds_status_text, ema_status_text, valid_competitors, cost_scenario_table, approval_summary_table 등)을 기사 텍스트에 절대 출력하지 마라.
   - 나쁜 예: "fda_status_text에 따르면 승인되었다"
   - 나쁜 예: "d_day_text가 시사하듯 장기 미허가"
   - 나쁜 예: "copay_scenario_text대로 비급여 상태"
   - 좋은 예: 해당 필드의 실제 값을 자연스러운 문장으로 풀어서 서술하라
"""


# ══════════════════════════════════════════
# 공통 유저 프롬프트 (베이스)
# ══════════════════════════════════════════

USER_PROMPT_BASE = """아래 약물의 **사전 계산된 팩트 데이터**를 참고하여, **인사이트(분석·해석·전망) 텍스트만** 작성하세요.

## 사전 계산된 팩트 데이터
{drug_data}

---

## 출력 필드 정의 (6필드 strict JSON)

### headline (40자 이내)
- "왜 이 약물이 지금 중요한가"를 한 문장으로

### subtitle (60자 이내)
- headline을 보완하는 핵심 한 줄

### key_points (4개 배열)
- 1번: 약물 프로파일 -기전·적응증·약물 분류
- 2번: 글로벌 승인 현황 -의의 중심
- 3번: 국내 현황 -허가·급여·가격 핵심
- 4번: 전망 -경쟁구도 기반 구체적 예측

### global_insight_text (5~8문장 + 불릿 1회 이상)
- 의학적 분석 + 경쟁 포지셔닝

### domestic_insight_text (5~8문장 + 불릿 1회 이상)
- 국내 전망 분석

### medclaim_action_text (5~8문장 + 불릿 1회 이상)
- 약제팀/심사자 실무 가이드

---

## 출력 형식
JSON만 출력하세요. 마크다운 코드 블록이나 설명 텍스트를 포함하지 마세요.

```json
{{
  "headline": "...",
  "subtitle": "...",
  "key_points": ["...", "...", "...", "..."],
  "global_insight_text": "...",
  "domestic_insight_text": "...",
  "medclaim_action_text": "..."
}}
```"""


# ══════════════════════════════════════════
# drug_data 재구성
# ══════════════════════════════════════════

def _compute_status_text(approved: bool, date_str: str | None, brand: str = "") -> str:
    if approved:
        label = f"승인 완료 ({date_str})" if date_str else "승인 완료"
        if brand:
            label += f" ({brand})"
        return label
    return "미허가 (not_approved)"


def _compute_copay_text(source_data: dict) -> str:
    hira_status = source_data.get("hira_status", "")
    hira_price = source_data.get("hira_price")

    if hira_status == "reimbursed" and hira_price:
        return f"HIRA 등재 약제 (상한가 ₩{hira_price:,.0f}). 일반 급여 시 본인부담 약 ₩{hira_price * 0.3:,.0f} (30%)."
    if not source_data.get("mfds_approved", False):
        return "국내 미허가 -급여 적용 불가. 전액 환자 부담."
    return "국내 허가 완료, 급여 미등재. 비급여 처방 시 전액 환자 부담."


def reconstruct_drug_data(article_json: dict) -> str:
    """저장된 V4 기사 JSON → LLM 입력용 drug_data 문자열 재구성"""
    sd = article_json.get("source_data", {})
    v4f = article_json.get("_v4_facts", {})
    known_inns = article_json.get("_known_inns", [])

    drug_data = {
        "inn": article_json.get("inn", sd.get("inn", "")),
        "fda": {
            "approved": sd.get("fda_approved", False),
            "date": sd.get("fda_date"),
        },
        "ema": {
            "approved": sd.get("ema_approved", False),
            "date": sd.get("ema_date"),
        },
        "mfds": {
            "approved": sd.get("mfds_approved", False),
            "date": sd.get("mfds_date"),
            "brand_name": sd.get("mfds_brand_name", ""),
        },
        "hira": {
            "status": sd.get("hira_status"),
            "price": sd.get("hira_price"),
            "criteria": sd.get("hira_criteria", ""),
        },
        "cris": {
            "trial_count": sd.get("cris_trial_count", 0),
            "trials": [],
        },
        "analysis": {
            "domestic_status": sd.get("domestic_status", "unknown"),
            "global_score": sd.get("global_score", 0),
            "hot_issue_reasons": sd.get("analysis", {}).get("hot_issue_reasons", []),
        },
        "context": {
            "therapeutic_areas": sd.get("therapeutic_areas", []),
        },
        # V4 사전 계산 필드
        "d_day_text": v4f.get("d_day_text", ""),
        "fda_status_text": _compute_status_text(
            sd.get("fda_approved", False), sd.get("fda_date")),
        "ema_status_text": _compute_status_text(
            sd.get("ema_approved", False), sd.get("ema_date")),
        "mfds_status_text": _compute_status_text(
            sd.get("mfds_approved", False), sd.get("mfds_date"),
            sd.get("mfds_brand_name", "")),
        "copay_scenario_text": _compute_copay_text(sd),
        "valid_competitors": [
            {"inn": inn} for inn in known_inns
            if inn.upper() != article_json.get("inn", "").upper()
        ],
        "approval_summary_table": v4f.get("approval_summary_table", ""),
        "cost_scenario_table": v4f.get("cost_scenario_table", ""),
    }
    return json.dumps(drug_data, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════
# 누출 검사
# ══════════════════════════════════════════

def check_leakage(text: str) -> list[str]:
    """출력 텍스트에서 변수명 누출 검사"""
    found = []
    for var in LEAKED_VARS:
        if var in text:
            found.append(var)
    return found


def check_json_valid(text: str) -> tuple[bool, dict | None]:
    """JSON 파싱 가능 여부"""
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        clean = "\n".join(lines)
    try:
        parsed = json.loads(clean)
        return True, parsed
    except json.JSONDecodeError:
        return False, None


# ══════════════════════════════════════════
# LLM 호출
# ══════════════════════════════════════════

async def call_llm(
    client: AsyncOpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-5.2",
) -> tuple[str, float]:
    """OpenAI API 호출 → (응답 텍스트, 레이턴시 ms)"""
    t0 = time.time()
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_completion_tokens=4096,
    )
    latency = (time.time() - t0) * 1000
    return resp.choices[0].message.content, latency


# ══════════════════════════════════════════
# 메인 테스트 루프
# ══════════════════════════════════════════

async def run_ab_test(n_runs: int = 3, max_drugs: int = 5):
    """A/B 테스트 실행"""
    # API 키 로드
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # .env 파일에서 로드 시도
        env_file = HARNESS_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
        if not api_key:
            env_file2 = REGSCAN_DIR / ".env"
            if env_file2.exists():
                for line in env_file2.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found")
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key)

    # 약물 데이터 로드
    target_files = [
        "ZANIDATAMAB-HRII.json",
        "polatuzumab_vedotin.json",
        "ZOLBETUXIMAB.json",
        "IVOSIDENIB.json",
        "entrectinib.json",
    ]

    drugs = []
    for fname in target_files[:max_drugs]:
        fpath = BRIEFINGS_DIR / fname
        if not fpath.exists():
            print(f"  SKIP: {fname}")
            continue
        data = json.loads(fpath.read_text(encoding="utf-8"))
        if data.get("_pipeline_version") != "v4":
            print(f"  SKIP (not v4): {fname}")
            continue
        drugs.append(data)

    if not drugs:
        print("ERROR: V4 기사 JSON 없음")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  V4 프롬프트 A/B 테스트")
    print(f"  약물: {len(drugs)}종 × {n_runs}회 = {len(drugs) * n_runs}회/프롬프트")
    print(f"  총 LLM 호출: {len(drugs) * n_runs * 2}회")
    print(f"{'='*60}\n")

    # 프롬프트 조합
    system_a = SYSTEM_PROMPT_V4 + PATCH_A
    system_b = SYSTEM_PROMPT_V4 + PATCH_B

    results = {"prompt_a": [], "prompt_b": []}
    summary = {
        "prompt_a": {"total": 0, "leaked": 0, "json_valid": 0, "latencies": [], "leaked_vars": {}},
        "prompt_b": {"total": 0, "leaked": 0, "json_valid": 0, "latencies": [], "leaked_vars": {}},
    }

    for drug in drugs:
        inn = drug["inn"]
        drug_data_str = reconstruct_drug_data(drug)

        for run_idx in range(n_runs):
            user_prompt = USER_PROMPT_BASE.format(drug_data=drug_data_str)

            # ── Prompt A ──
            print(f"  [{inn}] Run {run_idx+1}/{n_runs} -Prompt A ...", end="", flush=True)
            try:
                text_a, lat_a = await call_llm(client, system_a, user_prompt)
                leaked_a = check_leakage(text_a)
                valid_a, parsed_a = check_json_valid(text_a)
                status_a = "LEAK" if leaked_a else ("OK" if valid_a else "JSON_ERR")
                print(f" {status_a} ({lat_a:.0f}ms)" + (f" {leaked_a}" if leaked_a else ""))

                summary["prompt_a"]["total"] += 1
                if leaked_a:
                    summary["prompt_a"]["leaked"] += 1
                    for v in leaked_a:
                        summary["prompt_a"]["leaked_vars"][v] = summary["prompt_a"]["leaked_vars"].get(v, 0) + 1
                if valid_a:
                    summary["prompt_a"]["json_valid"] += 1
                summary["prompt_a"]["latencies"].append(lat_a)

                results["prompt_a"].append({
                    "inn": inn, "run": run_idx + 1,
                    "leaked_vars": leaked_a, "json_valid": valid_a,
                    "latency_ms": round(lat_a), "output": text_a,
                })
            except Exception as e:
                print(f" ERROR: {e}")
                results["prompt_a"].append({
                    "inn": inn, "run": run_idx + 1,
                    "error": str(e),
                })

            # ── Prompt B ──
            print(f"  [{inn}] Run {run_idx+1}/{n_runs} -Prompt B ...", end="", flush=True)
            try:
                text_b, lat_b = await call_llm(client, system_b, user_prompt)
                leaked_b = check_leakage(text_b)
                valid_b, parsed_b = check_json_valid(text_b)
                status_b = "LEAK" if leaked_b else ("OK" if valid_b else "JSON_ERR")
                print(f" {status_b} ({lat_b:.0f}ms)" + (f" {leaked_b}" if leaked_b else ""))

                summary["prompt_b"]["total"] += 1
                if leaked_b:
                    summary["prompt_b"]["leaked"] += 1
                    for v in leaked_b:
                        summary["prompt_b"]["leaked_vars"][v] = summary["prompt_b"]["leaked_vars"].get(v, 0) + 1
                if valid_b:
                    summary["prompt_b"]["json_valid"] += 1
                summary["prompt_b"]["latencies"].append(lat_b)

                results["prompt_b"].append({
                    "inn": inn, "run": run_idx + 1,
                    "leaked_vars": leaked_b, "json_valid": valid_b,
                    "latency_ms": round(lat_b), "output": text_b,
                })
            except Exception as e:
                print(f" ERROR: {e}")
                results["prompt_b"].append({
                    "inn": inn, "run": run_idx + 1,
                    "error": str(e),
                })

            print()

    # ══════════════════════════════════════════
    # 결과 요약
    # ══════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  결과 요약")
    print(f"{'='*60}\n")

    for label, key in [("Prompt A (Positive Framing)", "prompt_a"),
                       ("Prompt B (Negative Rule)", "prompt_b")]:
        s = summary[key]
        total = s["total"]
        if total == 0:
            continue
        leak_rate = s["leaked"] / total * 100
        json_rate = s["json_valid"] / total * 100
        avg_lat = sum(s["latencies"]) / len(s["latencies"]) if s["latencies"] else 0

        print(f"  {label}")
        print(f"    총 실행: {total}회")
        print(f"    변수 누출: {s['leaked']}회 ({leak_rate:.0f}%)")
        print(f"    JSON 유효: {s['json_valid']}회 ({json_rate:.0f}%)")
        print(f"    평균 레이턴시: {avg_lat:.0f}ms")
        if s["leaked_vars"]:
            print(f"    누출 변수별:")
            for v, cnt in sorted(s["leaked_vars"].items(), key=lambda x: -x[1]):
                print(f"      {v}: {cnt}회")
        print()

    # ── 승자 판정 ──
    leak_a = summary["prompt_a"]["leaked"]
    leak_b = summary["prompt_b"]["leaked"]
    total_a = summary["prompt_a"]["total"]
    total_b = summary["prompt_b"]["total"]

    print(f"  {'─'*40}")
    if total_a > 0 and total_b > 0:
        rate_a = leak_a / total_a * 100
        rate_b = leak_b / total_b * 100
        if rate_a < rate_b:
            print(f"  WINNER: Prompt A (누출 {rate_a:.0f}% vs {rate_b:.0f}%)")
        elif rate_b < rate_a:
            print(f"  WINNER: Prompt B (누출 {rate_b:.0f}% vs {rate_a:.0f}%)")
        else:
            print(f"  DRAW: 누출률 동일 ({rate_a:.0f}%)")
    print()

    # ── 파일 저장 ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 전체 결과
    result_path = OUTPUT_DIR / f"ab_results_{ts}.json"
    result_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  상세 결과: {result_path}")

    # 요약
    summary_path = OUTPUT_DIR / f"ab_summary_{ts}.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  요약: {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="V4 프롬프트 A/B 테스트")
    parser.add_argument("--runs", type=int, default=3, help="약물당 반복 횟수 (기본 3)")
    parser.add_argument("--drugs", type=int, default=5, help="테스트 약물 수 (기본 5)")
    args = parser.parse_args()

    asyncio.run(run_ab_test(n_runs=args.runs, max_drugs=args.drugs))


if __name__ == "__main__":
    main()
