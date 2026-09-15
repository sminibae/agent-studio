# 01 프로젝트 골격

## 구현 결과

프로젝트 골격의 범위를 완료했다. Python 3.13.15, Node.js 24.21.0, pnpm 10.33.0,
uv 0.12.14와 PostgreSQL 18을 기준으로 lockfile과 CI를 구성했다.

- FastAPI liveness/readiness, request ID, JSON 오류와 구조화 로그
- `app_user` migration, proxy identity 경계와 UUIDv7 owner provisioning
- Next.js shell, OpenAPI 생성 client, API/현재 사용자 상태 표시
- `make install/check/test-integration/test-e2e`와 GitHub Actions

실제 Google OIDC/OAuth2 Proxy 배포 검증은 운영 단계에 남아 있다. 다음 구현은
Agent SDK 호환성과 Python 실행 격리 spike다.

## 목표

첫 기능 구현이 프런트엔드, API, PostgreSQL을 같은 계약으로 통과할 수 있는
개발 기반을 만든다. 이 단계는 제품 전체 스키마나 Agent 실행기를 만들지 않는다.

완료 시 브라우저에서 서비스 상태와 현재 사용자 정보를 조회하고, 같은 요청을
FastAPI와 실제 PostgreSQL까지 추적할 수 있어야 한다.

## 범위

- `backend/`: FastAPI, SQLAlchemy, Alembic, 애플리케이션 설정과 테스트 골격
- `frontend/`: Next.js App Router, TypeScript strict, 기본 내비게이션 shell
- PostgreSQL 개발 서비스와 최초 `app_user` migration
- `/api/v1/health`와 인증이 필요한 `/api/v1/me`
- 신뢰된 proxy identity를 application의 owner context로 변환하는 경계
- OpenAPI 기반 TypeScript client 생성 계약
- `make` 개발 명령, lint/typecheck/test, CI

첫 로컬 개발에서는 명시적인 development identity adapter를 사용할 수 있다.
production 설정은 브라우저가 직접 보낸 identity header를 신뢰하지 않으며,
proxy와 API 사이의 credential이 없거나 잘못되면 요청을 거부해야 한다.

## 구현 전에 고정할 기준

- Python 3.13 계열과 Node.js 24 계열을 첫 runtime 기준으로 사용한다.
- Python 의존성은 `uv.lock`, JavaScript 의존성은 `pnpm-lock.yaml`로 고정한다.
- PostgreSQL major version은 로컬 Compose와 CI에서 동일하게 사용한다.
- HTTP API는 `/api/v1`, 브라우저 접근은 같은 origin의 `/api` 경로를 사용한다.
- UUID 생성 라이브러리는 Python 3.13에서 UUIDv7을 제공하지 않으므로 검증 후
  선택한다. 골격에서는 인증 공급자의 `(issuer, subject)` 유일성을 먼저 보장한다.

정확한 패치 버전은 lockfile을 생성하는 시점에 실제 설치와 테스트로 검증한다.

## 작은 구현 단위

1. 저장소 공통 설정과 backend 패키지, FastAPI health endpoint를 만든다.
2. SQLAlchemy/Alembic과 `app_user` migration, DB readiness를 연결한다.
3. 인증 transport와 owner context, `/api/v1/me`를 테스트부터 구현한다.
4. Next.js shell과 상태/사용자 조회를 생성 client로 연결한다.
5. Compose, Makefile, CI와 전체 검증 명령을 완성한다.

각 단위는 약 250 changed lines를 목표로 하고 1,000 changed lines를 넘지 않는
커밋으로 남긴다. 자동 생성 lockfile과 생성 client는 수동 코드와 구분해 보고한다.
병렬 브랜치를 병합할 때는 `--no-ff`를 사용하고 squash하지 않는다.

## 완료 확인

- 빈 환경에서 lockfile 기반 설치와 migration을 수행할 수 있다.
- API liveness와 PostgreSQL readiness가 서로 다른 실패를 표현한다.
- 인증되지 않은 `/api/v1/me` 요청은 JSON 401을 반환한다.
- 개발 identity로 조회한 사용자는 `(issuer, subject)`에 따라 생성 또는 조회된다.
- 프런트 화면에서 API/DB 상태와 현재 사용자를 확인할 수 있다.
- `make lint`, `make typecheck`, `make test`, `make test-integration`, frontend build가
  로컬 또는 CI에서 통과한다.
- production 설정에서 신뢰 정보 누락, identity header 위조, 다른 owner 조회가
  거부되는 테스트가 있다.

## 이번 단계에서 제외

- 전체 Definition/Setup/Experiment 스키마
- Agent SDK, worker queue, Trace, Judge, Analytics
- OAuth2 Proxy와 실제 Google OIDC 설정
- Python 자산 Git 저장과 격리 실행

다음 단계에서는 Agent SDK compatibility와 Python 실행 격리를 각각 작은
spike로 검증한 뒤 자산/Setup 수직 기능을 시작한다.

## 참고 문서

- [설계 기준](../docs/decisions.md)
- [아키텍처](../docs/architecture.md)
- [데이터 모델](../docs/data-model.md)
- [엔지니어링](../docs/engineering.md)
- [운영](../docs/operations.md)
