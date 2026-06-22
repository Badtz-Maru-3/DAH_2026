<div align="right">
  <a href="README.md">🇺🇸 English</a> | <strong>🇰🇷 한국어</strong>
</div>

# DAH 2026 Testbed

DAH 2026은 방산 AI 사이버 공방 해커톤 예선 보고서의 부가자료를 구성하기 위한 **software-defined UGV/GCS cybersecurity testbed**입니다.

이 저장소는 실제 군용 UGV 플랫폼의 복제물이 아닙니다. 방산 UGV 환경에서 중요한 GCS 제어, MAVLink 기반 명령/telemetry 흐름, mission upload, GNSS/location input, anomaly correlation, command hold/block response를 소프트웨어 계층에서 추상화해 검증합니다.

## 프로젝트 목적

- Docker 기반으로 GCS, 시뮬레이션, ROS2, MAVLink bridge를 재현 가능하게 실행합니다.
- QGroundControl과 ROS2/Gazebo 사이의 제어 및 telemetry 흐름을 검증합니다.
- mission upload, GNSS input, manual command를 controlled testbed 안에서 공격 표면으로 다룹니다.
- 탐지, 차단, hold, evidence log를 일자별 문서와 로그로 남깁니다.
- 실제 RF, 실제 GNSS 수신기, 실제 군용 UGV 하드웨어를 구현했다고 주장하지 않습니다.

## Logical Two-Layer Testbed Architecture

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

### Simulation Layer

- QGroundControl noVNC: GCS 화면, Fly View, virtual joystick, vehicle marker
- Gazebo / ROSbot: simulated UGV movement
- RViz noVNC: ROS2 topic, TF, scan, odometry visualization
- `/odometry/filtered`: simulated UGV state feedback

### Software-Defined UGV Security Layer

- MAVLink Bridge: QGC-MAVLink message와 ROS2 topic 사이의 변환
- Mission Audit: mission upload의 geofence, waypoint jump, altitude, command 검증
- GNSS Integrity: `GPS_INPUT`의 spoof jump 및 poor-fix 검증
- Correlation Engine: Mission/GNSS/Command anomaly signal을 risk score로 결합
- Command Hold / Block: threshold 도달 시 hold_engaged 및 command_blocked 기록

## 검증된 운용 흐름

```text
GCS 제어
  -> MAVLink MANUAL_CONTROL
  -> ROS2 /cmd_vel
  -> UGV 이동
  -> /odometry/filtered telemetry

Mission upload
  -> Mission Audit
  -> geofence / waypoint jump validation
  -> MISSION_ACK accepted or rejected

GPS_INPUT
  -> GNSS Integrity
  -> normal / spoof_jump / poor_fix classification

Mission/GNSS/Command anomaly signal
  -> Correlation Engine risk scoring
  -> hold_engaged
  -> command_blocked
```

## 현재 구현 상태

| Day | 검증 내용 | Evidence |
| --- | --- | --- |
| Day1 | ROSbot Gazebo simulation baseline | `docs/day1/README_KR.md` |
| Day2 | QGC/Gazebo/RViz noVNC web UI stack | `docs/day2/README_KR.md` |
| Day3 | `MANUAL_CONTROL -> /cmd_vel -> odometry` bridge MVP | `docs/day3/README_KR.md` |
| Day4 | mission upload audit accept/reject | `docs/day4/README_KR.md` |
| Day5 | `GPS_INPUT` normal/spoof/poor-fix validation | `docs/day5/README_KR.md` |
| Day6 | correlation risk scoring, hold, command block | `docs/day6/README_KR.md` |

## 런타임 서비스

`compose.webui.yml`은 기본 통합 실행 파일입니다.

| Service | URL | Container | Purpose |
| --- | --- | --- | --- |
| QGroundControl | `http://localhost:6080/vnc.html` | `dah-qgc-novnc` | GCS 화면 |
| Gazebo | `http://localhost:6081/vnc_auto.html` | `dah-rosbot-sim-novnc` | ROSbot simulation |
| RViz | `http://localhost:6082/vnc_auto.html` | `dah-rviz-novnc` | ROS2 visualization |
| Bridge | N/A | `dah-bridge` | MAVLink/ROS2 bridge |

## 빠른 실행

```bash
cp .env.example .env
docker compose --env-file .env -f compose.webui.yml up -d --build
```

웹 UI:

- QGroundControl: `http://localhost:6080/vnc.html`
- Gazebo: `http://localhost:6081/vnc_auto.html`
- RViz: `http://localhost:6082/vnc_auto.html`

종료:

```bash
docker compose --env-file .env -f compose.webui.yml down
```

## 검증 명령

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
ros2 topic list -t
ros2 topic info /cmd_vel -v
ros2 topic echo /odometry/filtered --once
docker logs dah-bridge
```

## 문서 구조

| English | Korean |
| --- | --- |
| `README.md` | `README_KR.md` |
| `AGENTS.md` | `AGENTS_KR.md` |
| `docs/README.md` | `docs/README_KR.md` |
| `docs/architecture/two_layer_architecture.md` | `docs/architecture/two_layer_architecture_KR.md` |
| `docs/day1/README.md` | `docs/day1/README_KR.md` |
| `docs/day2/README.md` | `docs/day2/README_KR.md` |
| `docs/day3/README.md` | `docs/day3/README_KR.md` |
| `docs/day3/evidence_summary.md` | `docs/day3/evidence_summary_KR.md` |
| `docs/day3/odom_delta.md` | `docs/day3/odom_delta_KR.md` |
| `docs/day4/README.md` | `docs/day4/README_KR.md` |
| `docs/day5/README.md` | `docs/day5/README_KR.md` |
| `docs/day6/README.md` | `docs/day6/README_KR.md` |

## 현재 상태

이 시스템은 bridge-only MVP 단계를 넘어섰습니다. 주요 제어 루프, mission audit, GNSS integrity, correlation hold/block 경로가 구현되었고 Day3-Day6 evidence로 뒷받침됩니다.

다음 보강 방향은 QGroundControl 화면 evidence, 반복 가능한 evidence 수집 스크립트, regression test, GNSS trust downgrade/fallback입니다.
