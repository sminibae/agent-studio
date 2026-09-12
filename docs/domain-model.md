# Domain Model

이 문서는 프로젝트에서 사용하는 용어의 정확한 의미를 정의한다. 여기에서 정의한 용어는 코드, DB, API, UI에서 그대로 사용한다. 새 개념을 추가하거나 기존 개념의 이름을 바꾸려면 먼저 이 문서를 수정한다.

용어는 영어를 정본으로 한다. 한국어 설명은 보조 설명일 뿐이며, 식별자·타입·테이블 이름은 영어 용어를 따른다.

---

## 개념 지도

자산(무엇으로 실행할지)과 실행(무엇이 실제로 일어났는지)을 분리한다.

```
[ 자산 계층 ]                       [ 실행 계층 ]

Definition (mutable, versioned)
  └─ Definition Version (immutable)
        │
        ├──> Agent Setup        (immutable snapshot)  ─┐
        └──> Evaluation Setup   (immutable snapshot)  ─┤
                                                        │
                                            Experiment ─┘
                                                 │
                                                 ├─ Run
                                                 │    └─ Case Run
                                                 │          ├─ Trace
                                                 │          └─ Evaluation Result
                                                 │
                                            [ 분석 계층 ]
                                                 │
                                    Case Run / Run / Experiment Analysis
                                                 │
                                            Comparison
```

자산 계층과 실행 계층의 경계는 분명하다. **Definition은 변경할 수 있지만, Setup부터 오른쪽에 있는 기록은 변경할 수 없다.**

---

## 자산 계층

### Definition

독립적으로 생성·수정·버전 관리할 수 있으며 여러 Setup에서 재사용되는 최소 단위의 자산이다.

- 사용자가 내용을 변경할 수 있다.
- 변경할 때마다 새 Definition Version이 생기며 이전 Version도 보존된다.
- Definition은 이름이 붙은 자산의 변경 이력을 나타내고, 실제 내용은 Definition Version에 저장한다.

### Definition Version

특정 시점의 Definition 내용을 고정한 변경 불가능한 레코드다.

- 생성한 뒤에는 수정하지 않는다.
- Setup은 Definition이 아니라 Definition Version을 참조한다. 이 규칙이 재현성의 핵심이다.
- 버전 번호는 Definition 안에서 1부터 증가한다.

### Definition의 종류

| Definition | 내용 | 사용처 |
| --- | --- | --- |
| Prompt | 프롬프트 본문, 변수 목록 | Agent Setup의 Agent Prompt, Evaluation Setup의 Judge Prompt |
| Tool | 도구 이름, Description, 입력 스키마, 구현 참조 | Agent Setup의 Tool Set |
| Model Config | Provider, Model ID, Runtime Parameter(temperature, max tokens 등) | Agent Setup의 Model, Evaluation Setup의 Judge Model |
| Test Case | Agent에 입력할 내용과 메타데이터 | Dataset |
| Dataset | Test Case Version들의 고정된 집합 | Evaluation Setup |
| Golden | 특정 Test Case에 대한 기대 결과 또는 검증 기준 | Golden Set |
| Golden Set | Golden Version들의 고정된 집합 | Evaluation Setup |
| Rubric | 점수 항목, 척도, 항목별 판정 기준 | Evaluation Setup |
| Scoring Rule | 항목 가중치, 합산 방식, Pass 기준 | Evaluation Setup |

Tool Description은 별도 Definition이 아니다. Tool Definition의 일부이며 Tool Version과 함께 고정된다. Description만 바꿔도 새 Tool Version이 생긴다. Description 변경은 Agent 동작을 바꾸는 변경이기 때문이다.

### Test Case

Agent에게 한 번 입력할 수 있는 최소 평가 단위다.

- 하나의 Test Case는 하나의 Case Run을 만든다.
- Test Case는 Definition이므로 Version을 가진다. 입력 문구를 고치면 새 Test Case Version이 된다.

### Dataset

평가에 사용할 Test Case들의 Version이 고정된 집합이다.

- Dataset Version은 Test Case Version 목록을 가리킨다. Test Case를 고쳐도 기존 Dataset Version이 가리키는 내용은 변하지 않는다.
- Dataset에 Case를 추가·제거하면 새 Dataset Version이 생긴다.

