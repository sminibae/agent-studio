# Data Model

이 문서는 Domain Model을 PostgreSQL 스키마로 표현하는 방법을 정의한다. 용어의 의미는 `docs/domain-model.md`가 정본이다.

지금은 ERD 수준까지만 확정한다. 실제 DDL은 Alembic 마이그레이션에서 작성한다.

---

## 공통 규칙

### ID 정책

- 모든 엔티티의 PK는 UUIDv7이다. 시간 순 정렬이 가능해 인덱스 지역성이 좋고, 서버에서 미리 생성할 수 있다.
- 컬럼 이름은 `id`, 외래키는 `<table>_id`로 통일한다.
- 사용자에게 보여주는 식별자는 UUID가 아니라 이름과 버전 번호다. UUID는 보조 표시다.

### 타임스탬프

- 모든 테이블은 `created_at timestamptz NOT NULL DEFAULT now()`를 가진다.
- 변경 가능한 테이블에만 `updated_at timestamptz NOT NULL`을 둔다. 변경할 수 없는 테이블에는 `updated_at`을 두지 않아 불변성을 스키마에 명시한다.
- 모든 시간은 UTC로 저장한다.

### 버전 관리 방식

Definition마다 테이블 두 개를 쓴다.

- `<x>_definition`: 이름, 설명, 소유자, 현재 최신 버전을 가리키는 포인터를 저장하며 변경할 수 있다.
- `<x>_version`: 실제 내용을 저장하며 생성 후에는 변경할 수 없다.

규칙:

- `<x>_version`의 `(definition_id, version_no)`에는 고유 제약 조건을 둔다. `version_no`는 1부터 증가한다.
- `<x>_version`은 UPDATE와 DELETE를 금지한다. 애플리케이션 레이어에서 막고, 필요하면 DB 권한으로도 막는다.
- `<x>_definition.latest_version_no`는 캐시이며, 최신 버전을 판정할 때는 `<x>_version`을 기준으로 삼는다.

### 스냅샷 방식

Setup은 Definition Version을 FK로 직접 참조한다. 내용을 복사하지 않는다.

- Version은 생성 후 변경되지 않으므로 FK 참조만으로 스냅샷을 보존할 수 있다. 내용을 복사하면 같은 데이터를 두 곳에 저장하여 불일치할 위험이 생긴다.
- 예외는 외부 시스템에서 온 값이다. 우리가 불변성을 보장할 수 없는 값은 실행 시점에 복사해 `case_run`에 남긴다.

### JSONB 사용 기준

JSONB는 다음 조건을 모두 만족할 때만 쓴다.

1. 구조가 사용자 정의이거나 스키마 변경이 잦다.
2. 개별 필드로 조인하거나 집계할 필요가 없다.
3. Pydantic 모델로 읽기·쓰기 양쪽에서 검증한다.

다음 값은 JSONB로 저장한다: 프롬프트 변수 정의, 도구 입력 스키마, 모델 Runtime Parameter, Test Case 입력, Golden 내용, Rubric 항목 정의, Trace Event Payload, 토큰 사용량 상세.

다음 값은 별도 컬럼에 저장한다: 상태, 점수, 지연시간, 총 토큰 수, 비용, 모든 FK, 정렬·필터·집계에 사용하는 값.

집계에 사용하는 값은 JSONB 안에 두지 않는다. Analytics 쿼리에서 매번 JSONB 값을 추출하면 성능이 낮아지고 쿼리를 읽기도 어려워진다.

### 삭제 정책

- Definition, Setup, Experiment는 논리 삭제하며 `deleted_at timestamptz NULL`을 둔다.
- Definition Version, Run, Case Run, Trace Event, Evaluation Result는 삭제하지 않는다. 실행 이력이기 때문이다.
- 논리 삭제한 Definition은 새 Setup에서 선택할 수 없지만 기존 Setup에서는 계속 조회할 수 있다. 이 규칙은 Invariant 10을 보장한다.
- 물리 삭제는 데이터 보존 정책이 생긴 뒤에 별도 배치로 다룬다. MVP 범위 밖이다.

---

## 엔티티 목록

### 자산 계층

```
prompt_definition          prompt_version
tool_definition            tool_version
model_config_definition    model_config_version
test_case_definition       test_case_version
dataset_definition         dataset_version        dataset_version_case
golden_definition          golden_version
golden_set_definition      golden_set_version     golden_set_version_item
rubric_definition          rubric_version
scoring_rule_definition    scoring_rule_version

agent_setup                agent_setup_tool_version
evaluation_setup
```

### 실행 계층

```
experiment                 experiment_case
run
case_run
trace_event
evaluation_result
```

---

