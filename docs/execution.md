# Execution

이 문서는 플랫폼의 Agent 실행 계약을 정의한다. 기술 배치는 [architecture.md](architecture.md), 지표는 [analytics.md](analytics.md)를 따른다.

## 실행 등록

```text
Experiment → Execution Batch → repeats개의 Run
                                → Case마다 Case Run + Evaluation 슬롯
Case Run: Agent 호출/도구 왕복 → Final Answer → Evaluation 대기열
Evaluation: Judge 호출 → 전체 응답 검증 → 항목 결과 일괄 확정
```

1. 인증 owner와 모든 참조의 동일 소유권, 요청 키, Experiment/Setup 및 선택한 사용자 실행 환경의 사용 가능 여부, 선택 Case의 Dataset 소속, Golden 정책, 도구/모델 구성, 실행 상한을 검증한다.
2. `(experiment_id, idempotency_key)`와 canonical request hash로 중복을 판단한다. 같은 요청은 기존 Batch를 반환하고 다른 요청은 409다.
3. Batch와 Run N개, 모든 Case Run과 Evaluation 슬롯을 **한 트랜잭션**으로 만든다. 참조와 Repeat 수는 이때 고정한다.
4. commit 후 202를 반환한다. worker는 DB에 commit된 작업만 소비한다. 외부 큐와의 이중 쓰기는 없다.

동시 동일 키 요청은 DB unique constraint로 하나만 성공시키고 다른 요청은 기존 Batch를 조회한다. created_at은 실행 묶음의 식별자가 아니다.

## 실행 정책 기본안

사용자 규모가 아직 지정되지 않아 다음은 작은 팀용 시작값 제안이다. 실제 provider 제한과 첫 부하 검증 후 조정한다. 값을 바꿔도 기존 Batch의 snapshot은 바꾸지 않는다.

| 항목 | 기본안 |
| --- | --- |
| Case/Experiment | 1~100 |
| Repeats | 1~10; Batch당 Case Run 최대 1,000 |
| worker | 첫 배포 1개, 진행 중 작업 최대 4개 |
| 동시성 | Agent와 Judge가 같은 worker 슬롯 상한을 공유; 먼저 queued된 작업 우선 |
| max_turns | 모델 호출 10회; retry는 같은 turn의 별도 attempt |
| Agent 전체 timeout | 120초; 호출·도구·retry 대기를 포함 |
| 개별 모델 / 도구 / Judge timeout | 각각 60초 / 10초 / 60초, 남은 전체 제한보다 길 수 없음 |
| 호출 retry | 최초 포함 최대 3 attempts, 1초 기반 지수 backoff+jitter, 대기 상한 10초 |
| heartbeat / lease | 5초 / 30초; DB 시각으로 판정 |
| 정리 종료 대기 | 10초 뒤 lease 복구에 맡김 |

Agent 도구는 한 Case Run 안에서 모델이 반환한 순서대로 실행한다. Case Run끼리는 병렬 가능하다. 여러 worker·provider별 분산 rate limit은 상한 검증 후 확장한다.

## Agent 실행 계약

첫 예시는 OpenAI 모델과 개발자가 Python decorator로 등록한 날씨 조회 HTTP 도구다. SDK adapter와 등록 계약은 [agent-runtime.md](agent-runtime.md)를 따른다. 아래 loop 규칙은 관찰할 동작 계약이며 SDK와 별도 loop를 중복 구현하라는 뜻이 아니다.

