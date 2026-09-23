# Architecture

제품·기술 구조와 구현 전 확인 항목은 [decisions.md](decisions.md)를 따른다.

## 구조의 목표

프런트엔드·HTTP API·worker·PostgreSQL로 실행 가능한 서비스를 만든다. 핵심 규칙은 HTTP, ORM, 모델 SDK 없이 실행하고 테스트할 수 있어야 한다. 도메인별 변경이 다른 영역으로 무분별하게 번지지 않게 한다.

**구조는 modular monolith다.** 백엔드 코드는 한 애플리케이션으로 관리하고 API와 worker는 같은 코드를 사용하는 별도 프로세스로 실행한다. 모듈을 나눴다는 이유만으로 네트워크 서비스나 별도 DB를 만들지 않는다.

## 방법론을 적용하는 위치

| 방법 | 이 프로젝트에서 적용하는 것 | 검증 방법 |
| --- | --- | --- |
| Clean Architecture | 바깥의 기술이 안쪽의 규칙에 의존 | import 경계 검사 |
| Hexagonal Architecture | 실제 I/O 경계를 port로 정의하고 adapter로 연결 | DB/모델 없이 유스케이스 테스트 |
| Domain-Driven Design | 용어, 모듈 책임, aggregate, 불변식 | 도메인 사례와 불변식 테스트 |
| Test-Driven Development | 규칙의 실패 예시를 먼저 작성하고 작은 구현 뒤 정리 | engineering의 개발 순서와 인수 시나리오 |

여기서 port는 현재 필요한 DB·모델·도구 등과 대화하는 계약이다. 구현체가 하나여도 규칙을 I/O에서 분리할 필요가 있으면 만든다. 단순 계산 함수마다 interface를 만들거나 모든 클래스에 대응 interface를 만들지는 않는다.

