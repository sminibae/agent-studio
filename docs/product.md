# Product

제품 구상의 원문은 [START.md](START.md), 설계 요약과 미정 항목은 [decisions.md](decisions.md)다. 이 문서는 구현된 기능 목록이 아닌 첫 서비스의 목표와 범위다.

## 목적

**Agent를 측정 근거로 개선한다.** Prompt·Model·Tool을 바꾼 뒤 같은 평가 조건으로 실행하고, 평균뿐 아니라 Case별 퇴행·실패·반복 변동과 Trace를 확인할 수 있게 한다.

사용자는 서버에 접속하는 개발자 본인과 소수 팀원이다. 플랫폼 안에서 Agent를 조합하고 직접 실행한다. 개발자는 Python 함수로 도구를 제공하고 화면에서 자산·Setup·실험을 관리한다. 첫 모델 provider는 OpenAI다. 데이터는 사용자별로 분리하고 첫 배포에는 한 사용자만 허용한다.

자산 내용은 Python 코드 편집기로 작성하고 화면 상단에 결과 변수·타입을 안내한다. 원문을 서버의 일반 폴더에 저장하고 Git으로 형상관리하며, 실제 Agent 실행 시 값을 계산한다. 사용자 경험과 미결 실행 계약은 [python-assets.md](python-assets.md)를 따른다.

향후 목표는 만든 Agent를 `.py`로 export하는 것이다. 첫 버전에 export 화면/코드 생성기를 구현하지 않되, 실행 코어와 설정·도구 계약을 웹/DB에서 분리한다. 외부 Agent의 Trace를 받아 평가하는 수집 플랫폼은 현재 첫 목표가 아니다.

## 첫 사용자 사례

날씨 조회 HTTP API를 사용하는 Agent로 한 사이클을 완주한다.

1. 개발자가 날씨 조회 Python 함수를 등록하고 배포한다. 함수는 명시적인 타입과 설명, HTTP timeout과 출력 계약을 가진다.
2. 사용자가 Agent Prompt·OpenAI 모델·날씨 도구로 Agent Setup A를 만든다.
3. Test Case, Dataset, Golden, Judge Prompt/Model, Rubric, Scoring Rule로 Evaluation Setup을 만든다.
4. A의 Experiment를 생성하고 반복 실행한다. 진행과 Agent Trace·평가 결과를 확인한다.
5. A를 복제해 Prompt 또는 Tool Description을 바꾼 B를 만들고 같은 조건으로 실행한다.
6. A/B의 품질·실패·비용을 비교하고, 퇴행 Case의 두 Trace와 Judge 근거를 확인한다.

실시간 날씨의 숫자를 고정 정답으로 저장하지 않는다. live 평가의 Golden은 ‘도구가 반환한 지역·시각·단위·수치를 왜곡하지 않는다’처럼 기준을 담고 Judge에게 실제 도구 결과를 제공한다. 자동 인수 테스트에는 고정 날씨 응답을 쓴다.

## 첫 완성본 범위

| 영역 | 제공할 동작 |
| --- | --- |
| 접근 | 브라우저 로그인, 허용된 팀원만 서버 접근; 개인 데이터 격리, 첫 배포 계정 1명 |
| 자산 | Definition 종류별 생성·새 Version 발행·이력 조회·보관, Dataset Case 편집 |
| Agent Setup | Prompt/Model/등록 Tool/Runtime 선택, 생성·목록·상세·복제·보관 |
| Evaluation Setup | Dataset/Golden/Judge/Rubric/Scoring 구성, 정합성 검증·복제·보관 |
| Experiment | 고정 구성 생성·복제, Case 범위와 Repeats 선택 |
| 실행 | 멱등 Batch 생성, Run/Case 진행, 취소, worker 중단 복구 |
| Trace | Agent 입력/모델/도구/최종 답변, 실패한 열린 호출, Judge 호출·근거 조회 |
| 분석 | 8 Scope의 기본 조회, 같은 평가 조건의 A/B 비교, Case 퇴행과 반복 변동 |
| 운영 | 서비스 기동, migration, 로그, 접근 차단 검증, backup/restore, live smoke |

‘MVP니까 화면만’ 또는 ‘실행만 되면 됨’으로 완료 기준을 줄이지 않는다. 구현은 작은 수직 기능으로 나누지만 첫 서비스는 위 흐름을 실제 웹·API·worker·DB에서 완주해야 한다.

Definition은 독립 자산/Version으로 재사용한다. 첫 버전은 8 Scope와 정해진 지표·축 선택, 정의·분모·분포 확인을 제공한다. 자유 수식/SQL 엔진은 범위에 추가하지 않는다.

## 내비게이션

```text
Setups                   Experiments                   Analytics
├─ Agent Setups          ├─ Experiments                ├─ Scope
└─ Evaluation Setups     ├─ Runs                       ├─ Overview
                        └─ Traces                     ├─ Setups
                                                      ├─ Cases
                                                      ├─ Traces
                                                      └─ Metrics
```

Definition 편집은 Setups 내부의 자산 관리 진입점과 Setup 구성 화면에서 접근한다. 실행 요청 묶음은 Experiment 상세의 실행 이력에 표시한다. Batch/Evaluation 내부 개념마다 최상위 탭을 추가하지 않는다.

Experiments의 Trace는 실행 하나를 설명하고 Analytics의 Trace는 선택한 비교 범위의 차이를 설명한다. 같은 viewer를 사용하고 탐색 맥락만 다르게 제공한다.

## 후속 범위

| 항목 | 첫 단계의 대비 |
| --- | --- |
| Python export | serializable Setup manifest, 명시적 도구 artifact, 웹/DB 독립 실행 계약 |
| 다른 model provider | provider SDK를 adapter 안에 유지, capability 검증 |
| 재평가 | Evaluation 작업과 Result 분리; 실제 재평가 저장/선택 계약은 기능 도입 때 확장 |
| 외부 Agent 수집, 다중 Agent | 현재 런타임과 제품 모델을 불필요하게 일반화하지 않음 |
| 코드 Evaluator | Judge 응답 검증과 scoring 순수 함수는 지금 구현, 평가 방식 확장은 실제 필요 때 |
| 자유 Metrics 탐색·통계 검정 | 고정 지표의 계약과 표본 수를 먼저 신뢰 가능하게 구현 |
| 자동 Prompt 최적화·Dataset 생성 | 수동 개선 루프가 안정된 뒤 판단 |
| CI/Slack 연동·댓글·세밀한 권한 | 개인 사용 흐름 완성 후 필요 확인 |
| 비용 예산·쿼터 UI | 첫 버전은 사용량·비용 및 실행 상한을 제공 |

## 제품 품질 기준

- 원본 입력·구성·Trace·평가 근거로 요약 수치를 추적할 수 있다.
- 실패/미평가/취소/진행 중을 구분하고 숫자의 분모를 표시한다.
- 화면의 시각적 완성도와 정보 밀도를 함께 챙긴다. 개발자 도구라는 이유로 읽기 어려운 UI를 정당화하지 않는다.
- 기본 동작은 명확한 버튼·빈 상태·오류 안내로 수행할 수 있고, 구현 내부 ID를 외워야 하지 않는다.
- 서버 서비스의 접근 제한, 데이터 영속성, 복구 가능성을 완성의 일부로 본다.

첫 인수 시나리오와 구현 순서는 [engineering.md](engineering.md), 도구/런타임은 [agent-runtime.md](agent-runtime.md), 배포 기본안은 [operations.md](operations.md)에 있다.