## 주요 테이블

아래에는 별도의 결정이 필요한 테이블만 정리한다. 나머지 Definition 테이블은 모두 같은 구조를 따른다.

### Definition 공통 형태

```
<x>_definition
  id                uuid pk
  name              text            -- 사용자에게 보이는 이름
  description       text null
  latest_version_no int
  deleted_at        timestamptz null
  created_at, updated_at

  unique (name) where deleted_at is null

<x>_version
  id                uuid pk
  definition_id     uuid fk -> <x>_definition(id)
  version_no        int
  <내용 컬럼들>
  created_at

  unique (definition_id, version_no)
  index (definition_id, version_no desc)
```

### agent_setup

```
agent_setup
  id                        uuid pk
  name                      text
  description               text null
  prompt_version_id         uuid fk -> prompt_version(id)
  model_config_version_id   uuid fk -> model_config_version(id)
  runtime_params            jsonb          -- max_turns, timeout_sec 등
  deleted_at                timestamptz null
  created_at

agent_setup_tool_version
  agent_setup_id    uuid fk -> agent_setup(id)
  tool_version_id   uuid fk -> tool_version(id)
  position          int              -- 프롬프트에 노출되는 순서
  primary key (agent_setup_id, tool_version_id)
```

Agent Setup은 생성 후 변경할 수 없으므로 `updated_at`이 없다. 내용을 바꾸려면 새 Agent Setup을 만든다.

### evaluation_setup

```
evaluation_setup
  id                          uuid pk
  name                        text
  description                 text null
  dataset_version_id          uuid fk -> dataset_version(id)
  golden_set_version_id       uuid fk -> golden_set_version(id) null
  judge_prompt_version_id     uuid fk -> prompt_version(id)
  judge_model_config_version_id uuid fk -> model_config_version(id)
  rubric_version_id           uuid fk -> rubric_version(id)
  scoring_rule_version_id     uuid fk -> scoring_rule_version(id)
  missing_golden_policy       text           -- 'skip' | 'rubric_only' | 'fail'
  deleted_at                  timestamptz null
  created_at
```

`missing_golden_policy`는 Golden이 없는 Case의 처리 방식을 정한다. 같은 Dataset에 서로 다른 정책을 적용한 결과는 별개의 실험이므로, 이 정책을 실행 코드에 숨기지 않고 Setup에 명시한다.

### experiment

```
experiment
  id                    uuid pk
  name                  text
  agent_setup_id        uuid fk -> agent_setup(id)
  evaluation_setup_id   uuid fk -> evaluation_setup(id)
  repeats               int  not null default 1  -- check repeats >= 1
  deleted_at            timestamptz null
  created_at, updated_at

experiment_case
  experiment_id         uuid fk -> experiment(id)
  test_case_version_id  uuid fk -> test_case_version(id)
  primary key (experiment_id, test_case_version_id)
```

`experiment_case`는 Case 범위를 명시적으로 고정한다. Dataset 전체를 사용하는 경우에도 모든 행을 저장한다. "전체"를 NULL로 표현하면 이후 Dataset Version이 변경될 때 Experiment의 Case 범위를 확정하기 어렵다.

Experiment는 `updated_at`을 가진다. 아직 실행하지 않은 Experiment는 수정할 수 있다. 단 Run이 하나라도 생긴 뒤에는 수정을 막는다. 이 규칙은 애플리케이션 레이어에서 강제한다.

### run

```
run
  id              uuid pk
  experiment_id   uuid fk -> experiment(id)
  repeat_index    int              -- 1..repeats, 같은 실행 요청 안에서의 순번
  status          text             -- queued|running|completed|partially_failed|failed|cancelled
  started_at      timestamptz null
  finished_at     timestamptz null
  created_at

  index (experiment_id, created_at desc)
  index (status) where status in ('queued','running')
```

### case_run

```
case_run
  id                    uuid pk
  run_id                uuid fk -> run(id)
  test_case_version_id  uuid fk -> test_case_version(id)
  status                text       -- pending|running|succeeded|failed|timed_out|cancelled
  final_answer          text null
  error_type            text null
  error_message         text null
  latency_ms            int null
  input_tokens          int null
  output_tokens         int null
  cost_usd              numeric(12,6) null
  started_at            timestamptz null
  finished_at           timestamptz null
  created_at

  unique (run_id, test_case_version_id)
  index (run_id, status)
```

`unique (run_id, test_case_version_id)`는 Invariant 6을 스키마에서 강제한다. 따라서 하나의 Run에서는 같은 Case를 두 번 실행할 수 없다. Repeats를 Run 단위로 표현하는 이유도 여기에 있다.

