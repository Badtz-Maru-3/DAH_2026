# DAH 2026 Testbed

DAH 2026은 단일 데모를 만들기 위한 저장소가 아니라, **QGroundControl, MAVLink, ROS2, Gazebo 기반 무인 시스템 실험을 빠르게 구성하고 검증하기 위한 testbed**입니다.

현재 구현된 ROSbot UGV 시뮬레이션과 ROS2-MAVLink 브리지는 이 testbed의 첫 번째 기준 시나리오입니다. 목표는 “QGroundControl로 ROSbot을 움직였다”에서 끝나는 것이 아니라, 이후 자율주행 로직, 임무 제어, 센서 처리, 다중 에이전트, GCS 연동, 실패 상황 대응을 반복 실험할 수 있는 기반을 만드는 것입니다.

## 프로젝트 목적

이 저장소의 목적은 다음과 같습니다.

- GCS, 시뮬레이터, 로봇 미들웨어, 통신 브리지를 Docker로 재현 가능하게 구성합니다.
- QGroundControl과 ROS2/Gazebo 사이의 제어 및 telemetry 흐름을 검증합니다.
- 실제 로봇 또는 더 복잡한 시뮬레이션으로 확장하기 전, 안전한 가상 환경에서 control loop를 검증합니다.
- 실험 결과를 `docs/`에 evidence로 남겨 재현성과 설명 가능성을 확보합니다.
- 향후 DAH 2026 본 과제/시나리오에 맞춰 UGV, UAV, 센서, 임무 로직을 교체하거나 추가할 수 있게 합니다.

## Testbed 관점의 핵심 아이디어

현재 시스템은 “완성품”이라기보다 다음을 검증하는 실험 플랫폼입니다.

```text
Operator / Autonomy Logic
  -> GCS or Mission Interface
  -> MAVLink / ROS2 Bridge
  -> ROS2 Control Topics
  -> Gazebo Robot Simulation
  -> Sensor / Odometry Feedback
  -> Logging / Evidence
```

즉, 특정 로봇 하나를 움직이는 것이 아니라 **제어 입력, 상태 피드백, 시각화, 검증 자료 수집이 모두 연결되는 실험 루프**를 만드는 것이 핵심입니다.

## 현재 기준 시나리오

현재 구현된 기준 시나리오는 다음과 같습니다.

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

통합 서비스들은 host network를 사용합니다. QGroundControl 설정은 `GCS/data`에 유지되고, RViz는 ROSbot simulation 이후에, bridge는 QGroundControl과 ROSbot simulation 이후에 실행되도록 구성되어 있습니다. 루트 stack의 장기 실행 서비스들은 `restart: unless-stopped` 정책을 사용합니다.

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

## 빠른 실행

필요하면 예시 환경 파일을 복사합니다.

```bash
cp .env.example .env
```

로봇 모델 선택:

```bash
# 기본값: ROBOT_MODEL을 쓰지 않으면 rosbot 사용

# 선택값:
ROBOT_MODEL=rosbot_xl
```

통합 testbed stack을 실행합니다.

```bash
docker compose --env-file .env -f compose.webui.yml up -d
```

통합 bridge가 실행 중이 아닐 때, bridge만 따로 디버깅하려면 다음 경로를 사용할 수 있습니다.

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
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

## 확장 방향

이 testbed는 다음 방향으로 확장할 수 있습니다.

| 확장 방향 | 설명 |
| --- | --- |
| 자율주행 노드 추가 | joystick 입력 대신 planner/controller가 `/cmd_vel`을 생성하도록 확장합니다. |
| 임무 제어 | QGroundControl mission, waypoint, command handling을 bridge에 추가합니다. |
| 센서 처리 | `/scan`, camera, point cloud 기반 인식/회피 로직을 추가합니다. |
| UAV/UGV 전환 | 현재 ROSbot UGV를 다른 로봇 모델 또는 UAV 시뮬레이터로 교체합니다. |
| 다중 에이전트 | ROS_DOMAIN_ID, namespace, MAV_SYS_ID를 분리해 여러 vehicle을 실험합니다. |
| 장애 상황 실험 | 통신 지연, packet loss, command timeout, container restart를 테스트합니다. |
| 자동 evidence 수집 | 컨테이너 상태, ROS2 topic, odometry delta, bridge log를 스크립트로 수집합니다. |

## 문서 구조

| 문서 | 목적 |
| --- | --- |
| `README.md` | 영문 프로젝트 개요입니다. |
| `KR.md` | 한국어 testbed 중심 프로젝트 개요입니다. |
| `docs/README.md` | evidence 폴더 전체 안내입니다. |
| `docs/day1/README.md` | ROSbot simulation baseline evidence입니다. |
| `docs/day2/README.md` | noVNC web UI integration evidence입니다. |
| `docs/day3/README.md` | ROS2-MAVLink bridge MVP 결과입니다. |
| `docs/day3/evidence_summary.md` | Day3 evidence 파일별 해석입니다. |

## 참고한 공개 기술 문서

웹에서 `DAH 2026`이라는 이름의 공식 요구사항 문서는 확인하지 못했습니다. 따라서 현재 문서는 저장소의 구현 상태와 testbed 목적을 기준으로 작성했고, 기술적 방향성은 다음 공개 문서를 참고했습니다.

- MAVLink `MANUAL_CONTROL`은 joystick 축을 `[-1000, 1000]` 범위로 표현하는 수동 조종 메시지입니다.
- QGroundControl은 MAVLink 설정에서 ground station system ID, heartbeat, link quality 등을 다룹니다.
- Gazebo는 ROS2와 topic bridge를 통해 센서 데이터와 명령을 주고받을 수 있습니다.

## 현재 상태

이 시스템은 강한 testbed MVP 단계에 있습니다. 주요 제어 루프가 end-to-end로 입증되었고, 컨테이너 상태, ROS2 토픽, 브리지 로그, `/cmd_vel` 연결, odometry 이동량에 대한 evidence가 확보되어 있습니다.

다음 단계는 “더 멋진 데모”보다 **반복 가능한 실험 환경**을 만드는 쪽이 좋습니다.

- bridge 검증 자동화 스크립트
- QGroundControl 연결 설정 문서화
- bridge unit test
- mission/waypoint 처리 범위 정의
- 장애 상황 evidence 추가
- 실제 DAH 2026 요구사항이 정리되면 이 testbed 목적과 시나리오에 반영