- 입력은 Test Case의 명시적 입력 메시지와 Prompt 계약의 입력이다. Python Prompt 자산을 실행 시 평가하여 `system_prompt: str`을 얻고, 누락 변수·결과 타입을 모델 호출 전에 검사한다. 원문을 발행 시 계산한 문자열로 대체하지 않는다. Case Run별 실행 단위·격리·실제 값 기록은 [python-assets.md](python-assets.md)를 따른다.
- Agent와 Judge는 각각 Setup에 고정된 사용자 Execution Environment를 사용한다. 가상환경과 dotenv의 현재 내용을 작업 시작 때 해석하고 실제 버전 관측을 기록한다. 재시도는 같은 작업에서 해석한 환경을 유지한다. 환경이 누락되거나 필요한 key·패키지가 없으면 모델 호출 전에 명시적으로 실패한다. [runtime-environments.md](runtime-environments.md)를 따른다.
- 매 모델 응답은 Final Answer, Tool Calls, 오류 중 하나로 해석한다. Tool Calls가 있으면 등록된 이름과 JSON schema로 인자를 검증하고 순서대로 실행한 뒤 결과를 다음 모델 호출에 넣는다.
- 등록되지 않은 도구, 잘못된 인자, 도구 실행 실패는 오류 Trace를 남기고 해당 Case Run을 실패로 끝내는 것을 첫 정책으로 한다. 모델의 자가 수정 루프는 후속 변경으로 별도 고정한다.
- 유효한 최종 텍스트 응답을 받으면 `succeeded`다. 빈/해석 불가능한 응답, turn 한도 초과, timeout은 각각 명시적 실패다.
- Tool 결과를 Prompt/권한 설정 변경 명령으로 해석하지 않는다. 도구 이름·주소·권한은 Setup의 고정 계약에서 가져온다.
- Agent 실행 코어는 메시지/도구 호출/종료 판단을 다루고 I/O는 port를 호출한다. 웹/DB 없는 동일 계약이 이후 Python export의 기반이 된다.

## 상태

### Case Run: Agent 실행

| 상태 | 의미 |
| --- | --- |
| pending | 아직 점유되지 않음 |
| running | 유효한 lease로 실행 중 |
| succeeded | Final Answer와 실행 결과 확정 |
| failed | 명시적 오류 또는 worker 점유 상실 |
| timed_out | Agent 전체 deadline 초과 |
| cancelled | 사용자 취소로 미실행 또는 중단 |

전이: `pending → running → succeeded/failed/timed_out/cancelled`, `pending → cancelled`. 터미널 상태를 다시 running으로 돌리지 않는다. worker 만료의 `running → failed`도 기록을 보존한다.

### Evaluation: 채점 작업

| 상태 | 의미 |
| --- | --- |
| pending | Agent 결과를 기다림 |
| queued | 채점 입력이 준비됨 |
| running | Judge 호출/검증 중 |
| scored | 모든 Rubric 항목이 검증·저장됨 |
| failed | 호출/검증 실패 또는 worker 점유 상실 |
| skipped | Golden 정책 또는 Agent 실패로 채점하지 않음; reason 필수 |
| cancelled | 사용자가 남은 채점을 취소함 |

Agent 성공 시 `pending → queued`, Golden skip이면 `pending → skipped(missing_golden)`. Agent failed/timed_out이면 `pending → skipped(agent_not_succeeded)`, Agent cancelled이면 `pending → cancelled`로 같은 저장 트랜잭션에서 처리한다.

Judge는 `queued → running → scored/failed`로 진행한다. 취소 시 `pending/queued/running → cancelled`가 가능하다. Agent가 성공했지만 평가 실패/skip인 경우 Agent 상태는 그대로 보존한다.

### Run: Agent 상태의 projection

Run의 `status`는 Agent 실행을 나타낸다. Case Run 전이 때 부모를 잠그고 아래 순서로 계산한다.

```text
nonterminal Case Run이 있음:
  아직 어떤 Case도 시작/종료하지 않았고 취소 요청도 없음 → queued
  그 외 → running
모든 Case Run이 terminal:
  취소 요청이 있고 cancelled Case가 하나 이상 → cancelled
  모두 succeeded → completed
  succeeded가 0 → failed
  그 외 → partially_failed
```

