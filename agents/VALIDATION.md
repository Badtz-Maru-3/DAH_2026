# DAH_2026 Agent Validation Guide

이 문서는 팀원이 `agents/` 코드를 내려받은 뒤 dry-run과 live stack에서 동일한 순서로
검증하기 위한 체크리스트다. 여기서 말하는 live stack은 Docker/Compose로 실행된
software-defined UGV/GCS testbed와, 에이전트를 실행하는 환경에서 접근 가능한 ROS2 graph
및 MAVLink Bridge를 함께 뜻한다.

> 검증 원칙: dry-run 결과는 재현 가능한 기능 검증이고, live 결과는 팀 live stack에서
> 별도로 확인해야 한다. live ROS2/MAVLink 검증이 끝나기 전에는 "live validated"라고
> 쓰지 않는다.

---

## 0. 현재 에이전트 구현으로 충분한 범위

현재 `agents/` 구현은 **대회/보고서용 AI 에이전트 아키텍처 프로토타입**으로는 충분한
상태다. 한 명령으로 A/B/C replay → detector → correlation → hold/block verdict →
incident report까지 이어지는 closed loop를 보여줄 수 있다.

현재 구현이 이미 제공하는 것:

- A/B/C 시나리오 선택 및 replay adapter
- Command Monitor, State Consistency, Mission-GNSS Guard detector
- agent-layer Correlation Agent의 `risk_score`, `hold_engaged`, `command_blocked` verdict
- Command Hold / Block 결정과 gated live zero-Twist hold publish path
- Reasoning & Report Agent의 LLM path 및 `--llm-backend none` deterministic template fallback
- dry-run end-to-end execution
- JSONL/Markdown report와 run trace 생성
- live mode safety gate: `--live --confirm-live-testbed-only`

따라서 보고서에는 다음 수준으로 말할 수 있다.

```text
The agent layer implements an LLM-brain + deterministic-reflex prototype that replays
A/B/C scenarios, produces deterministic anomaly signals, correlates them into hold/block
verdicts, and writes incident reports. The closed loop is reproducible in dry-run, and
live validation steps are provided for the team testbed.
```

하지만 다음은 아직 **팀 live stack에서 확인해야 하는 범위**다.

- Scenario A live `/cmd_vel` injection이 실제 ROS2 graph에서 독립 detector signal로 잡히는지
- Scenario B live `/scan`, `/odometry/filtered`, `/tf` 교란이 실제 독립 detector signal로
  잡히는지
- active zero-Twist `/cmd_vel` hold가 Gazebo/RViz에서 실제 정지 또는 command clamp로 보이는지
- Scenario C live Bridge/MAVLink tools가 Mission/GNSS logs와 fresh signal을 남기는지
- QGC/RViz 화면에서 사람이 확인 가능한 효과가 있는지

즉, 현재 상태를 한 줄로 요약하면 다음과 같다.

```text
Dry-run closed-loop prototype is implemented and reproducible.
Live ROS2/MAVLink validation is ready to run but must be confirmed on the team stack.
```

---

## 0.1 공격 시나리오 표현 수위

보고서나 발표에서 공격 시나리오를 설명할 때는 현재 구현보다 강하게 말하지 않는다.
아래 표현이 안전하다.

```text
A: /cmd_vel command injection replay and detection
B: /scan, /odometry/filtered, /tf state/perception deception replay and detection
C: MAVLink Mission/GNSS input manipulation replay and hold/block correlation
```

주의할 표현:

- Scenario A를 "목표 좌표까지 완전한 폐루프 정밀 유도 탈취가 구현됐다"고 쓰지 않는다.
  현재 구현은 `/cmd_vel` injection replay와 Command Monitor detection 중심이며,
  odometry-fed closed-loop guidance는 위협 모델/확장 가능성으로만 설명한다.
- Scenario B를 `/scan`만으로 좁히지 않는다. 현재 detector는 `/scan` anomaly와
  odom↔tf consistency를 함께 다룬다.
- Scenario C에서 Bridge Correlation Engine threshold와 agent-layer Correlation Agent
  threshold를 섞지 않는다. agent-layer 기준은 hold `>= 0.5`, block `>= 0.8`이다.
