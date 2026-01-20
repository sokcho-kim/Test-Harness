# Fastcampus 프롬프트 엔지니어링 A to Z 분석

> 분석일: 2026-01-09
> 원본: 강수진 (국내 공채1호 프롬프트 엔지니어)
> 총 13개 PDF, 687페이지

---

## 1. 자료 구성

| Part | 제목 | 페이지 | 핵심 키워드 |
|------|------|--------|------------|
| Intro | 프롬프트 엔지니어의 역할과 실무 이해 | 30 | 시스템1/2, Scaling Laws, 창발성 |
| Part 1 | 프롬프트 구조와 기능 탐구 | 65 | 프롬프트 유형, 구조 |
| Part 2 | 효과적인 프롬프트 분석 기법 | 92 | 분석 기법 |
| Part 3 | 목적 중심의 프롬프트 기획 전략 | 49 | 세그먼테이션, 연역/귀납 |
| Part 4 | 프롬프트 제작의 기초 (Ch1-4) | 207 | 핵심 원리, 방법론 |
| Part 5 | 프롬프트 제작 심화 | 135 | 고급 기법, 최적화 |
| Part 6 | 프롬프트 품질 관리 - 테스트 방법론 | 40 | 테스트 규칙, 루브릭 |
| Part 7 | 프롬프트 성능 평가 | 24 | 정량적/정성적 평가 |
| Part 8 | 프롬프트 기록과 버전 관리 | 16 | 버전 관리, 도구 |
| Part 9 | 생성형 AI 프롬프트 - 프로젝트 | 17 | 실전 프로젝트 |
| Part 10 | 프롬프트 엔지니어링의 현재와 미래 | 12 | 기법 흐름, 트렌드 |

---

## 2. 기존 학습 내용과 비교

### 이미 커버된 내용 (기존 guide/)

| 기존 가이드 | 커버 내용 | Fastcampus 대응 |
|------------|----------|----------------|
| 01-basics | 구성요소, Zero/Few-Shot, 파라미터 | Part 1, 4 일부 |
| 02-few-shot | Few-Shot 패턴, 라벨 공간 | Part 4 일부 |
| 03-chain-of-thought | CoT, Zero-shot CoT, Auto-CoT | Part 4 일부 |
| 04-llm-as-judge | 평가 패턴, 편향 | Part 7 일부 |
| 05-practical-design | NER, Entity Linking | 도메인 특화 (미포함) |

### 새로 배울 내용

| 우선순위 | 주제 | Fastcampus Part | 기존 커버리지 |
|---------|------|-----------------|--------------|
| ⭐⭐⭐ | 프롬프트 기획 전략 | Part 3 | 없음 |
| ⭐⭐⭐ | 테스트 방법론 | Part 6 | 없음 |
| ⭐⭐ | 버전 관리 | Part 8 | 없음 |
| ⭐ | 심화 이론 (창발성, Scaling Laws) | Intro | 없음 |

---

## 3. 새로 학습할 핵심 개념

### 3.1 프롬프트 기획 전략 (Part 3)

#### 사용자 세그먼테이션 4축

```
Turn      : 싱글턴 vs 멀티턴
Action    : 정보 검색 vs 다른 행위
Structure : 선호 구조 vs 비선호 구조
Stance    : 감정적 vs 비감정적
```

#### 세그먼트 분류표

| Stance | Turn | Info-Seeking | Other |
|--------|------|--------------|-------|
| - | Single | SI | SO |
| 만족 | Multi | MISP | MOSP |
| 불만족 | Multi | MISD | MOSD |
| 알수없음 | Multi | MISU | MOSU |

#### 기획 접근 방법

| 방식 | 프로세스 | 장점 | 단점 |
|------|---------|------|------|
| **연역적** | 가설 → 검증 | 빠름, 체계적 | 실제와 괴리 가능 |
| **귀납적** | 관찰 → 일반화 | 실제 반영 | 시간 소요, 편향 |

#### 핵심 이론

- **Nudge Theory**: 선택의 자유 유지하며 더 나은 선택 유도
- **Theory of Mind**: 타인의 정신 상태 추론 능력

#### 기획 실습 3종

1. **프롬프트 질문 생성기**: 멀티턴 유도
2. **프롬프트 자동 완성기**: 불완전한 프롬프트 보완
3. **시스템 프롬프트 개선**: 범용적 목적의 개선

---

### 3.2 테스트 방법론 (Part 6)

#### 프롬프트 테스트 9가지 규칙

1. 최소 **두 가지 버전**으로 작성
2. 버전은 **기능 이름**으로 (`systemprompt_v1`)
3. 기능 확장은 **세부 카테고리** 반영 (`FinancialAnalysis_Revenue_v1`)
4. 각 버전의 **목표와 기대 성능 문서화**
5. **작위적 문장 사용 금지** (실제 데이터 사용)
6. **테스트 데이터셋** 사용
7. 같은 테스트 **최소 10번 이상** 생성
8. **최소 3명**의 작업 관계자 참여
9. **다양한 모델 버전**으로 테스트

#### 테스트 데이터셋 요건

- 대표적이고 빈번한 실제 사용자 발화
- 다양하고 포괄적인 내용
- 예상치 못한 사항 포함
- 사용자 오류 패턴
- LLM 한계가 드러난 데이터

