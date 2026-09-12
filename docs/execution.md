# Execution

이 문서는 Experiment를 실행하는 방식과 상태, 실패 처리, Trace 기록 규칙을 정의한다.

이 문서에서는 실행 기술을 선택하지 않는다. Celery, Temporal, Redis Queue 중 어떤 기술을 사용하더라도 아래 규칙은 동일하게 적용한다. 기술 선택은 `docs/architecture.md`에서 다룬다.

---

## 실행 파이프라인

```
Experiment
  ↓  실행 요청 1회 → Run N개 (N = repeats)
Run
  ↓  Case 범위의 Test Case마다 1개
Case Run
  ↓
Agent Execution
  ↓  실행 중 계속 append
Trace Events
  ↓
Final Answer
  ↓  Judge Model 호출
Evaluation
  ↓  Rubric 항목마다 1개
Evaluation Result
```

---

## Experiment 실행 과정

1. **검증:** Experiment의 Case 범위가 비어 있지 않은지 확인하고, Agent Setup과 Evaluation Setup이 참조하는 Definition Version이 모두 존재하는지 검사한다. 검증에 실패하면 Run을 만들지 않고 요청을 거부한다.
2. **Run 생성:** `repeats` 수만큼 Run을 `queued` 상태로 생성한다. 모든 Run은 하나의 트랜잭션에서 생성하여 일부만 저장되는 상황을 막는다.
3. **Case Run 생성:** 각 Run에 Case 범위의 Test Case Version마다 하나의 Case Run을 `pending` 상태로 미리 생성한다.
4. **실행:** 워커가 `queued` 상태인 Run을 가져와 Case Run을 순차 또는 병렬로 실행한다.
5. **평가:** Case Run이 `succeeded` 상태로 끝나면 Evaluation을 수행한다.
6. **집계:** 모든 Case Run이 종료 상태에 도달하면 Run의 최종 상태를 확정한다.

Case Run을 미리 모두 생성하면 진행률을 정확하게 표시할 수 있다. 실행 중에 전체 개수를 다시 계산할 필요가 없으며, 실행이 중단되어도 DB만 조회하면 남은 작업을 확인할 수 있다.

---

## Run 생성 규칙

- 실행 요청 1회는 Run을 `repeats`개 만든다. Repeats가 3이면 Run 3개다.
- `repeat_index`는 그 요청 안에서 1부터 매긴다. 같은 Experiment를 두 번 실행하면 `repeat_index`가 1..3인 Run이 두 벌 생긴다. 구분은 `created_at`으로 한다.
- Run이 하나라도 존재하는 Experiment는 수정할 수 없다. 수정하려면 새 Experiment를 만든다. 실행 이력의 의미가 변하지 않게 하기 위한 규칙이다.

### Repeats의 의미

Repeats는 **같은 조건을 몇 번 반복 실행할지**를 뜻한다. 측정 대상은 Agent 출력의 비결정성이다.

- Repeats는 Case 단위 반복이 아니라 Run 단위 반복이다. `Run = 전체 Case를 한 번씩 실행`이라는 정의를 지키기 위해서다.
- Analytics의 Repetition 축은 같은 Experiment에 속한 여러 Run을 가리킨다.
- Repeats > 1이어도 Agent Setup과 Evaluation Setup은 동일하다. 달라지는 것은 모델 샘플링뿐이다.

---

## Case Run 생성 규칙

- Run × Test Case Version 조합마다 Case Run을 정확히 하나 생성한다. 스키마의 고유 제약 조건이 이 규칙을 강제한다.
- 생성 시점 상태는 `pending`이며 실행 직전에 `running`으로 바꾼다.
- 같은 Run 안의 Case Run들은 서로 독립이다. 한 Case Run의 실패가 다른 Case Run의 실행을 막지 않는다.
- Run 단위 설정값으로 동시 실행 수를 제한한다. 처음에는 보수적인 기본값을 사용하고 모델 API의 Rate Limit에 맞춰 조정한다.

---

## Trace Event 종류

모든 이벤트는 `case_run_id`, `seq`, `event_type`, `started_at`, `duration_ms`, `payload`를 가진다. `seq`는 1부터 증가하며 기록 후 변하지 않는다.

