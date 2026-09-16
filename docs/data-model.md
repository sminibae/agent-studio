# Data Model

이 문서는 논리 스키마를 정의한다. 프로젝트 골격에는 `app_user` 최초 migration만
있으며 나머지 DDL은 기능 단위로 추가한다. [domain-model.md](domain-model.md)의
불변식과 [execution.md](execution.md)의 상태 계약을 저장 구조로 표현한다.

## 공통 규칙

- PK는 애플리케이션에서 생성하는 UUID를 쓴다. UUIDv7을 후보로 두되 정확한 생성 라이브러리/런타임은 골격 단계에 검증한다. 정렬은 항상 `(created_at, id)`처럼 명시한다.
- 시간은 UTC `timestamptz`, 비용/점수 계산 입력은 decimal/numeric을 사용한다. 시간 단위와 null의 의미를 API에 명시한다.
- 모든 테이블에 `created_at`, 변경 가능한 행에 `updated_at`을 둔다. `updated_at` 유무만으로 불변성을 보장했다고 주장하지 않는다.
- 상태는 이름이 제한된 text + CHECK로 시작한다. 상태 전이 자체는 application/domain과 DB 조건부 UPDATE가 함께 보장한다.
- FK는 기본 RESTRICT. 과거 기록을 cascade delete하지 않는다.
- 비밀은 저장하지 않고 필요한 자격 증명 식별자만 참조한다.
- 사용자별 개인 데이터로 분리한다. 첫 배포 허용 계정은 한 명이다. 모든 개인 테이블의 owner와 조회 경계를 처음부터 구현한다.

## 사용자별 데이터 격리

```text
app_user
  id, auth_issuer, auth_subject, email, display_name
  created_at, updated_at
  UNIQUE(auth_issuer, auth_subject)
```

아래 테이블 표기에는 반복을 줄이기 위해 생략하지만, **모든 개인 데이터 테이블에 `owner_id NOT NULL FK -> app_user(id)`가 필수**다. 독립 PK를 가진 개인 테이블에는 `(owner_id, id)` UNIQUE를 두고 부모/Version/Setup 등의 개인 데이터 참조는 `(owner_id, referenced_id)` composite FK로 연결한다. membership 테이블도 owner를 포함한 composite PK/FK를 사용한다. `tool_implementation`만 시스템 read-only catalog로 owner가 없다.

이 규칙은 Definition/Version, membership, Setup, Experiment, Batch, Run, Case Run, Trace, Evaluation/Result, 모델 호출/응답 모두에 적용한다. `golden_set_version_item`의 Golden/Case 일치 FK에도 owner를 포함한다. 모든 DB 쿼리는 인증된 owner 범위를 요구하며 API body의 owner_id는 거부한다.

활성 Definition 이름 unique는 `(owner_id, name)`과 자산 종류 안에서 적용한다. 주요 목록/queue 읽기의 복합 인덱스는 owner 필터를 고려한다. worker의 전역 선점만 시스템 작업으로 여러 owner의 queued ID를 찾을 수 있고, 선점 뒤 모든 유스케이스는 해당 owner로 실행한다.

RLS는 현재 필수로 추가하지 않는다. owner-scoped repository/query와 composite FK, 두 사용자 integration/contract 테스트로 기본 격리를 보장한다. DB role을 사용자별로 분리하거나 직접 SQL 사용자 접근을 제공하게 되면 RLS를 추가 검토한다.

## 불변성과 보관

| 데이터 | 허용되는 변경 |
| --- | --- |
| Definition | 이름/설명, 최신 Version 포인터, archived_at |
| Definition Version + 멤버 연결 | 생성 후 내용/참조 변경 없음 |
| Setup/Experiment + 연결 | 구성 불변, archived_at만 갱신 가능 |
| Execution Batch | 요청과 정책 snapshot 불변 |
| Run | 상태 projection, 취소 의도, 진행 타임스탬프 |
| Case Run/Evaluation | 유효한 실행 중 상태/점유/결과 기록, 종료 결과 고정 |
| Trace/호출 이벤트/Evaluation Result | append-only |