### Golden

특정 Test Case의 평가에 사용할 기대 결과 또는 검증 가능한 기준이다.

- Golden은 반드시 하나의 Test Case Definition에 속한다.
- 같은 Test Case에 대해 서로 다른 기준을 두고 싶을 때를 위해 Golden은 Test Case와 별도 Definition으로 둔다.

### Golden Set

평가 한 번에 사용할 Golden Version들의 고정된 집합이다.

- Dataset과 짝을 이룬다. Dataset의 모든 Test Case가 Golden을 가질 필요는 없다.
- Golden이 없는 Case는 Rubric만으로 평가하거나 평가에서 제외한다. 정책은 Evaluation Setup이 정한다.

### Agent Setup

평가 대상 Agent에 필요한 Definition Version을 특정 시점에 조합하여 고정한 구성 스냅샷이다.

구성 요소:

- Agent Prompt: Prompt Version 1개
- Model: Model Config Version 1개
- Tool Set: Tool Version 0개 이상
- Agent Runtime Parameters: 최대 Turn 수, 타임아웃 등 실행 제어 값

Agent Runtime Parameters는 재사용하는 자산이 아니라 실험 조건이므로 Definition으로 관리하지 않고 Agent Setup에 직접 저장한다.

### Evaluation Setup

평가 방법을 고정한 변경 불가능한 구성 스냅샷이다.

구성 요소:

- Dataset: Dataset Version 1개
- Golden Set: Golden Set Version 0개 또는 1개
- Judge Prompt: Prompt Version 1개
- Judge Model: Model Config Version 1개
- Rubric: Rubric Version 1개
- Scoring Rule: Scoring Rule Version 1개

Agent Setup은 **무엇을 평가하는지**를 정의하고, Evaluation Setup은 **어떻게 평가하는지**를 정의한다.

---

## 실행 계층

### Experiment

특정 Agent Setup을 특정 Evaluation Setup과 실행 조건으로 평가하기 위해 생성된 실험 단위다.

구성 요소:

- Agent Setup 1개
- Evaluation Setup 1개
- Case 범위: Dataset의 Test Case 전체 또는 부분집합
- Repeats: 실행할 때 생성할 Run의 수

Experiment는 무엇을 실행할지 정의하며, 그 자체에는 실행 상태가 없다. 실행 상태는 Run에 기록한다.

### Run

Experiment에 정의된 전체 Test Case를 한 번씩 실행한 실행 단위다.

- 하나의 Run은 Case 범위의 모든 Test Case를 정확히 한 번씩 실행한다.
- Repeats가 N이면 실행 1회가 Run N개를 만든다. 즉 **반복은 Run 단위로 표현된다.**
- Run은 상태를 가진다. 상태 전이는 `docs/execution.md`에 정의한다.

### Case Run

Run 안에서 하나의 Test Case를 Agent가 실행한 결과다.

- Run × Test Case Version 조합마다 정확히 하나 존재한다.
- 실행 결과로 Final Answer, 상태, 지연시간, 토큰 사용량, 비용을 가진다.
- 실행이 실패해도 Case Run 레코드를 남긴다.

### Trace

하나의 Case Run에서 Agent가 입력을 받은 시점부터 Final Answer를 생성할 때까지 발생한 실행 이벤트를 순서대로 기록한 목록이다.

- Case Run과 1:1로 대응한다. Trace는 별도 엔티티라기보다 Case Run에 속한 이벤트 시퀀스를 가리키는 이름이다.
- 이벤트는 순서 번호를 가지며, 순서는 기록 후 변하지 않는다.
- 이벤트 종류와 필드는 `docs/execution.md`에 정의한다.

### Evaluation Result

Rubric 또는 Evaluator가 하나의 Case Run을 평가한 원자적 평가 결과다.

- 하나의 Case Run에 Rubric 항목별로 여러 Evaluation Result가 생길 수 있다. 여기에서 "원자적"은 더 나눌 수 없는 하나의 판정을 뜻한다.
- 어떤 Evaluation Setup의 어떤 Rubric Version으로 평가했는지를 함께 기록한다.
- 재평가는 기존 Evaluation Result를 수정하지 않는다. 새 Evaluation Result를 추가한다.

