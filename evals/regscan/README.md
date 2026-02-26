# RegScan Prompt Evaluation

promptfoo 기반 RegScan V4 프롬프트 품질 평가 시스템.

## 디렉터리 구조

```
evals/regscan/
├── promptfooconfig.yaml   # 메인 설정
├── prompts/               # 프롬프트 버전 파일
│   ├── v4.0_system.txt    # V4 시스템 프롬프트
│   ├── v4.0_user.txt      # V4 유저 프롬프트 (브리핑 리포트)
│   └── _meta.json         # 추출 메타데이터
├── datasets/
│   └── drug_samples.json  # 15종 약물 테스트 케이스
├── assertions/
│   └── regscan_quality.js # 커스텀 품질 체크 (12개 메트릭)
└── outputs/               # 평가 결과 (Git 추적)
```

## 실행 방법

### 1. 프롬프트 변경 시 추출

```bash
cd C:\Jimin\Test-Harness
python scripts/export_regscan_prompts.py --version v4.1
```

동일 내용이면 자동 스킵 (해시 비교).

### 2. 평가 실행

```bash
cd evals/regscan
npx promptfoo eval
```

또는 루트에서:

```bash
npm run eval:regscan
```

### 3. 대시보드 확인

```bash
npx promptfoo view    # → localhost:15500
```

또는:

```bash
npm run eval:regscan:view
```

### 4. 결과 커밋

```bash
git add outputs/
git commit -m "eval: v4.1 프롬프트 평가 결과"
```

## 품질 메트릭 (12개)

| # | 메트릭 | 기준 | 소스 |
|---|--------|------|------|
| 1 | is-json | JSON 파싱 가능 | 내장 |
| 2 | 금지 표현 | 16개 금지어 미포함 | compare_articles.py |
| 3 | 변수명 누출 | 12개 변수명 미포함 | test_v4_prompt_ab.py |
| 4 | 숫자 훅 | headline/첫문장에 숫자 | compare_articles.py |
| 5 | MOA 연쇄 | → 패턴 2회 이상 | compare_articles.py |
| 6 | 한계점 서술 | 다만/한계/CI/p-value | compare_articles.py |
| 7 | 반복 문구 | 6개 상투구 1회 이하 | compare_articles.py |
| 8-12 | 섹션 글자수 | headline/subtitle/insight 범위 | 경험적 기준 |
| 13 | key_points | 정확히 4개 | 프롬프트 스펙 |
| 14 | HTML 태그 | 태그 없음 | 프롬프트 규칙 |
| 15-17 | 불릿 포함 | insight 텍스트에 마크다운 불릿 | 프롬프트 스펙 |

## 테스트 약물 (15종)

| 카테고리 | 약물 | 특징 |
|----------|------|------|
| 미허가 (oncology) | Zanidatamab-hrii, Polatuzumab Vedotin, Zolbetuximab, Ivosidenib | FDA+EMA 승인, 국내 미허가 |
| 급여약 (oncology) | Entrectinib, Blinatumomab, Daratumumab, Lenvatinib | HIRA 등재, 가격 다양 |
| 급여약 (metabolic) | Semaglutide | 비종양 급여 |
| 다적응증 | Cabozantinib | oncology+metabolic |
| 희귀질환 | ECULIZUMAB-AAGH, MIGALASTAT | rare_disease |
| 심혈관 | Sotatercept-csrk | cardiovascular |
| 대사 | DULAGLUTIDE | metabolic |
| 면역 | SPESOLIMAB-SBZO | immunology |

## 데이터셋 갱신

```bash
python scripts/generate_dataset.py
```

RegScan output/briefings/ 스냅샷에서 15종 약물을 추출하여 drug_samples.json 갱신.

## 프롬프트 A/B 비교

새 프롬프트 버전을 추가하려면:

1. `export_regscan_prompts.py`로 새 버전 추출
2. `promptfooconfig.yaml`의 `prompts` 섹션에 새 버전 추가:

```yaml
prompts:
  - label: "V4.0"
    raw:
      - role: system
        content: "file://prompts/v4.0_system.txt"
      - role: user
        content: "file://prompts/v4.0_user.txt"
  - label: "V4.1"
    raw:
      - role: system
        content: "file://prompts/v4.1_system.txt"
      - role: user
        content: "file://prompts/v4.1_user.txt"
```

3. `npx promptfoo eval` → 대시보드에서 버전별 비교 확인
