# Product

이 문서는 제품의 목적과 범위를 정의한다. 용어의 정확한 의미는 `docs/domain-model.md`가 정본이다.

---

## 제품 목적

**Agent를 감이 아니라 측정으로 개선할 수 있게 한다.**

Agent를 개발하다 보면 프롬프트를 수정하고 몇 차례 실행한 뒤, 결과가 좋아진 것 같다는 인상만으로 변경 사항을 판단하기 쉽다. 이 제품은 그 과정의 각 단계를 기록할 수 있는 자산과 재현 가능한 실행으로 바꾼다. 무엇을 바꿨고 그 결과 어떤 부분이 개선되거나 악화되었는지 언제든 확인할 수 있게 하는 것이 목적이다.

---

## 대상 사용자

주요 사용자는 **Agent를 직접 개발하고 수정하는 개발자**다. 이 사용자는 실험을 설계하고 Trace를 읽는다.

이 사용자는 다음을 전제한다.

- 프롬프트, 도구 스키마, 모델 파라미터를 직접 다룬다.
- JSON과 스택 트레이스를 익숙하게 읽는다.
- 요약된 대시보드보다 원본 데이터에 접근하는 것을 선호한다.
- 화면이 예쁜 것보다 정보 밀도가 높은 것을 선호한다.

이 전제는 UI 설계에 직접 영향을 준다. 자세한 내용은 `docs/ui-ux.md`에 있다.

비개발 직군의 품질 검수자와 경영 보고용 지표를 확인하는 사람은 현재 대상 사용자가 아니다. 이들을 위한 요약 화면도 지금은 만들지 않는다.

---

## 핵심 문제

### 1. 무엇을 바꿨는지 남지 않는다

프롬프트를 고치고 돌려보면 이전 버전이 사라진다. 좋아졌다고 생각했는데 어제 버전이 더 나았다는 것을 알았을 때 되돌아갈 방법이 없다.

→ Definition의 버전을 관리하고, Setup을 변경할 수 없는 스냅샷으로 고정한다.

### 2. 좋아졌다는 판단에 근거가 없다

예시 몇 개만 실행한 결과로 품질을 판단하면 그 예시가 대표성을 갖는지, 결과가 우연히 잘 나온 것인지 알 수 없다.

→ Dataset과 Rubric으로 평가를 고정하고, 여러 Case에 대해 점수를 낸다.

### 3. 같은 입력에 매번 다른 결과가 나온다

LLM은 비결정적이다. 한 번 잘 나온 결과가 항상 잘 나오는 것은 아니다.

→ Repeats로 같은 조건을 반복 실행하고 분산을 측정한다.

### 4. 왜 그렇게 답했는지 알 수 없다

최종 답변만 보면 도구를 잘못 골랐는지, 도구 결과가 잘못됐는지, 종합을 잘못했는지 구분할 수 없다.

→ 모든 실행의 Trace를 이벤트 단위로 기록하고 끝까지 펼쳐 본다.

### 5. 평균은 올랐는데 무언가 망가진다

전체 점수가 올라도 특정 Case가 퇴행했을 수 있다. 평균만 보면 이것을 놓친다.

→ Regression을 Case 단위로 식별하고 목록으로 제공한다.

---

## 최상단 정보 구조

```
Setups                Experiments                 Analytics
├─ Agent Setups       ├─ Experiments              ├─ Scope
└─ Evaluation Setups  ├─ Runs                     ├─ Overview
                      └─ Traces                   ├─ Setups
                                                   ├─ Cases
                                                   ├─ Traces
                                                   └─ Metrics
```

세 영역의 역할은 서로 겹치지 않는다.

| 영역 | 역할 | 다루는 대상 |
| --- | --- | --- |
| Setups | 무엇을 어떻게 평가할지 정의한다 | Definition, Agent Setup, Evaluation Setup |
| Experiments | 실행하고 결과를 확인한다 | Experiment, Run, Case Run, Trace |
| Analytics | 여러 실행을 비교하고 해석한다 | Analysis, Comparison |

Experiments와 Analytics는 모두 Trace를 보여주지만 진입 경로가 다르다. Experiments의 Trace는 "이 Run에서 무슨 일이 있었는가"에 답하고, Analytics의 Trace는 "이 비교에서 어떤 실행이 차이를 만들었는가"에 답한다. 두 화면은 같은 컴포넌트를 사용하지만 서로 다른 맥락을 제공한다.

### Setups

Definition과 Setup을 관리한다.

- Agent Setups: Agent Prompt, Model, Tool Set, Tool Descriptions, Agent Runtime Parameters
- Evaluation Setups: Dataset, Golden Set, Judge Prompt, Judge Model, Rubric, 점수 합산 방식인 Scoring Rule

각 탭에서는 Setup의 목록과 상세 정보를 확인하고, 새 Setup을 만들거나 기존 Setup을 복제하고 삭제할 수 있다. Setup은 생성 후 변경되지 않으므로, 기존 Setup을 "수정"할 때는 복제본으로 새 Setup을 만든다. UI에서도 이 동작을 분명히 안내한다.

### Experiments

