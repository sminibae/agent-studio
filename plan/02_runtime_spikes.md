# 02 실행 기술 검증

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

| SDK 합격 기준 | 현재 상태 |
| --- | --- |
| 1. schema → registry 등록/복원 | schema 추출만 통과; registry 저장/복원 미검증 |
| 2. Description 동시 격리 | fake model에서 통과 |
| 3. unknown/invalid/exception/turn | SDK 오류 동작과 명시적 실패 설정 통과; 제품 상태·Trace 변환 미검증 |
| 4. retry/parallel/attempt/usage | parallel 설정 전달만 관찰; 실제 동시 호출·retry/usage 미검증 |
| 5. 취소/deadline/heartbeat | 미검증 |
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
