# DAH 2026 Testbed

DAH 2026은 단일 데모를 만들기 위한 저장소가 아니라, **방산 AI 사이버 공방 해커톤 예선 보고서의 부가자료(src + docs)를 구성하기 위한 software-defined UGV/GCS cybersecurity testbed**입니다.

현재 구현된 ROSbot UGV 시뮬레이션과 ROS2-MAVLink 브리지는 command, mission audit, GNSS integrity, correlation response까지 포함한 검증 기준 시나리오입니다. 목표는 “QGroundControl로 ROSbot을 움직였다”에서 끝나는 것이 아니라, **공격 주입 -> 이상 징후 -> AI 기반 탐지·차단·복구 -> 로그 evidence** 흐름을 반복 실험할 수 있는 기반을 만드는 것입니다.

## 프로젝트 목적

이 저장소의 목적은 다음과 같습니다.

- GCS, 시뮬레이터, 로봇 미들웨어, 통신 브리지를 Docker로 재현 가능하게 구성합니다.
- QGroundControl과 ROS2/Gazebo 사이의 제어 및 telemetry 흐름을 검증합니다.
- 실제 로봇 또는 더 복잡한 시뮬레이션으로 확장하기 전, ROSbot-based surrogate platform에서 defense UGV operational flow를 검증합니다.
- 실험 결과를 `docs/`에 evidence로 남겨 보고서 본문에서 설명 가능한 근거를 확보합니다.
- 제어명령, 임무명령, 위치입력의 상관관계를 이용해 UGV 운용 이상을 탐지하는 구조로 확장합니다.

## Logical Two-Layer Testbed Architecture

이 testbed는 실제 군용 UGV 플랫폼의 복제물이 아닙니다. defense UGV 환경에서 중요한 GCS 제어, mission upload, GNSS/location input, telemetry feedback, anomaly correlation, command hold/block response 흐름을 추상화한 software-defined UGV/GCS cybersecurity testbed입니다.

아키텍처는 두 개의 논리 계층으로 설명합니다.

### Simulation Layer

- QGroundControl noVNC: GCS 화면, Fly View, virtual joystick, vehicle marker
- Gazebo / ROSbot: simulated UGV movement
- RViz: ROS2 topic, TF, scan, odometry visualization
- `/odometry/filtered`: simulated UGV state feedback

### Software-Defined UGV Security Layer

- MAVLink Bridge: QGC-MAVLink messages to ROS2 and back
- Mission Audit: mission upload validation, geofence check, waypoint jump check
- GNSS Integrity: `GPS_INPUT` validation, spoof jump detection, poor-fix detection
- Correlation Engine: Mission/GNSS/Command anomaly signal을 risk score로 결합
- Command Hold / Block: risk threshold 도달 시 command output을 block 또는 zero 처리

### Inter-Layer Data Flow

```text
QGC joystick input is sent as MAVLink MANUAL_CONTROL to the Bridge.
The Bridge converts it into ROS2 /cmd_vel for the simulated ROSbot.
The simulated UGV publishes /odometry/filtered.
The Bridge uses odometry for telemetry feedback and as a reference for GNSS integrity validation.
Mission, GNSS, and command anomalies are evaluated in the Software-Defined UGV Security Layer.
When correlation risk reaches the threshold, Command Hold / Block prevents unsafe command execution.
```

즉, 특정 로봇 하나를 움직이는 것이 아니라 **제어 입력, 상태 피드백, 시각화, 검증 자료 수집, 탐지·차단 evidence가 연결되는 logical two-layer architecture**를 만드는 것이 핵심입니다.

## 목표 방어 시나리오

이 testbed가 최종적으로 뒷받침해야 하는 시나리오는 **UGV 임무명령·위치입력 복합 공격에 대한 AI 기반 탐지·차단·복구 오케스트레이터**입니다. 단일 공격 표면만 보는 것이 아니라, 서로 다른 이상 징후가 같은 방향을 가리킬 때 복합 공격 가능성을 높게 판단하는 구조가 목표입니다.

