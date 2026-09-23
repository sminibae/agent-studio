# 사용자 실행 환경

개발·운영 서비스의 Python 환경과 제품 사용자의 Agent 실행 환경은 별개다.
`backend/.venv`와 저장소 루트 `.env`는 개발자가 API, worker, migration, 테스트를
실행할 때 쓰는 고정 환경이다. 사용자의 선택으로 이 두 파일을 바꾸거나 사용자
코드에 전달하지 않는다.

## 사용자가 선택하는 환경

사용자는 자신의 작업 공간에 이름을 정해 Python 가상환경과 dotenv 파일을 만든다.
예를 들어 `weather-py`와 `.env.weather`를 각각 만들고, 두 항목을 묶은
`Execution Environment`를 Agent Setup 또는 Evaluation Setup에서 선택한다.
이름은 owner 안에서 유일하며 파일 경로 대신 이름/ID로 API에 전달한다.
서버는 owner별 전용 디렉터리 아래에서 실제 경로를 구성한다. 다른 사용자의 이름,
절대 경로, `..`, symlink를 통한 경로 이탈은 허용하지 않는다.

- 가상환경은 사용자가 지정한 이름으로 서비스가 생성한다. 사용자는 그 환경에
  필요한 패키지를 설치할 수 있다. 설치 작업은 실행 작업과 분리하고 진행·실패를
  표시한다. 패키지 설치도 서비스 credential 없이 제한된 별도 작업에서 수행한다.
  실행에는 그 환경의 Python 실행 파일을 직접 사용하며 `activate`나
  shell 명령 문자열에 의존하지 않는다.
- dotenv 파일은 사용자별 비밀 파일이다. 사용자는 파일 이름과 `KEY=value` 항목을
  관리한다. OpenAI 호출에는 선택한 파일의 `OPENAI_API_KEY`를 사용한다. 다른
  provider/도구의 키도 같은 방식으로 전달한다. 값은 저장 후 화면에서 다시
  보여주지 않고 DB, Setup, Trace, 로그에 복사하지 않는다. 편집은 파일을
  원자적으로 교체하고 새 revision ID를 만든다. 과거 비밀 값은 실행 이력을
  위해 보존하지 않는다. 이미 시작한 작업은 시작 시 읽은 값을 계속 사용한다.
- 하나의 Setup은 정확한 Execution Environment와 그 안의 **venv revision**을
  고정한다. Agent와 Judge는 서로 다른 환경을 선택할 수 있다. 미리보기에서는
  사용자가 환경을 명시적으로 선택하며 실제 실행과 같은 Python·dotenv 해석
  규칙을 사용한다.
- 패키지 설치·제거는 기존 venv revision을 수정하지 않고 새 revision을 만든다.
  새 revision으로 Agent를 실행하려면 Python 자산을 그 환경에서 다시 검증하여
  새 Version을 발행하고 Setup을 복제한다. 실행 요청에서 Setup의 환경을 다른
  환경으로 override하지 않는다.
- dotenv 값은 credential 회전을 위해 다음 실행부터 새 revision을 사용할 수
  있다. 실행마다 Python 버전, 고정된 패키지 목록 digest와 실제 dotenv revision
  ID를 기록한다. 비밀 값이나 비밀 값의 hash는 기록하지 않는다.
- 여러 작업이 같은 가상환경을 동시에 읽을 수 있다. 패키지 설치는 사용 중인
  디렉터리를 직접 수정하지 않고 새 venv revision을 준비한다. Setup이 참조하는
  revision은 자동으로 바뀌지 않는다. 시작한 작업은 읽기 전용 revision을 끝까지
  사용하며, 해당 revision을 참조하는 Setup과 실행 이력이 있는 동안 보존한다.

## 프로세스와 신뢰 경계

API와 worker는 서비스의 고정 환경에서 실행한다. worker는 owner와 Setup이
선택한 환경을 확인하고 별도 실행 프로세스에 자산 원문, 도구 구현, SDK 요청을
전달한다. 실행 프로세스는 선택한 가상환경의 Python으로 시작한다. dotenv는
shell에서 `source`하지 않고 파싱·검증하여 그 프로세스의 환경 변수로만 전달한다.
서비스의 DB URL, proxy 비밀, 다른 사용자 파일과 Git 저장소는 전달하지 않는다.
실행 프로세스에는 필요한 사용자 자산 파일과 해당 환경만 제공한다.

선택한 dotenv의 값은 그 환경에서 실행하는 사용자 Python 및 도구 코드가
`os.environ`으로 읽을 수 있다. 이는 사용자가 자신의 코드와 credential을 함께
실행하기로 선택한 계약이다. 다른 사용자의 credential을 함께 주입하지 않는다.
사용자 코드가 비밀을 출력할 수 있으므로 Trace·오류·stdout은 비밀 제거와 크기
제한을 거친다. 비밀 제거가 모든 임의 변환 출력까지 보장하지는 않는다. 여러
사용자를 허용하기 전에는 owner별 프로세스·파일·네트워크 격리를 공격 테스트로
입증해야 한다.

timeout·메모리·출력 제한, 취소 뒤 자식 프로세스 종료, worker heartbeat와
lease fencing은 [execution.md](execution.md)의 실행 정책을 따른다. 사용자
가상환경을 현재 OS와 아키텍처에 맞게 생성해야 한다. macOS 개발 환경의
가상환경 디렉터리를 Linux 서버로 복사해 실행하는 방식은 지원하지 않는다.
동시 작업의 owner별 슬롯·대기열·컨테이너 정리는 [scheduling.md](scheduling.md)를
따른다. 실험 실행기는 서비스와 다른 owner의 파일을 mount하지 않으며 Docker
socket에 접근하지 않는다.

## 생명주기와 검증

환경 생성·패키지 설치·dotenv 편집은 owner 인증을 요구한다. 이미 선택된 환경은
보관할 수 있지만 Setup이나 실행 이력이 참조하는 venv revision을 물리 삭제하지
않는다. 사용할 수 없게 된 환경의 새 실행은 `environment_unavailable`로 거부한다.
실행 등록 또는 시작 전에 Python 실행 파일, SDK·도구 의존성, 필요한
키의 존재 여부를 검사한다. 키 값 자체를 검증 오류에 넣지 않는다.

구현 전 spike에서는 사용자 지정 이름 두 개의 독립성, 패키지 설치와 선택한
가상환경에서의 import, venv 수정 시 새 revision과 Setup 복제가 필요한 동작,
dotenv 교체 후 다음 실행에만 적용되는 동작, Agent와 Judge의 별도 환경, 다른
owner 경로/비밀 차단, 자식 프로세스 종료를 검증한다.
실행 프로세스에서 SDK를 사용할 수 있도록 필요한 버전의 SDK/runner 패키지를
각 가상환경에 설치·검사하는 절차도 검증한다.
