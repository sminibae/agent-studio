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
