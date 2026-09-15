# Engineering

이 문서는 구현·검증 절차를 정의한다. 아직 패키지·Makefile·CI·실행 코드가 없으므로 아래 명령은 **구현할 계약이며 실행 검증된 명령이 아니다.**

## 좋은 코드의 기준

핵심 규칙이 프레임워크 없이 테스트되고, 변경 책임이 분명하며, 실패와 복구의 결과를 설명할 수 있어야 한다. 이름 붙인 패턴 수나 클래스 수를 품질 지표로 삼지 않는다.

## TDD 개발 순서

TDD는 테스트를 나중에 붙이는 방침이 아니라 개발 순서다. [TDD 설명](https://martinfowler.com/bliki/TestDrivenDevelopment.html)의 Red → Green → Refactor를 따른다.

1. 사용자 사례에서 구현할 규칙과 경계 사례를 목록으로 쓴다.
2. 가장 작은 관찰 가능한 동작의 실패 테스트 하나를 작성한다.
3. 의도한 이유로 실패하는지 확인한다.
4. 통과에 필요한 구현을 추가한다.
5. 통과 상태에서 이름, 중복, 책임, 의존성을 정리한다.
6. DB/API/화면까지 이어지는 인수 조건으로 기능을 확인한다.

상태 전이·버전 불변성·채점·멱등성·복구에는 이 순서를 기본으로 적용한다. 단순 문구/스타일 변경이나 생성 코드에 구현을 복제한 테스트를 만들지 않는다. 탐색용 spike는 운영 구현과 구분하고 얻은 계약을 테스트로 고정한다.

## 테스트 경계

| 종류 | 검증 대상 | 실행 환경 |
| --- | --- | --- |
| Domain unit | 상태 판정, 구성 검증, 점수·분모·비교 가능성 | I/O 없이 |
| Application | 유스케이스, port 계약, 실패 시 저장 여부 | fake model/tool/clock, 필요한 fake repository |
| DB integration | FK/unique/check, 동시 버전 발행, 멱등 등록, lease/fencing, commit/rollback | 실제 PostgreSQL |
| API contract | 입력/오류/응답, OpenAPI와 클라이언트 계약 | API + 적절한 persistence adapter |
| Frontend interaction | 편집/복제, 범위 선택, 오류·미평가·취소 UI | component 테스트 |
| E2E | 구성 → 실행 → 채점 → 비교 → Trace | 프런트 + API + worker + DB + deterministic provider |
| Live smoke | 실제 provider·도구 인증과 응답 계약 | 명시적으로 실행, 소수 요청 |

SQLite로 PostgreSQL 테스트를 대체하지 않는다. fake repository만으로 트랜잭션을 검증했다고 주장하지 않는다. 외부 LLM을 기본 CI에 호출하지 않는다. live smoke가 pass해도 stochastic score의 정확성을 증명하는 것은 아니다.

## 반드시 검증할 사례

- 두 사용자 A/B의 목록·상세·복제·Version 연결·실행·Trace·분석·cursor가 서로의 데이터를 노출하지 않는다. 교차 owner FK가 실제 DB에서 거부된다.
- 로그인 만료, 미허용 계정, identity header 위조, 직접 API 접근과 CSRF 요청을 거부한다.

- Definition 편집은 새 Version을 만들고 이전 Setup·Dataset·실행 참조를 바꾸지 않는다.
- 동시에 같은 Definition을 편집해도 Version 번호 충돌·수정 유실이 없다.
- Dataset에 없는 Case, 다른 Case Version의 Golden, 중복 도구 이름, 잘못된 Rubric/weight는 저장 전에 거부한다.
- Repeats 3, Cases 2의 실행 요청은 Batch 1, Runs 3, Case Runs 6을 원자적으로 만든다.
- 같은 멱등 키의 동시 요청도 Batch를 하나만 만들고 다른 payload는 409다.
- 취소 전부/일부, 성공·실패 혼합, Agent 완료·Judge 대기 등 상태 조합이 정의와 일치한다.
- worker 점유 만료 뒤 늦은 성공/Trace 쓰기가 차단된다. 실행 중 Agent를 자동 재실행하지 않는다.
- retry는 Case Run/Repeat 수를 늘리지 않으며 호출별 기록·비용 범위를 보존한다.
- Judge의 누락/중복/범위 밖 항목은 점수로 공개하지 않는다. 완전한 결과만 원자적으로 공개한다.
- Agent 실패, Judge 실패, skip, 취소, 진행 중, 빈 Scope, 비용 unknown을 구분한다.
- 평가 기준이 다른 Setup의 Δ/승패를 공식 비교로 반환하지 않는다.
- 분석 사례의 분모·coverage·Case 가중치가 [analytics.md](analytics.md)와 일치한다.

계산 테스트에는 손으로 검산 가능한 숫자를 쓴다. 테스트 이름은 관찰할 규칙을 설명하고 내부 메서드 호출 순서를 불필요하게 고정하지 않는다.

## 첫 서비스까지 구현 순서

각 단계는 API와 화면이 연결된 기능 단위다. 모든 DB 테이블을 먼저 만들고 마지막에 화면을 붙이는 순서로 진행하지 않는다.

| 단계 | 구현 | 종료 조건 |
| --- | --- | --- |
| 0 | 설계 기본안 확인, 프로젝트 골격, 로그인/owner context 경계 | 프런트 → API → DB health와 migration, CI 동작 |
| 1 | Prompt/Test Case/Dataset와 최소 Setup 편집·복제 | 새 버전 생성과 기존 참조 보존을 화면·DB에서 확인 |
| 2 | Experiment/Batch/Run/Case Run, fake Agent, worker, Trace | 화면에서 예약·진행·완료·취소 가능 |
| 3 | 실제 선택 provider와 실제 도구 연결 | 날씨 Agent 사례가 Final Answer와 사용량을 남김 |
| 4 | Rubric/Judge/Scoring, Evaluation 진행과 실패 | 정상/미평가를 구분하고 검산 가능한 점수를 표시 |
| 5 | Setup A/B 비교, Cases와 Trace, Repeats | 퇴행 Case를 찾아 양쪽 Trace까지 이동 |
| 6 | 8 Scope 검증, 복구·배포·운영 점검 | 첫 완성본 인수 시나리오 통과 |

Provider/tool은 OpenAI와 등록된 날씨 HTTP 도구를 사용하고, 본 런타임 구현 전에 [agent-runtime.md](agent-runtime.md)의 SDK compatibility spike를 마친다. 채점 정책은 analytics의 검산 예시를 테스트로 고정한다. UI 범위와 배포 조건에 맞춰 구현 단위와 인수 기준을 유지한다.

단계 1에 코드 편집기·Git commit과 DB Version 발행·owner별 원문 조회를 포함하고, 단계 2 전에 격리 실행과 결과 기록을 검증한다. 동시 저장 시 변경 혼입 방지, Git 성공 후 DB 실패·응답 유실, 작업 폴더가 바뀐 뒤 과거 commit 조회, 보존 참조·Git 정리 후 과거 Version 유지, DB와 Git 저장소의 복원을 확인한다. 실행 검증에는 저장/실행 시각이 다른 Prompt, Case Run별 재계산과 호출 retry의 값 유지, 결과 타입 오류·timeout, commit/파일 누락과 hash 불일치를 포함한다. 단계 4~5 전에 동적 평가 설정과 비교 계약을 정한다. 미정 항목은 [python-assets.md](python-assets.md)를 따른다.

## 첫 완주 인수 시나리오

아래는 비교 기능의 deterministic 인수 예시이며 실제 고객 데이터의 품질 목표가 아니다.

1. 두 Test Case Version과 Golden을 포함한 Dataset/Evaluation Setup을 만든다.
2. Agent Setup A를 복제해 Prompt만 바꾼 B를 만든다.
3. 동일한 Case 범위로 각각 Repeats 2를 실행한다. 총 Case Run은 8개다.
4. fake provider에서 A의 각 Case 점수는 모든 반복에서 0.8, 0.9, B는 1.0, 0.5로 반환한다. Pass threshold는 0.7이다.
5. Mean은 A 0.85, B 0.75이고 Δ는 -0.10이다. A의 Pass Rate는 100%, B는 50%다. 두 번째 Case가 Regression이다.
6. Regression 행에서 A/B의 해당 Case Trace를 보고 입력·도구 결과·Judge 근거까지 확인한다.
7. Prompt 원본을 다시 수정해도 위 결과와 Setup 참조는 바뀌지 않는다.
8. 별도 실행에서 provider 실패, Judge 실패, 취소, worker 중단을 주입해 상태·분모·재기동 후 조회를 확인한다.

실제 모델/도구 smoke는 별도 사례로 수행한다. 백업에서 복원한 DB의 Setup·실행·Trace 조회까지 배포 조건에 맞춰 확인한다.

## 언어와 코드 규칙

Python 후보 스택을 채택하면 uv, Ruff, mypy strict, pytest를 사용한다. 함수 경계에는 타입을 붙이고 `Any`는 외부 SDK/JSON 변환 경계에서만 이유와 함께 제한한다. Domain은 표준 Python 객체/값 객체를 사용하고 Pydantic은 외부 데이터·저장 payload 검증에 사용한다.

JSONB payload에는 `schema_version`을 둔다. 과거 데이터를 현재 모델로 무조건 읽지 않고 해당 버전을 검증·변환한다. 읽기 실패를 빈 값으로 숨기지 않는다.

TypeScript는 strict, ESLint, Prettier, 타입 검사를 기본으로 한다. 알 수 없는 입력은 `unknown`에서 좁힌다. API 타입은 OpenAPI로 생성하고 프런트에서 채점·비교 정책을 재구현하지 않는다.

Docstring은 공개 계약·오류·단위·비직관적인 판단을 설명할 때 쓴다. 이름과 타입을 반복하는 설명을 의무화하지 않는다. 함수 크기나 coverage 수치의 기계적인 목표보다 규칙·경계 사례를 검증한다.

## 개발·CI 명령 계약

프로젝트 골격에서 다음 진입점을 실제 명령으로 구현한다.

| 명령(예정) | 책임 |
| --- | --- |
| `make dev` | 로컬 서비스와 환경 안내 |
| `make fmt` | 소스 포매팅, 파일 변경 가능 |
| `make lint` | lint + format check, 파일 변경 없음 |
| `make typecheck` | Python/TypeScript 타입 검사 |
| `make test` | unit/application/component tests |
| `make test-integration` | 실제 DB/API·worker 경계 검증 |
| `make test-e2e` | deterministic 전체 흐름 |
| `make check` | lint, typecheck, 기본 테스트, import 경계, 생성 계약 검사 |

CI 후보는 GitHub Actions이며 PostgreSQL service를 사용한다. 로컬 DB 후보는 Docker Compose다. PR에서는 `check`, 관련 integration, 핵심 E2E와 build를 통과한다. 실제 PostgreSQL 버전을 개발·CI에서 일치시킨다. lockfile을 커밋하고 비밀은 커밋하지 않는다.

아직 Makefile이 없는 단계에서 `make check`를 실행했다고 보고하지 않는다. 문서만 바꾸는 작업은 링크·상충 규칙·diff를 검토한다. 구현 단계에서는 바뀐 경계에 해당하는 실행 검증을 수행하고 실패/미실행을 명시한다.

## 마이그레이션과 운영

스키마 변경은 migration으로 관리한다. 배포 시 migration을 담당하는 프로세스를 하나로 정한다. API/worker 각각이 기동하며 임의로 migration을 경쟁 실행하지 않는다.

모든 데이터 변환에 무손실 downgrade가 가능하다고 가정하지 않는다. 되돌릴 수 있는 변경은 downgrade를 작성하고, 파괴적 변경은 백업/복원 또는 forward fix 계획을 문서화한다. 작은 관련 데이터 변경은 원자성이 필요하면 같은 migration에 넣고 대규모 backfill은 나누어 재개 가능하게 만든다.

기동·종료, DB readiness, worker heartbeat, request/batch/run/case/evaluation ID 로그를 제공한다. 배포 형태·접근 제어·백업 기본안은 [operations.md](operations.md)를 따른다. 실제 값과 복원 훈련은 배포 준비에 포함한다.

## Git과 설계 변경

한 변경은 하나의 의도를 담고 커밋 제목은 그 행동을 설명한다. 설계 변경 시 결정 근거와 영향을 받는 문서를 같은 변경에 반영한다. 미결 사항을 코드에서 임의로 확정한 뒤 문서만 뒤따라 고치지 않는다.
