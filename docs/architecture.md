# Architecture

이 문서는 기술 선택과 구조 규칙을 정의한다. 도메인 개념은 `docs/domain-model.md`, 실행 규칙은 `docs/execution.md`가 정본이다. 여기서는 해당 개념과 규칙을 코드에 어떻게 배치할지만 다룬다.

---

## 기술 스택

### Frontend

- Next.js (App Router)
- TypeScript
- React
- shadcn/ui
- Tailwind CSS

### Backend

- Python
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic

### Database

- PostgreSQL

### 실행기

MVP는 별도 워커 프로세스 하나와 PostgreSQL 기반 작업 큐로 시작한다.

- 인프라를 추가하지 않고 시작하기 위해 작업 큐를 DB에 둔다. Run과 Case Run이 이미 상태를 가진 테이블이므로 `SELECT ... FOR UPDATE SKIP LOCKED`를 사용하면 필요한 작업 큐를 구현할 수 있다.
- 워커는 FastAPI 프로세스와 분리한다. API 요청 처리와 장시간 실행을 같은 프로세스에 두면 배포와 스케일링이 함께 묶인다.
- Celery, Temporal, Redis Queue로 교체할 가능성만을 위해 실행기를 추상 인터페이스 뒤에 두지는 않는다. 대신 **실행 규칙을 `docs/execution.md`에 기술과 무관한 형태로 정의하여** 구현을 교체할 여지를 남긴다. 구현체가 하나뿐인 단계에서는 추상 인터페이스를 미리 만들지 않는다.

---

## Backend 레이어

```
API
 ↓
Application / Service
 ↓
Domain
 ↓
Repository / Infrastructure
```

| 레이어 | 책임 | 하지 않는 것 |
| --- | --- | --- |
| API | HTTP 입출력, 인증, 요청/응답 스키마 변환 | 비즈니스 판단, 직접 쿼리 |
| Application / Service | 유스케이스 흐름, 트랜잭션 경계, 여러 도메인 객체 조율 | SQL 작성, HTTP 관심사 |
| Domain | 불변식, 상태 전이, 지표 계산 등 규칙 | I/O |
| Repository / Infrastructure | DB 접근, 모델 API 호출, 외부 시스템 | 비즈니스 판단 |

### 의존 방향

의존성은 위에서 아래로만 향한다. Domain은 다른 레이어를 import하지 않는다.

Domain은 I/O를 하지 않는다. 따라서 Application 레이어에서 Trace를 기록하고 모델을 호출하며, Domain에는 상태 전이 규칙처럼 외부 입출력이 필요 없는 판단만 둔다.

### 레이어 배치 기준

새 코드를 배치할 때는 **이 로직이 HTTP와 DB 없이도 의미가 있는지** 먼저 확인한다.

- 둘 다 없어도 의미가 있다 → Domain
- 여러 단계를 순서대로 엮는다 → Application
- DB나 외부 시스템과 통신한다 → Infrastructure
- HTTP 요청과 응답을 처리한다 → API

---

## 디렉터리 구조

### Backend

```
backend/
  app/
    api/              FastAPI 라우터, 요청/응답 스키마
    application/      유스케이스 서비스
    domain/           엔티티, 값 객체, 규칙
    infrastructure/
      db/             SQLAlchemy 모델, 세션, 리포지토리
      llm/            모델 provider 클라이언트
    worker/           실행 워커 진입점
  migrations/         Alembic
  tests/
```

모듈은 레이어 아래에서 도메인 영역별로 나눈다. 예: `application/setups/`, `application/experiments/`, `application/analytics/`.

레이어 규칙이 이 프로젝트에서 더 자주 참조되는 경계이므로, 먼저 레이어를 나눈 뒤 그 아래에서 도메인별로 모듈을 구성한다.

### Frontend

```
frontend/
  app/              Next.js routes
  features/         도메인별 화면 로직
    setups/
    experiments/
    analytics/
  components/       공용 UI
  api/              백엔드 클라이언트
  types/            공유 타입
```

