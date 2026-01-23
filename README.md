# Test Harness

LLM 프롬프트 최적화 및 워크플로우 검증을 위한 통합 테스트베드

## 주요 기능

- **Multi-Prompt Side-by-Side**: 여러 프롬프트/모델 답변 비교
- **자동 검사기 (Assertions)**: JSON 검증, 금지어 체크, 필수 포함어 체크
- **다중 모델 테스트**: Together AI, OpenAI, 사내 모델 동시 테스트
- **회귀 테스트**: 프롬프트 변경 시 기존 테스트 통과 여부 확인
- **Report Exporter**: HTML/PDF 보고서 출력

## 기술 스택

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: Next.js 14, React, TailwindCSS
- **Evaluation**: promptfoo
- **Database**: SQLite

## 프로젝트 구조

```
test-harness/
├── services/
│   ├── api/                    # FastAPI 백엔드 (포트 8080)
│   │   └── src/test_harness_api/
│   │       ├── main.py         # FastAPI 앱 엔트리포인트
│   │       ├── routers/        # API 라우터 (tests, prompts, datasets, evaluations)
│   │       ├── services/       # 비즈니스 로직
│   │       └── dependencies.py # 의존성 주입
│   └── web/                    # Next.js 대시보드 (포트 3000)
│       └── src/
│           ├── app/            # 페이지 (prompts, datasets, tests, compare)
│           ├── components/     # UI 컴포넌트
│           └── lib/            # API 클라이언트
├── shared/                     # 공유 코드 (API와 스크립트에서 공유)
│   ├── core/                   # 데이터 모델, 비즈니스 로직
│   │   ├── models.py           # Pydantic 모델
│   │   ├── mapping.py          # 필드 매핑 로직
│   │   └── promptfoo_runner.py # promptfoo 실행기
│   ├── adapters/               # LLM API 어댑터
│   │   ├── base.py             # 어댑터 베이스 클래스
│   │   ├── openai_compat.py    # OpenAI 호환 어댑터
│   │   └── together_ai.py      # Together AI 어댑터
│   └── database/               # SQLite 저장소
│       └── database.py         # DB 연결 및 CRUD
├── configs/
│   ├── models.yaml             # LLM 모델 설정 (Together, OpenAI, 사내)
│   └── prompts/                # 프롬프트 템플릿
├── data/
│   ├── test_harness.db         # SQLite 데이터베이스
│   ├── test_cases/             # 테스트 케이스 파일
│   └── goldset.example.json    # 골드셋 예시
├── docs/                       # 문서
│   ├── architecture-v2.md      # 아키텍처 설계
│   ├── roadmap-v2.md           # 로드맵
│   └── plan.md                 # 원본 계획
├── scripts/                    # 유틸리티 스크립트
│   └── import_ner_data.py      # NER 데이터 임포트
├── vendor/                     # 외주사 원본 코드 (Read-only)
├── docker-compose.yml          # Docker 구성
├── package.json                # promptfoo 의존성
└── .env.example                # 환경 변수 템플릿
```

## 시작하기

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 API 키 입력:
```env
TOGETHER_API_KEY=your_together_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 2. 실행 방법

#### Docker로 실행 (권장)

```bash
docker-compose up -d
```

- API: http://localhost:8080
- Web UI: http://localhost:3000

#### 로컬 개발 환경

**터미널 1: API 서버**
```bash
# 의존성 설치 (최초 1회)
cd services/api
pip install -e .

# API 서버 실행 (프로젝트 루트에서)
cd ../..
PYTHONPATH=. python -m uvicorn test_harness_api.main:app --reload --port 8080 --app-dir services/api/src
```

**터미널 2: Web UI**
```bash
cd services/web
npm install    # 최초 1회
npm run dev
```

- API: http://localhost:8080
- API Docs (Swagger): http://localhost:8080/docs
- Web UI: http://localhost:3000

### 3. promptfoo CLI (선택)

```bash
npm install          # 루트에서 promptfoo 설치
npm run eval         # 평가 실행
npm run eval:view    # 결과 뷰어
```

## API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /` | API 상태 확인 |
| `GET /health` | 헬스 체크 |
| `GET /docs` | Swagger UI |
| **Prompts** | |
| `GET /prompts` | 프롬프트 목록 |
| `POST /prompts` | 프롬프트 생성 |
| `GET /prompts/{id}` | 프롬프트 상세 |
| **Datasets** | |
| `GET /datasets` | 데이터셋 목록 |
| `POST /datasets` | 데이터셋 생성 |
| `GET /datasets/{id}` | 데이터셋 상세 |
| **Tests** | |
| `GET /tests` | 테스트 목록 |
| `POST /tests` | 테스트 생성/실행 |
| `GET /tests/{id}` | 테스트 결과 |
| **Evaluations** | |
| `GET /evaluations` | 평가 목록 |
| `POST /evaluations/run` | 평가 실행 |

## 문서

- [아키텍처 설계](docs/architecture-v2.md)
- [로드맵](docs/roadmap-v2.md)
- [원본 계획](docs/plan.md)

## 라이선스

MIT