서비스용 DB role에는 불변 테이블 UPDATE/DELETE를 주지 않는다. Setup의 보관처럼 제한적인 갱신은 컬럼 권한 또는 trigger로 허용 필드를 좁힌다. migration role과 서비스 role을 구분한다. 종료 결과 변경 방지는 상태/token 조건과 필요시 trigger로 구현하고 실제 DB 테스트로 확인한다.

UI의 ‘보관’은 `archived_at`이다. 보관한 자산은 새 구성의 기본 선택지에서 제외하지만 기존 기록에서 조회한다. 기존 Setup이 참조하는 보관 Version은 계속 유효하다. 실제 삭제/원문 제거는 별도 관리 절차로 기록하며 보존 정책을 불변성 규칙과 혼동하지 않는다.

## Definition 공통 형태

Python 원문은 서버의 일반 폴더에 저장하고 Git으로 형상관리한다. DB Version은 `source_repository_id`, `source_commit_id`, `source_path`로 정확한 원문을 참조한다. 발행·동시 저장·보존 참조의 규칙은 [python-assets.md](python-assets.md)를 따른다. DB에 편집 가능한 Python 원문 컬럼을 두지 않는다.

```text
asset_repository
  id, owner_id FK -> app_user(id)
  storage_path                      # 서버 영속 볼륨의 저장소 경로
  created_at
  UNIQUE(owner_id)                   # 첫 구조는 사용자별 저장소 하나
  UNIQUE(owner_id, id)
```

`storage_path`는 서버가 생성하며 사용자 입력으로 지정하지 않는다. 저장소는 애플리케이션 소스 저장소와 분리한다. Version의 저장소 참조에도 `(owner_id, source_repository_id)` composite FK를 적용한다.

원문 Version·정적 참조 계약·실행 결과를 구분한다. Version의 typed contract/membership은 실행 전 검사할 계약과 관계를 표현한다. Python의 동적 결과는 실행 기록으로 저장한다. Dataset/Golden 등 관계를 만드는 자산의 변수 계약은 구현 전에 정한다.

종류별 Definition/Version 테이블 쌍으로 독립 자산을 관리하고 각 종류의 검증을 적용한다.

```text
<x>_definition
  id, name, description
  current_version_no                  # 초기 version 1과 함께 생성
  archived_at, created_at, updated_at

<x>_version
  id, definition_id FK, version_no
  schema_version, <typed contract>
  source_repository_id FK -> asset_repository
  source_commit_id                   # 전체 Git commit ID
  source_path                        # 저장소 내부 상대 경로
  source_sha256, source_byte_size
  created_at
  UNIQUE(definition_id, version_no)
  CHECK(version_no >= 1)
```

위 `source_*` 필드는 Python 원문을 가진 Version에 필수다. commit ID는 Git object format을 고려한 text로 저장하고 약식 ID·브랜치 이름을 허용하지 않는다. `source_sha256`은 파일 바이트의 검증값이며 commit ID와 구분한다. 파일 경로는 저장소 내부 일반 `.py` 파일로 제한한다.

Git commit과 보존 참조를 먼저 생성한 뒤, DB에서 Definition 행 잠금 → 예상 current version 확인 → 새 Version INSERT → 포인터 갱신을 한 트랜잭션으로 한다. 동시에 같은 기반 Version에서 수정하면 한 요청은 conflict로 반환한다. 이름은 조회용이며 ID를 대신하지 않는다. 활성 Definition 이름 중복 제한은 종류별로 적용한다.

JSONB는 입력 메시지, parameter, tool schema, Golden 내용, Rubric 항목, Trace payload처럼 가변 구조에 쓴다. ID/FK·상태·정렬/집계 필드는 컬럼으로 둔다. JSON payload는 `schema_version`별로 읽기/쓰기 검증한다.

## 자산 관계

```text
prompt_definition / prompt_version
model_config_definition / model_config_version
tool_definition / tool_version
test_case_definition / test_case_version
dataset_definition / dataset_version / dataset_version_case
golden_definition / golden_version
golden_set_definition / golden_set_version / golden_set_version_item
rubric_definition / rubric_version
scoring_rule_definition / scoring_rule_version
```

