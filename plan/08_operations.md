# 08 배포와 운영

상태: 미착수. 선행: 03~07 제품 흐름과 각 단계의 격리·복구 검증.

## 목표

두 allowlist 계정이 동시에 쓰는 첫 서비스를 배포하고 백업 복원까지 확인한다.

## 구현 순서

- [ ] **08-1 배포 입력과 정책** — 서버 OS/자원·도메인·OIDC provider·allowlist·model ID·backup 위치를 정한다. 실제 데이터 반입 전 보존/영구 삭제 정책을 정한다. 운영자·OS 서비스·DB migration/service 권한을 구분한다.

- [ ] **08-2 배포 artifact와 로그인** — API/worker/web·DB·Caddy·OAuth2 Proxy 설정을 버전 고정해 구성한다. 단일 migration, 내부 포트 제한, issuer/subject 전달, API JSON 401, Origin/CSRF·session·logout 경계를 검증한다.

- [ ] **08-3 다중 사용자와 부하** — 두 계정으로 자산/Tool/환경/실행/평가/분석 격리와 동시 실행을 검증한다. 100 Cases × 10 Repeats와 4/2 예약의 최악 자원 사용량을 측정하고 실제 슬롯/서버 용량을 확정한다.

- [ ] **08-4 관측·복구·백업** — queue/heartbeat/예약/실제 컨테이너/정리 대기·용량을 관측한다. drain·중단·재기동·orphan 정리와 감사 기록을 확인한다. DB + Git commit/보존 ref + 별도 암호화 dotenv + venv 재생성 정보를 백업하고 복원 훈련한다.

- [ ] **08-5 첫 완주와 인계** — Setup A/B → 실행 → 평가 → 비교 → Trace를 deterministic E2E와 소수 live smoke로 확인한다. 배포·rollback/forward fix·복원·allowlist/quota 변경·긴급 중지 절차를 운영 문서에 남긴다.

## 착수 시 정할 것

실제 계정·서버·도메인·backup 입력은 이 단계에서 확인한다. 현재 2 vCPU/4 GiB, 일일 백업/7일 보존, RPO 24시간/RTO 4시간은 검증할 기본안이며 달성 실적이 아니다.

## 완료 확인

- [ ] 미허용 계정·위조 header·직접 API·CSRF가 거부되고 두 계정 데이터와 provider 과금/credential이 분리된다.
- [ ] 복원 DB의 모든 Git 원문 참조/hash와 Setup·실행·Trace를 조회하고 venv digest를 확인한다. 과거 dotenv 값을 실행 이력에 저장하지 않는다.
- [ ] worker 중단/배포 뒤 중복 Agent 실행이나 슬롯 조기 반환이 없고 운영 지표로 장애를 확인할 수 있다.
- [ ] 전체 check/integration/E2E, Linux 격리 검증, 실제 로그인/live smoke·부하·복원 결과를 명령/환경/실패·미실행 항목과 함께 기록한다.

## 참고

[operations.md](../docs/operations.md), [engineering.md](../docs/engineering.md), [scheduling.md](../docs/scheduling.md), [runtime-environments.md](../docs/runtime-environments.md), [python-assets.md](../docs/python-assets.md)

진행 순서와 상태는 [전체 계획](00_start.md), 재개 지점은 [handoff](handoff.md)를 따른다.
