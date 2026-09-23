# 다음 작업 인계 — 2026-09-16

## 어디서 다시 시작할지

- 코드 작업 브랜치: `feat/user-runtime-spikes`. 내일 이 브랜치에서 이어서 작업한다.
  `dev`에는 실행 환경 설계와 동시 실행 스케줄링 설계가 각각 `--no-ff`로 병합돼
  있다. 코드 spike는 아직 `dev`에 병합하지 않았다.
- 01 프로젝트 골격은 완료됐다. 현재 02 실행 기술 검증은 **진행 중**이다.
  관찰표와 재현 내용은 [02 실행 기술 검증](02_runtime_spikes.md)에 있다.
- 사용자별 `.venv`·`.env`는 개발용 `backend/.venv`·루트 `.env`와 별개다.
  Agent/Judge Setup이 사용자 Execution Environment를 선택하는 설계다.
  [사용자 실행 환경](../docs/runtime-environments.md)을 따른다.
- 여러 실험·사용자의 동시 실행 정책은 [실행 대기열과 자원 배분](../docs/scheduling.md)에
  정했다. 전체 4개·owner별 2개 실행 예약, 미종료 작업 owner별 5,000개·전체
  20,000개, owner 순환 점유, 컨테이너 정리 전 슬롯 보유가 **설계값**이다.
  큐·worker·예약 테이블은 아직 구현되지 않았다. 2 vCPU/4 GiB에서 4개 동시
  실행이 가능한지도 부하 시험 전에는 확정할 수 없다.

## 지금까지 검증한 것

- `openai-agents==0.22.2`를 lockfile에 고정했다. fake model 테스트로 typed tool
  schema, 서로 다른 Description의 동시 격리, unknown/invalid tool·예외·turn 한도,
  명시적 retry 정책과 시도 수, provider/local 도구 병렬 제한, async 취소 중
  heartbeat, tracing OFF 상태의 로컬 hook, 가짜 날씨 도구를 관찰했다.
  JSON tool manifest의 허용 factory 등록·복원도 prototype으로 확인했다.
- `backend/src/agent_studio/spikes/user_environment.py`와 테스트는 사용자가
  이름 붙인 venv Python·dotenv 선택, 선택 패키지 import, 다음 실행의 dotenv
  교체 반영, timeout·출력 상한·타입 오류를 확인한다. **이 host subprocess는 다른
  사용자/호스트 파일을 읽을 수 있음이 테스트로 드러났으므로 제품 실행기에
  연결하면 안 된다.** 서비스 환경 변수를 자식에 주지 않는 것만으로 파일 격리는
  이루어지지 않는다.
- `bash backend/spikes/container_environment_smoke.sh`는 macOS Docker Desktop에서
  제한된 Linux 컨테이너 안의 이름 지정 venv로 가짜 dotenv를 읽는 Prompt를
  실행했다. 다른 owner 파일·`.git`·서비스 DB 환경 변수의 미전달 및
  `--network none` 외부 연결 실패를 작은 smoke로 확인했다. 실제 SDK를 그
  컨테이너에서 실행하거나 전체 격리를 증명한 결과는 아니다.
- 마지막 코드 변경 후 `make check` 통과: backend 테스트 32개, frontend 테스트
  4개와 lint·typecheck·OpenAPI drift·build. 컨테이너 smoke도 통과했다.
  그 뒤 변경은 문서뿐이며 링크 존재와 `git diff --check`를 확인했다.

## 내일 먼저 할 일

1. `git status --short --branch`와 [02 계획](02_runtime_spikes.md)을 확인한다.
   코드 변경 전 필요하면 `make install`로 잠긴 의존성을 복원한다.
2. host subprocess를 제품 경계로 확장하지 말고, 제한된 컨테이너에서 **선택한
   사용자 venv의 SDK/runner와 Prompt**를 실행하는 최소 adapter를 검증한다.
   venv는 Linux 환경에서 만들고 읽기 전용 revision으로 고정한다. 사용자 dotenv만
   전달하고 개발용 `.env`·DB credential·Docker socket·다른 owner 파일은 빼야 한다.
3. timeout, 메모리·PID·출력 상한, 강제 취소 뒤 자식 프로세스/컨테이너 정리,
   정리 실패 시 슬롯 보유를 공격 테스트한다. Agent 모델 호출에 필요한 네트워크는
   허용 대상만 통과시키는 경로를 별도로 검증한다. `--network none` smoke만으로
   실제 SDK 호출 가능성을 주장하지 않는다. macOS뿐 아니라 Linux/CI에서도
   재현한다.
4. 02의 남은 SDK 항목인 제품 상태·Trace/usage 영속 매핑, 실패 attempt 기록,
   deadline·블로킹 sync 도구, 실제 HTTP weather adapter를 검증한다. 실제
   PostgreSQL·worker 경계를 건드릴 때 `make test-integration`을 실행한다.
   02 종료 조건을 충족한 후에만 [03 자산과 Setup](00_start.md)의 첫 Prompt
   Definition/Version 수직 기능으로 이동한다.

## 남은 위험과 필요한 입력

- 사용자 Python이 선택한 **자기 dotenv** 값을 읽는 것은 의도한 계약이다. 다른
  owner·서비스 비밀을 읽지 못하게 하는 컨테이너 mount/권한/네트워크 격리와
  출력 비밀 제거는 아직 제품 수준으로 검증되지 않았다.
- 사용자 환경 패키지 설치의 새 revision 교체, 선택 venv 안의 SDK 버전 검증,
  Agent/Judge별 환경, container orphan 복구, 동시 owner별 공정 점유는 설계만 있다.
  [실행 대기열과 자원 배분](../docs/scheduling.md) 및
  [실행 계약](../docs/execution.md)을 구현 시 기준으로 삼는다.
- 실제 OpenAI live smoke에는 사용자가 선택한 dotenv의 유효한 credential과
  사용 가능한 model ID가 필요하다. fake/컨테이너 검증은 이 입력 없이 진행할 수
  있다. 비밀을 Git·Trace·로그에 넣지 않는다.
- 제품 API/worker, 실제 로그인 프록시, 자산/Setup, 평가/분석은 아직 구현 전이다.
  현재 spike 통과를 이 기능들의 완료로 표시하지 않는다.

## 작업 방식

- 기능별 작은 커밋을 유지한다. 설계 전용 브랜치는 `--no-ff`로 `dev`에 병합했고,
  코드 spike는 별도 브랜치에 둔다. squash하지 않는다.
- 규칙은 실패 테스트 → 최소 구현 → 정리 순서로 개발한다. 코드 변경 뒤
  `make check`; DB 경계 변경 시 `make test-integration`; 프런트/API/DB 전체
  경계 변경 시 `make test-e2e`를 사용한다. 외부 LLM 호출은 기본 CI에 넣지 않는다.
- 다음 코드 작업에서 새로 확인한 사실과 미검증 항목을
  [02 실행 기술 검증](02_runtime_spikes.md)에 계속 기록한다.
