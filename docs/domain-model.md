# Domain Model

이 문서는 구현할 도메인 규칙을 정의한다. 설계 요약과 미정 항목은 [decisions.md](decisions.md)를 참고한다. 영어 용어를 코드·DB·API에서 일관되게 사용한다.

## 모델의 목적과 경계

평가 조건을 고정하고 실제 관측 결과를 보존하여 Agent 변경의 효과를 비교한다. 같은 설정을 보존하는 것은 동일 출력을 재생산한다는 뜻이 아니다. 외부 모델·날씨 데이터·Judge의 변동을 함께 기록한다.

```text
Definition → Definition Version → Agent Setup ──────┐
                               → Evaluation Setup ─┤
                                                    ↓
                                                Experiment
                                                    ↓
                                            Execution Batch
                                                    ↓
                                                   Run
                                                    ↓
                                                Case Run
                                                ↙      ↘
                                            Trace     Evaluation
                                                          ↓
                                                  Evaluation Result
                                                    ↓
                                              Analysis / Comparison
```

## 모듈 책임

| 모듈 | 소유하는 판단/변경 | 다른 모듈에 제공하는 것 |
| --- | --- | --- |
| Assets | Definition 버전 발행, Dataset/Golden 정합성, Setup 스냅샷 | 불변 구성 조회 |
| Experiments | 실행 요청, 반복, Agent 실행, 취소, Trace | 실행 결과와 고정된 평가 조건 |
| Evaluation | Judge 실행, 응답 검증, 항목 결과의 원자적 확정 | 평가 상태·완전한 판정 묶음 |
| Analytics | Scope, 비교 가능성, 점수·분모·집계 | read-only 분석 DTO |