- contract에 없는 `gnss_rejected` 같은 signal 이름을 쓰지 않는다. 현재 agent signal은
  `mission_rejected`, `spoof_jump`, `poor_fix`다.
- "동일 LAN 공격", "실제 RF/GNSS 공격", "실제 군용 UGV 침투"처럼 보이는 표현을 피하고,
  authorized local Docker/testbed network와 message/topic injection replay로 제한한다.

---

## 1. 받기 전 주의사항

커밋/공유 대상:

- `agents/` source files
- `docs/agents_KR.md`
- `.gitignore`

공유하지 않을 runtime artifact:

- `agents/reports/`
- `Bridge/logs/`
- `__pycache__/`
- `.pytest_cache/`

`agents/reports/`는 실행 중 자동 생성되며 `.gitignore`에 포함되어 있다.

---

## 2. Offline Dry-Run 검증

ROS2, Docker, QGC, Gazebo가 없어도 먼저 이 검증은 통과해야 한다.

```bash
python3 -m py_compile agents/*.py agents/attack/*.py agents/defense/*.py
python3 -m agents.main_orchestrator --rounds 3 --dry-run --llm-backend none
```

특정 시나리오만 검증할 때는 `--scenario-id`를 사용한다.

```bash
python3 -m agents.main_orchestrator --rounds 1 --dry-run --llm-backend none --scenario-id A
python3 -m agents.main_orchestrator --rounds 1 --dry-run --llm-backend none --scenario-id B
python3 -m agents.main_orchestrator --rounds 1 --dry-run --llm-backend none --scenario-id C
```

기대 stable core:

```text
A: risk_score=1.0, command_blocked=True
B: risk_score=0.48, hold/block false
C: risk_score=1.0, command_blocked=True
```

확인 포인트:

- Scenario A evidence source는 `/cmd_vel` synthetic ROS2-topic observation 형태다.
- Scenario B evidence source는 `/tf`, `/scan` synthetic ROS2-topic observation 형태다.
- Scenario C evidence source는 `adapter_c_mavlink` / `synthetic`이어야 한다.
- `agents/reports/` 아래 JSON/Markdown report와 run trace가 생성된다.

---

## 3. Live Stack 준비 확인

live 검증 전, Docker/Compose와 ROS2/MAVLink 접근이 모두 확인되어야 한다.

```bash
docker compose ps
ros2 topic list
ros2 topic info /cmd_vel -v
python3 -c "import rclpy; import geometry_msgs.msg; import nav_msgs.msg; import sensor_msgs.msg"
```

가능하면 다음 topic이 보여야 한다.

```text
/cmd_vel
/odometry/filtered
/scan
/tf
```

Bridge/MAVLink 쪽은 다음을 확인한다.

```bash
python3 Bridge/tools/send_manual_control.py stop --port 14551
```

실패하면 Bridge listen port, container network, `BRIDGE_LOCAL_PORT` 값을 먼저 확인한다.

---

## 4. Live Safety Gate 확인

게이트 없는 live 실행은 반드시 막혀야 한다.

```bash
python3 -m agents.main_orchestrator --rounds 1 --live
```

기대 결과:

```text
error: --live requires --confirm-live-testbed-only
```

실제 testbed에서만 다음 명령을 실행한다.

```bash
python3 -m agents.main_orchestrator --rounds 3 --live --confirm-live-testbed-only --llm-backend none
```

live에서 특정 시나리오만 검증할 때도 `--scenario-id`를 사용한다.

```bash
python3 -m agents.main_orchestrator --rounds 1 --live --confirm-live-testbed-only --llm-backend none --scenario-id A
python3 -m agents.main_orchestrator --rounds 1 --live --confirm-live-testbed-only --llm-backend none --scenario-id B
python3 -m agents.main_orchestrator --rounds 1 --live --confirm-live-testbed-only --llm-backend none --scenario-id C
```

---

## 5. Scenario A 검증 기준

Scenario A는 `/cmd_vel` command injection 재현과 Command Monitor 관측을 확인한다.

기대 trace 흐름:

```text
live_detector_started
live_command_observed
```

`live_command_observed`가 나오면 독립 detector subprocess가 `AnomalySignal` JSONL을
stdout으로 냈다는 뜻이다. 이때 기대 signal은 다음 중 하나 이상이다.

