# 배포·접근·운영

서버 배포, 브라우저 로그인, 사용자별 개인 데이터를 제공하며 첫 배포에는 한 사용자를 허용한다. 배포 공급자·도메인은 미정이며 아래 구성은 구현·검증할 운영 설계다.

## 첫 배포 구성

서버 1대에 Docker Compose로 다음 프로세스를 실행하는 안을 권한다. 특정 서버 사업자는 요구하지 않는다.

```text
Browser HTTPS
  → Caddy (TLS + route + 인증 확인)
      → OAuth2 Proxy (로그인/session)
      → /api/* : FastAPI
      → 나머지 : Next.js
FastAPI → PostgreSQL ← Worker (동일 backend artifact)
Worker → OpenAI / 등록된 날씨 HTTP API
```

PostgreSQL과 사용자별 자산 Git 저장소는 영속 volume을 사용한다. 자산 저장소는 애플리케이션 배포 디렉터리와 분리하고 Git 접근은 서비스 내부에서 처리한다. API/DB/worker 포트는 인터넷에 공개하지 않는다. Next.js와 API가 같은 origin 아래 있으므로 브라우저 CORS 우회 설정이 필요 없다. 첫 배포 자원 후보는 2 vCPU/4 GiB이며 부하 검증에서 조정한다. 처리량/SLA를 측정 전 보장하지 않는다.

## 로그인 기본안

Google OIDC + OAuth2 Proxy를 기본 후보로 둔다. 첫 배포에는 운영자가 지정한 한 계정만 allowlist로 허용한다. 로그인 provider의 최종 선택은 사용자 계정 환경을 확인한 뒤 설정한다. 앱 자체의 비밀번호 가입/재설정은 제공하지 않는다.

