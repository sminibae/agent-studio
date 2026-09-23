# 02 실행 기술 검증

상태: 진행 중. spike 코드는 `dev`에 병합됐지만 제품 실행기 합격을 뜻하지 않는다.
2026-09-23 재개 기준 02-1을 완료했고 다음 작업은 **02-2**다.

## 남은 구현 순서

- [x] **02-1 선택 venv의 SDK 실행** — 기존 container smoke를 확장해 Linux에서
  만든 고정 venv revision에 SDK/runner를 설치·검사한다. 읽기 전용 환경에서
  동적 Prompt → fake model → 사용자 Tool → Final Answer를 실행하고 중립 DTO를
  반환한다. 먼저 credential·네트워크가 필요 없는 최소 사례를 완성한다.
- [x] **02-2 사용자 Tool 계약** — `.py`의 `tool` 변수에서 지원 callable/SDK Tool을
  추출하고 schema snapshot 생성·재실행 일치·description 격리를 검증한다.
  변수 누락/지원하지 않는 객체/schema drift를 거부한다. 기존 허용 factory
  registry는 실험용 증거이며 사용자 함수를 대체하는 제품 registry가 아니다.
- [ ] **02-3 격리·종료 공격 테스트** — 두 owner의 파일/환경 분리, 서비스 credential·
  Git·Docker socket 차단, timeout·메모리·PID·출력 상한, 자식 프로세스와 컨테이너
  정리 실패를 검증한다. 설치 작업의 새 revision과 Agent/Judge 별도 환경,
  dotenv 회전도 확인한다. 허용 endpoint만 통과하는 네트워크 경로를 검증한다.
- [ ] **02-4 SDK 실패·이벤트 계약** — deadline·블로킹 sync 도구 처리 정책,
  실패 attempt/usage·취소 후 신규 호출 차단·비밀 제거·Trace 크기 제한을 fixture로
  고정한다. 제품 상태/이벤트 DTO와 incremental sink 계약을 정한다.
- [ ] **02-5 HTTP와 Linux 재현** — 날씨 HTTP adapter를 fake HTTP로 검증하고
  Linux/CI에서도 격리 하네스를 재현한다. 명령·실행 환경·관찰 결과·남은 차이를
  아래 표에 갱신하고 03 착수 여부를 판정한다.

## 단계 종료와 후속 검증의 경계

02는 격리 실행과 SDK 계약의 합격을 증명하는 단계다. 일곱 기준에 미검증이라고
적기만 해서는 종료할 수 없다. 사용자 코드/환경 격리·종료, 사용자 Tool 추출과
복원, 오류·이벤트 수집은 하네스에서 합격해야 한다. 격리 실패가 남으면 03의
사용자 코드 실행 기능으로 진행하지 않는다.

제품 저장 계층이 필요한 검증은 담당 단계에 이어 붙인다. 실제 Git/DB Tool Version
발행·digest 검증은 [03](03_assets_and_setups.md), lease·슬롯 정리와 제품 DB
Trace/attempt 영속화는 [04](04_experiment_execution.md), 실제 OpenAI/날씨 호출은
[05](05_live_agent.md)에서 완료한다. 02에서는 fake event sink로 실패/취소 중에도
점진 기록할 수 있는지 확인하고, 실제 DB 영속화를 완료했다고 표시하지 않는다.

## 목표와 범위

제품 테이블/UI보다 먼저 두 경계를 실행 가능한 하네스로 검증한다.

1. 고정된 OpenAI Agents SDK 버전에서 typed decorator 도구, fake model,
   실패·Trace·취소·retry 동작을 관찰한다.
2. 개발용 `backend/.venv`·루트 `.env`와 분리된 사용자 이름 지정 가상환경·dotenv로
   Python 자산을 실행한다. 필요한 격리와 자원 제한을 검증한다.

## 종료 조건

- [agent-runtime.md](../docs/agent-runtime.md)의 일곱 기준마다 통과 또는 미검증
  상태와 재현 명령을 기록한다.
- [runtime-environments.md](../docs/runtime-environments.md)의 사용자별 선택,
  패키지 import, dotenv revision, 서비스/타 owner 접근 차단을 검증한다.
- 보안 격리가 입증되기 전에는 실험용 실행기를 제품 API/worker에 연결하지 않는다.
- 기본 CI에는 fake model/HTTP만 포함한다. 실제 OpenAI smoke는 별도 credential과
  사용 가능한 model ID가 있을 때만 실행한다.

## 구현 순서

1. SDK를 lockfile에 고정하고 웹/DB 없는 fake harness를 테스트부터 작성한다.
2. 이름 지정 가상환경·dotenv 실행 prototype과 정상/실패 테스트를 작성한다.
3. OS별 실행 격리, timeout·메모리·출력·자식 프로세스 정리를 공격 테스트한다.
4. 관찰 결과와 남은 불일치를 본 문서와 설계 문서에 반영한다.

## 현재 관찰