```text
unexpected_publisher
rate_spike
envelope_breach
```

주의:

- `live_command_no_independent_signals`는 live stack에서 detector가 정상 실행됐지만
  독립 관측 signal이 없었다는 뜻이다. 이 경우 missed detection으로 취급한다.
- `live_command_adapter_snapshot_fallback`은 detector가 시작하지 못했거나 실패하여
  adapter metadata로만 fallback했다는 뜻이다. 이것은 독립 live detection 성공으로
  보고하지 않는다.

---

## 6. Scenario B 검증 기준

Scenario B는 `/odometry/filtered`, `/scan`, `/tf` consistency 관측을 확인한다.

기대 trace 흐름:

```text
live_detector_started
live_state_observed
```

`live_state_observed`가 나오면 독립 detector subprocess가 `AnomalySignal` JSONL을
stdout으로 냈다는 뜻이다. 기대 signal은 다음 중 하나 이상이다.

```text
odom_tf_mismatch
scan_anomaly
```

주의:

- `live_state_no_independent_signals`는 detector가 정상 실행됐지만 독립 관측 signal이
  없었다는 뜻이다. 이 경우 missed detection으로 취급한다.
- `live_state_adapter_snapshot_fallback`은 detector 실패 fallback이며, 독립 live detection
  성공으로 보고하지 않는다.

---

## 7. Scenario C 검증 기준

Scenario C는 MAVLink Bridge tools를 통한 mission/GNSS/manual input 재현과
Mission-GNSS Guard 관측을 확인한다.

검증 포인트:

- Adapter C는 caller-supplied script path를 받지 않고, 기존 `Bridge/tools/send_*.py`만
  allowlisted subprocess로 실행해야 한다.
- `shell=True`를 사용하지 않아야 한다.
- subprocess timeout이 적용되어야 한다.
- live mode에서는 Bridge log에서 `fresh_after` 이후의 Mission/GNSS signal만 수집해야 한다.

기대 signal:

```text
mission_rejected
spoof_jump
poor_fix
```

Dry-run에서는 Scenario C evidence가 `adapter_c_mavlink` / `synthetic`이어야 한다. Live
검증에서는 Bridge Mission/GNSS logs가 read-only evidence source가 된다.

---

## 8. Active Hold / Block 확인

Correlation verdict가 hold/block을 만들면 live mode에서 Command Hold / Block이 gated
zero-Twist `/cmd_vel` hold publish를 시도한다.

확인 포인트:

- `--live --confirm-live-testbed-only` 없이는 active publish가 없어야 한다.
- live mode에서 `command_blocked=True` 또는 `hold_engaged=True`일 때만 active publish가
  시도되어야 한다.
- `/cmd_vel`에서 zero-Twist hold가 관측되는지 확인한다.

예시:

```bash
ros2 topic echo /cmd_vel --once
```

---

## 9. 결과 보고 형식

팀원은 검증 결과를 다음 형태로 공유한다.

```text
환경:
- Docker/Compose profile:
- ROS_DOMAIN_ID:
- Bridge port:
- rclpy/message packages import: pass/fail

Dry-run:
- command:
- A result:
- B result:
- C result:

Live:
- command:
- A trace: live_command_observed / live_command_no_independent_signals / fallback
- B trace: live_state_observed / live_state_no_independent_signals / fallback
- C trace:
- hold/block observed:

Artifacts:
- run_trace path:
- report paths:

Notes:
- missed detections:
- dependency or topic gaps:
```

---

## 10. No-Overclaim Rule

다음 조건을 모두 만족하기 전에는 문서나 보고서에 live 검증 완료라고 쓰지 않는다.

- live stack에서 `--live --confirm-live-testbed-only` 실행
- A/B detector subprocess가 독립 signal을 emit하거나, no-signal 결과가 missed detection으로
  명확히 기록됨
- C가 Bridge tools와 Mission/GNSS read-only evidence path로 검증됨
- hold/block 또는 no-hold decision이 run trace와 report에 남음

이 testbed는 software-defined UGV/GCS cybersecurity testbed이며, 실제 군용 UGV, RF 계층,
물리 GNSS 수신기 통합을 주장하지 않는다.