- Experiments: Agent Setup과 Evaluation Setup, Case 범위, Repeats를 선택하여 실험을 정의하고 실행한다.
- Runs: 실행 이력과 Run별 상태 및 결과를 확인한다. 각 Run에 포함된 Case Run도 조회할 수 있다.
- Traces: 분할 화면의 왼쪽에는 Case Run 목록을, 오른쪽에는 선택한 Trace의 상세 정보를 표시한다.

### Analytics

Agent Setup × Case × Repetition 8가지 Scope에 따라 분석 성격이 달라진다. 자세한 내용은 `docs/analytics.md`에 있다.

---

## 전체 사용자 흐름

```
Setup      Agent Setup을 만든다
  ↓
Evaluate   Dataset과 Evaluation Setup으로 Experiment를 실행한다
  ↓
Analyze    성능 / 안정성 / 실패를 확인한다
  ↓
Debug      Case → Trace까지 내려간다
  ↓
Compare    이전 Setup과 새 Setup을 비교한다
  ↓
Improve    Prompt / Model / Tool / Runtime Definition을 수정한다
  ↓
New Agent Setup Snapshot   (다시 Evaluate로)
```

제품의 모든 기능은 이 흐름을 지원해야 한다. 기능을 추가할지는 **사용자가 이 흐름을 한 차례 완료하는 데 도움이 되는지**를 기준으로 판단한다.

이 흐름에서 `Improve → New Setup → Evaluate` 구간이 가장 자주 반복된다. 따라서 기존 Setup을 복제하고 한 항목만 바꾼 새 Setup을 몇 차례의 클릭만으로 만들 수 있어야 한다.

---

## MVP 범위

루프를 한 바퀴 완주할 수 있는 최소 기능만 넣는다.

### Setups

- Definition 생성·수정·목록·버전 이력 조회 (Prompt, Tool, Model Config, Test Case, Dataset, Golden, Golden Set, Rubric, Scoring Rule)
- Agent Setup 생성·목록·상세·복제
- Evaluation Setup 생성·목록·상세·복제

### Experiments

- Experiment 생성·목록·상세
- Case 범위 선택, Repeats 지정
- 실행, 진행 상황 확인, 취소
- Run 목록과 상세, Case Run 목록
- Trace 상세 조회 (분할 화면, 이벤트 시퀀스, Step별 Input/Output/Latency/Token/Model/Tool Arguments/Tool Result/Error)

### Evaluation

- LLM Judge 기반 Rubric 채점
- Scoring Rule에 따른 점수 합산
- Evaluation Result 조회

### Analytics

- 8가지 Scope 선택
- Overview, Setups, Cases, Traces, Metrics 탭
- `docs/analytics.md`에 정의된 지표

MVP는 기능 개수가 아니라 완결된 사용자 흐름을 기준으로 판단한다. **한 사용자가 Agent Setup 두 개를 만들고 같은 Evaluation Setup으로 비교한 뒤, 퇴행한 Case를 찾아 해당 Trace까지 확인할 수 있으면** MVP가 완성된 것이다.

---

## MVP에서 하지 않을 것

아래는 필요할 수 있지만 지금 만들지 않는다. 각각 왜 미루는지를 함께 적는다.

| 항목 | 미루는 이유 |
| --- | --- |
| 계정, 인증, 권한 | 단일 팀 사용을 전제한다. 나중에 추가해도 스키마 변경이 크지 않다 |
| 코드 기반 Evaluator (정확 일치, 정규식, 함수 실행) | LLM Judge 하나로 루프를 완주할 수 있다. Evaluator 추상화는 두 번째 구현이 생길 때 만든다 |
| 재평가 (같은 Case Run을 다른 Evaluation Setup으로 재채점) | 도메인상 가능하지만 루프 완주에 필요하지 않다 |
| Prompt 자동 최적화, 자동 개선 제안 | 먼저 신뢰할 수 있는 측정 체계를 마련해야 한다 |
| Dataset 자동 생성, 합성 데이터 | 평가 데이터의 신뢰성이 제품의 근거다. 자동 생성은 그 근거를 약화시킨다 |
| 외부 시스템 연동 (CI, Slack, Webhook) | 먼저 사용자가 화면에서 전체 흐름을 완료할 수 있어야 한다 |
| 실시간 협업, 코멘트 | 먼저 단일 사용자 흐름을 완성해야 한다 |
| Trace 비교의 자동 diff | Trace를 나란히 놓는 것까지만 한다. 자동 차이 탐지는 Trace 구조가 안정된 뒤에 |
| 다중 Agent, Agent 간 호출 | 단일 Agent 실행 모델을 먼저 고정한다 |
| 비용 예산, 쿼터 관리 | 비용을 측정하고 표시하는 것까지만 한다 |

---

## 열린 질문

- **Agent를 어디에서 실행할 것인가.** 현재는 이 플랫폼이 Agent를 직접 실행한다고 전제한다. 사용자가 자신의 시스템에서 Agent를 실행하고 결과만 전송하는 방식까지 지원할지는 정해지지 않았다. 이 방식을 지원한다면 Trace 수집 API가 제품의 중심 기능이 된다.
- **도구 실행 방식.** Tool Definition이 스키마만 가질지, 실제 실행 가능한 구현까지 가질지 정해지지 않았다. 후자라면 샌드박스와 보안이 큰 주제가 된다.
- **Dataset의 규모.** Case 수십 개를 전제하는지 수천 개를 전제하는지에 따라 실행기와 Analytics 설계가 달라진다.