필수 참조/제약:

- `dataset_version_case(dataset_version_id, test_case_version_id, position)`: membership PK, position unique. 같은 Case Definition의 여러 Version이 포함되지 않는 규칙은 Version 발행 트랜잭션에서 검사한다.
- `golden_definition.test_case_definition_id`와 `golden_version.test_case_version_id`를 저장하고 같은 Definition 소속임을 검증한다.
- `golden_set_version_item(golden_set_version_id, golden_version_id, test_case_version_id)`: Set/Case unique, Golden/Case 일치 composite FK.
- Rubric/Scoring Rule Version은 Python 원문과 결과 schema를 참조한다. 실행 시 생성한 Rubric의 key/min/max/기준과 Scoring Rule의 method/weight/threshold는 Evaluation에 연결한 실행 결과로 보존한다. 개별 판정 점수는 JSONB가 아닌 result 컬럼에 둔다.

## Python 도구 구현과 모델 노출 정보

개발자가 작성·배포한 도구 코드와 화면에서 편집하는 모델용 설명을 분리한다.

```text
tool_implementation
  id
  registry_key                        # 예: weather.get_current_weather
  artifact_digest                     # 코드와 의존성을 식별하는 배포 artifact
  entrypoint                          # 허용된 registry 내부 symbol
  input_schema, output_contract       # schema_version 포함
  credential_refs                     # 비밀 값 아님
  created_at
  UNIQUE(registry_key, artifact_digest)

tool_version
  id, definition_id, version_no
  implementation_id FK -> tool_implementation
  exposed_name, description
  input_schema_snapshot, schema_version
  created_at
```

스키마 snapshot은 실제 구현 계약과 같아야 한다. 화면에서 함수 인자 타입을 마음대로 바꾸지 않는다. Description만 바꾼 Version은 동일 implementation을 참조할 수 있다. 구현 변경은 새 artifact/implementation을 등록하며 과거 참조를 바꾸지 않는다.

최초 버전은 현재 배포에 포함된 구현만 실행할 수 있다. 과거 artifact가 없으면 `implementation_unavailable`로 거부하며 최신 함수로 조용히 대체하지 않는다. 과거 이력 조회는 가능하다. 오래된 코드 artifact를 실행하는 격리 worker/배포 전략은 후속 export/재실행 요구에 따라 추가한다.

## 사용자 실행 환경

개발용 `backend/.venv`와 저장소 `.env`는 아래 사용자 데이터에 포함하지 않는다.
실제 파일은 owner별 작업 디렉터리에 두고 DB에는 이름·상태·참조만 저장한다.

```text
user_venv
  id, owner_id FK, name, python_version, status, created_at
  UNIQUE(owner_id, name)

user_env_file
  id, owner_id FK, name, current_revision_id, created_at
  UNIQUE(owner_id, name)

user_env_revision
  id, owner_id, env_file_id FK, created_at
  # 실제 dotenv 파일은 owner별 비밀 저장 위치에 보관; DB에 key/value 없음

execution_environment
  id, owner_id FK, name, venv_id FK, env_file_id FK, created_at, archived_at
  UNIQUE(owner_id, name)

agent_setup.execution_environment_id FK -> execution_environment
evaluation_setup.execution_environment_id FK -> execution_environment
```

각 참조는 `(owner_id, id)` composite FK로 교차 owner 연결을 막는다. 이름은
서버가 관리하는 owner 디렉터리의 상대 이름으로 제한하며 클라이언트의 절대
경로를 저장하지 않는다. 환경 조합을 바꾸려면 새 Execution Environment를
만들고 Setup을 복제한다. 패키지·dotenv 내용 수정은 다음 실행에 적용된다.
실행마다 해석한 venv ID·Python 버전·패키지 digest와 env revision ID를
Case Run/Evaluation의 환경 관측에 남긴다. 비밀 값이나 값의 hash는 저장하지
않는다. 상세 파일 계약은 [runtime-environments.md](runtime-environments.md)를 따른다.

