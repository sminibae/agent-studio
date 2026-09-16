# Python 자산 편집과 실행

자산의 Python 원문은 서버의 일반 폴더에 저장하고 Git으로 형상관리한다. DB는 자산 Version과 정확한 Git 원문 참조를 관리하며, 실행기는 해당 원문을 실행해 약속된 변수의 값을 읽는다.

## 편집기와 결과 계약

- 자산 내용은 `.py` 코드 편집기에서 작성한다. 함수, 조건문, 반복문, 문자열 조합 등 기본 Python을 사용할 수 있다.
- 편집기 상단에 서비스가 읽는 변수와 결과 타입을 안내한다. Prompt는 `system_prompt: str`, Rubric은 `items: list[dict]`이며 항목에 `key`, `description`, `min_score`, `max_score`가 필요하다.
- 저장은 새 자산 Version 발행이다. 사용자는 Git 명령을 입력하지 않고 서비스가 commit과 DB 등록을 처리한다.
- 원문 보기·버전 간 차이 비교는 각 Version이 참조하는 Git 원문을 사용한다.
- 미리보기는 코드를 실행해 실제 문자열·구조화된 값을 보여준다. 미리보기 결과를 이후 실행의 값으로 고정하지 않는다.
- 사용자 자산 간 import는 첫 범위에 포함하지 않는다. 표준 라이브러리와 선택한 사용자 가상환경에 설치된 패키지는 [사용자 실행 환경](runtime-environments.md)의 계약으로 관리한다.

```python
import time

system_prompt = f"지금시간은 {time.time()} 입니다."
```

이 프롬프트에는 코드 실행 시점의 시간이 들어간다. 저장 시각이나 미리보기 시각을 이후 실행에 재사용하지 않는다.

## Git 저장소와 자산 Version

자산 저장소는 `agent-studio` 애플리케이션 소스 저장소와 분리한다. 서버 영속 볼륨에 사용자별 Git 저장소를 두고 서비스가 관리한다. GitHub·Gitea 같은 외부 호스팅은 필수 구성요소가 아니다.

폴더 구조 예시:

```text
asset-repositories/
  <repository_id>/
    .git/
    prompts/<definition_id>.py
    rubrics/<definition_id>.py
```

파일 경로는 자산 종류와 Definition ID로 생성하고 표시 이름과 분리한다. 같은 자산은 같은 경로를 사용하며 수정할 때 새 commit을 만든다. 자산 Version은 저장소 ID·전체 commit ID·저장소 내부 상대 경로로 정확한 원문을 식별한다. DB 필드는 [data-model.md](data-model.md)를 따른다.

```text
Prompt v001 → 저장소 R / commit A / prompts/P.py
Prompt v002 → 저장소 R / commit B / prompts/P.py
```

작업 폴더의 `prompts/P.py`가 바뀌어도 commit A의 원문은 유지된다. Version 번호는 Definition 안에서 증가하며 Git commit의 순번과 같지 않다. Setup은 각 자산의 정확한 Version을 조합하고, 여러 자산이 서로 다른 commit을 참조할 수 있다.

| 저장 위치 | 관리 대상 |
| --- | --- |
| Git 저장소 | Python 원문과 변경 이력 |
| DB | Definition/Version, Git 원문 참조, 소유권, 자산 관계, 실행 상태와 실제 결과 |
| 실행별 임시 디렉터리 | 지정한 commit에서 읽어 온 실행용 파일 |

원문의 기준은 commit에 저장된 파일이다. 작업 폴더는 저장 작업을 위한 공간이며, 발행 완료 여부는 DB의 Version 등록으로 판단한다. DB에 별도로 편집 가능한 Python 원문 복사본을 두지 않는다.

## 발행과 동시 저장

