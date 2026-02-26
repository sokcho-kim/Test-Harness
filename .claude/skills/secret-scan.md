---
name: secret-scan
description: 시크릿/API키 유출 스캔 및 pre-commit hook 관리
user_invocable: true
---

# Secret Scan 스킬

시크릿/API 키 유출을 검사하고 pre-commit hook을 관리합니다.

## 실행 시 수행할 작업

### 1. 전체 레포 시크릿 스캔
아래 패턴으로 전체 코드베이스를 스캔합니다:
- Google API Key: `AIza[0-9A-Za-z_-]{35}`
- AWS Access Key: `AKIA[0-9A-Z]{16}`
- OpenAI Key: `sk-[a-zA-Z0-9]{20,}`
- Anthropic Key: `sk-ant-[a-zA-Z0-9_-]{20,}`
- Together AI Key: `tgp_v[0-9]_[a-zA-Z0-9]{20,}`
- GitHub Token: `gh[pousr]_[A-Za-z0-9_]{36,}`
- Slack Token: `xox[baprs]-[0-9A-Za-z-]{10,}`
- 일반 시크릿: `api_key`, `secret`, `password`, `token` 등에 할당된 값

스캔 대상에서 제외: `.git/`, `node_modules/`, `*.lock`, 바이너리 파일

### 2. pre-commit hook 상태 확인
- `.git/hooks/pre-commit` 파일 존재 여부 확인
- 실행 권한 확인
- 없으면 자동 생성 제안

### 3. 결과 리포트
- 발견된 시크릿 위치와 패턴 종류 출력
- 조치 방법 안내 (제거, .gitignore 추가, 환경변수 전환 등)

## 사용법
```
/secret-scan
```
