# 06 평가

상태: 미착수. 선행: 03의 Evaluation Setup 구조 + 04의 작업/기록 경계; live Judge는 05 adapter 재사용.

## 목표

Agent 실행과 독립적으로 Judge 평가를 처리하고 검증된 점수만 공개한다.

## 구현 순서

- [ ] **06-1 평가 자산·비교 계약** — Judge Prompt/Model·Rubric·Scoring 편집·발행과 Evaluation Setup을 완성한다. 동적 결과와 입력으로 평가 조건 fingerprint/호환 판정 규칙을 정하고 설계·fixture에 고정한다.

- [ ] **06-2 평가 작업** — Agent 성공 후 queued 평가를 점유한다. Judge의 별도 고정 venv와 dotenv에서 실행하며 도구 권한을 주지 않는다. Agent 실패/취소 시 평가 상태 규칙을 적용하고 Agent/Judge 합산 슬롯을 사용한다.

- [ ] **06-3 결과 검증과 공개** — 실제 Judge Prompt/Rubric/Scoring 값을 호출 전에 기록한다. 누락·중복·범위 밖 점수를 거부하고 완전한 항목 결과와 정규화 가중 평균을 원자적으로 공개한다.

- [ ] **06-4 평가 UI·실패 복구** — Case Run에서 항목 점수·근거·Golden·Judge 기록을 조회한다. pending/queued/running·실패·skip·취소와 정상 결과를 구분하고 timeout·lease 만료·늦은 쓰기를 검증한다.

## 착수 시 정할 것

Rubric/Scoring 결과 변수와 평가 입력 범위, 동적 평가 조건의 비교 키는 06-1에서 먼저 정한다. 같은 Setup/Version ID만으로 비교 가능하다고 판단하지 않는다. 재평가 기능은 후속 범위다.

## 완료 확인

- [ ] fake Judge 정상/누락/중복/범위 밖 응답과 계산 경계를 손으로 검산 가능한 수치로 검증한다.
- [ ] 부분 결과는 점수로 공개되지 않는다. Agent 성공/Judge 실패를 Agent 실패나 0점으로 바꾸지 않는다.
- [ ] 별도 Agent/Judge 환경과 두 owner의 결과 격리를 실제 DB/worker에서 검증한다.
- [ ] 평가 성공·실패·취소 E2E와 관련 check/integration을 통과한다. live Judge smoke는 credential이 준비되면 별도로 기록한다.

## 참고

[analytics.md](../docs/analytics.md), [execution.md](../docs/execution.md), [data-model.md](../docs/data-model.md), [python-assets.md](../docs/python-assets.md), [agent-runtime.md](../docs/agent-runtime.md)

진행 순서와 상태는 [전체 계획](00_start.md), 재개 지점은 [handoff](handoff.md)를 따른다.
