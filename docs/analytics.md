# Analytics

이 문서는 지표와 비교 계약을 정의한다. [START.md](START.md)의 8 Scope에 공통 규칙을 적용하고 지표마다 관측 집합과 분모를 명시한다.

## 분석 입력

축은 `Agent Setup × Test Case Version × Repetition`이다. Repetition은 명시적으로 선택한 Run들이다. 여러 Setup을 비교하려면 여러 Experiment를 선택해야 한다.

선택 순서는 호환되는 Evaluation Setup → 복수 Experiment/Execution Batch → 각 Setup의 Run → 공통 Case Version 범위 → Baseline이다. 첫 기본안은 Setup당 Batch 하나, Batch 안의 Run 일부 또는 전체다. 서로 다른 실행 시점의 Batch를 몰래 합치지 않는다.

API 입력은 구체적인 `batch_ids`, `run_ids_by_setup`, `test_case_version_ids`, `baseline_setup_id`를 담는다. 서버는 소속·중복·빈 집합·권한을 검증한다. 결과에 해석된 Scope와 계산 정책 `analytics-v1`, 집계 기준 시각을 반환한다. 단일 일관된 DB snapshot에서 질의하여 한 응답에 서로 다른 시점의 상태를 섞지 않는다.

| Setup | Case | Repetition | 질문 / 기본 진입 |
| --- | --- | --- | --- |
| 1 | 1 | 1 | 이 실행은 어떻게 답했는가? / Traces |
| 1 | 1 | N | 같은 입력의 결과가 흔들리는가? / Overview |
| 1 | N | 1 | 어느 Case에 약한가? / Cases |
| 1 | N | N | 여러 Case를 반복해도 안정적인가? / Overview |
| N | 1 | 1 | 같은 Case에서 어떤 차이가 있었는가? / Traces |
| N | 1 | N | 같은 Case에서 어떤 Setup이 안정적인가? / Overview |
| N | N | 1 | 전체 Case에서 무엇이 좋아졌는가? / Setups |
| N | N | N | 평균·안정성·퇴행은 어떻게 다른가? / Overview |

Scope는 모든 분석 탭에 유지한다. 반복이 1이면 표준편차를 0으로 표시하지 않고 ‘반복 없음’으로 표시한다. Setup이 하나면 비교 열을 만들지 않는다.

## 비교 가능성

공식 Δ/Win/Loss/Regression을 계산하려면 다음을 만족해야 한다.

1. **같은 Evaluation Setup ID**를 사용한다. Dataset/Golden/Judge Prompt/Judge Model/Rubric/Scoring Rule의 Version 참조와 missing Golden 정책을 고정한다. Python 평가 자산의 실제 결과가 같다는 보장은 별도로 필요하다.
2. 정확히 같은 Test Case Version 집합을 선택한다. 입력의 Definition 이름만 같아서는 부족하다.
3. Setup별로 같은 수의 Run을 선택하여 Case별 계획 반복 수가 같다.
4. 선택 범위의 Agent와 Evaluation 작업이 모두 terminal이고 cancelled 관측이 없다.
5. Agent 성공 관측의 Evaluation이 모두 scored다. Judge 실패·Golden skip을 포함하면 공식 품질 비교는 미완성이다.

조건이 다르면 구성·원본 결과·각자의 기술 통계는 나란히 볼 수 있지만 공식 Δ/승패/순위를 반환하지 않는다. API는 `comparable: false`와 이유/빠진 개수를 반환한다. UI는 호환된 Run 또는 범위를 다시 선택하게 한다. 서로 다른 기준을 경고만 달고 숫자로 비교하는 기능은 첫 버전에 넣지 않는다.

동적 Judge/Rubric/Scoring 결과의 호환 판정은 구현 전 확인 항목이다. 같은 Setup ID만으로 같다고 간주하지 않고 실제 결과 기록을 확인한다. 호환 판정이 정해지기 전에는 평가 조건이 달라지거나 확인되지 않은 관측에 공식 비교를 허용하지 않는 것을 기본안으로 둔다. 항목별 점수 정규화·검산도 당시 사용한 Rubric/Scoring 결과를 사용하며 원문을 재실행하지 않는다. 상세 미결 사항은 [python-assets.md](python-assets.md)를 따른다.

같은 Setup을 복제한 별도 Evaluation Setup ID의 의미상 호환 판정, 교집합 비교, 불균형 반복 통계는 후속 기능이다. 공통 범위를 선택하는 것은 명시적 사용자 선택이어야 하며 원래 선택에서 제외된 Case 수를 표시한다.

현재 범위에 실패가 많다는 이유로 실패한 Run/Case를 자동 제외하지 않는다. 사용자가 범위를 줄이면 그 범위를 결과에 그대로 표시한다. `repeat_index`가 같다고 난수나 외부 환경이 통제된 paired observation이라고 주장하지 않는다.