## Setup과 Experiment

```text
agent_setup
  id, name, description
  prompt_version_id FK
  model_config_version_id FK
  execution_environment_id FK
  runtime_params, runtime_schema_version
  archived_at, created_at

agent_setup_tool_version
  agent_setup_id FK, tool_version_id FK, exposed_name, position
  PK(agent_setup_id, tool_version_id)
  UNIQUE(agent_setup_id, exposed_name)
  UNIQUE(agent_setup_id, position)

evaluation_setup
  id, name, description
  dataset_version_id FK, golden_set_version_id FK nullable
  execution_environment_id FK
  judge_prompt_version_id FK, judge_model_config_version_id FK
  rubric_version_id FK, scoring_rule_version_id FK
  missing_golden_policy CHECK in (fail, skip, rubric_only)
  archived_at, created_at

experiment
  id, name
  agent_setup_id FK, evaluation_setup_id FK
  repeats CHECK 1 <= repeats <= 10
  archived_at, created_at

experiment_case
  experiment_id FK, test_case_version_id FK, position
  PK(experiment_id, test_case_version_id)
  UNIQUE(experiment_id, position)
```

Agent Setup의 중복 exposed_name은 Tool Version과 일치 검증 후 저장한다. Experiment의 Case는 Evaluation Setup의 Dataset에 있어야 한다. 다른 테이블 조회가 필요한 membership/Golden/Rubric 검증은 application transaction으로 수행하고 일관성을 깨는 별도 쓰기 경로를 제공하지 않는다.

## Batch, Run, Case Run

```text
execution_batch
  id, experiment_id FK
  idempotency_key, request_hash
  execution_policy, policy_schema_version
  runtime_artifact_digest, sdk_versions
  # 실제 사용자 venv/dotenv 관측은 각 Case Run/Evaluation에 기록
  requested_by_actor FK -> app_user(id)    # 현재 owner와 동일
  created_at
  UNIQUE(experiment_id, idempotency_key)

run
  id, execution_batch_id FK
  repeat_index, status
  cancel_requested_at nullable
  started_at nullable, agent_finished_at nullable
  created_at, updated_at
  UNIQUE(execution_batch_id, repeat_index)

case_run
  id, run_id FK, test_case_version_id FK
  status
  final_answer nullable
  error_type nullable, error_message nullable
  agent_latency_ms nullable
  lease_token nullable, lease_expires_at nullable, worker_id nullable
  next_trace_seq
  started_at nullable, finished_at nullable
  created_at, updated_at
  UNIQUE(run_id, test_case_version_id)
```

Run의 Experiment는 Batch를 통해 조회한다. 같은 의미의 experiment_id를 여러 테이블에 저장해 불일치를 만들지 않는다. repeat_index 상한과 Case membership은 실행 등록 시 검사한다. Run/Case Run 개수 상한은 API와 DB migration에 일치시킨다.

`succeeded`이면 Final Answer/finished_at이 존재해야 하고 pending이면 started_at/finished_at은 null이다. terminal이면 finished_at이 존재하고 유효 lease를 보유하지 않는다. 시간/지연은 음수가 될 수 없다.

점유·완료·취소·복구는 부모 Run → Case Run 또는 Evaluation 순으로 잠근다. 동시에 마지막 두 Case가 완료될 때 부모 projection이 stale하지 않도록 공통 잠금 순서를 사용한다. 외부 호출 동안 lock을 유지하지 않는다.

## Trace와 모델 호출 기록

Python 자산의 실제 결과는 Case Run 또는 Evaluation에 연결한 실행 기록으로 보존한다. 자산 Version·저장소·commit·경로·원문 SHA-256, 실행 환경·실제 값·오류를 모델/Judge 호출 전에 기록한다. 상세 결과 테이블의 미정 항목은 [python-assets.md](python-assets.md)를 따른다. 함수·모듈 객체를 직렬화하지 않는다.

