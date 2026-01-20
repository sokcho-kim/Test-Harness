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
│   ├── api/          # FastAPI 백엔드 (포트 8080)
│   └── web/          # Next.js 대시보드 (포트 3000)
├── shared/           # 공유 코드
│   ├── core/         # 데이터 모델, 비즈니스 로직
│   ├── adapters/     # LLM API 어댑터
│   └── database/     # SQLite 저장소
├── vendor/           # 외주사 원본 코드 (Read-only)
├── configs/          # 설정 파일
└── data/             # 테스트 데이터
```

## 시작하기

### 환경 설정

```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력
```

### Docker로 실행

```bash
docker-compose up -d
```

### 로컬 개발

```bash
# API 서버
cd services/api
pip install -e .
uvicorn test_harness_api.main:app --reload --port 8080

# Web UI
cd services/web
npm install
npm run dev
```

## 문서

- [아키텍처 설계](docs/architecture-v2.md)
- [원본 계획](docs/plan.md)

## 라이선스

MIT
