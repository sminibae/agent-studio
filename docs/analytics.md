# Analytics

이 문서는 Analytics에서 계산할 지표와 Scope별 화면 구성을 정의한다.

사용자가 선택한 Scope에 따라 분석할 질문과 화면 구성이 달라진다. 같은 데이터라도 Scope가 다르면 서로 다른 관점으로 제시해야 한다.

---

## Scope 모델

분석 범위는 세 축의 조합이다.

```
Agent Setup × Case × Repetition
```

| 축 | 1 | N |
| --- | --- | --- |
| Setup | Agent Setup 하나 | Agent Setup 둘 이상 |
| Case | Test Case 하나 | Test Case 둘 이상 |
| Repetition | Run 하나 | 같은 Experiment의 Run 둘 이상 |

선택한 Scope는 Analytics의 모든 화면 상단에 계속 표시한다. 사용자는 이 정보를 통해 현재 보고 있는 데이터의 범위를 확인할 수 있다.

### 8가지 Scope

| # | Setup | Case | Repeats | 사용자가 알고 싶은 것 | 분석 성격 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | 1 | 1 | 이 실행에서 해당 답변이 나온 이유는 무엇인가? | Trace 관찰 |
| 2 | 1 | 1 | N | 같은 입력을 반복했을 때 품질이 안정적인가? | 분산 |
| 3 | 1 | N | 1 | 이 Setup은 여러 Case를 얼마나 잘 해결하는가? | 분포 |
| 4 | 1 | N | N | 이 Setup은 여러 Case를 반복해서도 안정적으로 해결하는가? | 분포 + 분산 |
| 5 | N | 1 | 1 | 이 Case에서는 어떤 Setup의 결과가 더 좋은가? | Trace 대조 |
| 6 | N | 1 | N | 이 Case를 반복했을 때 어떤 Setup이 더 안정적인가? | 분산 비교 |
| 7 | N | N | 1 | 전체 Case 집합에서는 어떤 Setup의 성능이 더 좋은가? | 집계 비교 |
| 8 | N | N | N | 평균 성능과 안정성을 함께 보면 어떤 Setup이 더 좋은가? | 집계 + 분산 비교 |

### 여러 항목을 선택했을 때 추가되는 정보

각 Scope의 모든 화면을 따로 설계하지 않는다. 한 축에서 여러 항목을 선택할 때 추가할 정보를 정하고, 여덟 가지 Scope에는 그 규칙을 조합하여 적용한다.

| 축 | 1일 때 | N이 될 때 더해지는 것 |
| --- | --- | --- |
| Setup | 절대값을 그대로 읽는다 | 비교 열, 차이(Δ), 승패, Regression 목록 |
| Case | 한 Case의 값을 읽는다 | 분포, 집계, Case별 순위, 약점 Case 목록 |
| Repetition | 단일 관측값이다 | 분산, 신뢰구간, 결과 일관성, Flaky Case 목록 |

**Repetition이 1이면 분산 지표를 보여주지 않는다.** 관측값이 하나뿐인데 표준편차를 0으로 표시하면 안정적인 결과라고 오해할 수 있다. 이 경우에는 지표값 대신 "반복 없음"을 표시한다.

**Setup이 1이면 비교 UI를 보여주지 않는다.** 비교 대상이 없는데 Δ 열을 비워 두면 화면만 복잡해진다.

### 비교 가능성 검사

Setup 축이 N일 때는 비교 결과를 보여주기 전에 다음을 검사한다.

1. 비교 대상들이 같은 Case 집합을 가지는가
2. 같은 Rubric Version으로 평가됐는가
3. 같은 Scoring Rule Version을 쓰는가

하나라도 다르면 비교값은 계산하되, 화면 상단에 경고를 표시하여 서로 다른 항목을 명시한다. Rubric이 다른 실험도 비교해야 할 수 있으므로 계산 자체를 막지는 않는다. 사용자는 이 경고를 바탕으로 비교 결과가 유효한지 판단할 수 있다.

---

## 지표 정의

모든 지표는 Case Run과 Evaluation Result에서 계산한다. 같은 이름의 지표를 화면마다 다르게 계산하지 않도록 이 문서에서 계산식을 정의한다.

### 기본 집합

`C` = Scope에 포함된 Case Run 집합
`C_succeeded` = `C` 중 `status = succeeded`인 것
`C_terminal` = `C` 중 종료 상태에 도달한 것 (`cancelled` 제외)

**분모는 항상 `C_terminal`이다.** 실패한 실행을 분모에서 제외하면 실패가 많은 Setup의 결과가 실제보다 좋아 보일 수 있다.

### 품질 지표

