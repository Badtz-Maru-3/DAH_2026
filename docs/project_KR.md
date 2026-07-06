<div align="right">
  <a href="../README.md">🇺🇸 English</a> | <strong>🇰🇷 한국어</strong>
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

Evidence 캡처는 `Bridge/tools/run_evidence.sh`로 `docs/evidence/` 아래에 생성됩니다
(`docs/evidence/README.md`가 index).

| Day | 검증 내용 | Evidence |
| --- | --- | --- |
| Day1 | ROSbot Gazebo simulation baseline | `docs/evidence/00_environment/` |
| Day2 | QGC/Gazebo/RViz noVNC web UI stack | `docs/evidence/00_environment/` |
| Day3 | `MANUAL_CONTROL -> /cmd_vel -> odometry` bridge MVP | `docs/evidence/03_manual_control/` |
| Day4 | mission upload audit accept/reject | `docs/evidence/04_mission_audit/` |
| Day5 | `GPS_INPUT` normal/spoof/poor-fix validation | `docs/evidence/05_gnss_integrity/` |
| Day6 | correlation risk scoring, hold, command block | `docs/evidence/06_correlation_hold/` |

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

## AI 에이전트 계층 (폐루프 방어)

`agents/` 패키지는 테스트베드 위에 AI 에이전트 계층을 얹어, **공격 replay → deterministic
탐지 → correlation → hold/block verdict → incident report**로 이어지는 폐루프를 한 명령으로
실행합니다. LLM이 추론 코어(시나리오 선택, gap analysis, root-cause, mitigation)를 맡고,
deterministic reflex가 안전상 중요한 hold/block을 소유합니다. 아키텍처는 `agents/README.md`,
전체 검증 체크리스트는 `agents/VALIDATION.md`를 참조하세요.

세 가지 시나리오를 replay합니다.

| 시나리오 | 공격 표면 | 기대 verdict |
| --- | --- | --- |
| A | ROS2 `/cmd_vel` command injection | `risk=1.0`, command blocked |
| B | ROS2 `/odometry/filtered` + `/scan` 상태·인지 교란 | `risk≈0.48`, 탐지되나 hold 없음 |
| C | MAVLink Mission / GNSS 입력 조작 | `risk=1.0`, command blocked |

### Dry-run (오프라인 재현, Docker·ROS2 불필요)

토큰과 ROS2/MAVLink 없이 전체 루프를 deterministic하게 실행합니다.

```bash
python3 -m agents.main_orchestrator --rounds 3 --dry-run --llm-backend none
```

기대 core verdict:

```text
A: risk=1.0  hold=True  block=True
B: risk=0.48 hold=False block=False
C: risk=1.0  hold=True  block=True
```

매 실행마다 JSONL run trace와 round별 JSON/Markdown incident report가 `agents/reports/`
(gitignore된 runtime artifact)에 생성됩니다.

### LLM 추론 경로 (선택)

reasoning/report 에이전트는 LLM 백엔드(Anthropic 또는 OpenAI)를 쓸 수 있습니다. 백엔드는
`provider:model` 형식으로 지정하며, prefix 없는 값은 Anthropic로 처리됩니다.

```bash
pip install openai            # 또는: pip install anthropic
export OPENAI_API_KEY=...      # 또는: export ANTHROPIC_API_KEY=...
python3 -m agents.main_orchestrator --rounds 1 --dry-run --scenario-id A \
  --llm-backend openai:gpt-4o-mini
```

출력 report 또는 `agents/reports/`의 JSON에서 `reasoning_source`가 `"template"`이 아닌
`"llm"`인지 확인합니다. LLM은 서술만 보강할 뿐 deterministic한 `risk_score` /
`hold_engaged` / `command_blocked` verdict를 바꾸지 않습니다. `--llm-backend none`에서도
루프는 deterministic template으로 완전히 동작합니다.

### Live run (실행 중인 스택 대상)

통합 스택이 떠 있으면(`docker compose ... up -d`), `compose.webui.yml`이 `./agents`를
`dah-bridge` 컨테이너에 bind-mount 하므로 전체 폐루프를 **한 명령**으로 실행합니다 —
시나리오 A/B/C 중 선택:

```bash
./agents/run_live.sh A     # 또는 B, C
```

이 명령은 **선택한 공격을 라이브 ROS2/MAVLink 그래프에 replay하고, 같은 명령으로 방어
루프(탐지 → correlation → hold/block → report)까지 실행**합니다. Live 모드는
`--confirm-live-testbed-only` 뒤에서만 동작하며(게이트 없는 `--live`는 거부), 래퍼가 이를
대신 붙이고 run trace/incident report를 `./agents/reports/`에 씁니다. 추가 플래그는 그대로
전달됩니다(예: `./agents/run_live.sh C --llm-backend openai:gpt-4o-mini`).

Live A·B adapter는 리포트의 독립 공격 PoC를 직접 실행하므로, 폐루프가 실제 공격을 구동합니다.
시나리오별 run-trace 마커:

- A → `live_command_observed`. adapter가 폐루프 hijack(`demo/hijack_nav.py`)을 실행해 로봇을
  공격자 목표로 몰고 가며, 비인가 `/cmd_vel` publisher가 탐지됨 → `hold_engaged`(고속 주행
  중이면 `command_blocked`도). 이어서 active zero-Twist hold가 로봇을 정지시킴.
- B → `live_state_observed`. adapter가 `/scan` 스푸퍼(`demo/spoof_scan.py`, 가짜 0.5m 장애물
  링)를 실행 → `scan_anomaly` 탐지(`risk≈0.24`). 인지 기만은 탐지되지만 리포트대로 hold는
  걸지 않음.
- C → Bridge 로그의 fresh Mission/GNSS signal 및 `MAV_MISSION_DENIED` ack → `risk=1.0`, blocked

fresh 스택에서는 A를 먼저 실행하면 로봇이 실제로 hijack됐다가 정지하는 것을 볼 수 있습니다.
로봇 pose가 실행 간 유지되므로, 리셋 없이 A를 재실행하면 로봇이 이미 목표에 있어 envelope
breach 없이 `hold`만 보고됩니다.

verdict가 hold/block을 걸면 `/cmd_vel`의 zero-Twist hold가 웹 UI에서 관찰됩니다(QGC 조이스틱
무효, Gazebo/RViz에서 ROSbot 정지). 시나리오별 live 체크리스트와 safety-gate 테스트는
`agents/VALIDATION.md` §3–§8을 참조하세요.

> **`agents/` vs `demo/`.** Live A/B adapter는 리포트의 독립 공격 PoC(`demo/hijack_nav.py`,
> `demo/spoof_scan.py`)를 **폐루프 안에서**(공격+방어를 한 명령으로) 실행합니다. 같은 `demo/`
> 스크립트는 대응 sentinel 방어자(`demo/kill_switch_sentinel.py`, `demo/scan_sentinel_secure.py`,
> `demo/mavlink_sentinel.py`)와 함께 **별도 터미널**에서 독립 실행할 수도 있으며, 리포트의
> 시나리오별 공격/방어 설명과 대응됩니다.

## 문서 구조

| English | Korean |
| --- | --- |
| `README.md` | `README_KR.md` |
| `AGENTS.md` | `AGENTS_KR.md` |
| `agents/README.md` | `docs/agents_architecture_KR.md` |
| `docs/README.md` | `docs/README_KR.md` |
| `docs/architecture/two_layer_architecture.md` | `docs/architecture/two_layer_architecture_KR.md` |
| `ai_collaboration.md` | `docs/ai_collaboration_KR.md` |
| `docs/evidence/README.md` | (자동 생성 캡처; 한국어 evidence index는 `docs/README_KR.md`) |

## 현재 상태

이 시스템은 bridge-only MVP 단계를 넘어섰습니다. 주요 제어 루프, mission audit, GNSS integrity, correlation hold/block 경로가 구현되었고 Day3-Day6 evidence로 뒷받침됩니다.

다음 보강 방향은 QGroundControl 화면 evidence, 반복 가능한 evidence 수집 스크립트, regression test, GNSS trust downgrade/fallback입니다.
