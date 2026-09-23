# 04 실험 실행

상태: 미착수. 선행: 03의 환경·자산·최소 Setup.

## 목표

fake Agent로 실행 등록부터 Trace 조회까지 제품의 실행 생명주기를 완성한다.

## 구현 순서

- [ ] **04-1 원자적 실행 등록** — Experiment·Batch·Run·Case Run 및 최소 Evaluation 예약 레코드를 추가한다. Case 범위·Repeats·불변 참조를 검증하고 idempotency와 queue 상한을 같은 트랜잭션으로 처리한다. Evaluation 처리기는 06에서 붙인다.

- [ ] **04-2 공정 점유와 예약** — 별도 worker와 PostgreSQL polling, owner 순환 점유, 전체 4/owner별 2 슬롯을 구현한다. Agent/Judge 합산 예약과 owner 5,000/전체 20,000 미종료 작업 한도를 적용한다. 환경 설치·미리보기 자원 제한도 연결한다.

- [ ] **04-3 실행과 점진 기록** — 02의 검증된 실행 경계를 AgentRuntime port로 연결한다. fake provider로 실제 Prompt/Tool 결과를 호출 전에 기록하고 상태·attempt·usage·Trace를 점진 저장한다. 사용자 실행 프로세스에 DB credential을 주지 않는다.

- [ ] **04-4 취소·복구** — lease/heartbeat/fencing, deadline, worker 중단, 늦은 쓰기 차단과 orphan container 정리를 구현한다. 컨테이너 정리 확인 전 슬롯을 반환하지 않고 실행 중 Agent를 자동 재실행하지 않는다.

- [ ] **04-5 실행 화면** — Experiment 생성·실행, Batch/Run/Case Run 상태·취소, Trace 상세를 연결한다. Agent 완료·평가 대기를 별도 표시한다.

## 착수 시 정할 것

컨테이너 실행/정리 port, worker 기동 명령, lease 주기·polling 간격·종료 유예와 이벤트 DTO를 구현 전에 고정한다. 4/2 슬롯은 설계 기본값이며 실제 배포 용량은 08에서 측정한다.

## 완료 확인

- [ ] Cases 2 × Repeats 3이 Batch 1/Run 3/Case Run 6으로 원자 생성된다. 같은 키 동시 요청은 하나만 만들고 다른 payload는 409다.
- [ ] 두 owner 동시 등록·점유가 슬롯/queue 상한을 넘지 않는다. 취소·lease 만료·정리 실패에도 늦은 성공과 Trace 쓰기가 차단된다.
- [ ] provider 실패·retry·부분 취소·Agent 완료/평가 대기 상태와 비용 unknown을 구분한다.
- [ ] 실제 PostgreSQL 동시성 integration과 fake provider E2E를 추가한다. 기존 health E2E 통과만으로 완료 처리하지 않는다.

## 참고

[execution.md](../docs/execution.md), [scheduling.md](../docs/scheduling.md), [data-model.md](../docs/data-model.md), [architecture.md](../docs/architecture.md), [engineering.md](../docs/engineering.md)

진행 순서와 상태는 [전체 계획](00_start.md), 재개 지점은 [handoff](handoff.md)를 따른다.
