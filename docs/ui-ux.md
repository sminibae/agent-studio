# UI / UX

이 문서는 첫 서비스의 화면 계약을 정의한다. [START.md](START.md)의 내비게이션과 8 Scope를 기본으로 한다. 세부 시각 디자인은 실제 화면에서 검토한다.

## 화면의 성격

읽기 쉽고 단정한 개발자 도구를 만든다. 테이블·분할 화면·원문 조회를 중심에 두고 충분한 여백과 시각적 위계를 제공한다. 모든 화면을 카드로 감싸거나 정보 밀도를 위해 글자/클릭 영역을 지나치게 줄이지 않는다.

구조화된 비교는 테이블, 실행 디버깅은 목록+상세 분할 화면, 요약은 다음 탐색으로 이어지는 지표를 사용한다. 긴 내용은 접을 수 있지만 전체 보기·복사가 가능해야 한다.

## 정보 구조와 진입점

사용자는 자신의 자산·실행만 본다. 첫 배포 허용 사용자는 한 명이고 로그인 상태/로그아웃 동작을 제공한다. 사용자 간 공유 선택기는 만들지 않는다.

상단은 Setups / Experiments / Analytics다. 하위 내비게이션은 해당 영역에서 유지한다. 첫 서비스는 desktop 중심이며 좁은 화면은 가로 스크롤 또는 목록→상세 전환을 제공한다.

### Setups와 Definition 편집

- Agent Setups / Evaluation Setups 탭에 목록·검색·상세·새로 만들기·복제·보관을 제공한다.
- 각 탭에 ‘자산 관리’ 진입점을 두어 관련 Prompt/Model/Tool/Dataset/Golden/Rubric/Scoring을 편집한다. Setup 작성 중에도 자산 선택기에서 생성·새 Version 발행으로 이동할 수 있다.
- 사용자 실행 환경 관리에서 원하는 이름의 가상환경과 dotenv 파일을 만들고 패키지·키를 관리한다. Setup에서는 Agent와 Judge 환경을 각각 선택하고 Python 버전·설치 상태·필요한 키 존재 여부를 확인한다. 저장된 비밀 값은 다시 표시하지 않는다. 개발용 `.venv`·`.env`는 목록에 나타나지 않는다.
- 자산 변경은 새 Version 생성임을 표시하고, 지금 만드는 Setup에 새 Version을 선택할지 보여준다. 이미 저장한 Setup은 자동으로 따라 바뀌지 않는다.
- 자산 내용은 `.py` 코드 편집기를 중심으로 작성한다. 상단에 `system_prompt: str`, `items: list[dict]` 등 읽어 갈 변수·필수 항목을 안내한다. 함수·조건문·반복문을 지원하고 실제 실행 시 값을 계산한다. 저장 버튼으로 새 Version을 발행하며 Git commit은 서비스가 처리한다. 원문과 버전 간 차이는 DB Version이 참조한 commit에서 읽는다. 미리보기·오류 줄 표시와 원문/실제 결과의 구분은 [python-assets.md](python-assets.md)를 따른다.
- 미저장 폼은 브라우저 상태의 draft다. DB의 불변 Setup에 부분 저장하지 않는다. 페이지 이탈 시 작성 내용 유실을 안내한다.
- Tool 목록은 배포된 Python 함수에서 등록된다. 화면에서는 선택·설명 변경·버전 확인을 제공한다. 자산 Python 편집과 도구 함수 구현 자체의 웹 편집은 구분하며, 후자의 범위는 [python-assets.md](python-assets.md)의 미결 사항이다.
- Dataset은 Case를 만들고 편집하며 목록에서 선택해 Version을 발행한다. 입력 버전과 Golden 대응 상태를 눈에 보이게 한다.

Setup 저장 전 구성 요약에서 Prompt/Tool/Model/평가 조건의 Version을 확인한다. 복제는 새 이름과 바꿀 항목으로 바로 진입한다. 기존 Setup과 달라진 항목을 표시한다. API key는 이 화면에 입력·출력하지 않는다.

### Experiments와 실행 이력

Experiment는 Agent Setup 하나, Evaluation Setup 하나, Case 범위, Repeats로 생성한다. 구성 변경은 복제다.

실행 전 `100 Cases × 3 Repeats = 300 Case Runs`처럼 요청량과 동시 실행 상한을 표시한다. 버튼 중복 클릭/네트워크 재전송에 같은 idempotency key를 사용한다. 사용자가 의도적으로 다시 실행할 때만 새 키를 만든다.

Experiment 상세는 Execution Batch마다 실행 시각·요청자·Run 목록을 묶는다. created_at으로 묶음을 추론하지 않는다. Runs 목록은 `Batch / Repeat / Agent status / Agent progress / Evaluation progress`를 보여준다.

```text
Batch 17 · Repeat 2/3
Agent      completed    성공 18 / 실패 2 / 취소 0  (20/20 종료)
Evaluation 진행 중       채점 15 / 실패 1 / 제외 2 / 대기·실행 2
```

Agent completed를 ‘전체 평가 완료’로 표시하지 않는다. 취소는 진행 중인 Agent와 남은 Evaluation에 적용되는 행동이라고 안내하고, 이미 얻은 결과를 보존한다.

### Traces와 Evaluation

왼쪽 Case Run 목록, 오른쪽 이벤트 시퀀스와 선택 이벤트 상세를 둔다. 목록에는 Agent 상태·Evaluation 상태·점수를 구별해 표시한다.

