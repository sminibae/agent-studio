# 03 자산과 Setup

상태: 미착수. 선행: 02의 격리·SDK 실행 하네스 합격.

## 목표

사용자가 자기 실행 환경과 Python 자산을 만들고 정확한 Version으로 Setup을 생성·복제한다.

## 구현 순서

- [ ] **03-1 사용자 실행 환경** — owner별 이름 지정 venv·dotenv·Execution Environment의 저장/API/관리 화면을 만든다. 설치 작업은 제한된 별도 실행으로 처리하고 새 venv revision을 발행한다. dotenv는 원자적으로 교체하고 값 재조회 없이 revision만 기록한다.

- [ ] **03-2 첫 Prompt 수직 기능** — Prompt Definition/Version migration → owner별 Git 저장소 → Python 편집·발행·미리보기·과거 원문 조회를 연결한다. system_prompt: str을 검증하고 Version에 venv revision과 commit/path/hash를 고정한다.

- [ ] **03-3 발행 실패와 복구** — 저장소 잠금, 기반 Version 충돌, 보존 ref, Git 성공 뒤 DB 실패·응답 유실을 처리한다. 실제 Git/DB로 동시 발행과 과거 commit 복원을 확인한다.

- [ ] **03-4 나머지 구성 자산** — Test Case·Dataset·Golden, Model·Runtime·Tool·Tool Description/Set 등 설계의 구성 자산을 작은 기능으로 추가한다. tool 변수의 사용자 callable/SDK 객체 추출·schema snapshot과 실행 시 일치 검사를 적용한다. 허용 factory 목록으로 사용자 Tool을 제한하지 않는다.

- [ ] **03-5 불변 Setup** — Agent/Evaluation Setup의 생성·목록·상세·복제·보관 UI/API를 연결한다. 참조 Version, Dataset/Golden 대응, 도구 이름·순서와 환경 일치를 검사한다. Judge/Rubric/Scoring 실행은 06에서 완성한다.

## 착수 시 정할 것

Prompt/Tool/Rubric 외 자산의 결과 변수·입력·평가 시점 및 Dataset/Golden 등 관계 선언을 03-4 전에 정한다. 03-5의 Evaluation Setup에 필요한 평가 자산 구조는 06과 공유할 계약으로 먼저 확정한다. 저장소 잠금·발행 복구 방식과 환경 설치/미리보기 자원 한도는 첫 구현에서 정한다.

## 완료 확인

- [ ] 두 owner의 목록·원문·환경·schema·오류가 섞이지 않고 교차 owner FK가 실제 PostgreSQL에서 거부된다.
- [ ] 편집은 새 Version을 만들며 기존 Setup과 Git 원문은 유지된다. 동시 발행은 한 요청만 성공하고 실패 복구 뒤에도 발행된 참조가 보존된다.
- [ ] 패키지 설치가 기존 revision을 바꾸지 않고, dotenv 변경은 다음 실행에 반영된다. 다른 환경의 자산 연결과 Setup 환경 override가 거부된다.
- [ ] 화면에서 환경 → Prompt 발행·미리보기 → Setup 생성·복제까지 수행한다. 관련 make check/test-integration/test-e2e를 통과한다.

## 참고

[python-assets.md](../docs/python-assets.md), [runtime-environments.md](../docs/runtime-environments.md), [data-model.md](../docs/data-model.md), [domain-model.md](../docs/domain-model.md), [ui-ux.md](../docs/ui-ux.md)

진행 순서와 상태는 [전체 계획](00_start.md), 재개 지점은 [handoff](handoff.md)를 따른다.