`openai-agents==0.22.2`를 고정하고 `test_sdk_spike.py`를 fake model로 실행했다.
typed decorator에서 숫자 schema가 생성되고, 동시에 실행한 두 Agent가 서로
다른 description을 유지했다. unknown tool은 `ModelBehaviorError`, turn 한도는
`MaxTurnsExceeded`였다. 잘못된 인자는 기본 설정에서 모델에 오류 도구 결과로
전달되어 다음 응답까지 진행했다. 따라서 [execution.md](../docs/execution.md)의
"잘못된 인자면 Case Run 실패" 정책을 그대로 만족하지 않는다. `function_tool`
생성 시 `failure_error_function=None`으로 두면 잘못된 인자는
`ModelBehaviorError`, 도구 예외는 `UserError`로 올라옴을 확인했다. 제품 adapter는
이 설정을 적용하고 안전한 오류 DTO로 변환해야 한다.
모델 retry는 `max_retries`만 지정해서는 활성화되지 않았다. `policy`에
`retry_policies.provider_suggested()`를 함께 전달하고 provider가 안전한 재시도를
권고할 때 1회 실패 뒤 2번째 시도로 복구했다. `max_retries=0`에서는 같은 오류가
1회 시도로 끝났다. 실패 attempt의 제품 이벤트·사용량 영속 기록은 별도 구현이
필요하다.

| SDK 합격 기준 | 현재 상태 |
| --- | --- |
| 1. schema → registry 등록/복원 | 사용자 `.py`의 sync/async 함수와 SDK `FunctionTool` 추출, JSON snapshot 재평가 일치와 drift 거부 통과; 실제 Version DB·digest 검증은 03 |
| 2. Description 동시 격리 | fake model과 같은 원문의 두 container Setup 동시 실행에서 통과 |
| 3. unknown/invalid/exception/turn | SDK 오류 동작과 명시적 실패 설정 통과; 제품 상태·Trace 변환 미검증 |
| 4. retry/parallel/attempt/usage | runner retry 정책·시도 수, provider parallel 설정 전달, 로컬 도구 동시 실행 상한 1/2, 성공 응답 usage hook 관찰; 실패 attempt 영속 기록 미검증 |
| 5. 취소/deadline/heartbeat | async 도구 중 취소 후 새 모델 호출 없음·event loop heartbeat 통과; deadline·블로킹 sync 도구 미검증 |
| 6. 외부 tracing OFF와 로컬 DB Trace | tracing OFF에서도 로컬 hooks의 모델 사용량·도구 이벤트 통과; 영속 DB Trace 미검증 |
| 7. 웹/DB 없는 날씨 harness | fake weather 함수 호출 통과; HTTP adapter 미검증 |

`user_environment.py`는 사용자가 만든 이름 지정 가상환경의 Python 실행 파일과
dotenv 값을 사용해 Prompt를 평가한다. 테스트에서 개발 서비스 환경 변수는
자식에 전달되지 않고, dotenv를 수정하면 다음 실행에 새 값이 반영되며, 타입 오류·
선택한 venv의 패키지 import, timeout·출력 제한·경로 이탈을 구분했다. **같은 호스트 사용자로 실행한 자식이
다른 파일을 읽을 수 있음도 테스트로 확인했다.** 이 prototype은 파일/네트워크·
메모리 격리를 제공하지 않으므로 제품 API/worker에 연결할 수 없다. 다음 단계는
OS별 격리 실행 경계와 패키지 설치·SDK 실행, 자식 프로세스 정리를 검증하는 것이다.

`bash backend/spikes/container_environment_smoke.sh`는 Docker의 제한된 Linux
컨테이너 안에 `weather-py` 가상환경을 만들고, 선택한 dotenv의 가짜 키를 주입한
Prompt를 평가했다. 실행 컨테이너에는 `.git`/타 owner 파일을 mount하지 않았고,
서비스 DB 변수가 없으며 `--network none`에서 외부 연결이 실패했다. macOS Docker
Desktop에서 통과했다. 이는 파일 mount·네트워크 차단의 작은 검증이다. 실제
SDK 호출에 필요한 제한 네트워크, 메모리/출력 상한의 실패 분류, 강제 종료 뒤
잔여 프로세스, Linux/CI 재현은 아직 확인하지 않았다.

`bash backend/spikes/container_sdk_environment_smoke.sh`는 별도의 설치 컨테이너에서
Linux venv revision을 만들고 `openai-agents==0.22.2`를 설치한 뒤, 실행 단계에는
그 venv를 읽기 전용으로 mount하고 네트워크를 끈다. 선택 dotenv로 동적으로 만든
Prompt와 사용자 `.py`의 `tool` 객체를 SDK `ScriptedModel`로 실제 호출해 Final
Answer·로컬 model/tool event·schema를 JSON DTO로 반환했다. SDK 미설치에는
`sdk_unavailable`, 저장 schema 불일치에는 `tool_schema_mismatch`를 반환했으며,
각 `--rm` 컨테이너가 종료 뒤 남지 않음을 확인했다. 이 smoke는 02-1의 최소 실행
경계를 통과하지만 설치 의존성 전체 고정, 악성 코드의 자원/파일/프로세스 공격,
허용 네트워크와 Linux CI 재현까지 증명하지 않는다.

02-2에서는 `.py`의 `tool` 변수로 지정한 sync/async 함수와 SDK `FunctionTool`을
허용하고, 누락·비호출 객체·지원하지 않는 callable 객체를 안정된 오류로 분류했다.
함수 signature·annotation·docstring에서 생성한 이름·description·입력 schema를
JSON snapshot으로 저장하고 같은 원문 재평가 결과 전체가 일치해야 한다. Setup별
description은 검증된 Version Tool을 변경하지 않고 실행 직전에 새 인스턴스에
적용한다. 단위 테스트와 container smoke에서 schema/description drift 거부 및 같은
원문의 두 Setup 동시 실행 description 격리가 통과했다. 재현 명령은
`backend/.venv/bin/pytest backend/tests/test_user_tool_contract_spike.py -q`와
`bash backend/spikes/container_sdk_environment_smoke.sh`다. 임의 callable 객체와
다른 SDK Tool 종류는 현재 지원하지 않는다.