OAuth2 Proxy의 Google 연결과 이메일 허용 목록을 활용하고 Caddy가 인증 precheck를 수행하는 구성이 가능하다. [Google provider](https://oauth2-proxy.github.io/oauth2-proxy/configuration/providers/google/), [이메일 허용 설정](https://oauth2-proxy.github.io/oauth2-proxy/7.6.x/configuration/providers/), [Caddy forward_auth](https://caddyserver.com/docs/caddyfile/directives/forward_auth)

공급자 이름과 사용 방법의 근거이며 실제 설정 파일은 아직 작성하지 않았다. 설치 때 지원 중인 버전의 integration 지침으로 검증한다.

- HTTPS, Secure/HttpOnly/SameSite cookie, OIDC state 검증과 안전한 redirect를 적용한다.
- UI 페이지의 비인증 요청은 로그인으로, `/api`는 401 JSON으로 처리한다. API가 login HTML을 200으로 받지 않게 한다.
- backend는 신뢰하는 내부 proxy가 설정한 신원만 받아들이며 외부가 보낸 identity header는 경계에서 제거·재설정한다.
- 내부 직접 호출로 인증을 우회할 수 없게 네트워크와 proxy→API 서비스 인증을 구성한다. 누락/잘못된 proxy credential이면 API는 거부한다.
- 변경 API는 허용 Origin과 CSRF token/검증 계약을 적용한다. SameSite cookie만으로 모든 CSRF를 막았다고 간주하지 않는다.
- logout 후 재접근, session 만료, 허용되지 않은 계정, 헤더 위조, 직접 API 접근을 배포 인수 테스트에 포함한다.

## 개인 데이터와 소유권

`app_user`는 인증 공급자의 안정된 `(issuer, subject)`로 식별한다. 이메일은 표시/초대 승인용이며 소유자 PK로 사용하지 않는다. API는 신뢰된 신원으로 app_user를 해석한다.

인증 integration 검증에서는 proxy가 전달하는 user 필드가 실제로 안정된 subject인지 확인한다. 이메일만 전달되는 설정을 subject로 오인하지 않는다. 필요한 issuer/subject를 전달·검증할 수 없으면 identity adapter 구성을 보완한 뒤 배포한다.

- 자산·Version·Setup·Experiment·실행·Trace·평가에 owner_id를 둔다. 서버가 인증에서 채우고 클라이언트의 owner_id 지정은 받지 않는다.
- 모든 조회·변경·보관·복제·실행·분석·목록 cursor의 소유자 범위를 검사한다.
- 다른 사용자의 ID는 404로 처리하며 존재/이름/오류 상세를 누설하지 않는다.
- 같은 요청에서 연결하는 Dataset/Golden/Setup/Run도 모두 같은 owner여야 한다. DB composite FK로 교차 소유자 연결을 차단한다.
- worker는 Batch의 고정 owner 범위로만 읽고 쓴다. Analytics의 여러 Run 선택도 같은 사용자 범위를 벗어날 수 없다.
- 배포된 Python 도구 구현 catalog는 서비스 관리자가 제공하는 read-only 자원이다. 개인 Tool Definition/Description/실행 결과는 각 사용자 소유다.

현재 허용 사용자는 한 명이어도 테스트에는 두 명을 만들어 API·DB·worker·Analytics 격리를 검증한다. 초대·공유·권한 등급·사용자 간 자산 이동 UI는 첫 범위에 넣지 않는다.

## 비밀과 사용량

첫 사용자 OpenAI credential은 서버 secret으로 주입하고 DB에는 식별자만 저장한다. prompt/도구 결과/오류/로그에 키가 남지 않도록 경계를 둔다. 브라우저에 provider key를 보내지 않는다.

향후 두 번째 사용자를 허용하기 전에는 provider credential과 과금 주체를 사용자별로 둘지 서비스 계정을 공유할지 정한다. 개인 데이터 격리만으로 credential/비용 권한까지 정해진 것은 아니다. 첫 배포에서 owner별 secret 관리 UI를 미리 구현할 필요는 없다.

도구 코드는 운영자가 검토하여 artifact에 포함한다. Python 함수는 trusted code이며 decorator가 sandbox를 제공하지 않는다. 사용자 Python 자산은 별도 격리 환경에서 실행한다. 웹·DB·provider credential과 다른 사용자 파일에 접근하지 못하도록 하고 시간·메모리·출력·파일/네트워크 접근 정책을 적용한다. 허용 모듈과 격리 기술은 [python-assets.md](python-assets.md)의 구현 전 검증 항목이다.

## 배포·복구 기본안

1. version을 고정한 container artifact를 build한다.
2. DB backup을 확인하고 새 migration을 단일 작업으로 수행한다.
3. 새 작업 선점을 멈추고 worker를 제한 시간 동안 drain한다. 남은 작업은 lease 복구 규칙을 따른다.
4. API/worker/web을 배포하고 readiness와 소규모 smoke를 확인한다.
5. 실패 시 호환 가능한 이전 artifact로 돌아가거나 migration 계획에 따라 forward fix/restore한다.

DB backup은 하루 1회 암호화하여 서버 밖에 저장하고 7일 보존하는 것을 시작값으로 제안한다. 목표 RPO 24시간/RTO 4시간은 복원 훈련으로 검증해야 하는 운영 목표이며 현재 달성했다고 주장하지 않는다. 중요한 실험 빈도에 따라 조정한다.

자산 Git 저장소도 백업·복구 대상이다. 복구할 DB snapshot이 참조하는 모든 commit·원문과 보존 참조를 포함한다. 작업 폴더의 최신 파일만 복사하지 않는다. 복원 시 DB의 저장소·commit·경로와 원문 hash를 검사한다. Git 보존 참조를 포함한 백업·복원 및 미발행 commit 처리 규칙은 [python-assets.md](python-assets.md)를 따른다.

첫 버전은 자동 실행 이력 삭제를 하지 않고 저장 용량을 모니터링한다. 실제 데이터 보존 기간과 영구 삭제 정책은 실사용 데이터 반입 전에 정한다. Git 작업 폴더에서 파일을 삭제해도 과거 commit에는 원문이 남으므로 이력과 백업까지 포함한 제거 절차가 필요하다. 보관(archive)은 삭제가 아니다. 민감 원문 제거 시 관련 분석의 불완전 상태와 감사 기록을 남긴다.

## 관측성과 제한

request/batch/run/case/evaluation/owner ID를 구조화 로그에 포함하되 Prompt와 secret을 기본 로그에 중복 기록하지 않는다. DB·worker heartbeat·queue 대기량·오류/timeout 수·저장 용량을 확인할 수 있어야 한다.

Case/Repeat/concurrency/deadline/Trace 크기는 [execution.md](execution.md), [agent-runtime.md](agent-runtime.md)의 상한을 적용한다. 한도 초과가 worker/DB 전체 장애로 번지지 않도록 입력과 저장 경계에서 검사한다.

## 배포 전에 필요한 실제 값

서버 위치/OS·도메인·Google 또는 대체 OIDC 앱 설정·허용 사용자 신원·OpenAI 사용 가능한 model ID·secret 주입·backup 저장 위치가 필요하다. 문서 단계에서는 임의 계정/비밀을 만들거나 서비스를 구매하지 않는다. 구체 값은 배포 준비 단계에서 확인하며, 그전에도 로컬 전체 서비스와 격리 테스트는 진행할 수 있다.