| event_type | 언제 | payload 주요 필드 |
| --- | --- | --- |
| `user_input` | Case Run 시작 시 1회 | `input`, `test_case_version_id` |
| `model_call` | 모델 호출마다 | `model`, `request_messages`, `response`, `input_tokens`, `output_tokens`, `finish_reason` |
| `agent_reasoning` | 모델이 중간 추론을 내놓을 때 | `content` |
| `tool_call` | 도구 호출마다 | `tool_name`, `tool_version_id`, `arguments` |
| `tool_result` | 도구 결과마다 | `tool_name`, `result`, `is_error` |
| `final_answer` | Case Run 종료 시 1회 | `answer` |
| `error` | 오류 발생 시 | `error_type`, `message`, `retryable`, `attempt` |

규칙:

- `tool_call`과 `tool_result`는 서로 대응해야 한다. 도구가 실패하더라도 `is_error: true`인 `tool_result`를 남겨 디버깅에 필요한 이벤트가 누락되지 않게 한다.
- `error`는 Case Run을 끝내는 오류와 재시도된 오류 모두를 기록한다. 구분은 `retryable`과 `attempt`로 한다.
- 실패로 끝난 Case Run에는 `final_answer`가 없다. UI는 이 경우를 정상적으로 표현해야 한다.
- Trace는 append-only다. 이벤트를 수정하거나 삭제하지 않는다.

START.md의 예시를 이 모델로 옮기면 다음과 같다.

```
seq 1  user_input
seq 2  model_call        (agent reasoning 포함)
seq 3  tool_call         search_document
seq 4  tool_result       search_document
seq 5  model_call
seq 6  tool_call         get_price
seq 7  tool_result       get_price
seq 8  model_call
seq 9  final_answer
```

---

## 상태 정의

### Run 상태

| 상태 | 의미 |
| --- | --- |
| `queued` | 생성되었지만 워커가 아직 가져가지 않음 |
| `running` | 하나 이상의 Case Run이 실행 중 |
| `completed` | 모든 Case Run이 `succeeded` |
| `partially_failed` | 일부 성공, 일부 실패 |
| `failed` | 모든 Case Run이 실패 |
| `cancelled` | 사용자가 취소 |

### Case Run 상태

| 상태 | 의미 |
| --- | --- |
| `pending` | 생성되었지만 아직 실행되지 않음 |
| `running` | 실행 중 |
| `succeeded` | Final Answer 생성 완료 |
| `failed` | 오류로 종료 |
| `timed_out` | Runtime Parameter의 타임아웃 초과 |
| `cancelled` | Run 취소로 실행되지 않았거나 중단됨 |

### Evaluation 상태

Evaluation Result의 상태다.

| 상태 | 의미 |
| --- | --- |
| `scored` | 정상 채점 |
| `failed` | Judge 호출 실패 |
| `skipped` | Golden 없음 등 정책에 따라 평가 제외 |

---

## 상태 전이

```
Run:
queued → running → completed
queued → running → partially_failed
queued → running → failed
queued → cancelled
queued → running → cancelled

Case Run:
pending → running → succeeded
pending → running → failed
pending → running → timed_out
pending → cancelled
pending → running → cancelled
```

Run 상태는 다음 규칙에 따라 Case Run의 상태에서 계산한다.

```
모든 Case Run이 종료 상태일 때:
  succeeded 개수 == 전체        → completed
  succeeded 개수 == 0           → failed
  cancelled가 하나라도 있고
    실행된 것이 없음            → cancelled
  그 외                         → partially_failed
```

Run 상태는 저장하지만 직접 지정하지 않고 계산한 값만 사용한다. 이렇게 하면 Run 상태와 Case Run 상태가 서로 어긋나지 않는다.

---

## 실패 처리

실패를 두 종류로 나눈다.

**Case Run 실패:** 하나의 Case에서만 발생한 오류다. 모델 오류, 도구 오류, 타임아웃, 파싱 실패가 이에 해당한다. 해당 Case Run만 `failed` 상태로 바꾸고 나머지 Case Run은 계속 실행한다.

**Run 실패:** 실행 자체를 계속할 수 없는 상태다. Setup 참조가 유효하지 않거나 인증이 실패한 경우, 또는 워커가 중단된 경우가 이에 해당한다. 남은 Case Run을 `cancelled` 상태로 바꾸고 Run을 `failed`로 종료한다.

