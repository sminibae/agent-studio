# 설계 기준과 구현 전 확인 항목

이 문서는 현재 설계의 요약과 미정 항목을 관리한다. 세부 규칙은 각 담당 문서를
따른다. 프로젝트 골격은 실행 검증됐으며 제품 기능과 운영 검증은 진행 중이다.

## 제품과 기술 구조

| 항목 | 설계 | 담당 문서 |
| --- | --- | --- |
| 제품 | 브라우저에서 Agent 구성·실행·평가·비교를 수행하는 개발자 도구 | [product.md](product.md) |
| 접근 | allowlist의 복수 계정 동시 사용, 사용자별 데이터·환경 격리 | [operations.md](operations.md) |
| 자산 | 독립 Definition/Version 재사용, Python 코드 편집기와 결과 변수 계약 | [domain-model.md](domain-model.md), [python-assets.md](python-assets.md) |
| 원문 저장 | 서버 일반 폴더와 Git 형상관리, DB Version의 저장소·commit·경로 참조 | [python-assets.md](python-assets.md), [data-model.md](data-model.md) |
| Python 실행 | 실행 시 코드 평가, 실제 생성된 값 보존, 격리된 실행 환경 | [python-assets.md](python-assets.md) |
| 실행 환경 | 개발 환경과 분리; Setup은 사용자 venv revision을 고정하고 실행 시 override 금지 | [runtime-environments.md](runtime-environments.md) |
| 실행 구성 | Setup/Experiment의 참조 고정, 변경은 복제로 새 구성 생성 | [domain-model.md](domain-model.md) |
| 실행 이력 | Execution Batch, Run, Case Run과 Trace; 평가 작업은 별도 상태 | [execution.md](execution.md) |
| 첫 사례 | OpenAI와 Python decorator 도구를 사용하는 날씨 HTTP Agent | [agent-runtime.md](agent-runtime.md) |
| 분석 | 8 Scope, 지표·분모·분포, 평가 조건을 확인한 비교 | [analytics.md](analytics.md) |
| 애플리케이션 | Next.js + FastAPI + PostgreSQL, 모듈화한 백엔드와 별도 worker | [architecture.md](architecture.md) |
| 후속 기능 | Python export, 웹·DB와 분리된 실행 코어와 도구 계약 | [agent-runtime.md](agent-runtime.md) |
| 개발 방식 | 작은 수직 기능 단위, 규칙과 I/O 분리, 상태·동시성의 실행 가능한 검증 | [engineering.md](engineering.md) |

## 검증이 필요한 기본안

| 항목 | 기본안 | 검증 기준 |
| --- | --- | --- |
| SDK | OpenAI Agents SDK를 AgentRuntime adapter로 사용 | 도구 설명 격리, retry·Trace·취소 계약의 compatibility spike |
| 배포 | 서버 1대, Compose + Caddy + OAuth2 Proxy, Google OIDC 후보 | 실제 계정 로그인, 접근 격리, 서비스 기동·복구 |
| 채점 | LLM Judge + 정규화 가중 평균 | 응답 검증, 실패/미평가 구분, 점수 검산 |
| 실행량 | 100 Cases × 10 Repeats, 전체 4개·owner별 2개 실행 예약 | 실제 provider 제한, 호스트 자원·부하와 저장 용량 |
| 작업 대기열 | PostgreSQL 기반 owner 순환 점유와 lease·컨테이너 예약 | 동시 점유, 공정성, heartbeat, worker 중단·정리와 늦은 쓰기 차단; [scheduling.md](scheduling.md) |
| Queue 확장 | PostgreSQL polling → 필요 시 Redis wake-up → 다중 서버 운영 시 broker/outbox 검토 | DB 상태 기준과 scheduler 정책을 유지; [scheduling.md](scheduling.md) |

## 구현 전 확인 항목

| 항목 | 확인할 단계 | 기준 |
| --- | --- | --- |
| 자산별 Python 변수·입력·실행 단위 | 해당 자산 기능 구현 전 | [python-assets.md](python-assets.md)의 결과·관계 계약 |
| 사용자 환경 실행과 격리 | 자산 실행기 구현 전 | 사용자별 venv·dotenv 선택, 서비스/타 사용자 credential·파일 차단, timeout·메모리·출력 제한 |
| Git 발행·복구·백업 구현 | 자산 저장과 운영 기능 | 동시 저장, Git 성공 후 DB 실패, 보존 참조, 과거 Version 복원 |
| 동적 평가 조건의 호환 판정 | 평가·비교 기능 구현 전 | 실제 Judge/Rubric/Scoring 결과와 입력 조건 |
| 사용자 Tool 실행 계약 | Tool 편집 기능 구현 전 | 지정 변수의 객체 추출, schema 검증, 격리 실행과 네트워크 정책 |
| Agent SDK를 포함한 후속 패키지 버전 | 실행 기술 검증 | SDK 호환성, 깨끗한 설치와 CI |
| 인덱스·집계 캐시·Trace 외부 저장 | 첫 부하 측정 | EXPLAIN, 응답시간, DB/Trace 크기 |
| 여러 worker·외부 큐 | 동시 실행량 검증 | 점유 경쟁, 처리량, 운영 복잡도 |
| 신뢰구간·통계 검정 | 지표 계약 안정화 이후 | 표본 수, 독립성, 분석 목적 |
| 다중 Agent·재평가·외부 수집 | 첫 완성본 이후 | 실제 사용 사례 |
| 로그인 provider·도메인·서버 | 배포 준비 | 계정 환경과 [operations.md](operations.md)의 인수 기준 |
| 보존 기간·영구 삭제 | 실제 데이터 반입 전 | 데이터 성격, Git 이력의 원문 제거, 운영 목적 |
| 사용자별 provider 과금·격리 | 첫 다중 사용자 배포 전 | 각자의 dotenv credential과 과금 주체, owner별 실행 격리 검증 |

agent-studio 슈퍼 유저는 배포·allowlist·quota·백업을 관리하는 운영 주체다. OS
root, PostgreSQL superuser, 일반 app_user와 동일한 계정이나 권한으로 취급하지
않는다. 구체 경계는 [operations.md](operations.md)를 따른다.