```text
제어명령 주입
  + 비인가 mission / waypoint 변경
  + GNSS 좌표 jump 또는 drift
  -> 상관관계 기반 이상 탐지
  -> hold / zero cmd_vel / mission reject / operator alert
  -> evidence log
```

현재 검증된 공격 표면:

- MAVLink `MANUAL_CONTROL`, `RC_CHANNELS_OVERRIDE` 기반 C2 analog 명령 주입 경로
- `MISSION_COUNT`, `MISSION_REQUEST_INT`, `MISSION_ITEM_INT` 기반 mission upload audit 경로
- `GPS_INPUT` 기반 GNSS position-input integrity 경로
- mission/GNSS reject 이후 correlation hold 및 manual command block 경로
- ROS2 odometry를 MAVLink local/global position telemetry로 변환하는 telemetry 경로

남은 보강 표면:

- QGroundControl 화면에서 mission rejection / warning 상태를 보여주는 operator evidence
- 장시간 안정성, 재시작, 반복 regression evidence
- audit/reject를 넘어선 실제 mission execution/autopilot 동작
- GNSS trust downgrade와 dead-reckoning fallback의 장시간 운용

## 현재 기준 시나리오

현재 구현된 기준 시나리오는 위 2계층 구조에서 Day3 evidence로 검증된 inter-layer command/telemetry 흐름입니다.

```text
QGroundControl noVNC
  -> MAVLink UDP / MANUAL_CONTROL
  -> dah-bridge
  -> ROS2 /cmd_vel
  -> ROSbot Gazebo
  -> ROS2 /odometry/filtered
  -> dah-bridge
  -> MAVLink telemetry
  -> QGroundControl HUD / map
```

이 시나리오는 Day3 evidence에서 MVP로 검증되었습니다.

- QGroundControl이 MAVLink `MANUAL_CONTROL`을 전송합니다.
- `dah-bridge`가 MAVLink 입력을 ROS2 `/cmd_vel`로 변환합니다.
- Gazebo의 ROSbot drive controller가 `/cmd_vel`을 받아 이동합니다.
- `/odometry/filtered` 변화량으로 실제 움직임을 확인합니다.
- bridge가 odometry를 MAVLink telemetry 형태로 QGroundControl에 되돌려줍니다.

## 구성 요소

| 구성 요소 | 경로 | 역할 |
| --- | --- | --- |
| UGV Simulation | `UGV/` | ROSbot Gazebo 시뮬레이션을 실행하고 ROS2 센서/odometry 토픽을 제공합니다. |
| GCS | `GCS/` | QGroundControl을 noVNC 웹 화면으로 실행합니다. |
| Bridge | `Bridge/` | MAVLink UDP와 ROS2 토픽 사이의 제어/telemetry 변환을 담당합니다. |
| Evidence | `docs/` | 일자별 실험 로그, 토픽 상태, 검증 결과를 저장합니다. |

## 런타임 서비스

`compose.webui.yml`은 현재 기본 통합 실행 파일입니다. QGroundControl, Gazebo, RViz, bridge를 한 번에 실행합니다.

| 서비스 | URL | 컨테이너 | 목적 |
| --- | --- | --- | --- |
| QGroundControl | `http://localhost:6080/vnc.html` | `dah-qgc-novnc` | GCS 조종 화면입니다. |
| Gazebo | `http://localhost:6081/vnc_auto.html` | `dah-rosbot-sim-novnc` | ROSbot 시뮬레이션 화면입니다. |
| RViz | `http://localhost:6082/vnc_auto.html` | `dah-rviz-novnc` | ROS2 토픽/TF 시각화 화면입니다. |
| Bridge | 없음 | `dah-bridge` | MAVLink/ROS2 제어 및 telemetry 브리지입니다. |

통합 서비스들은 현재 host network를 사용합니다. QGroundControl 설정은 `GCS/data`에 유지되고, RViz는 ROSbot simulation 이후에, bridge는 QGroundControl과 ROSbot simulation 이후에 실행되도록 구성되어 있습니다. 루트 stack의 장기 실행 서비스들은 `restart: unless-stopped` 정책을 사용합니다.

