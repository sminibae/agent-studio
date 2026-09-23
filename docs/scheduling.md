# 실행 대기열과 자원 배분

이 문서는 여러 Experiment와 여러 owner가 동시에 실행을 요청할 때의 점유·공정성·
자원 계약이다. 작업 상태와 lease는 [execution.md](execution.md), 사용자 코드의
격리는 [runtime-environments.md](runtime-environments.md)를 따른다. 아래 값은
첫 배포 기본안이며 부하 시험 전 처리량을 보장하지 않는다.

## 작업과 상한

Batch 등록은 작업 예약이다. Case Run 하나가 Agent 작업 하나이고, Agent가
끝나서 `queued`가 된 Evaluation 하나가 Judge 작업 하나다. 같은 사용자에게
여러 Batch를 허용하며 Batch/Experiment별 전용 worker를 만들지 않는다.

| 범위 | 첫 기본안 | 적용 시점 |
| --- | --- | --- |
| 전체 실행 | 4개 | 컨테이너 예약부터 종료·정리 확인까지 |
| owner별 실행 | 2개 | 같은 기간; Agent/Judge 합산 |
| owner별 미종료 작업 | 5,000개 | Batch 등록 시 Case Run+Evaluation 모두 계산 |
| 전체 미종료 작업 | 20,000개 | 같은 등록 트랜잭션 |

한 Batch의 최대 1,000 Case Run은 Evaluation 1,000개까지 포함해 2,000
작업을 예약한다. 미종료 작업은 Case Run의 `pending/running` 및 Evaluation의
`pending/queued/running`이다. 완료·실패·취소·skip은 이 상한에서 빠진다.
상한을 넘는 등록은 Batch를 일부만 만들지 않고 `429 queue_capacity_exceeded`
및 재시도 안내를 반환한다. 같은 idempotency key의 기존 Batch 조회는 새 예약이
아니므로 상한보다 먼저 처리한다. 환경 생성·패키지 설치·미리보기에도 별도
자원 상한과 대기열을 적용하고, 실험 슬롯을 몰래 사용하지 않는다. 이 작업들의
구체적인 상한은 해당 기능을 구현하기 전에 정한다.

전체 4개와 owner별 2개는 서로 다른 제한이다. 한 사람만 실행하면 최대 2개가
진행되고 나머지는 대기한다. 두 사람이 각각 작업을 쌓으면 동시에 최대 2개씩
진행할 수 있다. 작업 수는 모델 호출 수가 아니다. 각 작업 안의 도구 동시성,
provider rate limit, 호출 재시도는 별도 제한을 받는다.

## 공정한 점유

첫 배포는 worker 하나가 최대 4개 작업을 관리한다. 같은 DB에서 여러 worker로
늘려도 아래 트랜잭션을 유지한다.

1. 예약이 비면 PostgreSQL의 단일 `scheduler_state` 행을 잠근다. 모든 Batch
   등록도 이 행을 잠근 뒤 미종료 작업 수를 세고 새 작업을 만든다. 이 행으로
   등록과 점유의 상한 판단을 직렬화한다.
2. `released_at IS NULL`인 실행 예약 수로 전체·owner별 슬롯을 확인한다.
   `scheduler_owner_state`의 가장 오래전에 점유한 eligible owner를 고른다.
   한 번도 점유하지 않은 owner는 먼저 두고, 동률은 가장 오래된 준비 작업 시각과
   owner ID로 정한다. 선택 때마다 전역 단조 증가 순번을 기록한다.
3. 고른 owner 안에서 `(ready_at, id)`가 가장 앞선 준비 작업을 점유한다.
   Case Run의 준비 시각은 생성 시각, Evaluation의 준비 시각은 `queued` 전이
   시각이다. 부모 Run → 작업 순으로 잠그고 상태·취소 의도를 재확인한다.
   잠긴/취소된 작업은 건너뛴다. 작업과 `runtime_reservation`에 같은 lease token,
   worker ID, 만료 시각을 기록하고 commit한다.
4. DB 트랜잭션 밖에서 선택 환경을 확인하고 격리 컨테이너를 시작한다. heartbeat와
   결과 기록은 token으로 fencing한다. 실행이 끝나면 컨테이너 및 자식 프로세스
   정리를 확인한 뒤 결과를 확정하고 예약을 반환한다.

따라서 긴 Batch가 새 Batch를 독점하지 않으며, 빈 슬롯이 생길 때마다 대기 중인
owner가 번갈아 기회를 얻는다. 기존 실행을 선점하거나 강제 종료하지는 않으므로
새 사용자는 현재 작업이 끝날 때까지 기다릴 수 있다. 잠금 경합과 취소가 있으면
준비 시각의 엄격한 전역 FIFO는 보장하지 않는다.

## 컨테이너와 슬롯 반환

