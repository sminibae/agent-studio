# 구현 재개 인계

기준: 2026-09-23, 로컬 `dev` / `a1b9ef8` 확인. 이번 정리는 문서 작업이며
제품 코드는 변경하지 않았다. 다음 구현은 **[02 실행 기술 검증](02_runtime_spikes.md)의
02-1: 컨테이너 안의 선택 사용자 venv에서 SDK와 사용자 Tool 실행**이다.

## 어디까지 했나

| 영역 | 실제 상태와 근거 |
| --- | --- |
| 프로젝트 골격 | 완료. FastAPI health/me, 신뢰 proxy identity·owner provisioning, PostgreSQL migration, Next.js shell·생성 API client, Makefile/CI |
| 제품 DB/API | 아직 미구현. migration은 `app_user` 하나이며 API는 health/identity router만 등록 |
| 제품 화면 | Setups/Experiments/Analytics는 placeholder. 편집·실행·비교 화면은 아직 없음 |
| SDK spike | `openai-agents==0.22.2` 고정. fake model의 schema/description 격리·오류/retry/parallel/cancel/로컬 hook 검증 코드 존재 |
| 사용자 환경 spike | host subprocess prototype과 제한된 Linux container Prompt smoke 존재. 컨테이너 SDK/사용자 Tool·전체 격리 검증은 남음 |
| 최근 설계 | 사용자 Python Tool 계약, Setup의 venv revision 고정, 다중 사용자 운영·공정 스케줄링은 문서에 반영. 제품 구현은 미착수 |

기존 인계의 “`feat/user-runtime-spikes`에서 계속, 아직 dev 미병합”은 이제 해당하지
않는다. `0d624a8`에서 spike가, `eaa1351`에서 Tool/환경 설계가,
`a1b9ef8`에서 다중 사용자 운영 설계가 `dev`에 병합됐다. 원격 fetch는 이번에
수행하지 않았으므로 원격의 최신 상태까지 확인한 것은 아니다.

## 코드와 문서 진입점

- [API 조립](../backend/src/agent_studio/bootstrap/api.py),
  [최초 migration](../backend/migrations/versions/20260915_01_create_app_user.py)
- [SDK 검증](../backend/tests/test_sdk_spike.py),
  [registry prototype](../backend/src/agent_studio/spikes/sdk_registry.py)
- [환경 prototype](../backend/src/agent_studio/spikes/user_environment.py),
  [환경 테스트](../backend/tests/test_user_environment_spike.py),
  [container smoke](../backend/spikes/container_environment_smoke.sh)
- [설계 요약](../docs/decisions.md) → [runtime](../docs/agent-runtime.md) →
  [사용자 환경](../docs/runtime-environments.md) → [실행](../docs/execution.md) /
  [스케줄링](../docs/scheduling.md)
- 모든 후속 계획과 의존성은 [00_start.md](00_start.md)에 정리했다.

## 다음 구현 세션에서 할 일

1. `git status --short --branch`로 시작 위치와 사용자 변경을 확인한다. 현재 인계는
   `dev` 기준이며 구현은 필요하면 여기서 기능 브랜치를 만든다. 과거 spike 브랜치로
   돌아갈 필요는 없다. 의존성이 없거나 달라졌으면 `make install`로 lockfile을 복원한다.
2. 02 계획의 관찰표와 최신 Tool 계약을 읽는다. 첫 작업의 실패 테스트는
   **선택한 Linux venv에 SDK/runner가 없으면 명시적 오류로 종료**하는 사례로 잡는다.
3. 최소 컨테이너 하네스에서 읽기 전용 venv, 선택한 가짜 dotenv, 실행할 자산 파일만
   전달한다. 사용자 `.py`의 `tool`을 추출하고 fake model로 호출해 Final Answer와
   로컬 이벤트를 받는다. API key나 live 네트워크 없이 재현 가능하게 만든다.
4. Prompt의 Case Run별 재계산/호출 retry 중 값 유지, schema mismatch,
   다른 owner 접근·강제 종료·출력 상한 테스트를 순서대로 추가한다.
   SDK/도구 결과를 제품 상태·이벤트 DTO로 매핑하되 아직 없는 제품 DB 전체를
   한 번에 만들지 않는다. 세부 남은 작업은 02-2~02-5를 따른다.
5. 변경 경계에 맞는 검증을 실행하고 02 관찰표에 통과/실패/미실행과 명령을 남긴다.
   02의 하네스 합격 뒤 [03 자산과 Setup](03_assets_and_setups.md)의 사용자 환경
   관리 → 첫 Prompt Definition/Version 수직 기능으로 이동한다.