### Windows Docker Desktop noVNC 접속 주의

현재 통합 stack은 host networking 동작을 기준으로 검증되어 있습니다. Windows Docker Desktop에서는 `network_mode: host`가 Linux/WSL과 다르게 동작할 수 있어서, 컨테이너는 정상 실행되고 내부 통신도 되지만 Windows 본체 브라우저에서 아래 URL이 열리지 않을 수 있습니다.

- `http://localhost:6080/vnc.html`
- `http://localhost:6081/vnc_auto.html`
- `http://localhost:6082/vnc_auto.html`

이 증상이 나오면 먼저 noVNC entrypoint의 `websockify` bind 주소를 확인합니다. 현재는 컨테이너 내부 loopback에 묶여 있습니다.

| 파일 | 현재 bind | Windows 접속 후보 수정 |
| --- | --- | --- |
| `GCS/entrypoint-novnc.sh` | `127.0.0.1:6080` | `0.0.0.0:6080` |
| `UGV/entrypoint-ugv-novnc.sh` | `127.0.0.1:6081` | `0.0.0.0:6081` |
| `UGV/entrypoint-rviz-novnc.sh` | `127.0.0.1:6082` | `0.0.0.0:6082` |

compose 쪽 후보 수정은 noVNC 서비스에서 `network_mode: host`를 제거하고 명시적인 `ports:`를 여는 방식입니다.

```yaml
ports:
  - "6080:6080"  # QGroundControl
  - "6081:6081"  # Gazebo
  - "6082:6082"  # RViz
```

단, 이것은 아직 기본 stack을 대체하는 검증 완료 변경이 아닙니다. `network_mode: host`를 제거하면 ROS2 DDS discovery와 MAVLink 주소 가정이 달라질 수 있으므로, Windows 전용 compose 경로를 만들 경우 QGC, ROSbot, RViz, bridge, mission audit, GNSS integrity, correlation evidence를 다시 검증해야 합니다.

`Bridge/compose.bridge.yml`은 QGroundControl과 simulation을 별도 compose로 띄운 상태에서 bridge만 확인하기 위한 단독 디버깅 경로입니다. `compose.webui.yml` 안의 bridge와 동시에 실행하면 둘 다 `dah-bridge` 컨테이너 이름을 쓰기 때문에 충돌합니다.

| 서비스 | 컨테이너 | 목적 |
| --- | --- | --- |
| bridge | `dah-bridge` | `Bridge/` 디렉토리 기준으로 MAVLink/ROS2 브리지만 실행합니다. |

## 환경 변수

프로젝트는 `.env` 또는 `.env.example`로 공통 설정을 관리합니다.

