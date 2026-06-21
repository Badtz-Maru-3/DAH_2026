# AGENTS.md — DAH 2026 Testbed: 작업 계획 및 컨텍스트

> 이 문서는 AI 코딩 에이전트(Codex 등)와 팀원이 저장소의 목적·현재 상태·다음 작업을
> 빠르게 파악하도록 작성되었다. 코드 수정 전 반드시 이 문서와 `docs/day3/`를 먼저 읽을 것.

## 1. 프로젝트 목적

DAH 2026(방산 AI 사이버 공방 해커톤) 예선 보고서의 부가자료(src + docs)다.
QGroundControl ⇄ MAVLink ⇄ ROS2 ⇄ Gazebo(ROSbot UGV) 제어 루프를 재현하는 Docker
testbed이며, 그 위에서 **공격 주입 → 이상 징후 → AI 기반 탐지·차단·복구**를 실증하고
로그로 남기는 것이 목표다.

이 testbed는 실제 군용 UGV 플랫폼의 복제물이 아니다. defense UGV 환경의 핵심 운용 흐름인
GCS 제어, mission upload, GNSS/location input, telemetry feedback, anomaly correlation,
command hold/block response를 추상화한 software-defined UGV/GCS cybersecurity testbed다.

핵심 시나리오:
> UGV 임무명령·위치입력 복합 공격에 대한 AI 기반 탐지·차단·복구 오케스트레이터.
> 단일 공격 표면 탐지가 아니라, 제어명령·임무명령·위치입력의 상관관계를 이용해
> UGV 운용 이상을 탐지한다.

## 2. 현재 구현 상태 (Day6까지, 검증 완료)

- `Bridge/ros2_mavlink_bridge.py`: MAVLink ⇄ ROS2 브리지
  - 수신 처리: MANUAL_CONTROL, RC_CHANNELS_OVERRIDE → `/cmd_vel`(Twist)
  - 송신: odometry(`/odometry/filtered`) → MAVLink LOCAL_POSITION_NED / GLOBAL_POSITION_INT
  - 부가: heartbeat, statustext, 최소 파라미터 세트 응답
  - Mission: MISSION_REQUEST_LIST, MISSION_CLEAR_ALL, MISSION_COUNT, MISSION_ITEM_INT/MISSION_ITEM 처리
  - GNSS: GPS_INPUT 수신 후 odometry 기준 위치 잔차, fix type, 위성 수, 수평 정확도 검사
  - Correlation: mission/GNSS reject 및 high manual command 신호를 risk score로 결합하고 hold 시 zero `/cmd_vel` 발행
  - 안전: `CMD_TIMEOUT` 경과 시 zero `/cmd_vel` 발행(watchdog)
- `Bridge/mission_audit.py`: mission upload audit 및 JSONL evidence 기록
- `Bridge/gnss_integrity.py`: GPS_INPUT integrity check 및 JSONL evidence 기록
- `Bridge/correlation_engine.py`: 상관 신호 기반 hold/command block 및 JSONL evidence 기록
- `compose.webui.yml`: QGC(noVNC) + ROSbot sim + RViz + bridge 통합 실행
  - 현재 기본 경로는 `network_mode: host` 기반이다. Linux/WSL에서는 단순하지만, Windows Docker Desktop에서는 브라우저에서 `6080/6081/6082` noVNC 접속이 막힐 수 있다.
  - Windows 접속 문제를 문서화할 때는 코드 전체를 바로 덮어쓰지 말고, `websockify` bind 주소(`127.0.0.1:608x` → `0.0.0.0:608x`)와 compose `ports:` 전환이 필요한 후보 workaround임을 명시한다.
- `docs/day3/`: end-to-end 입증 evidence (조이스틱 입력 → UGV 1.078m 이동)
- `docs/day4/`: MISSION audit evidence (정상 mission accepted, 악성 mission rejected)
- `docs/day5/`: GNSS integrity evidence (정상 GPS_INPUT accepted, spoof/poor fix rejected)
- `docs/day6/`: Correlation evidence (mission/GNSS reject → hold, MANUAL_CONTROL block)

