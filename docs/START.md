# 시작하기

이 문서는 제품의 화면 구조와 핵심 개념을 간략하게 소개한다. 제품의 목적은 `docs/product.md`, 용어의 정확한 의미는 `docs/domain-model.md`, 분석 규칙은 `docs/analytics.md`에서 확인한다.

---

## 화면 구조

최상단에는 다음 세 탭을 둔다.

```
Setups | Experiments | Analytics
```

### Setups

Setups에는 `Agent Setups`와 `Evaluation Setups` 탭이 있다. 각 탭에서는 Setup의 목록과 상세 정보를 확인하고, 새 Setup을 만들거나 기존 Setup을 복제하고 삭제할 수 있다.

Agent Setup은 다음 항목으로 구성된다.

- Agent Prompt
- Model
- Tool Set과 Tool Description
- Agent Runtime Parameters

Evaluation Setup은 다음 항목으로 구성된다.

- Dataset
- Golden Set
- Judge Prompt
- Judge Model
- 채점 기준인 Rubric
- 점수 합산 방식인 Scoring Rule

Setup은 생성 후 변경되지 않는다. 화면에서 기존 Setup을 수정하는 동작은 해당 Setup을 복제한 뒤 새 Setup을 만드는 방식으로 제공한다.

### Experiments

Experiments에는 `Experiments`, `Runs`, `Traces` 탭이 있다.

- `Experiments`에서는 Agent Setup과 Evaluation Setup, Case 범위, Repeats를 지정하여 Experiment를 만들고 실행한다. 목록과 상세 화면에서는 실행 이력도 확인할 수 있다.
- `Runs`에서는 하나의 Experiment에서 생성된 Run 목록과 Run별 상태 및 결과를 확인한다. 각 Run에 포함된 Case Run도 이 탭에서 조회한다.
- `Traces`에서는 Case Run의 실행 과정을 자세히 확인한다. 화면 왼쪽에는 Case Run 목록을, 오른쪽에는 선택한 Case Run의 Trace를 표시한다.

Trace는 다음과 같은 Step으로 구성될 수 있다.

```
User Input
→ Agent Reasoning / Model Call
→ Tool Call: search_document
→ Tool Result
→ Model Call
→ Tool Call: get_price
→ Final Answer
```

각 Step에는 해당되는 경우 다음 정보를 표시한다.

- Input과 Output
- Latency와 Token
- Model
- Tool Arguments와 Tool Result
- Error

### Analytics

Analytics에는 `Scope`, `Overview`, `Setups`, `Cases`, `Traces`, `Metrics` 탭이 있다. 사용자가 선택한 `Agent Setup × Case × Repetition` 범위는 모든 탭의 상단에 계속 표시한다.

`Scope`에서는 다음 여덟 가지 분석 범위 중 하나를 선택한다.

| Setup | Case | Repeats | 사용자가 확인하려는 내용 |
| --- | --- | --- | --- |
| 1 | 1 | 1 | 한 실행을 디버깅하고 해당 답변이 나온 과정을 확인한다. |
| 1 | 1 | N | 같은 입력을 반복했을 때 품질이 안정적인지 확인한다. |
| 1 | N | 1 | 하나의 Setup이 여러 Case를 얼마나 잘 해결하는지 확인한다. |
| 1 | N | N | 하나의 Setup이 여러 Case를 반복해서도 안정적으로 해결하는지 확인한다. |
| N | 1 | 1 | 하나의 Case에서 여러 Setup의 결과를 비교한다. |
| N | 1 | N | 하나의 Case를 반복했을 때 여러 Setup 중 무엇이 더 안정적인지 비교한다. |
| N | N | 1 | 전체 Case 집합에서 여러 Setup의 성능을 비교한다. |
| N | N | N | 여러 Setup의 평균 성능과 안정성을 함께 비교한다. |

나머지 탭은 선택한 Scope가 답하려는 질문에 맞게 달라진다. 자세한 화면과 지표는 `docs/analytics.md`에 정의한다.

---

## 핵심 개념

### Definition

여러 Setup에서 재사용할 수 있는 최소 단위의 자산이다. 독립적으로 생성하고 수정할 수 있으며, 변경 이력을 Version으로 관리한다.

### Test Case

Agent에 한 번 입력할 수 있는 최소 평가 단위다.

### Dataset

평가에 사용할 Test Case Version을 고정하여 구성한 집합이다.

### Golden

특정 Test Case를 평가할 때 사용하는 기대 결과 또는 검증 기준이다.

### Agent Setup / Evaluation Setup

특정 시점의 Definition Version을 조합하여 만든 변경 불가능한 구성 스냅샷이다.

### Experiment

특정 Agent Setup을 특정 Evaluation Setup과 실행 조건으로 평가하기 위한 실험 단위다.

### Run

Experiment에 정의된 모든 Test Case를 한 번씩 실행하는 단위다.

### Case Run

Run 안에서 Agent가 하나의 Test Case를 실행한 결과다.

### Trace

Agent가 하나의 Case Run에서 입력을 받은 시점부터 Final Answer를 생성할 때까지 기록한 실행 이벤트의 순서 있는 목록이다.

### Evaluation Result

Rubric 또는 Evaluator가 하나의 Case Run을 평가한 원자적 결과다.

### Case Run Analysis / Run Analysis / Experiment Analysis

하나 이상의 Case Run과 Evaluation Result를 집계하거나 변환하여 계산한 해석 결과다.

### Comparison

평가 기준이 같거나 서로 비교할 수 있는 둘 이상의 실행 또는 구성 집합에서 차이를 계산하고 설명하는 분석 작업이다.

---

## 사용자 흐름

```
Setups
Agent Setup을 만든다.
  ↓
Evaluate
Dataset과 Evaluation Setup으로 Experiment를 실행한다.
  ↓
Analyze
성능, 안정성, 실패를 확인한다.
  ↓
Debug
Case에서 Trace까지 상세 정보를 확인한다.
  ↓
Compare
이전 Setup과 새 Setup을 비교한다.
  ↓
Improve
Prompt, Model, Tool, Runtime Definition을 수정한다.
  ↓
New Agent Setup Snapshot
새 Agent Setup을 만들고 다시 평가한다.
```