`features/` 안에서만 도메인 지식을 다룬다. `components/`는 도메인을 모른다.

---

## 아키텍처 규칙

1. **FastAPI 라우트에 비즈니스 로직을 넣지 않는다.** 라우터는 요청을 검증하여 서비스에 전달하고, 서비스가 반환한 결과를 응답으로 변환한다.
2. **SQLAlchemy ORM 객체를 API 스키마로 직접 사용하지 않는다.** 응답은 항상 Pydantic 모델로 변환한다. ORM 객체를 그대로 반환하면 DB 스키마 변경이 의도하지 않게 API 계약까지 바꿀 수 있다.
3. **React 컴포넌트에서 비즈니스 규칙을 다시 구현하지 않는다.** 점수 계산과 상태 유도, 비교 판정은 모두 백엔드가 담당하고 프런트엔드는 결과만 표시한다.
4. **Domain 레이어는 I/O를 하지 않는다.**
5. **트랜잭션 경계는 Application 레이어가 소유한다.** 리포지토리가 각자 커밋하지 않는다.
6. **변경할 수 없는 엔티티에 UPDATE를 수행하는 코드를 작성하지 않는다.** Definition Version, Setup, Run, Case Run, Trace Event, Evaluation Result가 이에 해당한다. Run과 Case Run의 상태 전이는 예외로 두되, 상태 컬럼과 타임스탬프만 변경한다.

---

## API 설계 방침

- REST를 기본으로 한다. 리소스는 도메인 용어를 그대로 쓴다. `/agent-setups`, `/experiments`, `/runs`, `/case-runs`, `/case-runs/{id}/trace`.
- 실행은 리소스 생성으로 표현한다. `POST /experiments/{id}/runs`는 Run을 생성한다.
- Analytics는 리소스가 아니라 질의로 다룬다. `POST /analytics/query`가 Scope와 지표를 받아 결과를 반환한다. Scope는 세 축의 조합이어서 URL 쿼리 문자열로 명확하게 표현하기 어렵다.
- 목록 응답은 커서 기반 페이지네이션을 쓴다. Trace Event와 Case Run은 수가 많아질 수 있다.
- 오류 응답 형식을 하나로 고정한다. `{ "error": { "type": ..., "message": ..., "details": ... } }`.

### 실시간 진행 상황

실행 중인 Run의 진행 상황은 몇 초 간격으로 폴링한다. MVP에는 이 방식으로 충분하며, WebSocket이나 SSE를 사용하면 상태 관리가 복잡해진다. 폴링으로 요구사항을 충족하기 어려워지면 SSE를 검토한다.

---

## 모델 Provider 연동

- Provider 클라이언트는 `infrastructure/llm/` 아래에 둔다.
- Agent와 Judge는 모두 같은 클라이언트로 모델을 호출한다.
- 토큰 사용량과 지연시간은 클라이언트 레이어에서 측정해 Trace Event에 기록한다. 측정을 호출부마다 반복하지 않는다.
- 실행 레이어가 재시도를 담당한다. 재시도 이력을 Trace에 남겨야 하므로 Provider 클라이언트에서는 재시도하지 않는다. 구체적인 규칙은 `docs/execution.md`의 Retry 정책을 따른다.

---

## 열린 질문

- **Next.js 렌더링 전략.** App Router에서 서버 컴포넌트를 어디까지 쓸지 정해지지 않았다. Analytics처럼 상호작용이 많은 화면은 클라이언트 컴포넌트가 자연스럽다.
- **백엔드와 프런트엔드의 타입 공유.** OpenAPI 스키마에서 TypeScript 타입을 생성할지, 수동으로 유지할지 정해지지 않았다. 생성 쪽이 유리해 보이지만 빌드 파이프라인이 하나 늘어난다.
- **워커 배포 형태.** 단일 프로세스로 시작하지만 여러 워커를 띄울 때의 작업 분배와 하트비트 구현이 남아 있다.
- **모노레포 도구.** `backend/`와 `frontend/`를 한 저장소에 두되 workspace 도구를 쓸지는 정해지지 않았다.