| 변수 | 기본값 | 의미 |
| --- | --- | --- |
| `ROS_DOMAIN_ID` | `17` | UGV, RViz, Bridge가 같은 ROS2 DDS 도메인을 보게 합니다. |
| `ROBOT_MODEL` | `rosbot` | Gazebo에서 실행할 로봇 모델을 선택합니다. `.env`에 없으면 `rosbot`을 사용하고, `ROBOT_MODEL=rosbot_xl`을 넣으면 `rosbot_xl`을 사용합니다. |
| `QGC_IP` | `127.0.0.1` | QGroundControl MAVLink 수신 주소입니다. |
| `QGC_PORT` | `14550` | QGroundControl MAVLink UDP 포트입니다. |
| `BRIDGE_LOCAL_PORT` | `14551` | 브리지가 MAVLink 패킷을 수신하는 UDP 포트입니다. |
| `MAX_LINEAR` | `0.5` | `/cmd_vel`에 발행할 최대 선속도입니다. |
| `MAX_ANGULAR` | `1.2` | `/cmd_vel`에 발행할 최대 각속도입니다. |
| `CMD_TIMEOUT` | `0.6` | 입력이 끊긴 뒤 zero command를 발행하기까지의 시간입니다. |
| `BASE_LAT`, `BASE_LON`, `BASE_ALT` | 서울 기본값 | local odometry를 MAVLink global position telemetry로 바꿀 때 쓰는 원점입니다. |
| `LIBGL_ALWAYS_SOFTWARE` | `1` | Gazebo/QGC 안정성을 위해 소프트웨어 렌더링을 우선 사용합니다. |
| `MAVLINK_DEBUG` | `0` | `1`로 설정하면 자세한 MAVLink 수신 로그를 출력합니다. |
| `MISSION_MAX_ITEMS` | `20` | mission audit이 허용하는 최대 mission item 수입니다. |
| `MISSION_GEOFENCE_RADIUS_M` | `300` | `BASE_LAT`/`BASE_LON` 중심 mission geofence 반경입니다. |
| `MISSION_MAX_JUMP_M` | `120` | waypoint 간 허용 최대 jump 거리입니다. |
| `MISSION_MIN_ALT_M`, `MISSION_MAX_ALT_M` | `-20`, `200` | mission altitude 허용 범위입니다. |
| `MISSION_ALLOWED_COMMANDS` | `16,20` | audit v1에서 허용하는 MAVLink mission command입니다. |
| `GNSS_MAX_RESIDUAL_M` | `30` | odometry 기준 expected position과 GPS_INPUT 사이의 허용 잔차입니다. |
| `GNSS_MIN_FIX_TYPE` | `3` | 허용하는 최소 GPS fix type입니다. |
| `GNSS_MIN_SATELLITES` | `6` | 허용하는 최소 위성 수입니다. |
| `GNSS_MAX_HACC_M` | `15` | 허용하는 최대 수평 정확도 값입니다. |
| `CORRELATION_RISK_THRESHOLD` | `0.75` | hold를 걸기 위한 risk score 기준입니다. |
| `CORRELATION_HOLD_SECONDS` | `5` | threshold 초과 뒤 command를 차단하는 hold 시간입니다. |

## 빠른 실행

필요하면 예시 환경 파일을 복사합니다.

```bash
cp .env.example .env
```

로봇 모델은 `.env`에서 선택합니다. 기본 모델은 `rosbot`이고, `rosbot_xl`로 실행하려면 `docker compose up` 전에 `.env`에 아래 줄을 추가하거나 기존 값을 수정합니다.

```bash
ROBOT_MODEL=rosbot_xl
```

기본 모델로 되돌리려면 `.env`에서 `ROBOT_MODEL=rosbot`으로 설정하거나 `ROBOT_MODEL` 줄을 삭제하면 됩니다. `.env.example`에는 기본값 예시가 들어 있습니다.

통합 testbed stack을 실행합니다. 이 경로가 기본 실행 경로이며, 이미 `dah-bridge`를 포함합니다.

```bash
docker compose --env-file .env -f compose.webui.yml up -d
```

bridge 단독 디버깅은 통합 stack 실행 뒤에 추가로 실행하는 단계가 아니라 대체 경로입니다. QGroundControl과 simulation을 다른 방식으로 이미 띄워 둔 상태이거나, 통합 bridge 컨테이너를 먼저 제거한 뒤에만 사용합니다.

```bash
docker compose --env-file .env -f compose.webui.yml stop bridge
docker compose --env-file .env -f compose.webui.yml rm -f bridge
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

Docker가 `Conflict. The container name "/dah-bridge" is already in use`를 출력하면 통합 bridge 컨테이너가 아직 남아 있는 상태입니다. 이때는 해당 컨테이너를 만든 compose 경로로 먼저 내린 뒤 bridge 단독 경로를 실행합니다.

```bash
docker compose --env-file .env -f compose.webui.yml down
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

통합 bridge가 실행 중이 아닌 것이 확실할 때의 bridge 단독 실행 명령은 다음과 같습니다.

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

bridge 단독 디버깅에서 다시 통합 stack으로 돌아갈 때는 bridge 단독 컨테이너를 먼저 제거합니다.

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml down
docker compose --env-file .env -f compose.webui.yml up -d
```

웹 UI에 접속합니다.

- QGroundControl: `http://localhost:6080/vnc.html`
- Gazebo: `http://localhost:6081/vnc_auto.html`
- RViz: `http://localhost:6082/vnc_auto.html`

