# 구현 계획 안내

2026-09-23 저장소 확인 기준. 다시 시작할 때는 [handoff.md](handoff.md)를 먼저 읽는다.
설계 기준은 [docs/decisions.md](../docs/decisions.md), 검증 기준은
[docs/engineering.md](../docs/engineering.md)를 따른다. 아래 상태는 설계 문서의
완성도가 아니라 실제 코드의 구현 상태다.

## 현재 위치와 진행 순서

| 순서 | 계획 | 상태 | 다음 결과물 |
| --- | --- | --- | --- |
| 01 | [프로젝트 골격](01_project_skeleton.md) | 완료 | 기존 개발·검증 기반 유지 |
| 02 | [실행 기술 검증](02_runtime_spikes.md) | 진행 중 · 바로 시작 | 격리된 사용자 venv에서 SDK/Tool 실행 및 실패·취소 검증 |
| 03 | [자산과 Setup](03_assets_and_setups.md) | 미착수 | 환경 → Python 자산 발행 → 불변 Setup 생성·복제 |
| 04 | [실험 실행](04_experiment_execution.md) | 미착수 | fake Agent로 예약·실행·취소·Trace 조회 |
| 05 | [실제 Agent 연결](05_live_agent.md) | 미착수 | OpenAI + 날씨 HTTP 도구의 실제 실행 |
| 06 | [평가](06_evaluation.md) | 미착수 | Judge·Rubric·Scoring과 평가 상태·결과 |
| 07 | [분석과 비교](07_analytics.md) | 미착수 | 8 Scope와 A/B 비교 → 퇴행 Case → Trace |
| 08 | [배포와 운영](08_operations.md) | 미착수 | 두 계정 동시 사용·복구·백업·첫 완주 |

기본 순서는 02 → 03 → 04 → 05 → 06 → 07 → 08이다. 05의 credential 대기는
04의 deterministic 실행 경계가 준비된 뒤 06의 fake Judge 구현을 막지 않는다.
최종 배포 전에는 05의 live smoke까지 확인한다. owner 격리·비밀 제거·복구 검증은
각 단계에서 구현하며 08에서 처음 추가하지 않는다.

## 단계 진행 규칙

- 각 계획의 작은 단위 하나씩 API·저장·필요한 화면까지 연결한다.
- 미결사항은 해당 단계의 첫 작업에서 테스트 가능한 계약으로 정하고 담당 설계에 반영한다.
- 체크박스는 구현과 해당 검증이 끝났을 때만 완료한다. spike 결과와 제품 기능 완료를 구분한다.
- 02에서는 격리와 SDK 계약을 하네스로 검증한다. 실제 Version 저장은 03,
  worker·DB Trace 영속화는 04, 실제 provider 연결은 05에서 검증한다.
- 종료 시 해당 계획에 결과·명령·미검증 항목을 기록하고 handoff의 다음 작업을 갱신한다.

## 첫 완성본

화면에서 Setup 구성 → 실험 실행 → 평가 → 비교 → Trace 확인을 완주한다.
[첫 완주 인수 시나리오](../docs/engineering.md)의 두 Case × 두 Repeats × 두 Setup,
총 8 Case Run으로 평균 A 0.85 / B 0.75, Δ -0.10과 퇴행 Case를 검산한다.
첫 완성본 이후 항목은 Python export, 다중 Agent, 재평가, 외부 수집,
사용자 간 공유, 필요가 입증된 외부 큐·통계 검정이다.