지연시간·토큰·비용을 컬럼으로 둔 이유는 Analytics의 거의 모든 지표가 이 값들을 집계하기 때문이다.

### trace_event

```
trace_event
  id            uuid pk
  case_run_id   uuid fk -> case_run(id)
  seq           int            -- 1부터 증가, Case Run 안에서 유일
  event_type    text           -- docs/execution.md 참조
  started_at    timestamptz
  duration_ms   int null
  payload       jsonb          -- event_type별 구조
  created_at

  unique (case_run_id, seq)
  index (case_run_id, seq)
```

Trace는 별도 테이블이 아니다. 같은 `case_run_id`를 가진 `trace_event`의 시퀀스가 하나의 Trace를 이룬다. 별도 엔티티를 만들지 않는 대신 `seq`의 유일성으로 이벤트 순서를 보장한다.

Event Type마다 구조가 다르고 이벤트 내부 필드를 집계할 필요가 없으므로 `payload`는 JSONB로 저장한다. 집계에 사용하는 `duration_ms`는 별도 컬럼에 둔다.

### evaluation_result

```
evaluation_result
  id                    uuid pk
  case_run_id           uuid fk -> case_run(id)
  rubric_version_id     uuid fk -> rubric_version(id)
  rubric_item_key       text          -- rubric 안의 항목 식별자
  score                 numeric(6,3) null
  passed                boolean null
  reasoning             text null
  judge_raw_output      jsonb null
  status                text          -- scored|failed|skipped
  created_at

  index (case_run_id)
  index (rubric_version_id, rubric_item_key)
```

집계 점수는 여기에 저장하지 않는다. Scoring Rule로 계산되는 파생값이며, Analysis 계층이 계산한다.

재평가를 지원하기 위해 `(case_run_id, rubric_item_key)`에 unique를 걸지 않는다. 대신 조회 시 최신 `created_at`을 기준으로 선택한다.

---

## 주요 관계

```
prompt_version        ──┐
model_config_version  ──┼──> agent_setup ──┐
tool_version (N)      ──┘                   │
                                             ├──> experiment ──> run ──> case_run ──┬──> trace_event
dataset_version       ──┐                   │                                        └──> evaluation_result
golden_set_version    ──┤                   │
prompt_version        ──┼──> evaluation_setup ┘
model_config_version  ──┤
rubric_version        ──┤
scoring_rule_version  ──┘

dataset_version    ──> dataset_version_case    ──> test_case_version
golden_set_version ──> golden_set_version_item ──> golden_version ──> test_case_definition
```

카디널리티:

| 관계 | 카디널리티 |
| --- | --- |
| Definition : Definition Version | 1 : N |
| Agent Setup : Tool Version | N : M |
| Experiment : Run | 1 : N |
| Run : Case Run | 1 : N |
| Case Run : Trace Event | 1 : N |
| Case Run : Evaluation Result | 1 : N |

---

## 인덱스 방침

Analytics 쿼리를 기준으로 인덱스를 설계한다. 기본 접근 경로는 세 가지다.

1. Experiment 하나의 모든 Run과 Case Run 집계 → `run(experiment_id, created_at desc)`, `case_run(run_id, status)`
2. 여러 Experiment를 Case 단위로 비교 → `case_run(test_case_version_id)` 인덱스 추가 필요
3. Case Run 하나의 Trace 조회 → `trace_event(case_run_id, seq)`

실제 쿼리를 확인하기 전에는 인덱스를 더 추가하지 않는다. Analytics 쿼리를 작성한 뒤 `EXPLAIN` 결과를 보고 결정한다.

---

## 열린 질문

- **Analysis 결과를 저장할 것인가.** 지금은 저장하지 않고 매번 계산한다. Case Run 수가 커져 집계가 느려지면 `run_analysis` 같은 캐시 테이블을 추가한다. 그때도 원본은 `case_run`과 `evaluation_result`다.
- **Trace payload를 별도 저장소로 뺄 것인가.** 긴 모델 출력이 쌓이면 테이블이 빠르게 커진다. MVP는 PostgreSQL에 그대로 두고, 크기가 문제가 되면 payload만 오브젝트 스토리지로 옮기고 참조를 남긴다.
- **`cost_usd`를 실행 시점에 계산할 것인가.** 모델 단가는 변한다. 지금은 실행 시점 단가로 계산해 고정한다. 대안은 토큰만 저장하고 조회 시 단가표를 조인하는 것이다.
- **멀티 유저와 소유권.** 지금 스키마에 `owner_id`가 없다. 단일 팀 사용을 전제한 결정이며, 계정 개념이 생기면 Definition·Setup·Experiment에 `owner_id`를 추가한다.