1. 요청의 owner, 기반 Version, 문법과 자산 계약을 검사하고 새 Version ID를 생성한다.
2. 저장소별 쓰기를 직렬화한다. commit에는 요청한 파일 변경만 포함하고 다른 요청의 미저장 내용이 섞이지 않게 한다. 여러 API 프로세스에서도 유효한 저장소 잠금을 사용한다.
3. Git에 파일을 저장하고 commit을 만든다. commit의 해당 파일에서 SHA-256과 크기를 계산한다. DB에 등록하기 전에 `refs/asset-versions/<version_id>`라는 보존용 Git 참조를 생성해 commit을 유지한다.
4. DB 트랜잭션에서 Definition을 잠그고 기반 Version을 다시 검사한다. 새 Version의 저장소·commit·경로·hash를 기록하고 현재 버전 포인터를 갱신한다.
5. DB commit 후 발행 성공을 반환한다. 같은 기반 Version을 동시에 수정하면 하나만 발행되고 다른 요청은 conflict를 반환한다.

Git과 PostgreSQL은 하나의 트랜잭션으로 묶이지 않는다. Git 저장이 실패하면 DB Version을 만들지 않는다. Git 저장 후 DB 등록이 실패하거나 프로세스가 중단되면 미발행 commit/ref가 남을 수 있다. 복구 작업은 DB와 진행 중 발행을 확인해 정리 대상을 판단한다. DB commit 결과가 불명확하면 Version ID로 확인하기 전에 보존 참조를 제거하지 않는다.