---

## 분석 계층

### Case Run Analysis / Run Analysis / Experiment Analysis

하나 이상의 Case Run 및 Evaluation Result를 집계·변환하여 계산한 해석 결과다.

- Analysis는 파생 데이터다. 원본 Case Run과 Evaluation Result로부터 항상 다시 계산할 수 있어야 한다.
- 저장 여부는 성능 요구사항에 따라 정한다. Analysis를 저장하더라도 이를 원본 데이터로 취급해서는 안 된다.
- 집계 범위에 따라 이름이 다르다. Case Run 하나면 Case Run Analysis, Run 하나면 Run Analysis, Experiment 전체면 Experiment Analysis다.

### Comparison

평가 기준이 같거나 서로 비교할 수 있는 둘 이상의 실행 또는 구성 집합에서 차이를 계산하고 설명하는 분석 작업이다.

- 비교 가능성의 최소 조건은 같은 Case 집합과 같은 Rubric이다. 이 조건이 깨지면 비교 결과를 보여주기 전에 경고한다.
- 비교 대상은 보통 Agent Setup이다. 같은 Evaluation Setup 아래에서 Agent Setup A와 B를 비교하는 것이 기본 형태다.

---

## Invariants

이 규칙들은 구현 어디에서도 위반되어서는 안 된다.

1. An Agent Setup MUST NOT change after creation.
2. An Evaluation Setup MUST NOT change after creation.
3. A Definition Version MUST NOT change after creation.
4. A Setup MUST reference Definition Versions, never Definitions.
5. A Run belongs to exactly one Experiment.
6. A Case Run belongs to exactly one Run and one Test Case Version.
7. A Trace belongs to exactly one Case Run.
8. An Evaluation Result belongs to exactly one Case Run.
9. Execution history MUST NOT change when a Definition is edited.
10. Deleting a Definition MUST NOT delete or alter any Setup or execution record that references it.

10번 규칙에 따라 대부분의 삭제는 논리 삭제로 처리한다. 자세한 삭제 정책은 `docs/data-model.md`에 정의한다.

---

## 이름 대응표

| 도메인 용어 | 코드 식별자 | 테이블 |
| --- | --- | --- |
| Prompt Definition | `PromptDefinition` | `prompt_definition` |
| Prompt Version | `PromptVersion` | `prompt_version` |
| Agent Setup | `AgentSetup` | `agent_setup` |
| Evaluation Setup | `EvaluationSetup` | `evaluation_setup` |
| Experiment | `Experiment` | `experiment` |
| Run | `Run` | `run` |
| Case Run | `CaseRun` | `case_run` |
| Trace Event | `TraceEvent` | `trace_event` |
| Evaluation Result | `EvaluationResult` | `evaluation_result` |

---

## 열린 질문

- **Model Config를 Definition으로 둘 것인가.** 현재는 재사용할 수 있는 자산으로 판단하여 Definition으로 두었다. 대안은 Agent Setup에 Model ID와 Parameter를 직접 저장하는 것이다. Setup을 만들 때마다 모델을 선택하는 방식이 더 자연스럽다면 Definition에서 제외한다.
- **Golden Set을 별도 Definition으로 둘 것인가.** 현재 구조에서는 Dataset과 Golden Set을 따로 선택할 수 있지만 테이블이 네 개 늘어난다. 같은 Dataset에 서로 다른 Golden을 적용할 필요가 없다면 Golden을 Dataset Version에 직접 연결하는 편이 단순하다.
- **Tool Set을 Definition으로 둘 것인가.** 지금은 Agent Setup이 Tool Version들을 직접 참조한다. "이 도구 묶음"을 이름 붙여 재사용하고 싶어지면 Tool Set Definition을 추가한다.
- **Evaluation이 Judge Model만인가.** 지금 정의는 LLM Judge를 전제한다. 코드 기반 검증(정확 일치, 정규식, 함수 실행)을 넣으려면 Evaluator 개념을 추가해야 한다.
