# 프로젝트 명: Test Harness

**부제**: LLM 프롬프트 최적화 및 워크플로우 검증을 위한 통합 테스트베드

## 1. 배경 및 목적

* **배경**: 모델 변경 후 기존 프롬프트의 오버피팅 문제로 답변 품질 저하 및 추론 과정 노출 현상 발생.
* **현황**: 외주사 코드의 구조적 난잡함(Zip 형태 인계) 및 사내 GPU 자원 점유 최적화 필요.
* **목적**:
1. Together AI 등 외부 API를 활용한 신속한 프롬프트 최적화.
2. `promptfoo` 기반의 객관적 성능 지표(Metric) 확보.
3. 비개발자(도메인 전문가, 고객사 담당자)도 테스트하고 결과를 공유할 수 있는 웹 인터페이스 제공.



## 2. 기술 스택 (Tech Stack)

* **Frontend/UI**: Streamlit (빠른 프로토타이핑 및 대시보드 구축)
* **Evaluation**: Promptfoo (프롬프트 비교 매트릭스 및 단언문 검증)
* **LLM Engine**: Together AI (OSS 모델 API), 사내 서빙 모델 (OpenAI 호환 API)
* **Language**: Python 3.9+
* **Storage**: SQLite (테스트 이력 저장용) 또는 Local File System

## 3. 시스템 아키텍처

1. **Wrapper Layer**: 외주사의 원본 코드(Zip)를 수정하지 않고 환경 변수 주입을 통해 API 엔드포인트만 가로채서 실행.
2. **Inference Layer**: Together AI API를 'Gold Standard'로 사용하여 내부 모델 성능과 비교.
3. **Evaluation Layer**: `promptfoo`를 백엔드에서 호출하여 JSON 형식 준수 여부, 금지어 포함 여부 등을 자동 검증.
4. **Presentation Layer**: Streamlit을 통해 테스트 결과를 시각화하고 릴라(경기도 담당자) 등 이해관계자에게 URL 공유.

## 4. 핵심 기능 (Features)

* **Multi-Prompt Side-by-Side**: 동일 질문에 대해 여러 프롬프트/모델의 답변을 나란히 비교.
* **RAG 인터셉터**: 질문에 대해 DB에서 가져온 Context(Chunk)가 적절한지 별도 로그 탭 제공.
* **자동 검사기 (Assertions)**:
* `not-contains`: "thinking process", "<thinking>" 등 추론 과정 포함 여부.
* `is-json`: 최종 결과물이 유효한 JSON 포맷인지 확인.
* `contains`: SQL 쿼리에 필수 테이블명이 포함되었는지 확인.


* **Report Exporter**: 테스트 결과를 HTML 또는 PDF 보고서 형태로 출력하여 납품 증빙 자료로 활용.

## 5. 디렉토리 구조

```text
test-harness/
├── app.py                # Streamlit 메인 실행 파일
├── core/
│   ├── engine.py         # Together AI / 사내 모델 API 호출 로직
│   └── evaluator.py      # promptfoo 실행 및 결과 파싱
├── vendor/               # 외주사 원본 코드 (Read-only)
├── configs/
│   ├── promptfooconfig.yaml  # promptfoo 설정 템플릿
│   └── prompts.json      # 관리 중인 프롬프트 리스트
├── data/
│   └── goldset.json      # 검증용 질문 및 정답셋
└── .env                  # API_KEY 및 환경 설정

```

## 6. 클로드(Claude) 협업을 위한 프롬프트 가이드

클로드에게 첫 세션을 시작할 때 아래와 같이 명령하세요.

> "나는 AI 엔지니어이고, 현재 경기도 의회 에이전트 프로젝트의 프롬프트 최적화를 위해 **'Test Harness'**라는 도구를 만들려고 해.
> **나의 핵심 요구사항:**
> 1. 외주사의 코드가 엉망이라 직접 수정하기 힘드니, 그 코드를 실행할 때 환경 변수만 바꿔서 Together AI API로 연동되게 만드는 'Wrapper' 스크립트가 필요해.
> 2. `promptfoo`를 파이썬에서 subprocess로 실행하고, 그 결과물인 JSON을 읽어서 Streamlit 화면에 이쁜 표로 보여줘야 해.
> 3. 비개발자도 쓸 수 있게 프롬프트를 웹 화면에서 수정하고 바로 '테스트 실행' 버튼을 누를 수 있는 UI를 짜줘.
> 
> 
> 먼저 프로젝트의 기본이 되는 `app.py` 구조부터 같이 잡아보자."