이 원칙은 [Clean Architecture 원문](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)의 안쪽으로 향하는 소스 의존성과 [Hexagonal Architecture 원문](https://alistair.cockburn.us/hexagonal-architecture)의 외부 장치에서 독립된 애플리케이션을 따른다. 아래에 애플리케이션 모듈과 기술 구성을 정의한다.

## 의존 방향과 호출 방향

소스 코드의 허용 의존성:

```text
Driving adapters (HTTP, worker) → Application → Domain
Driven adapters (PostgreSQL, model SDK, tools) → Application ports / Domain types
Composition root → 각 계층의 구체 구현 (객체 조립만 담당)
```

실행 시 Application이 port를 통해 PostgreSQL adapter를 호출할 수 있다. 그렇다고 Application이 SQLAlchemy 구현을 import하는 것은 아니다.

- Domain: 엔티티·값 객체·상태 판정·점수 계산. 표준 라이브러리와 같은 모듈의 도메인 타입을 사용한다.
- Application: command/query 유스케이스, 입출력 DTO, port, 트랜잭션 범위. FastAPI·SQLAlchemy·provider SDK를 import하지 않는다.
- Adapters: HTTP/Pydantic 변환, SQLAlchemy, 모델 SDK, 도구 연결. domain/application 계약을 구현한다.
- Bootstrap: 환경 설정과 의존성 조립. 비즈니스 판단을 넣지 않는다.

## 모듈과 저장소 구조

[domain-model.md](domain-model.md)의 책임 경계를 따라 먼저 기능별 모듈을 나눈다.

```text
backend/
  src/agent_studio/
    assets/           # Definition, Version, Setup
      domain/
      application/    # 유스케이스, DTO, ports
      adapters/       # HTTP, persistence 등 필요한 것만
    experiments/      # Experiment, Batch, Run, Case Run, Trace
      domain/
      application/
      adapters/
    evaluation/       # Evaluation 작업, Judge, 항목 결과
      domain/
      application/
      adapters/
    analytics/        # 비교 가능성, 점수, Scope
      domain/
      application/
      adapters/       # 분석용 read queries
    platform/         # DB 연결, 공통 모델 transport 등 기술 지원
    bootstrap/        # API/worker 진입점, 설정, 의존성 조립
  migrations/
  tests/
    unit/
    integration/
    contract/
frontend/
  src/
    app/              # router, providers, 앱 조립
    features/
      setups/
      experiments/
      analytics/
    components/ui/    # 도메인을 모르는 기본 UI
    api/generated/    # OpenAPI에서 생성하는 계약
    api/              # transport와 오류 처리
  tests/
e2e/
```

폴더는 실제 코드가 생길 때 만든다. 다른 모듈의 내부 ORM/repository를 호출하지 않는다. 다른 모듈의 공개 application 계약이나 명시적 read port를 사용한다. Analytics의 조회 adapter는 문서화된 여러 테이블을 조인할 수 있지만 다른 모듈을 수정할 수 없다.

`shared`에 모든 모델을 모으지 않는다. 공통 기반 클래스·generic repository·도메인 이벤트 버스는 반복이 실제로 생겼을 때 필요를 판단한다. Aggregate는 테이블마다 기계적으로 만들지 않는다.

## 트랜잭션과 읽기

- Application이 Unit of Work port를 통해 트랜잭션을 소유한다. repository는 commit하지 않는다.
- Definition Version 발행, Setup 생성, 실행 요청 등록, 실행 결과 확정은 각자 짧은 트랜잭션이다.
- Git 저장과 DB Version 발행은 서로 다른 저장 경계다. 일반 폴더의 원문을 commit하고 보존 참조를 만든 뒤 DB에 저장소·commit·경로를 등록한다. Git 저장소와 사용자별 Python 실행기는 application port/adapter로 연결하며, Git I/O나 코드 실행 중 DB 트랜잭션을 유지하지 않는다. 동시 발행과 실패 복구는 [python-assets.md](python-assets.md)를 따른다.
- **모델/도구 네트워크 호출을 기다리며 DB 트랜잭션을 열어 두지 않는다.** 점유·호출·결과 저장을 구분한다.
- 실행 등록 시 Batch, Runs, Case Runs, Evaluation 작업을 함께 생성한다. 행 수 상한으로 트랜잭션 크기를 제한한다.
- 목록·Analytics는 query port로 필요한 read DTO를 조회한다. 읽기 때문에 거대한 aggregate를 복원하지 않는다.
- 점수/비교 정책은 Domain의 순수 함수가 담당한다. Application은 데이터 선택과 계산을 조율하고 SQL adapter는 정의된 집계 입력을 효율적으로 읽는다.
- ORM 모델·Pydantic API 스키마·도메인 객체를 구분하되 의미 없는 동일 구조 복사 계층은 추가하지 않는다.

## 기술 선택의 상태

| 영역 | 첫 구현 기본안 | 이유/검증 |
| --- | --- | --- |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic | Python 도구와 실행/평가 중심 |
| Frontend | TypeScript, Next.js App Router, React, shadcn/ui, Tailwind | 사용자에게 익숙한 Next.js 유지 |
| DB | PostgreSQL | queue·FK·transaction·JSONB |
| Agent runtime | OpenAI Agents SDK adapter | function_tool 등록, 첫 provider OpenAI; compatibility spike 필요 |
| 사용자 실행 환경 | owner별 이름 붙인 `.venv`·`.env`, 별도 실행 프로세스 | 서비스 환경과 분리; [runtime-environments.md](runtime-environments.md) 검증 필요 |
| 작업 실행 | 별도 worker + PostgreSQL queue | 작은 초기 규모, lease/fencing 계약 포함 |
| 개발 도구 | uv, pnpm, Makefile, Docker Compose | 골격 단계에서 실제 명령과 버전 검증 |

Next.js는 route/layout shell과 화면 구성에 사용하고 편집·폴링·분석 상호작용은 client components로 둔다. 데이터 읽기/변경은 생성 API client를 통해 동일 origin의 FastAPI `/api`로 통일한다. Server Actions에 비즈니스 API를 복제하지 않는다. 프런트는 DB에 직접 접근하지 않는다.

Server/Client component의 역할은 [Next.js 공식 문서](https://nextjs.org/docs/app/getting-started/server-and-client-components)를 따른다. 이 제품에서 SSR은 필수 조건이 아니다.

## API 계약 기본안

`/api/v1` 아래 REST JSON을 사용한다. API/worker는 같은 application 유스케이스를 호출한다. 목록은 안정적인 `(created_at, id)` 커서와 `items`, `next_cursor`를 제공한다. 큰 Trace는 `after_seq`, `limit`으로 읽는다. 페이지 크기와 실행 생성 상한은 API 스키마로 공개한다.

| 요청 | 의미 | 응답 |
| --- | --- | --- |
| `POST /venvs` | owner 범위에서 이름 붙인 가상환경 생성 | 202 + 환경 ID/설치 상태 |
| `POST /venvs/{id}/packages` | 선택 가상환경에 패키지 설치 작업 요청 | 202 + 작업 ID |
| `POST /env-files` / `PUT /env-files/{id}/entries` | owner dotenv 생성·키 갱신 | 파일 ID / 새 revision ID; 비밀 값은 응답에 없음 |
| `POST /execution-environments` | venv와 dotenv 이름/ID를 묶어 선택 가능한 환경 생성 | 201 + 환경 ID |
| `POST /agent-setups` | 검증된 Version 참조로 스냅샷 생성 | 201 + Setup |
| `POST /evaluation-setups` | Dataset/Golden/Rubric 정합성 검증 후 생성 | 201 + Setup |
| `POST /experiments` | 변경 불가능한 실험 구성 생성 | 201 + Experiment |
| `POST /experiments/{id}/execution-batches` | Repeats 전체 실행 예약 | 202 + Batch ID, Run IDs, 조회 URL |
| `GET /execution-batches/{id}` | 실행 요청 단위 진행 조회 | 실행/평가 상태별 개수 |
| `POST /runs/{id}/cancel` | 취소 의도 등록 | 진행 중이면 202, 이미 종료했으면 200 + 현재 상태 |
| `GET /case-runs/{id}` | 실행 결과와 평가 상태 조회 | Case Run + Evaluation 요약 |
| `GET /case-runs/{id}/trace` | Trace 일부 조회 | seq 순 events + next cursor |
| `POST /analytics/query` | 명시적 실행 범위의 분석 | compatibility, coverage, metrics, exclusions |

실행 생성은 `Idempotency-Key`를 요구한다. 키의 범위는 `(experiment_id, key)`다. 동일 키·동일 요청은 기존 Batch를 반환하고 동일 키·다른 요청은 409다. 키 비교는 canonical request hash로 한다. 실행 등록의 validation과 원자성은 [execution.md](execution.md)를 따른다.

오류는 `{ "error": { "type": "...", "message": "...", "details": {}, "request_id": "..." } }`로 통일한다. 404는 리소스 없음, 409는 충돌, 422는 잘못된 입력/불변식 위반, 503은 일시적 서비스 불가다. 내부 stack trace와 자격 증명은 HTTP 오류에 포함하지 않는다.

OpenAPI에서 TypeScript 타입/클라이언트를 생성하는 것을 기본안으로 삼는다. CI에서 생성물 drift를 검사한다. 프런트는 임의의 string 상태나 수동 복제한 API 타입을 유지하지 않는다.

## 비동기 실행과 진행 표시

- 폴링 기본안: 활성 화면에서 약 2초 간격, 백그라운드 탭은 완화, 종료 후 정지. 오류 시 backoff.
- agent 실행과 evaluation 진행을 따로 반환한다. Agent 완료를 평가 완료로 표시하지 않는다.
- PostgreSQL `SKIP LOCKED`는 작업 선점에 사용한다. 실제 신뢰성은 lease·fencing·멱등 저장·복구 계약으로 보장한다.
- [PostgreSQL SELECT 문서](https://www.postgresql.org/docs/current/sql-select.html)는 `SKIP LOCKED`가 큐 형태 소비에 사용 가능함을 설명한다. 이것만으로 외부 모델·도구 호출의 exactly-once를 보장하지 않는다.
- API는 실행을 DB에 등록하고 응답한다. 요청 프로세스의 background task에 장시간 작업을 맡기지 않는다.
- Batch 등록과 worker 점유는 같은 DB scheduler 행으로 상한 판단을 직렬화한다. owner별 순환 선택과 컨테이너 정리 전 슬롯 보유는 [scheduling.md](scheduling.md)를 따른다.

## 모델·도구 경계

Application 소유 port의 예는 `AgentRuntime`, Judge용 `ModelGateway`, `UnitOfWork`, `AnalysisReader`다. SDK 내부에서 끝나는 도구 왕복을 application에 중복 구현하지 않으며 사용자 Tool 원문 로딩·객체 검증·격리 호출 계약은 runtime adapter 안에서 연결한다. 구체 메서드는 실제 유스케이스 테스트에서 필요한 계약으로 정한다.
worker는 사용자 환경 ID를 해석해 선택한 `.venv`의 Python으로 실행 프로세스를 시작한다. 선택한 `.env`만 그 프로세스에 주입하고 서비스 설정·DB credential은 전달하지 않는다. API와 worker 자신의 Python 환경은 바뀌지 않는다.

모델 adapter는 provider 응답을 명시적인 메시지·도구 호출·사용량·오류 타입으로 변환한다. Agent와 Judge는 transport를 공유할 수 있지만 prompt 생성·결과 검증·상태 전이는 별도 책임이다. SDK 자동 retry는 끄거나 한 층으로 통합하여 실제 시도 수를 추적한다.

도구 구현 참조는 이름만으로 충분하지 않다. 사용자 Tool Version의 Git 원문,
고정 venv revision, 입출력 스키마·timeout·비밀 참조·외부 데이터 의존성을 기록할
계약이 필요하다. 사용자가 작성한 decorator 기반 Python 함수의 `tool` 변수를
읽으며 첫 함수가 날씨 HTTP API를 호출한다. 구체 계약과 export 대비는
[agent-runtime.md](agent-runtime.md)에 있다.

## 인증과 소유권 경계

브라우저 로그인 뒤에도 모든 리소스는 사용자 개인 소유다. 첫 배포에는 한 계정만 허용한다. Application command/query에는 인증으로 결정한 owner context를 전달한다. 클라이언트가 임의 owner를 지정할 수 없다.

Repository/query port는 owner 범위를 요구하며 Setup/Golden/Batch/Trace를 교차 소유자로 연결하지 않는다. worker는 Batch owner를 이어받고 analytics도 입력 Run 모두의 owner를 검증한다. DB composite FK와 실제 두 사용자 격리 테스트로 뒷받침한다.

서버·인증 프록시·TLS·비밀·백업은 [operations.md](operations.md)를 따른다. 사용자 provider key는 owner별 dotenv 파일에 두며 Definition/Setup/Trace에는 환경 참조와 실행 시 revision만 저장한다.