오류 분류는 `error_type`에 기록한다.

| error_type | 재시도 | 예 |
| --- | --- | --- |
| `rate_limit` | 재시도 | 모델 API 429 |
| `provider_error` | 재시도 | 5xx, 네트워크 오류 |
| `timeout` | 재시도 안 함 | Runtime Parameter 초과 |
| `tool_error` | 재시도 안 함 | 도구 실행 예외 |
| `invalid_output` | 재시도 안 함 | 출력 파싱 실패 |
| `config_error` | 재시도 안 함 | 참조 깨짐, 인증 실패 |

---

## Retry 정책

- 재시도는 `rate_limit`과 `provider_error`에만 적용한다. 나머지는 즉시 실패로 확정한다.
- 지수 백오프에 지터를 더한다. 기본값은 최대 3회, 초기 대기 1초, 배수 2다.
- **재시도는 기존 Case Run 안에서 처리한다.** 재시도를 위해 새 Case Run을 만들면 재시도 횟수가 Repeats에 포함되어 Analytics의 반복 통계가 왜곡된다.
- 각 재시도 시도는 `error` Trace Event로 남긴다. `attempt` 필드로 몇 번째 시도인지 구분한다.
- Evaluation 실패도 같은 정책으로 재시도한다. 최종 실패하면 Evaluation Result를 `failed` 상태로 남긴다. Case Run 상태는 바꾸지 않는다.

---

## 취소

- 취소 대상은 Run이다. Case Run 단위 취소는 제공하지 않는다.
- 취소 요청은 즉시 Run 상태를 `cancelled`로 바꾸지 않는다. 실행 중인 Case Run이 정리될 때까지 기다린다.
- `pending` Case Run은 즉시 `cancelled`가 된다. `running` Case Run은 현재 모델 호출이 끝나면 중단하고 `cancelled`로 둔다.
- 이미 끝난 Case Run의 결과는 그대로 보존한다. 취소는 기록을 지우지 않는다.

---

## 부분 실패

Partial Failure는 시스템 오류가 아니라 실행 과정에서 발생할 수 있는 결과다.

- `partially_failed` 상태인 Run도 Analytics에 포함한다. 제외하면 실패가 많은 Setup의 결과가 실제보다 좋아 보일 수 있다.
- 지표를 계산할 때 분모를 명확히 한다. Pass Rate의 분모는 성공한 Case Run이 아니라 전체 Case Run이다. 자세한 정의는 `docs/analytics.md`에 있다.
- UI는 Run의 성공·실패 개수를 상태 옆에 항상 같이 보여준다.

---

## 멱등성과 재실행

- 실행 요청은 클라이언트가 보낸 요청 키로 멱등 처리한다. 같은 키로 두 번 요청해도 Run이 두 벌 생기지 않는다.
- 워커가 중단되어 `running` 상태로 남은 Run은 하트비트 타임아웃이 지나면 회수한다. 회수한 Run에서 `running` 상태였던 Case Run을 `failed`로 바꾸고 Run 상태를 다시 계산한다.
- 이미 끝난 Run은 재실행하지 않는다. 다시 실행하려면 같은 Experiment를 다시 실행해 새 Run을 만든다. 기존 Run을 덮어쓰면 이력이 사라진다.

---

## 열린 질문

- **Case Run 병렬 실행 수준.** 지금은 Run 안에서 Case Run을 병렬 실행하고 동시 실행 수를 제한한다. Run 자체를 병렬로 돌릴지, 모델별 rate limit을 어디서 관리할지는 정해지지 않았다.
- **Evaluation을 Case Run 직후에 할 것인가, Run 종료 후 일괄로 할 것인가.** 지금은 Case Run 직후다. 결과를 빨리 볼 수 있지만 Judge 호출이 Agent 실행과 rate limit을 나눠 쓴다.
- **재평가 기능.** 같은 Case Run을 다른 Evaluation Setup으로 다시 채점하는 기능은 도메인상 가능하지만 MVP 범위에 넣지 않았다. 넣는다면 Evaluation Result에 `evaluation_setup_id`를 추가해야 한다.
- **하트비트 타임아웃 값.** 워커 구현을 고른 뒤 정한다.
