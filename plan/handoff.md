# 다음 작업 인계

## 현재 위치

- 기준 브랜치: `dev` (`feat/project-skeleton`과 실행 환경 설계 변경의 no-ff 병합).
- [01 프로젝트 골격](01_project_skeleton.md) 완료: Next.js → FastAPI → PostgreSQL,
  `app_user` migration, 개발용 owner identity, OpenAPI client, Makefile과 CI.
- 아직 없는 것: 실제 로그인 프록시, Agent SDK adapter, 사용자 Python 격리 실행기,
  자산/Setup, worker, 평가와 분석. 개발용 고정 identity를 배포 인증으로 간주하지 않는다.
- 개발 서버와 Docker의 현재 상태는 다음 작업을 시작할 때 다시 확인한다.

## 바로 다음 작업: 02 실행 기술 검증

새 `feat/user-runtime-spikes` 브랜치에서 [02 계획](00_start.md)의 두 spike를 수행한다.
두 결과가 자산 실행과 worker 설계의 선행 조건이다. 제품 테이블이나 UI를 먼저
넓히지 않는다. 상세 결정은 `plan/02_runtime_spikes.md`에 기록하고, 검증 결과에
따라 [decisions.md](../docs/decisions.md)와 담당 설계 문서를 함께 갱신한다.

### 1. OpenAI Agents SDK compatibility spike

- SDK 버전을 lockfile에 고정하고, 웹/DB 없는 작은 harness에서 typed decorator
  도구와 `AgentExecutionSpec` 유사 입력을 실행한다.
- 도구 schema 추출·등록/복원, 같은 함수의 서로 다른 Description을 동시에 사용한
  경우의 격리, unknown tool/잘못된 인자/도구 예외/turn limit을 확인한다.
- SDK의 retry와 parallel tool 설정, 개별 호출 attempt·사용량·Trace 수집,
  취소/deadline 뒤 새 호출 차단을 실제 SDK 버전에서 확인한다.
- 외부 tracing 전송을 끈 상태에서도 제품이 소유할 로컬 이벤트가 남는지 확인한다.
  블로킹 sync 도구가 heartbeat를 막는다면 등록 거부 또는 executor 경계를 정한다.
- 기본 CI는 fake model/HTTP로 결정적으로 실행한다. 실제 OpenAI 호출은 계정에서
  사용 가능한 model ID와 별도 API credential이 준비된 경우에만 소수 live smoke로
  수행하며, 이를 fake 테스트의 대체로 취급하지 않는다.

합격 산출물은 실행 가능한 spike 테스트, 관찰한 SDK 동작/제약, 채택할 adapter
계약 또는 불일치 시 수정할 정책이다. [agent-runtime.md](../docs/agent-runtime.md)의
7개 합격 기준을 모두 대조한다. 통과하지 못한 항목은 미검증으로 명시한다.

### 2. 사용자 이름 지정 실행 환경과 Python 격리 spike

- 개발용 `backend/.venv`·루트 `.env`를 그대로 두고, owner가 이름 붙인 별도
  `.venv`와 `.env`를 선택해 `system_prompt: str`을 평가하는 최소 경로를 만든다.
  미리보기와 실행은 동일한 환경 선택·격리 경계를 사용한다.
- 선택한 venv의 패키지 import와 dotenv의 `OPENAI_API_KEY` 전달을 확인한다.
  사용자 Python은 자기 dotenv 값을 읽을 수 있다. 웹/DB credential, 다른 사용자
  파일과 비밀, Git `.git`과 자산 저장소 전체에는 접근하지 못하는지 공격 테스트로
  확인한다. 파일·네트워크 접근 범위,
  timeout·메모리·출력 제한과 종료 후 잔여 프로세스 처리를 검증한다.
- 같은 원문을 두 번 실행해 시간 등 동적 값이 달라질 수 있음을 확인하고, 실행
  결과 타입 오류·무한 루프·과다 출력·비허용 import를 실패로 구분한다.
- Python 내부의 `exec` 제한이나 Git 저장만을 보안 격리로 간주하지 않는다.
  macOS 개발과 Linux/CI 배포에서 같은 보안 계약을 어떻게 시험할지 기록한다.

합격 산출물은 재현 가능한 실행기 prototype, 위험 경계와 제한 값, 통과/실패
테스트다. 격리 기술을 증명하지 못하면 사용자 Python을 API/worker 프로세스에서
실행하지 않고 해당 기능을 보류한다. 기준은
[runtime-environments.md](../docs/runtime-environments.md)와
[python-assets.md](../docs/python-assets.md)의 실행·결과 보존 계약이다.

## 02 이후 첫 제품 수직 기능

두 spike의 결과를 설계에 반영한 뒤 [03 자산과 Setup](00_start.md)으로 이동한다.
첫 slice는 Prompt Definition/Version 한 종류에 집중한다.

1. 사용자별 이름 지정 가상환경·dotenv 생성/선택과 `system_prompt: str`의
   발행 시 검사·실행 시 평가 계약을 확정한다.
2. 사용자별 별도 Git 저장소에 원문을 commit하고 보존 ref를 만든 뒤, DB에
   repository/commit/path/hash와 Version을 원자적인 DB 변경으로 등록한다.
3. owner 범위의 생성·버전 목록·원문 조회·미리보기 API와 최소 편집 화면을 연결한다.
4. 이전 Version과 참조를 바꾸지 않는지, 동시 발행 conflict, Git 성공 후 DB 실패,
   과거 commit 조회·hash 불일치·복원을 실제 Git/PostgreSQL로 검증한다.

Test Case/Dataset, Model/Tool, Agent/Evaluation Setup은 그 다음 작은 수직 slice로
확장한다. Prompt 하나만 구현하고 첫 서비스의 자산 범위가 완료됐다고 표시하지
않는다. 관계형 자산의 결과 변수·입력·실행 단위는 구현 전에
[python-assets.md](../docs/python-assets.md)의 미결 항목을 결정한다.

## 작업 방식과 검증

- 기능 단위 커밋을 약 250 changed lines 목표로 나눈다. 1,000줄은 기계적
  절대 제한이 아니며 lockfile/생성물은 수동 코드와 구분해 보고한다.
- 별도 브랜치 병합은 `--no-ff`, squash 금지. 검증되지 않은 spike를 제품 런타임
  완료로 표현하지 않는다.
- 규칙은 실패 테스트 → 최소 구현 → 정리 순서로 개발한다. 기본 확인은
  `make check`; DB 경계가 있으면 `make test-integration`; 프런트/API/DB 경계가
  바뀌면 `make test-e2e`를 실행한다. 외부 LLM 호출은 기본 CI에 넣지 않는다.
- 시작 전 `git status --short --branch`로 사용자 변경을 확인하고,
  `make install`로 잠긴 의존성을 복원한다. Docker Desktop이 켜져 있어야
  PostgreSQL 통합/E2E 테스트를 실행할 수 있다.

## 사용자에게 필요한 입력

02의 fake 기반 검증과 로컬 격리 검증은 추가 계정 없이 진행할 수 있다. 실제
OpenAI live smoke 때는 사용자가 선택한 dotenv의 API credential과 사용 가능한
model ID가 필요하다. 비밀은 Git이나 Trace에 넣지 않고 사용자 실행 프로세스에만
주입한다. Google OIDC·도메인·서버,
백업 저장 위치는 08 배포 단계에서 확인한다.
