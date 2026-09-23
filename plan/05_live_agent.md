# 05 실제 Agent 연결

상태: 미착수. 선행: 04의 fake Agent 실행·Trace 경계.

## 목표

선택한 사용자 환경에서 OpenAI 모델과 사용자 날씨 HTTP Tool이 Final Answer를 생성한다.

## 구현 순서

- [ ] **05-1 SDK 제품 adapter** — 02 하네스의 검증된 SDK 설정을 제품 AgentRuntime으로 옮긴다. 고정 Tool 원문/venv에서 객체를 복원하고 schema drift를 거부한다. 오류·retry·parallel·usage·외부 tracing OFF를 제품 기록에 연결한다.

- [ ] **05-2 날씨 HTTP 자산** — 좌표 입력과 고정 endpoint의 날씨 Tool 예제 원문을 제공한다. 응답 구조·단위·시각·출처, timeout·body/결과 상한을 검사하고 실패를 정상 데이터로 반환하지 않는다.

- [ ] **05-3 deterministic 경계 검증** — fake model/HTTP로 tool calling부터 Final Answer·Trace·시도별 usage까지 검증한다. 제한 네트워크의 허용/거부, 사용자 dotenv 선택과 비밀 제거를 확인한다.

- [ ] **05-4 명시적 live smoke** — 실제 사용 가능한 Agent model ID와 사용자 dotenv를 받아 소수 요청으로 실행한다. 선택한 모델·환경 revision·검증 결과를 기록하고 API key는 남기지 않는다.

## 착수 시 정할 것

live 실행 때 허용 model ID와 지원 parameter 조합, 날씨 공급자/endpoint 및 이용 조건을 확인한다. 실제 credential이 없어도 05-1~3 및 06의 fake Judge는 진행 가능하다.

## 완료 확인

- [ ] 날씨 Tool 호출과 Final Answer·입출력·usage가 화면 Trace까지 이어진다.
- [ ] 잘못된 인자·HTTP 실패·취소·timeout이 제품 정책대로 기록되고 서비스/타 owner 비밀이 전달되지 않는다.
- [ ] make check와 관련 integration/E2E는 외부 LLM 없이 통과한다. live smoke는 별도 실행 결과로 남기며 미실행이면 완료로 표시하지 않는다.

## 참고

[agent-runtime.md](../docs/agent-runtime.md), [execution.md](../docs/execution.md), [runtime-environments.md](../docs/runtime-environments.md), [python-assets.md](../docs/python-assets.md)

진행 순서와 상태는 [전체 계획](00_start.md), 재개 지점은 [handoff](handoff.md)를 따른다.
