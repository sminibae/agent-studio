# Agent Runtime와 Python 도구

이 문서는 실행·도구 계약을 정의한다. OpenAI Agents SDK를 adapter로 사용하는 것은 기본안이며, 정확한 SDK 설정은 구현 전 compatibility spike로 검증한다.

## 실행 범위

- 플랫폼에서 Prompt·Model·Tool을 조합해 실행한다.
- 도구는 개발자가 Python 함수와 decorator로 작성한다.
- 첫 provider는 OpenAI, 첫 도구는 날씨 조회 HTTP API다.
- 후속 목표는 `.py` export다. 첫 버전에는 코드 생성 기능을 만들지 않는다.
- 자산은 웹 Python 편집기로 작성하고 실행 시 약속된 변수 값을 읽는다. 원문은 서버의 일반 폴더와 Git 저장소에 보관한다. 이는 아래 배포 도구 registry와 구별되는 [Python 자산 계약](python-assets.md)이다.

## function_tool 방식

공식 문서는 Python 함수에 `@function_tool`을 붙이고 `Agent(tools=[...])`에 넣는 형태를 제공한다. 아래는 등록 방식의 개념 예시이며 HTTP 구현은 아직 작성하지 않았다. [공식 Agent 정의](https://developers.openai.com/api/docs/guides/agents/define-agents), [공식 Quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart)

```python
from agents import function_tool

@function_tool
async def get_current_weather(latitude: float, longitude: float) -> str:
    """지정한 좌표의 현재 날씨를 단위·조회 시각과 함께 반환한다."""
    # 구현 시 고정된 날씨 HTTP endpoint를 호출하고 검증한 JSON을 반환한다.
    ...
```

decorator가 붙었다는 사실만으로 우리 DB에 등록되는 것은 아니다. 배포 manifest에 허용 모듈을 명시하고 importer가 그 안의 도구를 읽어 등록한다. import 경로·DB 등록·구현 artifact를 제품의 adapter가 연결한다. 도구 registry는 화면의 임의 모듈 경로를 import하지 않는다. 사용자 작성 Python 자산은 Version이 참조한 Git commit의 파일을 읽어 격리된 실행 adapter로 처리한다.

## 세 가지 계약

| 계약 | 내용 | 누가 변경하는가 |
| --- | --- | --- |
| Python 구현 | 함수·입출력 타입·실제 HTTP 호출·의존성 | 개발자가 코드 배포 |
| Tool Version | 모델에 보이는 이름/설명, 검증된 입력 schema, 구현 ID | 사용자가 화면에서 새 Version 생성 |
| Agent Setup | 정확한 Tool Version 목록과 순서, Prompt/Model/Runtime | 사용자가 복제 후 새 Setup 생성 |

Importer는 명시적 `registry_key`, 배포 artifact digest, entrypoint, 생성된 스키마를 검증한다. SDK 객체는 adapter 안에서 다루고 Domain/DB에는 serializable 계약을 저장한다. 도구 구현은 trusted 배포 코드이며 registry 자체가 사용자 Python의 격리를 제공하지는 않는다. 자산 실행의 격리는 별도 책임이다.

화면에서 Description을 바꾸면 새 Tool Version을 만든다. 함수 인자 schema는 구현과 묶여 있어 화면에서 자유 편집하지 않는다. 실행 시 저장된 설명을 사용한 별도 SDK tool 객체를 조립하고 전역 decorator 객체를 수정하지 않는다. 사용자/Setup 간 설명이 섞이지 않아야 한다.

## 실행 adapter

Application은 `AgentRuntime` port에 `AgentExecutionSpec`, 입력, 취소/deadline, 이벤트 기록 계약을 전달한다. SDK adapter가 `Agent`와 Runner를 조립하고 결과를 중립 DTO로 돌려준다.
Agent와 Judge의 실제 SDK 호출은 각 Setup이 선택한 사용자 가상환경의 Python에서 수행한다. 해당 환경의 dotenv에서 읽은 provider credential을 실행 프로세스에만 제공한다. API·worker의 개발/서비스 `.venv`·`.env`는 그대로 유지한다. SDK/runner 버전과 도구 의존성은 선택한 가상환경에서 검사한다. [사용자 실행 환경](runtime-environments.md)을 따른다.

- SDK의 Agent/Runner ‘run’과 제품의 Run은 다르다. SDK 호출 한 번은 제품의 **Case Run 실행**을 구현한다.
- Experiment 반복·DB 작업 선점·재시도 저장·권한·평가·Analytics는 제품이 소유한다.
- SDK의 도구 호출/agent loop 기능을 우선 사용한다. 같은 loop를 따로 구현해 SDK와 이중 관리하지 않는다.
- SDK 기본 동작이 [execution.md](execution.md)의 정책과 다르면 설정/얇은 adapter로 맞출 수 있는지 검증한다. 맞지 않으면 실행 계약 또는 runtime adapter를 조정한다.
- 첫 실행 정책의 순차 도구 호출에는 provider의 `parallel_tool_calls=False`와 SDK의 로컬 도구 동시 실행 상한 1을 함께 적용한다. 두 설정이 별개임을 고정 버전의 fake model에서 확인했다.
- SDK에는 DB session·HTTP request를 넘기지 않는다. Tool context에는 필요한 HTTP client 등 명시적 런타임 의존성만 주입한다. credential은 선택한 사용자 dotenv에서 주입된 프로세스 환경으로 해석한다.
- Agent와 Judge는 별도 호출/기록이다. Judge에는 도구 실행 권한을 주지 않는다. Judge 입력은 Case 입력, Final Answer, 필요한 Agent Trace/도구 결과, Golden, Rubric이다.

Model ID는 배포 환경에서 허용한 OpenAI 모델 목록에서 명시적으로 선택한다. Agent용과 Judge용을 각각 고정하고 같은 모델도 선택할 수 있다. 지원하지 않는 tool calling/출력 구조/parameter 조합은 등록 또는 실행 전에 거부하며 parameter를 조용히 버리지 않는다. 실제 첫 model ID는 계정의 사용 가능 모델을 확인하여 smoke 때 고정하고 문서 예시에 임의 최신 모델명을 박아 두지 않는다.

[공식 Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)는 Runner 기반 실행을 설명한다. 이 문서의 port/DTO/상태 모델은 SDK 제공 기능이 아니라 제품 설계다.

## Trace 처리

SDK 이벤트/호출을 제품의 Trace와 호출 기록으로 변환한다. SDK가 자동으로 완전한 DB 실행 이력을 제공한다고 가정하지 않는다.

공식 문서상 SDK의 일반 서버 실행에서는 tracing이 기본 활성화되어 있다. 제품의 DB 기록과 외부 Trace 전송을 구분하고, 외부 전송은 기본 비활성으로 구성·검증한다. 외부 전송을 끄면서 로컬 Trace가 사라지지 않는 수집 경로를 spike에서 확인한다. [공식 Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)

Retry 단위의 요청/오류/사용량, 열린 호출의 중단, 취소 뒤 늦은 쓰기를 기록할 수 있어야 한다. 이벤트를 메모리에만 모았다가 마지막에 한 번 저장하지 않는다. secret/header를 제거하고 payload 제한을 적용한다.

## 날씨 도구 예시 계약

HTTP 공급자 기본 후보는 Open-Meteo다. 좌표에 대한 current temperature/weather code 등을 제공하는 API가 있다. 실제 배포 용도의 요금제·호출 한도는 공급자 선정 때 확인한다. [Open-Meteo Weather Forecast API](https://open-meteo.com/en/docs)

- 모델 입력: `latitude` [-90,90], `longitude` [-180,180]. 첫 예제 Case에는 도시와 좌표를 함께 제공하여 지오코딩 기능을 추가하지 않는다.
- 고정 endpoint에 GET으로 호출한다. 모델이 URL/hostname/auth header를 지정하지 않는다.
- 출력: 위치, 공급자가 반환한 시각과 timezone, 조회 시각, 기온·단위·weather code·출처. 반환 내용을 검증한 뒤 JSON 문자열로 모델에 제공한다.
- 네트워크/응답 검증 실패는 도구 오류로 기록한다. 에러 응답을 정상 날씨 데이터로 전달하지 않는다.
- HTTP body 최대 256 KiB, 모델에 전달할 검증 결과 최대 64 KiB, 도구 timeout 10초를 기본안으로 둔다.
- Trace event payload 최대 256 KiB, Case Run별 누적 5 MiB를 기본안으로 둔다. 용량 초과로 원문을 남길 수 없으면 `trace_limit_exceeded`로 종료하고 작은 오류 이벤트 저장 공간을 별도로 확보한다. 잘린 데이터를 완전한 원문처럼 표시하지 않는다.

자동 테스트는 HTTP adapter에 고정 응답을 제공한다. live 결과 비교는 데이터가 달라질 수 있다는 사실을 표시한다. 실행 조건이 고정되어도 날씨 응답이 달라지는 환경을 통제된 실험이라고 설명하지 않는다.

## 구현 전 compatibility spike의 합격 기준

이것은 문서 정비에서 실제로 실행한 검증이 아니다. 골격 직후 실제 SDK 버전을 고정하여 아래를 확인한 뒤 본 실행기를 구현한다.

1. typed Python 함수 → schema 추출 → registry import → Tool Version 저장/복원.
2. 같은 함수에 서로 다른 Description을 적용한 두 Setup을 동시에 실행해 격리 확인.
3. unknown tool, invalid args, tool exception, turn limit의 SDK 기본 동작과 제품 정책을 일치시킴.
4. SDK retry/parallel tool 설정을 제어하고 개별 시도 Trace·사용량을 기록.
5. cancellation/deadline 이후 새 호출을 막고 worker heartbeat가 계속 진행됨. 블로킹 sync 도구는 명시적으로 executor에 격리하거나 첫 등록에서 거부.
6. SDK 외부 tracing 전송을 끄고도 제품 DB Trace가 남음.
7. 웹/DB 없는 작은 harness에서 같은 ExecutionSpec을 받아 날씨 도구를 호출함.

먼저 fake model/HTTP로 검증하고 실제 OpenAI 호출은 선택한 계정/모델로 소수 smoke만 실행한다. SDK 세부 메서드/설정값을 확인하지 않은 상태에서 동작을 검증했다고 기록하지 않는다.

## Python export를 위한 현재 경계

Setup manifest는 자산 Version·저장소 ID·commit ID·파일 경로·원문 SHA-256·결과 계약, Tool Version·implementation 참조, 사용자 Execution Environment 참조, runtime 정책과 schema version을 직렬화할 수 있어야 한다. 실행할 때 불변 참조를 해석하고 Python 자산을 평가한 실제 Prompt/설정으로 ExecutionSpec을 조립한다. 같은 원문 Version의 동적 결과는 실행마다 달라질 수 있다.

export 시 미래에 필요한 것은 manifest, Python 자산 원문과 실행 시 평가 계약, Python 도구 코드/의존성, runtime 조립 코드, 사용자 가상환경 재생성 및 dotenv 변수 안내다. 미리 계산한 Prompt만 내보내 동적 의미를 잃지 않아야 한다. API key·사용자 비밀은 export하지 않는다. 함수 closure·서버 전역 DB 접근처럼 외부로 옮길 수 없는 의존성은 도구 등록 계약에서 드러나야 한다.

독립 단일 `.py` 파일로 모든 의존성을 포함할지, `.py` + runtime package로 제공할지는 export 착수 때 결정한다. 지금 임의 코드 생성기·범용 workflow DSL을 만들지는 않는다.