비교 조건을 만족하더라도 코드/runtime artifact, 실행 정책, 실행 시각이나 실제 도구 응답이 다르면 환경 차이로 표시한다. 공식 비교는 정의된 범위의 기술 통계이며 Agent 변경만이 원인이라는 인과관계나 통계적 유의성을 보장하지 않는다.

## 채점 계약

첫 Scoring Rule 제안은 `weighted_mean_v1`이다. Rubric 항목 i는 고유 key, 최소값 `min_i`, 최대값 `max_i`, 점수가 높을수록 좋다는 의미를 가진다. `max_i > min_i`이고 가중치는 유한한 0 이상, 전체 합은 양수다. Threshold는 [0,1]이다.

```text
normalized_i = (raw_i - min_i) / (max_i - min_i)
Case Score = sum(weight_i * normalized_i) / sum(weight_i)
Case Pass = Case Score >= pass_threshold
```

모든 항목을 정확히 한 번 받아야 한다. 누락·중복·알 수 없는 key·범위 밖·NaN/무한대는 Evaluation 실패다. 일부 항목을 빼고 가중치를 재정규화하지 않는다. UI 표시만 반올림하고 통과/동점 판정은 반올림 전 값으로 한다.

예: 정확성 0~4에 weight 3, 간결성 0~2에 weight 1, 원점수 3과 2이면 `(3×0.75 + 1×1)/4 = 0.8125`다. Threshold 0.8이면 통과다.

## 관측 집합과 누락

선택한 Setup별로 다음 집합을 정의한다.

| 기호 | 관측 |
| --- | --- |
| P | Scope가 계획한 모든 Case Run 슬롯 |
| F | Agent가 failed 또는 timed_out으로 종료 |
| Q | Agent succeeded이고 Evaluation scored |
| U | Agent succeeded이나 Evaluation이 아직 scored가 아님 |
| X | Agent cancelled |
| W | Agent pending/running |
| M | 유효 품질 관측 `F ∪ Q` |

F에는 `effective_score=0`, `effective_pass=false`를 부여한다. 저장된 Judge 점수를 만들지는 않는다. Q는 검증된 Case Score/Pass를 쓴다. **U/X/W의 점수는 null**이다. 평가 실패를 Agent 오답으로 취급하지 않는다. Threshold가 0이어도 Agent 실패는 pass가 아니다.

P는 반드시 `F + Q + U + X + W`로 분해된다. `Quality Coverage = |M| / |P|`, `Evaluation Coverage = |Q| / (|Q| + |U|)`다. 분모가 0이면 값은 null과 이유를 반환한다.

U/W가 있으면 현재 품질 통계는 `provisional`로, X가 있으면 `incomplete`로 표시한다. 요약은 품질 수치 옆에 coverage와 각각의 누락 이유를 함께 표시한다. M만 평균 내어 완성된 결과처럼 표시하지 않는다.

## 품질·운영 지표

| 지표 | 계산과 분모 |
| --- | --- |
| Mean Score (observed) | `sum(effective_score) / |M|`; 기본 품질 수치, coverage 필수 |
| Pass Rate (observed) | `count(effective_pass) / |M|`; F는 실패로 포함 |
| Mean Score (scored only) | Q의 Case Score 평균; 채점된 성공 결과의 품질 |
| Rubric Item Score | Q의 항목별 normalized score 평균; F를 가짜 항목 점수로 만들지 않음 |
| Execution Failure Rate | `|F| / (|F| + |Q| + |U|)`; 종료한 미취소 Agent 기준 |
| Cancellation Rate | `|X| / |P|` |
| Mean/P50/P95 Agent Latency | Agent succeeded 관측(Q+U)의 실행 시간; Judge 제외, 표본 수 표시 |
| Agent/Judge/Total Cost | 각각의 확인된 호출 비용 합; retry 포함, null 호출 수/coverage 표시 |
| Token Usage | 확인된 Agent/Judge input/output 사용량 합과 역할별 관측당 평균 |
| Tool Call Count | 시작한 tool_call 수; 실패한 호출 포함 |

비용·토큰의 Case당 평균은 역할별 **실제 호출을 시작한 Case Run 수**로 나눈다. Judge가 여러 번 retry해도 Case당 분모는 1이다. 확인하지 못한 비용이 있으면 평균/합계를 ‘확인된 부분’으로 표시한다. 미시작 관측의 비용 0과 시작했으나 알 수 없는 비용 null을 구분한다.

Latency의 P50/P95는 정렬 표본 x에 `h=(n−1)p`, 양쪽 값의 선형 보간을 적용한다. n=1이면 단일 관측이며 표본 1이라고 표시하고 n=0이면 null이다. 실패/timeout 소요시간은 별도로 보여준다.

