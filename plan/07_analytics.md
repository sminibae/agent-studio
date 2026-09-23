# 07 분석과 비교

상태: 미착수. 선행: 04 실행 이력 + 06 검증된 평가 결과·호환 계약.

## 목표

8 Scope에서 지표와 비교 가능성을 설명하고 퇴행 Case에서 양쪽 Trace까지 이동한다.

## 구현 순서

- [ ] **07-1 Scope·비교 가능성** — Agent Setup × Case × Repetition의 8 Scope를 API와 URL/화면 상태로 연결한다. owner·Case 집합·평가 조건·venv revision을 검사하고 environment_mismatch 등 거부 사유를 표시한다.

- [ ] **07-2 집계 규칙** — mean/pass rate/coverage/분포·안정성/latency/token/cost를 backend에서 계산한다. 실패·미평가·진행 중·빈 Scope·비용 unknown의 분모를 명시한다.

- [ ] **07-3 비교와 탐색** — Overview/Setups/Cases/Traces/Metrics를 연결한다. A/B Δ·승패·회귀 Case와 반복별 분포에서 Agent/Judge 근거까지 탐색한다. 프런트에서 채점 규칙을 재구현하지 않는다.

- [ ] **07-4 검산과 조회 부하** — 설계의 8 Case Run fixture와 누락/동적 기준 불일치 fixture로 검산한다. 실제 조회의 EXPLAIN과 데이터 크기를 보고 필요한 인덱스·pagination을 조정한다.

## 착수 시 정할 것

비교 조건은 06의 동적 평가 계약을 재사용한다. 캐시·Trace 외부 저장·통계 검정은 측정/요구가 있을 때 별도 결정한다.

## 완료 확인

- [ ] A 평균 0.85/B 0.75/Δ -0.10, pass rate 100%/50%와 두 번째 Case 회귀를 화면·API에서 확인한다.
- [ ] 기준이 다른 실행의 공식 Δ/승패는 거부하고, 실패·미평가를 0점으로 합산하지 않는다.
- [ ] 8 Scope와 빈/부분 완료 데이터, 교차 owner ID·cursor를 테스트한다.
- [ ] 비교 → 회귀 Case → A/B Trace의 deterministic E2E와 관련 check/integration을 통과한다.

## 참고

[analytics.md](../docs/analytics.md), [ui-ux.md](../docs/ui-ux.md), [engineering.md](../docs/engineering.md), [data-model.md](../docs/data-model.md)

진행 순서와 상태는 [전체 계획](00_start.md), 재개 지점은 [handoff](handoff.md)를 따른다.