취소가 완료와 경합하여 이미 모든 Case가 성공한 경우 `completed`를 유지한다. 취소 의도(`cancel_requested_at`)와 실제 영향(`cancelled` 개수)을 따로 보존한다. 성공 뒤 실패한 Judge 때문에 Run의 Agent 상태를 failed로 바꾸지 않는다.

Run 조회는 Evaluation 상태별 개수와 `evaluation_complete`(모두 terminal), `pipeline_complete`(Agent와 Evaluation 모두 terminal)를 별도로 제공한다. `pipeline_complete`가 true여도 미평가가 있으면 공식 품질 비교 준비 상태는 아니다.

전부 취소된 Run은 failed가 아니다. Run 상태를 worker가 임의로 지정하는 별도 ‘Run 실패’ 경로를 두지 않는다. 구성 오류는 등록 시 거부하고 호출 시 드러난 오류는 해당 Case/평가 작업에 기록한다.

## 점유, 외부 호출, 결과 확정

1. 짧은 트랜잭션에서 대상 부모 Run과 작업을 공통 잠금 순서로 잠근다. 선택은 `SKIP LOCKED`를 사용하고 pending/queued 상태를 다시 확인한다.
2. 작업을 running으로 바꾸고 `lease_token`, `lease_expires_at`, `worker_id`를 저장한다. commit한다.
3. DB 트랜잭션 밖에서 모델·도구를 호출한다. heartbeat는 짧은 별도 트랜잭션으로 유효한 token의 lease만 연장한다.
4. Trace append, 사용량 기록, 결과 확정은 매번 token·running 상태·만료 시각을 확인하는 조건부 변경으로 처리한다. seq 할당과 append도 그 트랜잭션에 속한다.
5. 종료 변경과 관련 Evaluation 전이/Run projection을 한 트랜잭션에서 확정한다. 결과를 보낸 뒤 늦게 도착한 중복 완료는 결과를 덮어쓰지 않는다.

lease 만료 시 복구기는 부모/작업을 잠그고 token을 무효화한다. running Agent는 `failed(worker_lost)`, running Evaluation은 `failed(worker_lost)`로 종료한다. pending/queued 작업은 계속 처리한다. 자동으로 Agent를 처음부터 재실행하지 않는다. 사용자는 새 Batch를 실행할 수 있다.

이 정책은 외부 호출의 exactly-once를 보장하지 않는다. provider가 처리했으나 응답을 받지 못했을 수 있으며 비용도 미확인일 수 있다. DB에 같은 결과가 중복 확정되는 것을 막고, 알 수 없는 외부 결과를 사실대로 남긴다.

## Retry

- 429, 재시도 가능한 5xx/연결 오류에만 적용한다. provider가 준 retry 지연이 남은 deadline을 넘으면 종료한다.
- **개별 모델 호출**을 같은 메시지로 재시도한다. Agent 전체 흐름이나 이전 도구 호출을 반복하지 않는다.
- 인증/설정 오류, 잘못된 출력, 인자 오류, 도구 오류, 전체 deadline 초과는 재시도하지 않는다.
- HTTP 도구 자동 retry는 첫 정책에서 하지 않는다. 부작용 없는 요청인지 보장할 계약을 도입할 때 확장한다.
- Judge도 개별 호출에 같은 정책을 적용한다. 부분 응답은 평가 점수로 공개하지 않는다.
- SDK retry와 application retry가 겹치지 않게 한다. 모든 attempt에 call ID와 attempt 번호를 남긴다.

## 취소와 종료

취소 단위는 Run이다. Experiment 화면의 Batch 전체 취소는 해당 Run들에 같은 취소 요청을 적용하는 UI 동작이다. 취소 요청을 여러 번 보내도 추가 효과가 없다.