검증된 공격 표면: 명령주입(C2 analog), mission upload audit, GNSS 입력 무결성, telemetry 변환부, correlation hold. 미구현: 실제 mission execution/autopilot, 장시간 GNSS dead-reckoning 운용, 실제 QGC operator alert 화면 캡처.

## 3. Logical Two-Layer Testbed Architecture

```text
[Simulation Layer]
QGC 화면 / Gazebo / RViz / ROSbot 이동 / odometry

[Software-Defined UGV Security Layer]
MAVLink Bridge
Mission Audit
GNSS Integrity
Correlation Engine
Command Hold / Block
```

이 구분은 논리 아키텍처다. Docker runtime이 두 개의 물리적으로 격리된 network zone으로
분리되어 있다는 뜻이 아니라, simulation/visualization 구성요소와 software-defined security
validation layer의 책임을 구분하기 위한 설명이다.

## 4. 목표 공격·방어 구성

```text
Attack Agent
  ├─ C2 Attack Adapter        # MANUAL_CONTROL 변조/주입 (기반 존재)
  ├─ Mission Attack Adapter   # 비인가 waypoint / geofence 이탈 mission 주입
  └─ GNSS Attack Adapter      # 좌표 점프 / 드리프트 / fix quality 조작

Defense Agent
  ├─ Command Guard
  ├─ Mission Guard
  ├─ GNSS Integrity Monitor
  ├─ Correlation Engine       # 표면 간 상관관계로 복합 공격 탐지
  └─ Stability Manager        # AIxCC 교훈: 안정성이 결정적 요인
```

설계 원칙: 각 공격 표면은 **①주입점 ②이상 징후 ③탐지·차단·복구 ④로그 증거**의
4-튜플로 구현한다. 이는 DAH REQ의 D2(공방 1:1 매핑)·AI5(본문 자체 입증)를 충족하기 위함.

## 5. 구현 순서 및 작업 정의

### Step 1 — MISSION audit mode  [구현·검증 완료]

위치: `Bridge/ros2_mavlink_bridge.py`의 `handle_mavlink_msg` elif 체인 확장.

구현:
- [x] MISSION_COUNT 수신 → 항목 수 파악, MISSION_REQUEST_INT로 항목 요청
- [x] MISSION_ITEM_INT/MISSION_ITEM 수신 → pending items에 (seq, lat, lon, alt, command) 저장
- [x] geofence 경계 검사 (중심 BASE_LAT/BASE_LON 기준 반경)
- [x] waypoint 간 비현실적 jump 거리 검사
- [x] 업로드 sysid / 시퀀스 무결성 검사
- [x] 정상이면 MISSION_ACK accepted, 위반이면 denied + active_mission 유지
- [x] `docs/day4/mission_audit.log`에 수신 waypoint, 판정, 사유 기록

성공 증거(보고서용):
- 정상 mission accepted / 악성 mission rejected 로그
- mission_audit.log
- bridge_mission_audit_clean.log

주의:
- MISSION_ITEM_INT 필드 순서·MAV_FRAME 처리가 QGC 버전별로 민감.
  QGC 버전이 바뀌면 `MAVLINK_DEBUG=1`로 실제 QGC 패킷을 다시 덤프해 필드를 확인할 것.
- pymavlink dialect: `pymavlink.dialects.v20.common` 사용(기존 코드와 동일).

### Step 2 — GNSS integrity adapter  [구현·검증 완료]

위치: bridge에 GNSS 입력 수신부 신설 + odometry 교차검증 로직.

구현:
- [x] GPS_INPUT(MAVLink) 입력 수신
- [x] odometry 기반 expected lat/lon과 GPS_INPUT 좌표 잔차 비교
- [x] 잔차 임계 초과 / fix type 저하 / 위성 수 부족 / 수평 정확도 악화 탐지
- [x] reject 시 MAVLink STATUSTEXT warning 송신
- [x] `docs/day5/gnss_integrity.log`에 잔차·판정 기록

성공 증거:
- 정상 GNSS accepted / jump spoofing rejected / poor fix rejected 로그