첫 변경의 완료 기준은 **실제 SDK가 선택 venv 안에서 fake Tool을 실행하고,
SDK 누락·schema 오류를 분류하며, 종료 후 컨테이너가 남지 않는 재현 명령**이다.
이 한 변경만으로 02 전체 완료나 다중 사용자 격리 완료를 선언하지 않는다.

## 구현 중 유지할 결정

- 첫 완성본부터 복수 allowlist 계정의 동시 사용을 지원한다. 모든 제품 조회·연결·
  실행·Trace·분석은 owner 범위를 적용하고 실제 DB composite FK로 교차 연결을 막는다.
- Tool은 사용자가 작성하는 Python 자산이다. 기존 factory registry spike를 제품의
  사용자 함수 허용 목록으로 굳히지 않는다. `tool` 객체 추출·schema snapshot·
  고정 원문 재실행이 제품 계약이다.
- 서비스 `backend/.venv`·루트 `.env`와 사용자 환경을 분리한다. Setup은 venv
  revision을 고정하며 패키지 변경은 새 revision/Version/Setup으로 이어진다.
  dotenv는 다음 실행부터 교체 가능하고 값이나 값의 hash를 실행 기록에 저장하지 않는다.
- **host subprocess prototype은 다른 호스트 파일을 읽을 수 있다. 제품 API/worker에
  연결하지 않는다.** 현재 `--network none` Prompt smoke는 SDK/도구 네트워크나
  자원·취소·전체 격리의 합격 증거가 아니다.
- 큐는 PostgreSQL 기반이다. 전체 4/owner별 2 Agent·Judge 합산 실행 예약,
  미종료 작업 owner별 5,000/전체 20,000, owner 순환 점유와 정리 전 슬롯 보유는
  설계 기본값이다. worker/예약 테이블은 아직 없고 서버 용량은 부하 검증 전이다.
- Python 원문은 사용자별 별도 Git 저장소, Version은 commit/path/hash와 보존 ref를
  사용한다. Git+DB 실패 복구를 구현하며 현재 작업 폴더를 과거 실행의 기준으로 쓰지 않는다.
- 동적 평가 조건은 실제 생성값과 입력으로 판단한다. 같은 Setup ID만으로 비교하지
  않으며 다른 venv revision의 실행 비교는 `environment_mismatch`로 거부한다.

## 검증 명령과 현재 증거

```sh
make install
make check
# PostgreSQL/worker 저장 경계를 변경했을 때
make test-integration
# 화면/API/DB의 사용자 흐름을 변경했을 때
make test-e2e
# 기존 Prompt 컨테이너 smoke — 새 SDK 하네스와 구분
bash backend/spikes/container_environment_smoke.sh
```

Docker Desktop이 DB/컨테이너 명령 전에 실행돼 있어야 한다. 일반 로컬 기동은
`make dev`이며 web 3000/API 8000을 사용한다. 현재 E2E는 readiness/me만 확인한다.
향후 제품 흐름 검증은 각 단계에서 추가해야 한다.

이전 2026-09-16 인계에는 `make check`(backend 32개/frontend 4개)와 macOS
container smoke 통과가 기록돼 있다. **이번 문서 정리에서는 이를 재실행하지 않았다.**
현재 실행 결과로 오인하지 않는다. 이번에는 코드·Git 이력·설계 대조와 계획 문서의
상대 링크, `git diff --check`를 확인한다.

## 나중에 필요한 입력과 범위

- 02~04 및 fake Judge/분석은 실제 API key 없이 진행한다.
- 05 live smoke: 사용자가 선택한 dotenv의 유효 credential, 허용 Agent model ID,
  날씨 endpoint/네트워크 정책. 06 live Judge에는 사용 가능한 Judge model ID가 필요하다.
- 08 배포: 서버/도메인/OIDC 앱·허용 신원/backup 위치/실제 데이터 보존·삭제 정책.
  계정·서버가 아직 없어도 로컬 구현을 진행한다.
- Python export, 다중 Agent, 재평가, 외부 수집, 사용자 간 공유는 첫 완성본 이후다.

기능은 작은 수직 단위로 구현하고 상태·동시성·불변성 규칙은 실패 테스트부터
고정한다. 코드 변경 뒤 관련 검증을 완료하고 계획 체크박스와 이 문서의 다음 작업을
갱신한다. 기존 계획의 기능별 작은 커밋·병합 시 `--no-ff`/비-squash 방침을 유지한다.