발행한 Version의 보존 참조는 이동하거나 삭제하지 않는다. Git의 commit ID를 DB에 적는 것만으로 Git 객체가 보존되지는 않으므로, 보존 참조를 통해 도달 가능한 상태로 유지한다. 미발행 이력 정리는 발행·백업 작업과 경합하지 않도록 하고 발행된 commit을 다시 작성하지 않는다. [Git 참조 관리](https://git-scm.com/docs/git-update-ref), [Git 객체 정리](https://git-scm.com/docs/git-gc)

## 원문 조회와 실행

1. 인증 owner 범위에서 Version과 저장소를 조회한다.
2. 전체 commit ID와 저장소 내부 경로로 원문을 읽고 저장된 SHA-256·크기와 비교한다.
3. 검증된 원문을 실행별 임시 디렉터리에 일반 파일로 준비한다.
4. 선택한 사용자 가상환경의 Python과 dotenv로 별도 프로세스에서 실행하고 결과 변수·타입·자산 규칙을 검사한다.
5. 실제 결과를 영속 기록한 뒤 Agent 또는 Judge에 전달한다.

Git은 특정 commit의 파일을 작업 폴더 변경 없이 읽을 수 있다. 실행 시 `HEAD`나 브랜치의 최신 파일을 사용하지 않고, 공유 작업 폴더를 과거 commit으로 checkout하지 않는다. 저장소·commit·파일 누락과 hash 불일치는 오류로 처리한다. [Git 파일 조회](https://git-scm.com/docs/git-show)

저장소 경로와 Git 인자는 서버가 검증하여 구성한다. 사용자 입력을 shell 명령에 연결하지 않는다. 저장·조회 대상은 허용된 상대 경로의 일반 `.py` 파일로 제한하고 경로 이탈·symlink·사용자 제공 Git 설정이나 hook을 허용하지 않는다. 사용자 Python에 자산 저장소 전체나 `.git` 디렉터리를 전달하지 않는다.

## 실행 시점과 결과 보존

Version은 원문과 결과 계약을 고정한다. 같은 Version도 시간·난수 등에 따라 다른 값을 만들 수 있다. Setup은 Version 참조를 고정하며, 실제 생성된 값은 Case Run 또는 Evaluation의 실행 기록으로 보존한다.

Agent Prompt는 각 Case Run의 Agent 조립 직전에 한 번 평가한다. 같은 Case Run의 모델 왕복과 개별 호출 retry는 이미 생성한 값을 사용한다. 다른 Case Run과 새 Batch에서는 다시 계산한다. 매 모델 호출마다 Prompt를 갱신하는 기능은 첫 범위에 포함하지 않는다.

Judge Prompt·Rubric은 Evaluation 시작 때 해석하고, 해당 작업의 Judge 호출·응답 검증·점수 계산에서 같은 결과를 사용한다. 나머지 자산의 정확한 실행 시점과 관계 선언 계약은 구현 전 확인 항목이다.

발행 시에는 문법·지원 계약을 검사하고 실행 시에는 결과 변수 존재 여부·타입·자산별 정합성을 다시 검사한다. 함수·모듈 같은 중간 객체는 내보내지 않고 계약에 맞는 문자열·구조화된 값만 전달한다.

실행 기록에는 다음을 남긴다.

- 자산 Version ID와 저장소 ID·commit ID·파일 경로·원문 SHA-256.
- 실행 환경 버전, 시작·종료 시각, 검증된 실제 결과와 결과 schema version.
- 선택한 가상환경 ID·Python/패키지 digest와 dotenv revision ID. 비밀 값은 보존하지 않는다.
- 실패 시 자산·오류 종류·코드 줄. 오류를 빈 프롬프트나 기본값으로 대체하지 않는다.

실제 값을 모델/Judge 호출 전에 기록한다. 기록에 실패하면 후속 호출을 시작하지 않는다. lease·취소·owner·비밀 제거·크기 제한은 [execution.md](execution.md)와 [operations.md](operations.md)를 따른다. 과거 결과 조회는 기록된 값을 사용하며 Python을 다시 실행하지 않는다.

## 실행 격리와 운영

사용자 Python은 웹·DB credential과 다른 사용자 파일에 접근할 수 없는 별도 프로세스에서 처리한다. 선택한 사용자 dotenv의 credential은 해당 Python에서 읽을 수 있다. 이는 사용자가 자신의 코드에 제공하기로 선택한 값이다. 서비스의 고정 `.env`와 `backend/.venv`는 사용자 실행에 사용하지 않는다. 시간·메모리·출력 제한과 프로세스 종료를 적용하고 공유 프로세스의 import 캐시와 전역 상태를 실행 간 재사용하지 않는다. 미리보기에도 같은 경계를 적용한다. 네트워크와 파일 접근의 세부 제한은 사용자 패키지·도구 호출과 함께 spike에서 검증한다. Git은 코드의 저장·형상관리를 담당하며 Python 실행 격리를 제공하지 않는다. 경계는 [runtime-environments.md](runtime-environments.md)를 따른다.

백업에는 DB snapshot이 참조하는 모든 commit과 보존 참조를 포함한 Git 저장소를 담는다. 작업 폴더의 최신 `.py` 파일만 복사해서는 과거 Version을 복원할 수 없다. 복원 시 DB의 모든 원문 참조를 읽고 hash를 검사한다. 저장소 잠금·일관된 snapshot·보존 참조를 포함하는 백업 방식은 운영 검증에서 확인한다.

## 구현 전 확인 항목

- Prompt/Rubric 외 자산의 결과 변수·타입, 주입 입력, 실행 단위.
- Dataset 멤버, Golden 대응, Tool 구현 참조처럼 실행 등록 전에 필요한 관계의 선언·검증 계약. 실행 중 관계 변경으로 기존 슬롯·FK를 무효화하지 않는다.
- 동적으로 생성되는 Rubric/Scoring/Judge 설정의 비교 가능성. 같은 Version/Setup ID만으로 실제 평가 조건이 같다고 판단하지 않는다.
- 사용자 가상환경·dotenv를 별도 프로세스에 전달하는 기술, 타 owner 접근 차단, 자원·네트워크 제한 값.
- 저장소 잠금·발행 복구·백업 구현과 실제 파일·Git·DB 장애 검증.
- 도구 함수 구현 자체의 웹 편집 범위. 배포 도구 registry의 계약은 [agent-runtime.md](agent-runtime.md)를 따른다.