서비스를 종료합니다.

```bash
docker compose --env-file .env -f compose.webui.yml down
```

bridge를 `Bridge/compose.bridge.yml`로 따로 띄웠다면 별도로 종료합니다.

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml down
```

## 검증 명령

유용한 확인 명령:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
ros2 topic list -t
ros2 topic info /cmd_vel -v
ros2 topic echo /odometry/filtered --once
docker logs dah-bridge
```

현재 Day3 evidence가 보여주는 내용:

- `dah-bridge`, QGC, RViz, ROSbot simulation 컨테이너가 함께 실행되었습니다.
- 현재 `compose.webui.yml`에 bridge 서비스가 포함되어, 기본 경로 하나로 baseline stack 전체를 실행할 수 있습니다.
- `/cmd_vel`에는 `ros2_mavlink_bridge` publisher와 `drive_controller` subscriber가 연결되었습니다.
- 브리지는 QGroundControl에서 MAVLink `MANUAL_CONTROL`을 수신했습니다.
- 브리지는 non-zero `/cmd_vel`을 발행했습니다.
- QGC joystick 입력 이후 ROSbot odometry가 약 `1.078 m` 변화했습니다.

자세한 MVP evidence는 `docs/day3/README.md`와 `docs/day3/evidence_summary.md`에 정리되어 있습니다.

이후 evidence가 추가로 보여주는 내용:

- Day4: 정상 mission accepted, 악성 geofence/jump mission rejected, `MISSION_ACK` 송신
- Day5: 정상 `GPS_INPUT` accepted, spoof jump 및 poor fix rejected
- Day6: mission/GNSS reject가 correlation risk로 기록되고, hold 중 `MANUAL_CONTROL` block

## 확장 방향

이 testbed는 다음 공격·방어 표면으로 확장할 수 있습니다.

| 확장 방향 | 설명 |
| --- | --- |
| Mission audit mode | `MISSION_COUNT` 수신 후 `MISSION_REQUEST_INT`로 항목을 요청하고, `MISSION_ITEM_INT`의 waypoint, geofence, sequence 무결성을 검사합니다. 구현 및 Day4 검증 완료. |
| GNSS integrity monitor | odometry 기준 expected position과 GNSS 입력의 잔차로 jump, fix quality 이상을 탐지합니다. 구현 및 Day5 검증 완료. |
| Correlation engine | 제어명령, mission, GNSS 이상을 함께 판단해 risk score를 만들고 hold/zero `/cmd_vel`을 수행합니다. 구현 및 Day6 검증 완료. |
| Stability manager | AIxCC 교훈에 맞춰 탐지뿐 아니라 hold, zero `/cmd_vel`, rollback 같은 안정적 복구를 담당합니다. |
| 자동 evidence 수집 | 컨테이너 상태, ROS2 topic, odometry delta, bridge log, audit log를 스크립트로 수집합니다. |
| 모델 교체 | `ROBOT_MODEL`로 `rosbot`, `rosbot_xl`을 선택하고 이후 다른 UGV/UAV 시뮬레이터로 확장합니다. |

## 문서 구조

| 문서 | 목적 |
| --- | --- |
| `README.md` | 영문 프로젝트 개요입니다. |
| `KR.md` | 한국어 testbed 중심 프로젝트 개요입니다. |
| `docs/README.md` | evidence 폴더 전체 안내입니다. |
| `docs/architecture/two_layer_architecture.md` | 논리적 2계층 아키텍처, 책임, evidence mapping, 한계 설명입니다. |
| `docs/day1/README.md` | ROSbot simulation baseline evidence입니다. |
| `docs/day2/README.md` | noVNC web UI integration evidence입니다. |
| `docs/day3/README.md` | ROS2-MAVLink bridge MVP 결과입니다. |
| `docs/day3/evidence_summary.md` | Day3 evidence 파일별 해석입니다. |
| `docs/day3/odom_delta.md` | command path가 실제 이동을 만들었는지 계산한 odometry delta입니다. |
| `docs/day4/README.md` | Mission audit 구현과 accepted/rejected evidence입니다. |
| `docs/day5/README.md` | GNSS integrity 구현과 GPS_INPUT evidence입니다. |
| `docs/day6/README.md` | Correlation engine hold/blocking evidence입니다. |