```text
trace_event
  id, case_run_id FK, seq
  event_type, occurred_at
  call_id nullable
  duration_ms nullable
  payload_schema_version, payload
  created_at
  UNIQUE(case_run_id, seq)

model_call_attempt
  id                             # call attempt 식별자
  case_run_id FK nullable
  evaluation_id FK nullable
  logical_call_id, attempt_no
  provider, requested_model, started_at
  request_payload, payload_schema_version
  created_at
  CHECK(exactly one of case_run_id, evaluation_id is not null)
  UNIQUE(logical_call_id, attempt_no)

model_call_outcome
  id, model_call_attempt_id FK UNIQUE
  outcome_type                   # returned / error / unknown
  returned_model nullable, provider_request_id nullable
  duration_ms nullable
  input_tokens nullable, output_tokens nullable, usage_detail
  cost_usd nullable, pricing_snapshot nullable
  response_payload nullable, error_payload nullable
  created_at
```

시작을 먼저 append하고 종료 outcome을 하나 추가한다. 시작만 있고 프로세스가 죽었으면 복구기가 `unknown` outcome을 기록한다. null 사용량/가격을 0으로 바꾸지 않는다. 기록 쓰기도 작업 token으로 fencing하며 복구기가 종료시킨 뒤 늦은 worker가 outcome을 추가할 수 없다.

가격 snapshot은 단위당 가격/통화/출처·기준시각/계산 정책을 포함한다. cached/reasoning 등의 사용량 구분이 제공되면 기록한다. 이 값에서 Agent/Judge 합계를 읽는다. Case Run 합계 컬럼을 추가할 경우 재계산 가능한 projection임을 표시한다.

Trace는 원문 payload와 호출 ID를 참조하며 비용/토큰을 같은 원본에서 읽는다. seq는 `next_trace_seq` 갱신과 INSERT를 같은 트랜잭션으로 처리한다. `MAX(seq)+1`만으로 동시 append를 구현하지 않는다.

## Evaluation과 항목 결과

```text
evaluation
  id, case_run_id FK UNIQUE
  evaluation_setup_id FK
  status, status_reason nullable
  lease_token nullable, lease_expires_at nullable, worker_id nullable
  started_at nullable, finished_at nullable
  created_at, updated_at

evaluation_result
  id, evaluation_id FK
  rubric_item_key
  raw_score numeric
  rationale text
  created_at
  UNIQUE(evaluation_id, rubric_item_key)
```

Evaluation Setup은 Case Run의 Experiment에서 고정한 것과 같아야 한다. 첫 버전은 재평가를 제공하지 않으므로 case_run_id unique를 둔다. 이후 재평가가 필요하면 명시적 evaluation selection과 함께 migration한다.

전체 응답을 검증한 뒤 항목 INSERT들과 `status=scored`를 한 트랜잭션으로 처리한다. Result 자체에 failed/skipped 상태나 null score를 넣지 않는다. 실패/skip은 Evaluation 상태다. 원본 Judge 응답은 연결된 model_call_outcome에 보존한다.

normalized/weighted Case Score와 passed는 파생값이며 [analytics.md](analytics.md)의 버전 있는 함수로 계산한다. 항목별 created_at 최신 선택은 금지한다.

## 인덱스·조회·보존

첫 필수 접근 경로는 Definition의 버전 조회, Experiment의 Batch, Batch의 Run, Run의 Case/Evaluation 상태, Case의 Trace, 비교 Case Version이다. FK 참조 조회와 queue 상태·lease 만료 대상에 인덱스를 둔다.

```text
execution_batch(experiment_id, created_at, id)
run(execution_batch_id, repeat_index)
case_run(run_id, status)
case_run(test_case_version_id)
case_run(created_at, id) WHERE status = pending
case_run(lease_expires_at) WHERE status = running
evaluation(status, created_at, id)
evaluation(lease_expires_at) WHERE status = running
trace_event(case_run_id, seq)           # UNIQUE index 재사용
```

DB 영속 볼륨, backup/restore, retention과 접근 감사는 [operations.md](operations.md)를 따른다. Analytics 캐시와 Trace object storage는 실제 규모 측정 후 도입한다. migration을 만들 때 전체 FK/unique/check와 동시성 사례를 실제 PostgreSQL로 검증한다.