`runtime_reservation`은 작업 ID·owner ID·lease token·container ID와 상태
(`reserved/launching/active/cleanup_pending/released`)를 가진다. 예약 이후
컨테이너 시작 실패, 작업 취소, timeout, worker 중단 모두 동일한 정리 경로를
거친다. 상태가 terminal이어도 컨테이너가 남아 있으면 슬롯을 차지한다.

lease가 만료되면 복구기가 먼저 token을 무효화하고 작업을 기존 규칙대로
`worker_lost`로 종료한다. 예약은 `cleanup_pending`으로 유지한다. DB 밖에서
해당 ID의 컨테이너와 자식 프로세스가 없음을 확인한 후에만 `released`로 바꾼다.
정리 여부가 불확실하면 슬롯을 보유하고 경보를 낸다. 재시작 때 모든 미반환
예약과 실제 컨테이너를 대조한다. 늦은 worker는 token 검증에 실패하며 예약을
반환하거나 결과를 덮어쓸 수 없다. 정리·반환은 같은 reservation ID로 멱등이다.

각 실행은 제한된 컨테이너에서 선택한 owner의 읽기 전용 환경 revision과 필요한
자산만 사용한다. 서비스/다른 owner의 파일과 Docker socket은 mount하지 않는다.
CPU·메모리·PID·임시 저장소·출력·시간 상한을 컨테이너에 적용하고, 전체 예약의
최대 사용량에 서비스·DB 여유분을 더해 호스트 용량을 넘지 않게 설정한다.
2 vCPU/4 GiB 후보에서 4개를 실제로 수용할 수 있는지 부하 시험으로 확인하며,
부족하면 배포 설정의 전체 슬롯을 낮추거나 호스트 용량을 늘린다. 모델 API와
허용된 HTTP 도구의 네트워크 경로는 별도 제한·검증한다. 컨테이너 실행 주체만
런타임 제어 권한을 갖고 사용자 코드에 그 권한을 주지 않는다.

## 관측과 검증

API는 Batch/Run별 queued·running·완료 개수와 설정된 상한을 보여준다.
대기 순번과 시작 시각은 경합·취소·호출 시간 때문에 확정값으로 약속하지 않는다.
운영 지표는 전체/owner별 대기·실행·정리 대기 작업, 가장 오래된 대기 시간,
예약 수, 컨테이너 실제 수, CPU/메모리 사용량, 점유 실패와 provider 429를
포함한다. owner 지표와 로그는 다른 사용자에게 공개하지 않는다.

실제 PostgreSQL과 격리 실행기에서 두 owner의 동시 등록·점유, 한 owner의 여러
Batch, 4/2 슬롯 상한, 공정한 다음 점유, 등록 상한과 멱등 재전송, 취소·timeout·
worker 강제 종료, orphan 컨테이너, lease 만료 뒤 늦은 쓰기, 정리 실패로 슬롯이
남는 경우를 검증한다. 2 vCPU/4 GiB 후보의 부하와 provider 제한은 배포 전
측정한다. 이 문서는 목표 계약이며 현재 제품 worker 구현 완료를 뜻하지 않는다.

## Redis와 Celery로 확장하는 조건

첫 구현은 PostgreSQL polling으로 시작한다. worker는 사용할 수 있는 슬롯만큼만
점유하며 빈 큐에서는 약 1초 간격으로 조회하고, 계속 비어 있으면 최대 5초까지
backoff와 jitter를 적용한다. 실제 polling 부하와 작업 접수 후 시작 지연을 먼저
측정한다.

1. polling 부하나 시작 지연만 문제가 되면 Redis를 **wake-up 신호**로 먼저
   검토한다. PostgreSQL 작업 행이 상태의 기준이며 Redis 알림은 유실 가능한
   힌트다. 알림이 없어도 주기적인 DB 조회로 작업을 발견해야 한다.
2. 여러 서버의 worker 라우팅·전달·재전송을 broker에 맡길 운영 필요가 생기면
   Celery 또는 다른 broker adapter를 검토한다. worker 수가 늘었다는 이유만으로
   바로 Celery를 도입하지 않는다.
3. broker 발행이 필요하면 작업 등록과 outbox INSERT를 같은 PostgreSQL
   트랜잭션에서 처리한다. dispatcher는 미발행 outbox를 전달하고, 발행 성공 뒤
   표시 전에 죽어서 생기는 중복 전달을 허용한다. consumer는 work ID로 DB 상태와
   선점 가능 여부를 다시 검사한다.
4. broker 메시지, ack, Celery result backend는 제품 상태의 기준이 아니다.
   scheduler의 owner 공정성·quota·취소·lease를 우회해 작업을 시작할 수 없다.
   prefetch는 실제 실행 슬롯보다 크게 잡지 않는다.

Application의 실행 함수는 `execute(claim, execution_spec)` 같은 port 계약을
사용하며 Celery decorator를 import하지 않는다. Celery를 추가할 경우 task 함수는
DB 선점과 application 유스케이스를 연결하는 얇은 adapter다. 메시지 재전달만으로
멱등성이 생기지 않으므로 work ID와 lease token의 fencing을 그대로 유지한다.