## 참고자료

공식 문서 및 기술 문서:

- DAH 2026 예선 안내서, 2026.06.15.
- MAVLink Developer Guide, Common Message Set.
- MAVLink Developer Guide, Mission Protocol.
- QGroundControl User Guide, Download and Install.
- Husarion Documentation, How to use Husarion Docker images.
- Docker Documentation, Compose file services reference.
- noVNC GitHub Repository, HTML VNC client library and application.

프로젝트 내부 자료:

- Badtz-Maru-3/DAH_2026, `README.md`.
- Badtz-Maru-3/DAH_2026, `compose.webui.yml`.
- Badtz-Maru-3/DAH_2026, `Bridge/ros2_mavlink_bridge.py`.
- Badtz-Maru-3/DAH_2026, `Bridge/mission_audit.py`.
- Badtz-Maru-3/DAH_2026, `Bridge/gnss_integrity.py`.
- Badtz-Maru-3/DAH_2026, `Bridge/correlation_engine.py`.
- Badtz-Maru-3/DAH_2026, `docs/day3/evidence_summary.md`.
- Badtz-Maru-3/DAH_2026, `docs/day3/odom_delta.md`.
- Badtz-Maru-3/DAH_2026, `docs/day3/bridge_clean.log`.
- Badtz-Maru-3/DAH_2026, `docs/day3/cmd_vel_info.txt`.
- Badtz-Maru-3/DAH_2026, `docs/day3/ros2_topics.txt`.
- Badtz-Maru-3/DAH_2026, `docs/day4/mission_audit.log`.
- Badtz-Maru-3/DAH_2026, `docs/day5/gnss_integrity.log`.
- Badtz-Maru-3/DAH_2026, `docs/day6/correlation_mission_malicious.log`.
- Badtz-Maru-3/DAH_2026, `docs/day6/correlation_gnss_spoof.log`.

논문 및 연구자료:

- Mayoral Vilches, V. et al., SROS2: Usable Cyber Security Tools for ROS 2, arXiv:2208.02615.
- Choton, J. C. et al., Formal Modeling and Verification of Publisher-Subscriber Paradigm in ROS 2, arXiv:2412.16186.
- Macenski, S. et al., Impact of ROS 2 Node Composition in Robotic Systems, arXiv:2305.09933.
- Clements, Z., Yoder, J. E., Humphreys, T. E., Carrier-phase and IMU based GNSS Spoofing Detection for Ground Vehicles, arXiv:2203.00140.
- Johansson, T., Spanghero, M., Papadimitratos, P., Consumer INS Coupled with Carrier Phase Measurements for GNSS Spoofing Detection, arXiv:2502.03870.
- Park, S., Cho, D. J., Son, P. W., Wide-Area GNSS Spoofing and Jamming Detection Using AIS-Derived Spatiotemporal Integrity Monitoring, arXiv:2603.11055.

## 현재 상태

이 시스템은 bridge-only MVP 단계를 넘어섰습니다. 주요 제어 루프, mission audit, GNSS integrity, correlation hold 경로가 구현되었고 Day3-Day6 evidence로 입증되어 있습니다.

다음 단계는 “더 멋진 데모”보다 **공격·방어 1:1 매핑과 evidence 로그**를 만드는 쪽이 좋습니다.

- QGroundControl mission upload/rejection 및 warning 상태 스크린샷 확보
- Day3-Day6 로그를 한 번에 수집하는 repeatable evidence script 추가
- `MANUAL_CONTROL -> /cmd_vel`, mission audit, GNSS reject, correlation hold를 지키는 regression test 추가
- GNSS rejection/warning 이후 trust downgrade와 fallback 동작을 더 명확히 구현
- 기존 Day3 `MANUAL_CONTROL -> /cmd_vel` 및 `CMD_TIMEOUT` watchdog 경로 유지