#### 질적 분석 3단계

```
1. 목적 확인
   - 핵심 단어/구문 추출
   - 문장 구성 분석 (명령어 vs 질문)

2. 구조 분석
   - 정보 흐름 논리성
   - 구조화 방식 (일반→구체)

3. 효율성 평가
   - 프롬프트 길이 적절성
   - 컨텍스트 충분/과도 여부
```

#### 프롬프트 테스트 루브릭 (5점 척도)

| 평가 항목 | 설명 |
|----------|------|
| 정확성 | 주제와 맞게 생성하는가 |
| 일관성 | 내용 흐름과 전개 방식 |
| 유용성 | 바로 사용 가능한가 |
| 문법/문체 | 자연스러운 언어 |
| 모델 대응 | 다양한 모델에서 작동 |

#### 정량적 테스트

1. **N번 생성** (N > 100)
2. **응답 패턴 분석**
3. **모델별 비교 테스트**

---

### 3.3 버전 관리 (Part 8)

#### 프롬프트 관리 도구

| 도구 | 특징 |
|------|------|
| **PromptLayer** | 버전 관리, 팀 협업, A/B 테스트 |
| **LangSmith** | LangChain 연동, Playground |
| **LangChain Hub** | 커뮤니티 프롬프트 공유 |
| **Anthropic Prompt Library** | Claude 최적화 프롬프트 |
| **Notion** | 커스텀 데이터베이스 |

#### Semantic Versioning 규칙

```
버전 형식: Major.Minor.Patch (예: 2.1.3)

규칙 1 - 주요 기능 변경: Major 증가 (1.0 → 2.0)
         예: 새 기능 추가, 메인 구조 변경, 토큰 수 변경

규칙 2 - 마이너 업데이트: Minor 증가 (1.0 → 1.1)
         예: 일부 수정, 성능 개선, 오류 수정

규칙 3 - 버그 수정: Patch 증가 (1.0.0 → 1.0.1)
         예: 오타, 출력 깨짐

규칙 4 - 피드백 반영: Minor 또는 Patch
         예: 사용자 피드백 기반 수정

규칙 5 - 주기적 검토: 기능 크기에 따라 결정
```

#### Notion 프롬프트 데이터베이스 스키마

| Property | Type | Description |
|----------|------|-------------|
| Name | Title | 프롬프트 이름 |
| Status | Select | Draft/In Progress/In Review/Done |
| Version | Number | 버전 번호 |
| Author | Person | 작성자 |
| Created at | Created Time | 생성 날짜 |
| Updated at | Last Edited | 수정 날짜 |
| Project | Multi-Select | 관련 프로젝트 |
| Change Log | Relation | 변경 로그 연결 |

---

### 3.4 심화 이론 (Intro)

#### 시스템 1/2 (다니엘 카너먼)

| 시스템 1 (빠른 사고) | 시스템 2 (느린 사고) |
|---------------------|---------------------|
| 직관적, 자동적 | 의식적, 논리적 |
| 감정적, 무의식적 | 분석적, 계산적 |
| 경험 기반 빠른 판단 | 복잡한 문제 해결 |

#### Semantics vs Pragmatics

- **mono-semanticity** (단일성): LLM이 잘함
- **multi-semanticity** (다의성): LLM이 못함
- 고맥락 언어(한국어)의 "눈치" vs 저맥락 언어(영어)의 "Assertive"

#### Scaling Laws (Kaplan, McCandish 2020)

- 모델 크기, 데이터 양, 연산량과 성능의 관계
- 프롬프트 고도화/최적화의 이론적 기반

#### 창발성 (Emergence)

> "양적 변화가 질적 변화를 불러옴" - Philip Anderson, 1972

- "많아지면 달라진다" (More is different)
- 모델 스케일 증가 시 예상치 못한 능력 출현

---

## 4. 반영 계획

### 폴더 구조 확장

```
_learning/guide/
├── 01-basics/           (기존)
├── 02-few-shot/         (기존)
├── 03-chain-of-thought/ (기존)
├── 04-llm-as-judge/     (기존)
├── 05-practical-design/ (기존)
├── 06-prompt-planning/  ← NEW: 기획 전략
│   └── notes.md
├── 07-testing/          ← NEW: 테스트 방법론
│   └── notes.md
└── 08-version-control/  ← NEW: 버전 관리
    └── notes.md
```

### 실습 연계

| 기존 자산 | 새로운 적용 |
|----------|------------|
| NER 프롬프트 v1~v4 | 테스트 루브릭 평가 |
| experiments/runs/ | Semantic Versioning 적용 |
| experiments/prompts/ | 프롬프트 문서화 템플릿 |

---

## 5. 참고 자료

### 논문/서적
- Kahneman, D. (2011). Thinking, Fast and Slow
- Kaplan, J. et al. (2020). Scaling Laws for Neural Language Models
- Anderson, P. (1972). More is Different
- Thaler, R. & Sunstein, C. (2008). Nudge

### 도구
- PromptLayer: https://promptlayer.com
- LangSmith: https://smith.langchain.com
- LangChain Hub: https://smith.langchain.com/hub
- Anthropic Prompt Library: https://docs.anthropic.com/claude/prompt-library