주의:
- odometry도 `/cmd_vel` 적분 기반이라 장시간 드리프트 존재 → 단기 변화율로 판정.
- 잔차 임계값은 EKF/RAIM/센서융합 문헌 교차검증으로 보강(보고서 신뢰도 상승).

### Step 3 — Correlation Engine  [구현·검증 완료]

위치: `Bridge/correlation_engine.py`, `Bridge/mission_audit.py`, `Bridge/gnss_integrity.py`, `Bridge/ros2_mavlink_bridge.py`.

로직 예시:
```text
MISSION waypoint가 geofence 바깥으로 변경됨
  AND 동시에 GNSS 좌표가 같은 방향으로 drift
  → 단일 오탐이 아니라 복합 공격 가능성 상승
  → hold mode / zero cmd_vel / operator alert
```

이 단계가 AI 에이전트 항목(25점)의 구체성·혁신성을 뒷받침하는 핵심.

구현 상태:
- mission audit reject, GNSS integrity reject, high manual command를 signal로 기록
- signal TTL 내 risk score 계산
- threshold 이상이면 hold engaged, zero `/cmd_vel`, STATUSTEXT warning
- hold 중 MANUAL_CONTROL/RC override는 `/cmd_vel` 대신 zero command로 차단
- `docs/day6/`에 mission malicious, GNSS spoof, command block 로그 저장

## 6. 향후 확장 (예선 범위 밖)

펌웨어 업데이트 트랜잭션 시뮬레이터: manifest hash, version rollback,
signature verification 기반 업데이트 무결성 검증. **실제 부트로더/OTA는 구현하지 않음.**
보고서의 "결론 및 향후 계획"에 확장 항목으로 기재.

## 7. 미확정 설계값 (TODO / 실험으로 조정)

| 값 | 현재 | 근거 |
| --- | --- | --- |
| geofence 반경 | `MISSION_GEOFENCE_RADIUS_M=300` | 현재 실험값, `.env`/compose로 조정 |
| waypoint jump 거리 임계 | `MISSION_MAX_JUMP_M=120` | 현재 실험값, `.env`/compose로 조정 |
| GNSS-odometry 잔차 임계 | `GNSS_MAX_RESIDUAL_M=30` | 현재 실험값, EKF/RAIM 문헌으로 보강 필요 |

위 값들은 실제 실험 로그를 보고 확정한다. 현 상태에서 임의 하드코딩 금지, 환경변수로 노출 권장.

## 8. 일정

| 단계 | 기한 |
| --- | --- |
| 예선 시작 | 2026.06.15 |
| 보고서 제출 마감 | 2026.07.10 23:59 KST |
| 본선 진출 발표 | 2026.07.31 |

평가 배점: 공격 시나리오 30 / 방어 전략 25 / AI 에이전트 25 / 팀 역량 10 / 문서 완성도 10.
부가자료는 외부 클라우드 링크로 제출(필수), 외부 링크는 보조 참고 → **입증은 보고서 본문 우선(AI5).**

## 9. 코딩 에이전트 작업 규칙

- 코드 수정 전 `docs/day3/README.md`와 `evidence_summary.md`를 읽어 기존 검증 경로를 깨지 말 것.
- bridge 수정 시 기존 MANUAL_CONTROL → /cmd_vel 경로와 CMD_TIMEOUT watchdog 동작 유지.
- compose/network 수정 시 Windows noVNC 접속 개선과 ROS2 DDS/MAVLink 통신 안정성을 함께 재검증한다. `network_mode: host` 제거는 브라우저 포트 노출에는 유리하지만 ROS2 discovery 및 bridge 통신 동작이 달라질 수 있다.
- 새 핸들러는 기존 `handle_mavlink_msg` 패턴(elif + 로그 throttle)을 따를 것.
- 모든 공격/방어 동작은 `docs/dayN/`에 로그 evidence를 남기는 것을 완료 조건으로 한다.
- Mission audit mode는 `docs/day4/`, GNSS integrity는 `docs/day5/`, correlation은 `docs/day6/`를 기본 evidence 위치로 사용한다.
- 임계값·좌표 원점 등은 하드코딩 대신 환경변수(`.env`)로 노출.