- pending Case Run과 시작 전 Evaluation은 즉시 cancelled로 전환한다.
- running 작업은 각 호출 전후와 heartbeat에서 취소를 확인한다. 취소 이후 새 모델·도구·Judge 호출을 시작하지 않는다.
- 실행 중 외부 요청은 가능하면 취소하되 provider의 처리/과금까지 취소됐다고 주장하지 않는다. 취소 뒤 받은 응답은 이미 종료된 결과를 덮어쓰지 않는다.
- Agent 성공 뒤 Judge만 남아 있으면 Agent 결과는 보존하고 Evaluation을 취소한다. Run의 Agent status는 completed일 수 있다.
- 종료한 Run이라도 Judge가 진행 중이면 pipeline 취소가 가능하다. 모든 작업이 terminal이면 현재 결과를 반환한다.
- worker 정상 종료 시 새 선점을 멈추고 제한 시간 동안 정리한다. 강제 종료/프로세스 중단은 lease 복구와 같은 규칙을 따른다.

## Trace와 호출 기록

Agent Trace는 `case_run_id`, `seq`, `event_type`, `occurred_at`, `payload_schema_version`, `payload`를 갖는다. seq는 관측·저장 순서다.

| event_type | 주요 내용 |
| --- | --- |
| user_input | 입력, Case Version; 실제 시작 때 1회 |
| model_call_started / model_call_finished | call_id, attempt, 요청/응답, 공개 사용량, duration, provider request ID |
| model_output | provider가 공개한 중간 텍스트/요약; 내부 추론 수집을 전제하지 않음 |
| tool_call / tool_result | call_id, tool Version/구현 참조, 인자/결과, is_error |
| final_answer | 최종 답변; 성공 때 1회 |
| error | 분류, 원인, retry 여부, call_id/attempt |
| execution_cancelled / execution_interrupted | 사용자 취소 또는 worker 상실 |

`tool_result.call_id`는 해당 `tool_call`을 연결한다. 프로세스가 죽으면 결과 이벤트가 없을 수 있다. 복구기가 가짜 도구 응답을 만들지 않고 interruption을 남긴다. UI는 열린 호출과 누락 결과를 표시한다.

Judge의 요청/응답/attempt는 Evaluation에 연결된 호출 기록으로 저장한다. 채점 근거는 모델이 반환한 사용자 표시용 설명이다. 내부 chain of thought를 요구하지 않는다.

호출 기록에는 provider/model 요청값·응답 model ID(제공될 때), 구현 버전, 타임스탬프, 오류, 사용량, 가격 근거와 계산된 비용을 남긴다. Agent/Judge 비용을 나누고 retries의 확인된 비용도 포함한다. 알 수 없는 사용량/가격은 null과 coverage로 표현한다. 현재 단가로 과거 비용을 다시 쓰지 않는다.

Trace/도구 결과의 크기 상한은 [agent-runtime.md](agent-runtime.md)의 날씨 도구/Trace 기본안을 따른다. 초과 원문을 무한 저장하지 않으며 잘림/저장 누락 여부와 원래 크기(알 때)를 표시한다. 비밀 값·인증 헤더는 저장 대상에서 제외한다.

## 재현성의 범위

저장할 것은 선택된 Version, 실행 코어/도구 구현 버전, 실행 정책, 실제 호출과 사용량, 외부 응답이다. Repeats는 이 조건 아래의 관측 변동을 측정한다. Judge와 외부 날씨 데이터도 달라질 수 있어 Agent sampling만의 분산이라고 해석하지 않는다.

Python 자산은 같은 원문에서도 실행 시각 등에 따라 다른 값을 만든다. 실제 생성된 Prompt/평가 설정도 기록하며 같은 Version을 같은 최종 문자열로 취급하지 않는다. Git 저장소·commit·파일 누락, 원문 hash 불일치, 코드 실행·결과 검증 실패는 모델/Judge 호출 전에 해당 작업의 명시적 오류로 남긴다.

첫 인수 테스트는 고정 날씨 응답을 사용하고 live smoke는 실제 응답과 조회 시각을 저장한다. 역사적 조건의 조회·검산과 동일 출력 재생산을 구분한다.