- 모델 요청/응답, 도구 인자/결과, 소요시간, 확인된 토큰/비용, 오류를 본다.
- call ID로 도구 호출과 결과를 연결한다. worker 중단으로 결과가 없으면 ‘중단됨·결과 미확인’을 보여준다.
- 실패/취소에는 Final Answer가 없을 수 있다. 빈 텍스트를 성공 결과처럼 표시하지 않는다.
- Judge는 별도 ‘평가’ 패널에서 입력·항목 판정·근거·오류·호출 사용량을 본다.
- 실행에 사용한 환경 이름, Python/패키지 digest와 dotenv revision을 값 없이 확인한다.
- 원문 JSON/Prompt/응답은 고정폭 글꼴, 접기, 검색, 복사를 제공한다. 비밀을 제거한 뒤 보여준다.
- 모델의 내부 생각을 모두 볼 수 있다고 표시하지 않는다. API로 관측한 정보와 공개 요약만 표시한다.

긴 Trace는 페이지 단위로 읽고 추가 로드를 제공한다. 가상 스크롤은 실제 크기 측정 후 넣되 전체 원문 접근을 잃지 않는다.

### Analytics

Scope는 고정 상단에 유지한다. 선택 순서는 [analytics.md](analytics.md)를 따른다. 여러 Setup의 비교를 위해 여러 Experiment/Batch를 선택할 수 있어야 한다.

- Overview: 현재 Scope의 질문, 품질/실행/평가 coverage, 가능한 경우 Δ/Regression.
- Setups: 고정 구성과 차이, 지표 테이블.
- Cases: Case × Setup, 반복 평균과 n, 미평가 수, Regression에서 Trace로 이동.
- Traces: 동일 Case의 A/B Trace 나란히, 각 반복 전환.
- Metrics: 정의된 지표와 Setup/Case/Repetition 축을 골라 지원하는 집계·분포를 본다. 계산식·분모·대상 수를 표시한다. 임의 수식/SQL 편집기는 제공하지 않는다.

비교 조건이 맞지 않으면 이유와 해결 동작을 보여준다. 서로 다른 Rubric/Judge 조건의 숫자를 순위로 표현하지 않는다. 8 Scope에 대해 화면을 각각 만들지 않고 축이 N일 때 필요한 열/반복 선택기를 조합한다.

## 공통 표현

| 대상 | 규칙 |
| --- | --- |
| 지표 | `Pass 65% (13/20)`처럼 분자·분모, coverage와 provisional 여부 |
| null | 데이터 없음 / 미평가 / 반복 없음 / 비용 미확인을 구분 |
| 점수/비율 | 점수 소수 2자리, 퍼센트와 분수 병기; 판정은 반올림 전 서버 값 |
| 차이 | +/− 부호와 단위 |
| 상태 | 색 + 텍스트; 의미가 색에만 의존하지 않음 |
| 자산 | 이름·Version 우선, ID 복사는 보조 |
| 시간 | 사용자 시간대로 표시하고 시간대 표기; 저장은 UTC |
| 정렬 | 실패/미평가 필터, 점수 낮은 Case 우선; null의 위치 명시 |
| 로딩 | 레이아웃을 유지하고 polling 갱신으로 선택/스크롤을 잃지 않음 |
| 오류 | 안전하게 정리한 실제 원인 + 재시도/수정 동작 + request ID |
| 보관 | 삭제와 구분; 과거 이력에 영향 없음을 안내 |

인증이 만료된 API 요청은 HTML을 데이터로 파싱하지 않는다. 로그인 화면으로 이동하되 원래 URL로 돌아올 수 있게 한다. 권한 없는 팀원에게 자산/Trace 일부가 먼저 나타나지 않게 한다.

## URL과 화면 상태

선택된 Setup/Batch/Run/Case Run, 분석 Scope, 탭·필터·정렬은 복원 가능한 URL 상태로 둔다. 큰 Scope는 ID 목록 길이 제한을 검사하고 첫 버전 상한 내에서 직렬화한다. Prompt/비밀·원문 입력을 URL에 넣지 않는다.

Trace에서 Run, Run에서 Experiment, Regression에서 원래 비교 Scope로 돌아갈 수 있어야 한다. 탭 전환이 Scope를 초기화하지 않는다.

## 시각 디자인과 접근성

Next.js/React와 shadcn/ui를 사용하되 구성 요소 선택은 화면 목적에 따른다. 첫 디자인은 중립 색상, 일관된 간격·타이포그래피, 명확한 구분선과 상태 강조를 기본으로 한다. 라이트/다크는 같은 design token으로 지원하는 안을 채택한다.

키보드로 주요 폼·테이블 선택·Trace 상세에 접근하고 focus가 보이게 한다. 아이콘 버튼에는 이름을 제공하고 분할 화면은 읽기 순서를 유지한다. 오류를 색만으로 표시하지 않고 기본 UI 확대에서도 내용이 사라지지 않게 한다.

확인 모달은 보관 등 짧은 결정에만 사용하고 긴 상세 정보는 페이지/패널로 보여준다. 화면의 구체적인 글꼴·폭·행 높이는 첫 수직 기능의 실제 화면으로 검토한다.

## UI 인수 확인

빈 저장소에서 사용자가 자산과 Setup을 만들 수 있는지, 중복 실행 방지, 평가 대기/실패, 취소, 반복 없음, 비교 불가, Regression → 두 Trace, 로그인 만료, 좁은 화면과 키보드 탐색을 확인한다. wireframe만으로 완료했다고 판단하지 않는다.