서로 다른 Case를 집계할 때 기본 Mean은 M 관측을 동일 가중하는 micro 평균이다. 공식 비교는 완전하고 반복 수가 같은 범위만 허용하므로 Case별 평균의 평균과 같다. 미완료 범위에서는 이 등가성을 전제하지 않는다. Case weight는 첫 버전에서 제공하지 않는다.

## 안정성과 비교

같은 Setup·Case의 **선택 반복이 모두 M에 포함되고 n≥2**인 경우만 안정성을 계산한다.

- Std Dev: Case별 effective_score의 표본표준편차, 분모 n−1. 요약은 유효 Case의 단순 평균과 유효 Case 수다.
- Score Range: Case별 max−min.
- Pass Consistency: 모든 반복이 통과하거나 모두 실패한 유효 Case 수 / 안정성을 계산할 수 있는 Case 수.
- Flaky Case: 반복에 pass와 fail이 함께 있는 Case.

관측 1개와 미평가 때문에 1개만 남은 경우를 구별해서 표시한다. Judge 변동과 외부 응답 변화도 섞이므로 Agent 자체의 비결정성만의 수치라고 부르지 않는다. 신뢰구간·통계적 유의성 검정은 첫 버전에 넣지 않으며 반복 수를 표시한다.

공식 비교에서 Baseline은 선택 Setup 중 하나다. 후보가 여러 개면 각각 Baseline과 비교한다.

| 지표 | 규칙 |
| --- | --- |
| Δ Mean Score | 후보 전체 평균 − Baseline 전체 평균 |
| Win/Tie/Loss | Case별 반복 평균 차이로 판정; `abs(diff) <= 0.01`이면 Tie, 양수 Win, 음수 Loss |
| Win Rate | Win / 전체 비교 Case 수; Tie 포함 |
| Regression | Baseline의 Case 반복 평균 >= threshold, 후보는 < threshold |
| Improvement | 위의 반대 |

Tie 폭 0.01은 [0,1] 점수의 분석 기본 정책이다. Threshold 판정과 Tie 판정은 별개라서 Tie인 Case도 threshold를 넘나들면 Regression일 수 있다. 실행에 실패한 관측만 있는 Case는 평균 threshold가 0이더라도 통과 Case로 분류하지 않는다. 반복 평균 통과 판정에는 해당 Case에 적어도 하나의 Q가 있어야 한다.

## 검산 예시

Scope에 4개 Case Run이 있고 Q 점수 1.0과 0.6, Agent 실패 F 1개, Judge 실패 U 1개라면:

- Mean Score (observed) = 1.6/3 ≈ 0.5333, Quality Coverage = 3/4.
- Threshold 0.7의 Pass Rate (observed) = 1/3. Judge 실패를 0점으로 더하지 않는다.
- Evaluation Coverage = 2/3, Execution Failure Rate = 1/4.
- U가 남아 있으므로 공식 Setup 비교를 하지 않는다. Judge 실패가 있는 현재 통계라는 설명을 보여준다.

취소뿐인 Scope는 Mean/Pass가 null이고 Cancellation Rate 100%다. 데이터 없음/미평가/실제 0점을 각각 다른 상태로 표현한다.

## 화면 계약

Scope / Overview / Setups / Cases / Traces / Metrics를 유지하는 것이 기본안이다.

- Overview: 품질·실행·평가 진행과 coverage, 공식 비교 가능할 때만 Δ/Regression.
- Setups: 구성 차이와 지표를 나란히 표시. 호환되지 않으면 각자 수치와 이유만 표시.
- Cases: Case × Setup 매트릭스, Case 평균/반복 수/누락 개수. 낮은 점수와 미평가를 구별해 정렬·필터.
- Traces: 같은 Case의 두 실행을 나란히 보기, 반복 전환, Judge 작업으로 이동.
- Metrics: 정의된 지표와 Setup/Case/Repetition 축을 선택해 지원하는 집계·분포를 확인한다. 계산식·분모를 표시한다. 임의 수식/SQL 작성 엔진은 제공하지 않는다.

집계는 백엔드에서 수행하고 프런트는 표시/탐색만 담당한다. 첫 구현은 DB 조회로 시작하고 캐시는 측정 후 도입한다. 정책을 변경하면 `analytics-v1`을 조용히 바꾸지 않고 새 버전과 검산 예시를 남긴다.

## Metrics의 축 선택 계약

지표 선택과 축별 grouping은 서버가 허용한 조합으로 한정한다. 품질/실패/비용은 Setup·Case·Repetition별 집계, 안정성은 같은 Case의 반복 집합, 비교는 Setup별 Baseline 대조를 지원한다. 의미 없는 조합은 이유와 함께 비활성화한다. UI에서 계산식을 재구현하지 않는다.