| 지표 | 계산식 | 비고 |
| --- | --- | --- |
| Case Score | Scoring Rule을 Evaluation Result 항목들에 적용한 값 | Case Run 하나의 최종 점수 |
| Mean Score | `sum(Case Score) / count(C_terminal)` | 실패한 Case Run의 점수는 0으로 본다 |
| Pass Rate | `count(Case Score >= pass_threshold) / count(C_terminal)` | 임계값은 Scoring Rule이 정의 |
| Rubric Item Score | 항목별 평균 점수 | 어떤 기준에서 약한지 보는 용도 |

Mean Score를 계산할 때 실패한 Case Run을 0점으로 처리하는 방식과 아예 제외하는 방식은 서로 다른 질문에 답한다. 기본 지표에서는 실패를 0점으로 처리한다. 성공한 Case Run의 품질만 확인할 수 있도록 `Mean Score (succeeded only)`도 보조 지표로 제공한다. 두 값을 함께 표시하면 실패가 평균 점수에 미친 영향을 확인할 수 있다.

### 안정성 지표

Repetition 축이 N일 때만 계산한다.

| 지표 | 계산식 | 비고 |
| --- | --- | --- |
| Std Dev | 같은 Case의 반복 점수들의 표본표준편차 | Case 단위로 계산한 뒤 평균 |
| Score Range | 같은 Case의 반복 점수 max − min | 최악의 흔들림 |
| Pass Consistency | 반복 전체가 통과했거나 전체가 실패한 Case의 비율 | 1에 가까울수록 결정적 |
| Flaky Case | 반복 중 통과와 실패가 섞인 Case | 개수와 목록을 함께 제공 |

### 실행 지표

| 지표 | 계산식 |
| --- | --- |
| Failure Rate | `(count(C_terminal) − count(C_succeeded)) / count(C_terminal)` |
| P50 / P95 Latency | `C_succeeded`의 `latency_ms` 백분위수 |
| Mean Latency | `C_succeeded`의 `latency_ms` 평균 |
| Token Usage | `input_tokens + output_tokens`의 합과 Case당 평균 |
| Cost | `cost_usd`의 합과 Case당 평균 |
| Tool Call Count | Trace의 `tool_call` 이벤트 수, Case당 평균 |

Latency는 성공한 Case Run만으로 계산한다. 타임아웃으로 실패한 실행을 포함하면 지연시간 분포가 타임아웃 값에 끌려간다.

### 비교 지표

Setup을 여러 개 선택했을 때만 계산한다. 기준 Setup인 Baseline을 하나 정하고 나머지 Setup을 이 값과 비교한다.

| 지표 | 계산식 |
| --- | --- |
| Δ Mean Score | `대상 Mean Score − baseline Mean Score` |
| Win / Tie / Loss | Case별로 점수를 비교해 센 개수. 동점 판정 폭은 설정값 |
| Win Rate | `Win / (Win + Tie + Loss)` |
| Regression Count | baseline에서 통과했으나 대상에서 실패한 Case 수 |
| Improvement Count | baseline에서 실패했으나 대상에서 통과한 Case 수 |

Regression은 평균 점수만으로 드러나지 않는 품질 저하를 보여준다. 따라서 Regression Count는 개수뿐 아니라 해당 Case 목록과 함께 제공한다.

Repetition이 N일 때 Case별 비교는 단일 값이 아니라 반복 평균으로 한다.

---

## 좌측 탭별 설계

Analytics의 좌측 탭은 Scope | Overview | Setups | Cases | Traces | Metrics다.

### Scope

분석 범위를 선택하는 화면이다. 다른 모든 탭의 입력이 된다.

- 선택 순서는 Experiment → Agent Setup → Case → Run이다. Experiment를 먼저 고르면 나머지 선택지가 자연히 좁혀진다.
- Setup을 둘 이상 고르면 baseline을 지정하게 한다.
- 선택 결과를 `1 × N × N`처럼 축 표기로 요약해 보여주고, 그 조합이 답하는 질문을 한 줄로 함께 표시한다. 위 표의 "사용자가 알고 싶은 것" 문장을 그대로 쓴다.

### Overview

현재 Scope의 주요 결과를 가장 먼저 보여주는 화면이다.

| Scope 조건 | Overview 내용 |
| --- | --- |
| Setup 1 | 핵심 지표 요약. Mean Score, Pass Rate, Failure Rate, P95 Latency, Cost |
| Setup N | baseline 대비 Δ 요약 테이블. Win/Tie/Loss와 Regression 개수를 상단에 배치 |
| Case N | 점수 분포 히스토그램과 하위 Case 목록 |
| Repetition N | 안정성 요약. Std Dev, Flaky Case 개수 |
| `1×1×1` | 요약 대신 해당 Case Run의 결과와 Trace 바로가기를 보여준다 |

`1×1×1`에서는 관측값이 하나이므로 평균과 분포를 제공하지 않는다. 이 Scope의 Overview에는 Case Run의 주요 정보를 표시하고 Traces 탭으로 이동할 수 있는 경로를 제공한다.

### Setups

선택한 Setup의 구성과 지표를 확인하는 화면이다.

