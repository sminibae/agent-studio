# 설계 문서 안내

현재 단계는 **구현 전 설계**다. 프런트엔드·백엔드·DB가 연결된 서비스를 완성하고, 변경과 검증이 쉬운 코드베이스를 만드는 것이 목표다.

## 문서의 범위

- [START.md](START.md)는 제품 구상의 개요다.
- [decisions.md](decisions.md)는 현재 설계 기준과 구현 전 확인 항목을 요약한다.
- 문서는 구현할 동작과 제약을 설명한다. 구현 완료 여부는 코드와 실행 가능한 검증 결과로 확인한다.
- 미정 항목은 해당 문서에 구분하고 확인할 단계와 기준을 적는다.

## 읽는 순서와 책임

| 문서 | 답하는 질문 |
| --- | --- |
| [START.md](START.md) | 사용자가 처음 구상한 제품은 무엇인가? |
| [decisions.md](decisions.md) | 현재 설계 기준과 구현 전 확인 항목은 무엇인가? |
| [product.md](product.md) | 누구의 어떤 일을 어디까지 해결하는가? |
| [domain-model.md](domain-model.md) | 용어, 책임 경계, 불변식은 무엇인가? |
| [execution.md](execution.md) | 실행·평가·재시도·취소·복구는 어떻게 동작하는가? |
| [analytics.md](analytics.md) | 어떤 실행을 비교하며 지표는 어떻게 계산하는가? |
| [architecture.md](architecture.md) | 의존성과 I/O 경계를 코드로 어떻게 표현하는가? |
| [agent-runtime.md](agent-runtime.md) | Python 함수 등록, SDK 실행, 후속 export를 어떻게 연결하는가? |
| [python-assets.md](python-assets.md) | Python 편집기, Git 원문 버전과 실행 시 값을 어떻게 연결하는가? |
| [operations.md](operations.md) | 개인 데이터, 로그인, 배포와 복구를 어떻게 보장하는가? |
| [data-model.md](data-model.md) | 규칙을 어떤 저장 구조와 제약으로 보장하는가? |
| [ui-ux.md](ui-ux.md) | 사용자가 구성·실행·비교·디버깅하는 화면은 어떤가? |
| [engineering.md](engineering.md) | 어떤 순서로 구현하고 무엇으로 검증하는가? |

규칙은 담당 문서에 한 번 정의하고 다른 문서는 링크한다. 설계를 변경할 때 관련 문서의 용어·규칙·저장 구조를 함께 맞춘다. 현재 설계와 미정 항목만 기록하고 결정 날짜·대화 경위·변경 순서는 남기지 않는다.

## 코딩 시작 조건

1. 실제 Agent 예시와 입력 → 도구 → 답변 → 평가의 한 사례가 정해져 있다.
2. 첫 배포의 사용자·접근 경계, Agent 실행 위치, 도구 실행 계약이 정해져 있다.
3. 첫 완성본 범위와 기술 스택이 정해져 있다.
4. 실행·평가 상태, 실패/미평가 처리, 비교 조건이 서로 모순되지 않는다.
5. 핵심 사용자 흐름의 인수 시나리오와 첫 구현 단위가 정해져 있다.

패키지의 정확한 패치 버전, 파일의 세부 이름, 실제 쿼리를 보아야 정할 인덱스까지 미리 고정할 필요는 없다. 결정하지 않은 항목에는 담당 단계와 검증 방법을 적는다.

## 설계 요약

서버에서 브라우저로 접근하고 사용자별 개인 데이터를 관리한다. 첫 배포는 한 계정이며, 플랫폼 내 Agent 조합·실행, Python decorator 도구, 날씨 HTTP 예제, OpenAI, 독립 자산/Version 재사용을 제공한다. Python export는 후속 기능이다.

자산은 Python 편집기로 작성하고 실행 시 약속된 변수 값을 읽는다. 원문은 서버의 일반 폴더에 저장하고 Git으로 형상관리한다. DB의 Version은 저장소 ID·commit ID·파일 경로를 참조한다. 편집·발행·실행 규칙은 [python-assets.md](python-assets.md)를 따른다.

기술 구조는 Next.js + FastAPI + PostgreSQL, 모듈화한 백엔드와 별도 worker, SDK runtime adapter다. owner-scoped 데이터와 실제 DB 격리 테스트를 적용한다. 로그인 provider, 배포 설정과 SDK 호환성은 구현·운영 단계에서 검증한다.