첫 단계에서는 한 제품의 용어를 공유하는 모듈 경계다. 각 폴더를 독립 bounded context나 microservice라고 가정하지 않는다. 모델/언어/팀 책임이 갈라질 때 경계를 재검토한다. 이는 [Bounded Context 설명](https://martinfowler.com/bliki/BoundedContext.html)을 참고한 프로젝트 적용안이다.

## 사용자와 소유권

각 사용자는 자기 자산·Setup·실행·분석만 접근한다. 복수 사용자가 동시에 작업을
제출해도 이 경계를 유지한다. 모든 개인 데이터에는 owner가 있고 서로 다른 owner의
Version/Setup/Run을 연결할 수 없다. 사용자 간 공유와 역할별 권한은 첫 범위가 아니다.

Tool Definition/Version은 사용자가 Python 편집기에서 작성한 개인 자산이다. 인증
신원은 `(issuer, subject)`로 식별하고 email을 소유자 ID로 사용하지 않는다. 실제
접근 계약은 [operations.md](operations.md)를 따른다.

## 자산

### Definition / Definition Version

Definition은 이름 붙인 자산의 정체성과 변경 이력이다. 이름·설명·보관 상태를 변경할 수 있고 내용 변경은 새 Version을 발행한다. Version 번호는 Definition 안에서 1부터 증가한다. Version의 내용과 참조는 발행 후 수정하지 않는다.

Python 자산에서 Version은 저장소 ID·commit ID·파일 경로로 식별한 원문과 결과 계약을 고정한다. 아래 표는 각 자산이 제공해야 하는 의미이며 동적 Python의 결과 값까지 발행 시 고정한다는 뜻은 아니다. 실행 때 생성된 실제 값은 Case Run/Evaluation의 기록으로 보존한다. 편집·저장·실행 계약과 관계형 자산의 미결 경계는 [python-assets.md](python-assets.md)를 따른다.

| 종류 | Version에 고정하는 내용 |
| --- | --- |
| Prompt | 본문, 명시적 변수와 입력 계약 |
| Tool | Python 원문, 지정 변수 `tool`, 모델에 노출할 이름·설명·검증된 입출력 스키마 |
| Model Config | provider, model ID, 요청 파라미터; 비밀 값 제외 |
| Test Case | Agent 입력과 메타데이터 |
| Dataset | 순서 있는 Test Case Version 집합 |
| Golden | 정확한 Test Case Version에 대한 기대 결과/검증 기준 |
| Golden Set | Golden Version 집합 |
| Rubric | 안정적인 항목 key, 설명, 척도, 평가 기준 |
| Scoring Rule | 항목 key별 weight, 합산 방식, pass threshold |

Model Config·Golden Set·Scoring Rule을 포함한 위 종류는 독립 편집·버전 자산이다. 모든 종류를 같은 generic entity나 하나의 JSON 테이블로 구현해야 한다는 뜻은 아니다.

### Test Case / Dataset / Golden

- 첫 버전의 Test Case는 하나의 입력으로 시작하는 Agent 실행이다. Agent 내부의 모델·도구 왕복은 여러 번 가능하다. 대화형 사용자 세션과 다중 Agent는 후속 범위다.
- 한 Dataset Version에 같은 Test Case Definition의 여러 Version을 섞거나 동일 Version을 중복 넣지 않는다.
- Case Version을 바꾸면 Dataset의 새 Version을 발행한다. 기존 Dataset은 변하지 않는다.
- Golden Definition은 Test Case Definition에 속하고, **Golden Version은 정확한 Test Case Version을 참조**한다. 입력을 바꾸면 기준을 검토하고 새 Golden Version을 발행한다.
- Golden Set Version에는 같은 Test Case Version의 Golden을 둘 이상 넣지 않는다. 여러 정답 표현은 Golden 하나의 내용에 넣는다.
- Evaluation Setup의 Golden은 선택한 Dataset Version에 포함된 Case Version과 정확히 대응해야 한다. 불필요한 Golden을 조용히 무시하지 않고 구성 오류로 알린다.

### Agent Setup

Agent Prompt Version, Model Config Version, 순서 있는 Tool Version 목록, Agent Runtime Parameters와 사용자 Execution Environment 참조를 묶은 불변 실행 구성이다.

Prompt와 Tool을 포함해 Setup에 연결하는 모든 실행 Python 자산은 Setup이 고정한
venv revision에서 발행·검증된 Version이어야 한다. 다른 환경에서 실행하려면
자산을 대상 환경에서 새 Version으로 발행하고 Setup을 복제한다.

Runtime Parameters는 `max_turns`, 실행 timeout 등 Agent 제어값이며 모델 sampling parameter와 구분한다. 같은 Tool 이름을 두 번 노출할 수 없다. Tool Description만 바꿔도 새 Tool Version과 새 Setup이 된다.

플랫폼이 이 구성을 직접 실행한다. 향후 `.py` export는 이 구성과 실행 코어/도구 adapter 계약을 변환해 제공하는 별도 기능이다. export 형태(독립 단일 파일 또는 runtime 의존)는 아직 정하지 않는다. 현재 구현에서는 웹 요청·ORM 객체·DB 세션을 Agent 실행 코어에 넘기지 않는다.

### Evaluation Setup

Dataset Version, Golden Set Version(선택), Judge Prompt/Model Config Version, Rubric/Scoring Rule Version, 사용자 Execution Environment 참조, `missing_golden_policy`를 고정한다.

Execution Environment는 owner가 이름 붙인 `.venv`와 `.env`의 조합이다. Setup은 선택한 환경 ID를 고정하지만 환경 파일의 내용은 실행 시 읽는다. 실제 사용한 패키지 digest와 dotenv revision은 실행 기록에 남긴다. [사용자 실행 환경](runtime-environments.md)을 따른다.

- `fail`: 실행 대상으로 선택한 Case에 Golden이 없으면 실행 등록을 거부한다.
- `skip`: 해당 Case의 Evaluation을 `skipped`로 둔다.
- `rubric_only`: Golden 없이 Rubric으로 평가한다. Judge Prompt가 Golden 선택 입력을 지원해야 한다.

어떤 정책도 미평가를 임의의 0점으로 만들지 않는다. Rubric 항목 key와 Scoring Rule의 key 집합은 같아야 한다. 비어 있는 항목, 유효하지 않은 척도/weight/threshold는 Setup 생성 때 거부한다.

### 불변 구성과 메타데이터

Definition Version, Setup과 Experiment의 **실행 의미를 바꾸는 필드**는 수정하지 않는다. 보관 상태(`archived_at`) 변경은 허용하며 과거 참조는 계속 조회된다. 생성 후 수정 UI는 복제를 통해 새 ID를 만든다. 이름·설명을 바꾸는 기능은 첫 버전에서 Definition에만 제공한다.

보관은 삭제가 아니다. 개인정보/비밀 제거와 보존 기간에 따른 물리 삭제는 별도 운영 정책으로 관리한다. 무기한 보존을 불변성의 필수 조건으로 삼지 않는다.

## 실행과 평가

### Experiment

Agent Setup 1개 + Evaluation Setup 1개 + 비어 있지 않은 Case Version 부분집합 + Repeats를 고정한다. 생성부터 불변이며 변경은 복제로 표현한다. 실행 상태는 자식 실행 기록에 둔다.

### Execution Batch

사용자의 **실행 요청 한 번**이다. Experiment, 멱등 키와 요청 hash, 실행 정책 snapshot, 코드/runtime 버전, 생성한 Run들을 연결한다.

한 Experiment를 두 번 실행하면 Batch 두 개가 생긴다. 동일 키의 재전송은 같은 Batch를 반환한다. 첫 UI에서는 별도 상위 탭 대신 Experiment 상세의 실행 이력 묶음으로 보여준다.

### Run

한 Batch 안에서 Experiment의 모든 Case를 한 번씩 시도할 슬롯을 갖는 반복 단위다. `repeat_index`는 Batch 안에서 1..repeats다. 실행 중에는 상태를 변경할 수 있으며 취소/실패 때문에 실제 호출을 하지 못한 슬롯도 남긴다.

Run의 실행 상태와 평가 진행은 별개다. 정확한 유도 규칙은 [execution.md](execution.md)에 있다.

### Case Run

Run × Test Case Version마다 하나의 Agent 실행 슬롯과 결과다. 재시도는 같은 Case Run 내부의 개별 호출 시도이며 새로운 Repeat가 아니다. 실행 중 상태와 사용량을 기록하고 종료할 때 Final Answer 또는 오류를 확정한다. 종료 결과를 덮어쓰지 않는다.

### Trace

한 Case Run의 Agent 실행에서 관측한 append-only 이벤트 시퀀스다. 실행 전에는 이벤트 0개일 수 있다. seq는 기록 순서이며 병렬 이벤트의 정확한 인과관계는 call ID로 표현한다. 실패/취소 시 Final Answer가 없을 수 있다.

모델이 API로 제공한 공개 응답/요약만 저장한다. 숨겨진 내부 추론을 수집할 수 있다고 전제하지 않는다. Judge 호출 기록은 Evaluation에 연결하여 Agent Trace와 구분한다.

### Evaluation / Evaluation Result

Evaluation은 하나의 Case Run을 하나의 고정 Evaluation Setup으로 채점하는 **작업**이다. `pending/queued/running/scored/failed/skipped/cancelled`의 상태를 가진다. 첫 버전은 Case Run당 하나다.

Evaluation Result는 그 작업의 Rubric 항목별 원자적 판정이다. Judge 응답 전체를 검증하고 모든 항목 결과를 한 트랜잭션에서 기록한 뒤 Evaluation을 `scored`로 확정한다. 실패한 작업은 점수 항목 일부를 공개하지 않는다.

항목별 최신 created_at을 선택하여 서로 다른 채점 작업을 합치지 않는다. 재평가를 도입하면 별도 Evaluation ID와 명시적 분석 선택을 추가한다. 첫 버전에서 미리 재평가 UI나 중복 결과 허용을 구현하지 않는다.

## Aggregate와 일관성 경계

| 경계 | 하나의 변경으로 지킬 규칙 |
| --- | --- |
| Definition | 새 Version 번호 발행과 현재 버전 포인터 갱신 |
| Dataset/Golden Set Version | 고정된 멤버 목록과 중복/참조 검증 |
| Setup | 구성 참조와 정합성을 검증하여 한 번에 생성 |
| Experiment | 선택 Case 범위와 Repeats 유효성 |
| 실행 등록 application transaction | Batch + 모든 Run/Case Run/Evaluation 슬롯의 원자적 생성 |
| Case Run | 유효한 lease 소유자의 상태 전이·Trace append·결과 확정 |
| Evaluation | 유효한 작업 상태와 완전한 항목 결과 집합의 원자적 확정 |

Run 전체의 자식과 Trace를 한 거대한 객체로 읽고 잠그지 않는다. Run 상태는 자식 상태의 projection이며 자식 변경과 함께 짧은 트랜잭션으로 갱신하고 복구 시 재계산할 수 있다. command는 부모 Run을 먼저 잠그는 공통 잠금 순서를 따른다.

## 분석

Analysis는 Case Run/Evaluation Result와 명시적 계산 정책에서 파생된다. 분석 입력은 구체적인 Batch/Run/Case Version ID로 고정하고 결과에는 계산 정책 버전을 포함한다. 저장하더라도 원본을 대체하지 않는다.

Comparison은 Baseline과 대상의 같은 평가 조건·Case 범위에서 차이를 계산한다. 최소 비교 조건과 미완료 처리의 정본은 [analytics.md](analytics.md)다.

## 핵심 불변식

1. Version과 Setup/Experiment의 실행 구성은 생성 이후 바뀌지 않는다.
2. Setup은 Definition의 최신 포인터가 아닌 정확한 Version을 참조한다.
3. Golden은 정확한 Case Version에 대응한다.
4. Definition 편집/보관은 기존 참조와 실행 결과를 바꾸지 않는다.
5. Batch는 Experiment 하나, Run은 Batch 하나, Case Run은 Run 하나와 Case Version 하나에 속한다.
6. `(batch_id, repeat_index)`와 `(run_id, test_case_version_id)`는 각각 유일하다.
7. Retry는 Batch/Run/Case Run 개수를 늘리지 않는다.
8. 유효한 lease 소유자만 실행 중 기록을 변경하며 종료 결과를 덮어쓸 수 없다.
9. Evaluation Result는 Evaluation 하나의 Rubric 항목에 속하고 같은 항목을 중복 기록하지 않는다.
10. 측정 실패/누락과 Agent 품질 실패를 구분한다.
11. 분석은 입력 범위·평가 조건·계산 정책·분모를 명시한다.
12. 개인 데이터 조회·변경·실행·비교는 인증된 owner 범위를 벗어날 수 없다. 서로 다른 owner의 자산/실행 참조는 금지한다.

## 코드 이름

`Definition`, `DefinitionVersion`, `AgentSetup`, `EvaluationSetup`, `Experiment`, `ExecutionBatch`, `Run`, `CaseRun`, `TraceEvent`, `Evaluation`, `EvaluationResult`를 사용한다. 저장 구조는 [data-model.md](data-model.md)에 매핑한다. `Evaluation`은 작업, `EvaluationResult`는 항목 판정이므로 서로 바꾸어 쓰지 않는다.