- Setup이 1이면 이 탭은 해당 Agent Setup의 구성 내용을 보여준다. Prompt Version, Model, Tool Set, Runtime Parameters를 그대로 나열한다.
- Setup이 N이면 Setup 하나당 한 행인 비교 테이블이다. 지표 열은 Mean Score, Pass Rate, Failure Rate, Std Dev, Latency, Cost다.
- **Setup을 여러 개 선택하면 구성 차이도 함께 보여준다.** Prompt Version이나 Model이 다른지, Tool이 추가되었는지 등을 나란히 표시하면 성능 차이의 원인을 파악할 수 있다.

### Cases

선택한 Case의 입력과 실행 결과를 확인하는 화면이다.

- Case가 1이면 해당 Test Case의 입력과 Golden, 그리고 그 Case의 모든 Case Run 목록을 보여준다.
- Case를 여러 개 선택하면 Case 하나당 한 행으로 구성한 테이블을 보여준다. 사용자가 점수가 낮은 Case부터 확인할 수 있도록 기본 정렬은 점수 오름차순으로 설정한다.
- Setup이 N이면 Setup을 열로 펼쳐 Case × Setup 매트릭스가 된다. 셀에는 점수를, Regression인 셀에는 표식을 넣는다.
- Repetition이 N이면 각 셀은 단일 값이 아니라 평균과 편차를 함께 표시한다.

### Traces

실행 하나를 끝까지 내려가 보는 화면이다. Experiments의 Traces 탭과 같은 컴포넌트를 쓰되, 진입 맥락이 Analytics의 Scope다.

- 좌측은 Scope에 포함된 Case Run 목록, 우측은 선택한 Case Run의 Trace다.
- Setup이 N이면 같은 Case에 대한 서로 다른 Setup의 Trace를 나란히 놓을 수 있어야 한다. Scope 5와 6에서 이것이 핵심 기능이다.
- Repetition이 N이면 같은 Case를 반복 실행한 Trace를 전환하며 볼 수 있어야 한다. 이를 통해 실행 결과가 달라지기 시작한 이벤트를 찾을 수 있다.

### Metrics

지표를 직접 고르고 축을 바꿔 보는 화면이다.

- 지표 목록에서 원하는 것을 고르고, 축(Setup / Case / Repetition)을 골라 집계 방식을 바꾼다.
- Overview는 미리 정의한 주요 질문에 답하고, Metrics는 사용자가 직접 구성한 질문을 분석한다.
- 각 지표 옆에 계산식을 볼 수 있게 한다. 분모가 무엇인지 확인할 수 없는 지표는 신뢰받지 못한다.

---

## Scope별 화면 요약

위 규칙을 8가지 Scope에 적용한 결과다.

| Scope | 기본 진입 탭 | 화면의 중심 |
| --- | --- | --- |
| `1×1×1` | Traces | Trace 이벤트 시퀀스, 오류, 지연시간 |
| `1×1×N` | Overview | 반복 점수 산포, Flaky 여부, 반복별 Trace 비교 |
| `1×N×1` | Cases | 점수 분포, 하위 Case 목록, Rubric 항목별 약점 |
| `1×N×N` | Overview | 평균 + 분산, Flaky Case 목록 |
| `N×1×1` | Traces | 두 Trace 나란히 보기, 구성 diff |
| `N×1×N` | Overview | Setup별 반복 산포 대조 |
| `N×N×1` | Setups | 비교 테이블, Win/Tie/Loss, Regression 목록 |
| `N×N×N` | Overview | 순위 + 안정성 + Regression을 함께 |

---

## 계산 위치

- 지표 계산은 백엔드 Application 레이어에서 한다. 프런트엔드는 계산하지 않고 표시만 한다.
- 같은 지표를 백엔드와 프런트엔드 양쪽에서 계산하지 않는다. 값이 어긋나는 순간 어느 쪽이 맞는지 판단할 방법이 없다.
- 집계 결과는 캐시하지 않는다. 느려지면 그때 캐시 계층을 넣는다. 원본은 언제나 Case Run과 Evaluation Result다.

---

## 열린 질문

- **동점 판정 폭.** Win/Tie/Loss의 Tie 기준을 점수 차 몇 점까지로 볼 것인가. 지금은 설정값으로 두었고 기본값을 정하지 않았다.
- **통계적 유의성.** Repeats가 작을 때 Δ Mean Score의 차이가 의미 있는지 판단할 근거가 없다. 신뢰구간이나 간단한 검정을 넣을지, 아니면 반복 수를 그대로 보여주고 판단을 사용자에게 맡길지 정해지지 않았다.
- **Case 가중치.** 지금은 모든 Case의 가중치가 같다. 중요한 Case에 가중치를 주려면 Test Case나 Dataset에 weight를 넣어야 한다.
- **Cost 비교.** 점수와 비용을 함께 놓고 보는 화면이 필요한가. 필요하다면 Metrics 탭의 2축 플롯이 자연스럽다.
