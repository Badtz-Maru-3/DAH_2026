<div align="right">
  <strong>🇺🇸 English</strong> | <a href="docs/project_KR.md">🇰🇷 한국어</a>
</div>

# DAH 2026

DAH 2026 is a Docker-based software-defined UGV/GCS cybersecurity testbed for the DAH 2026 Defense AI cyber attack-defense hackathon preliminary report package.

The current ROSbot UGV scenario now includes the validated command, mission-audit, GNSS-integrity, and correlation-response layers. QGroundControl or MAVLink test tools send control, mission, and GPS_INPUT messages; the bridge converts or audits them; Gazebo/ROS2 provide odometry; and defense decisions are written as evidence logs.

The goal is not just to move one robot in simulation. This repository is intended to support repeatable evidence for the attack-defense loop: attack injection, abnormal behavior, AI-assisted detection, blocking, recovery, and logs that can be used as report evidence.

This testbed is not a replica of an actual military UGV platform. It is a software-defined UGV/GCS cybersecurity testbed that abstracts key operational flows found in defense UGV environments: GCS control, mission upload, GNSS/location input, telemetry feedback, anomaly correlation, and command hold/block response.

## Logical Two-Layer Testbed Architecture

The architecture is best understood as two logical layers: a Simulation Layer that provides operator UI, robot motion, visualization, and odometry; and a Software-Defined UGV Security Layer that validates MAVLink/ROS2 inputs and produces hold/block evidence.

### Simulation Layer

- QGroundControl noVNC provides the GCS screen, Fly View, virtual joystick, and vehicle marker.
- Gazebo / ROSbot provides simulated UGV movement with a ROSbot-based surrogate platform.
- RViz visualizes ROS2 topics, TF, scan, and odometry.
- `/odometry/filtered` provides simulated UGV state feedback.

### Software-Defined UGV Security Layer

- MAVLink Bridge translates QGC-MAVLink messages to ROS2 and sends telemetry back.
- Mission Audit validates mission uploads with geofence and waypoint jump checks.
- GNSS Integrity validates `GPS_INPUT` and detects spoof jumps or poor-fix inputs.
- Correlation Engine combines Mission, GNSS, and Command anomaly signals into a risk score.
- Command Hold / Block blocks or zeroes command output when risk reaches the configured threshold.

### Inter-Layer Data Flow

```text
QGC joystick input is sent as MAVLink MANUAL_CONTROL to the Bridge.
The Bridge converts it into ROS2 /cmd_vel for the simulated ROSbot.
The simulated UGV publishes /odometry/filtered.
The Bridge uses odometry for telemetry feedback and as a reference for GNSS integrity validation.
Mission, GNSS, and command anomalies are evaluated in the Software-Defined UGV Security Layer.
When correlation risk reaches the threshold, Command Hold / Block prevents unsafe command execution.
```

## Components

| Component | Path | Role |
| --- | --- | --- |
| UGV simulation | `UGV/` | Runs the ROSbot Gazebo simulation and publishes ROS2 sensor/odometry topics. |
| GCS | `GCS/` | Runs QGroundControl through noVNC. |
| Bridge | `Bridge/` | Translates between MAVLink UDP and ROS2 topics. |
| AI Agent Layer | `agents/` | Runs the closed-loop attack replay → detect → correlate → hold/block → report pipeline. |
| Evidence | `docs/` | Stores day-by-day test logs, topic snapshots, and MVP validation notes. |

## Testbed Goals

- Keep GCS, simulation, robotics middleware, and communication bridge setup reproducible with Docker.
- Validate the control and telemetry loop between QGroundControl and ROS2/Gazebo.
- Provide a safe simulation layer for UGV mission-command, control-command, and position-input attack experiments.
- Store evidence in `docs/` so experiments remain reviewable and repeatable.
- Implement each attack surface as an evidence-producing tuple: injection point, abnormal symptom, detection/blocking/recovery response, and log proof.

## Target Defense Scenario

The planned defense scenario is an AI-assisted orchestrator for complex UGV operation attacks. The testbed should eventually correlate multiple surfaces instead of treating each event in isolation:

```text
Command injection
  + unauthorized mission / waypoint change
  + suspicious GNSS jump or drift
  -> correlated anomaly
  -> hold / zero cmd_vel / reject mission / operator alert
  -> evidence log
```

Current validated surface:

- C2-like command injection path through MAVLink `MANUAL_CONTROL` and `RC_CHANNELS_OVERRIDE`.
- Mission upload audit through `MISSION_COUNT`, `MISSION_REQUEST_INT`, and `MISSION_ITEM_INT`.
- GNSS position-input integrity checks through `GPS_INPUT`.
- Correlation hold that blocks manual commands after mission or GNSS rejection.
- Telemetry conversion path from ROS2 odometry to MAVLink local/global position messages.

Remaining planned/hardening surfaces:

- QGroundControl operator-facing screenshots for mission rejection and warning state.
- Longer-duration stability, restart, and regression evidence collection.
- Full mission execution/autopilot behavior beyond audit-and-reject.
- More advanced GNSS fallback/dead-reckoning behavior.

## Runtime Services

`compose.webui.yml` is the default integrated stack. It starts QGroundControl, Gazebo, RViz, and the bridge together:

| Service | URL | Container | Purpose |
| --- | --- | --- | --- |
| QGroundControl | `http://localhost:6080/vnc.html` | `dah-qgc-novnc` | Ground control UI. |
| Gazebo | `http://localhost:6081/vnc_auto.html` | `dah-rosbot-sim-novnc` | ROSbot simulation UI. |
| RViz | `http://localhost:6082/vnc_auto.html` | `dah-rviz-novnc` | ROS2 visualization UI. |
| Bridge | N/A | `dah-bridge` | MAVLink/ROS2 control and telemetry bridge. |

Integrated services currently use host networking. QGroundControl persists its configuration under `GCS/data`, RViz waits for the ROSbot simulation service, and the bridge waits for QGroundControl and ROSbot simulation. The root stack uses `restart: unless-stopped` for the long-running services.

### Windows Docker Desktop noVNC note

The current integrated stack was validated with host networking semantics. On Windows Docker Desktop, `network_mode: host` may not expose the noVNC browser ports to the Windows host in the same way it does on Linux/WSL. A symptom is that containers appear healthy and can communicate internally, but these URLs do not open from the Windows browser:

- `http://localhost:6080/vnc.html`
- `http://localhost:6081/vnc_auto.html`
- `http://localhost:6082/vnc_auto.html`

If that happens, check the noVNC entrypoints first. They currently bind `websockify` to loopback inside the container:

| File | Current bind | Windows access candidate |
| --- | --- | --- |
| `GCS/entrypoint-novnc.sh` | `127.0.0.1:6080` | `0.0.0.0:6080` |
| `UGV/entrypoint-ugv-novnc.sh` | `127.0.0.1:6081` | `0.0.0.0:6081` |
| `UGV/entrypoint-rviz-novnc.sh` | `127.0.0.1:6082` | `0.0.0.0:6082` |

The matching Windows compose candidate is to replace host networking for the noVNC services with explicit port publishing:

```yaml
ports:
  - "6080:6080"  # QGroundControl
  - "6081:6081"  # Gazebo
  - "6082:6082"  # RViz
```

Do not treat this as a fully validated replacement for the default stack yet. Removing `network_mode: host` changes ROS2 DDS discovery and MAVLink addressing assumptions, so a Windows-specific compose path should be tested again for QGC, ROSbot, RViz, bridge, mission audit, GNSS integrity, and correlation evidence before replacing `compose.webui.yml`.

`Bridge/compose.bridge.yml` is kept for bridge-only debugging when QGroundControl and the simulation are started separately. Do not run it at the same time as the bridge service in `compose.webui.yml`, because both paths use the `dah-bridge` container name:

| Service | Container | Purpose |
| --- | --- | --- |
| bridge | `dah-bridge` | Starts only the MAVLink/ROS2 bridge from the `Bridge/` directory. |

## Environment

The project uses `.env` or `.env.example` for shared configuration.

| Variable | Default | Meaning |
| --- | --- | --- |
| `ROS_DOMAIN_ID` | `17` | Keeps UGV, RViz, and bridge in the same ROS2 DDS domain. |
| `ROBOT_MODEL` | `rosbot_xl` | Selects the Gazebo robot model. The standard testbed profile uses `rosbot_xl`. |
| `ROBOT_CONFIGURATION` | `autonomy` | Selects the ROSbot sensor/configuration profile. The standard testbed profile uses `autonomy` for scan and autonomy sensor topics. |
| `QGC_IP` | `127.0.0.1` | QGroundControl MAVLink receiver address. |
| `QGC_PORT` | `14550` | QGroundControl MAVLink UDP port. |
| `BRIDGE_LOCAL_PORT` | `14551` | UDP port where the bridge listens for MAVLink packets. |
| `MAX_LINEAR` | `0.5` | Max linear velocity published to `/cmd_vel`. |
| `MAX_ANGULAR` | `1.2` | Max angular velocity published to `/cmd_vel`. |
| `CMD_TIMEOUT` | `0.6` | Time before the bridge publishes a zero command after input stops. |
| `BASE_LAT`, `BASE_LON`, `BASE_ALT` | Seoul defaults | Origin used to convert local odometry into MAVLink global position telemetry. |
| `LIBGL_ALWAYS_SOFTWARE` | `1` | Prefers software rendering for Gazebo/QGC stability. |
| `MAVLINK_DEBUG` | `0` | Enables verbose MAVLink receive logs when set to `1`. |
| `MISSION_MAX_ITEMS` | `20` | Maximum mission item count accepted by mission audit. |
| `MISSION_GEOFENCE_RADIUS_M` | `300` | Mission waypoint geofence radius around `BASE_LAT`/`BASE_LON`. |
| `MISSION_MAX_JUMP_M` | `120` | Maximum allowed waypoint-to-waypoint jump distance. |
| `MISSION_MIN_ALT_M`, `MISSION_MAX_ALT_M` | `-20`, `200` | Accepted mission altitude range. |
| `MISSION_ALLOWED_COMMANDS` | `16,20` | Allowed MAVLink mission commands in audit v1. |
| `GNSS_MAX_RESIDUAL_M` | `30` | Maximum GNSS-to-odometry position residual. |
| `GNSS_MIN_FIX_TYPE` | `3` | Minimum accepted GPS fix type. |
| `GNSS_MIN_SATELLITES` | `6` | Minimum accepted visible satellite count. |
| `GNSS_MAX_HACC_M` | `15` | Maximum accepted horizontal accuracy in meters. |
| `CORRELATION_RISK_THRESHOLD` | `0.75` | Risk score required to engage hold. |
| `CORRELATION_HOLD_SECONDS` | `5` | Duration of hold/command blocking after threshold crossing. |
| `COMMAND_HIGH_LINEAR_MPS` | `0.60` | Linear command threshold used by correlation command guard. |
| `COMMAND_HIGH_ANGULAR_RADPS` | `1.50` | Angular command threshold used by correlation command guard. |

## Quick Start

Copy the example environment file if needed:

```bash
cp .env.example .env
```

Robot model and sensor configuration are configured in `.env`. The standard testbed profile is `rosbot_xl` with the `autonomy` configuration:

```bash
ROBOT_MODEL=rosbot_xl
ROBOT_CONFIGURATION=autonomy
```

`.env.example` includes this standard profile as a template. If you intentionally switch to another robot model or configuration, re-check `/cmd_vel`, `/odometry/filtered`, `/scan`, `/tf`, and the Day3-Day6 validation flow because available sensor topics can change.

Start the integrated testbed stack. This is the normal path and already includes `dah-bridge`:

```bash
docker compose --env-file .env -f compose.webui.yml up -d
```

Bridge-only debugging is an alternative path, not an extra step after the integrated stack. Use it only when QGroundControl and the simulation are already running some other way, or after removing the integrated bridge service container:

```bash
docker compose --env-file .env -f compose.webui.yml stop bridge
docker compose --env-file .env -f compose.webui.yml rm -f bridge
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

If Docker reports `Conflict. The container name "/dah-bridge" is already in use`, the integrated bridge container is still present. Stop it through the compose file that created it before starting the bridge-only compose file:

```bash
docker compose --env-file .env -f compose.webui.yml down
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

If you already know the integrated bridge is not running, the bridge-only command is:

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

To switch back from bridge-only debugging to the integrated stack, remove the bridge-only container first:

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml down
docker compose --env-file .env -f compose.webui.yml up -d
```

Open the web UIs:

- QGroundControl: `http://localhost:6080/vnc.html`
- Gazebo: `http://localhost:6081/vnc_auto.html`
- RViz: `http://localhost:6082/vnc_auto.html`

Stop services:

```bash
docker compose --env-file .env -f compose.webui.yml down
```

If the bridge was started through `Bridge/compose.bridge.yml`, stop it separately:

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml down
```

## RViz Setup

Recommended RViz displays:

- Set `Fixed Frame` to `odom`.
- Add `TF`.
- Add `/scan` as `LaserScan`.
- Add `/odometry/filtered` as `Odometry`.

## Verification

Useful checks:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
ros2 topic list -t
ros2 topic info /cmd_vel -v
ros2 topic echo /odometry/filtered --once
docker logs dah-bridge
```

The Day3 evidence currently shows:

- `dah-bridge`, QGC, RViz, and ROSbot simulation containers running together.
- The integrated `compose.webui.yml` now includes the bridge service, so one compose file can launch the full baseline stack.
- `/cmd_vel` has `ros2_mavlink_bridge` as a publisher and `drive_controller` as a subscriber.
- The bridge receives MAVLink `MANUAL_CONTROL` from QGroundControl.
- The bridge publishes non-zero `/cmd_vel`.
- ROSbot odometry changes by about `1.078 m` after QGC joystick input.

See `docs/day3/README.md` and `docs/day3/evidence_summary.md` for the detailed MVP evidence.

Later evidence shows:

- Day4: normal mission accepted, malicious geofence/jump missions rejected, and `MISSION_ACK` emitted.
- Day5: normal `GPS_INPUT` accepted, spoof jump and poor fix rejected.
- Day6: mission/GNSS rejection converted into correlation risk, hold engaged, and `MANUAL_CONTROL` blocked during hold.

## AI Agent Layer (Closed-Loop Defense)

The `agents/` package adds an AI agent layer on top of the testbed and runs the full
attack-defense loop as a single command: **attack replay → deterministic detection →
correlation → hold/block verdict → incident report**. An LLM is the reasoning core
(scenario selection, gap analysis, root-cause, mitigation) while a deterministic reflex
owns the safety-critical hold/block. See `agents/README.md` for the architecture and
`agents/VALIDATION.md` for the full validation checklist.

Three scenarios are replayed:

| Scenario | Surface | Expected verdict |
| --- | --- | --- |
| A | ROS2 `/cmd_vel` command injection | `risk=1.0`, command blocked |
| B | ROS2 `/odometry/filtered` + `/scan` state/perception deception | `risk≈0.48`, detected, no hold |
| C | MAVLink Mission / GNSS input manipulation | `risk=1.0`, command blocked |

### Dry-run (reproducible offline, no Docker or ROS2 required)

Runs the whole loop deterministically, with no tokens and no ROS2/MAVLink:

```bash
python3 -m agents.main_orchestrator --rounds 3 --dry-run --llm-backend none
```

Expected core verdicts:

```text
A: risk=1.0  hold=True  block=True
B: risk=0.48 hold=False block=False
C: risk=1.0  hold=True  block=True
```

Each run writes a JSONL run trace and per-round JSON/Markdown incident reports under
`agents/reports/` (gitignored runtime artifacts).

### LLM reasoning path (optional)

The reasoning/report agent can use an LLM backend (Anthropic or OpenAI). Select the
provider with a `provider:model` string; a bare value defaults to Anthropic:

```bash
pip install openai            # or: pip install anthropic
export OPENAI_API_KEY=...      # or: export ANTHROPIC_API_KEY=...
python3 -m agents.main_orchestrator --rounds 1 --dry-run --scenario-id A \
  --llm-backend openai:gpt-4o-mini
```

Confirm `reasoning_source` is `"llm"` (not `"template"`) in the printed report / the JSON
under `agents/reports/`. The LLM only enriches the narrative — it never changes the
deterministic `risk_score` / `hold_engaged` / `command_blocked` verdict. With
`--llm-backend none` the loop still runs fully via deterministic templates.

### Live run (against the running stack)

With the integrated stack up (`docker compose ... up -d`), `compose.webui.yml` bind-mounts
`./agents` into the `dah-bridge` container, so the whole closed loop runs live with one
command — pick the scenario A, B, or C:

```bash
./agents/run_live.sh A     # or B, or C
```

This **replays the selected attack into the live ROS2/MAVLink graph and runs the defense
loop (detect → correlate → hold/block → report) in the same command.** Live mode is gated
behind `--confirm-live-testbed-only` (an ungated `--live` is rejected); the wrapper sets it
for you and writes run traces / incident reports to `./agents/reports/`. Extra flags pass
through, e.g. `./agents/run_live.sh C --llm-backend openai:gpt-4o-mini`.

The live A and B adapters launch the report's own standalone attack PoCs, so the closed loop
exercises the real attacks. Confirm the run-trace markers per scenario:

- A → `live_command_observed`. The adapter runs the closed-loop hijack (`demo/hijack_nav.py`),
  which drives the robot toward the attacker target while an unauthorized `/cmd_vel` publisher
  is detected → `hold_engaged` (and `command_blocked` when the hijack is actively driving at
  high velocity). The active zero-Twist hold then stops the robot.
- B → `live_state_observed`. The adapter runs the `/scan` spoofer (`demo/spoof_scan.py`, a fake
  0.5 m obstacle ring); the detector flags `scan_anomaly` (`risk≈0.24`) — perception deception
  is detected but, as in the report, engages no hold.
- C → fresh Mission/GNSS signals from the Bridge logs and a `MAV_MISSION_DENIED` ack →
  `risk=1.0`, command blocked.

On a freshly started stack, run A first to see the robot visibly hijacked and then stopped;
because the robot's pose persists between runs, re-running A without resetting it leaves the
robot already at the target, so A then reports `hold` without the envelope breach.

When a verdict engages hold/block, the active zero-Twist hold on `/cmd_vel` is observable in
the web UIs: the QGC joystick has no effect and the ROSbot stops in Gazebo/RViz. See
`agents/VALIDATION.md` §3–§8 for the per-scenario live checklist, the safety-gate test, and
the expected signals.

> **`agents/` vs `demo/`.** The live A/B adapters invoke the report's standalone attack PoCs
> (`demo/hijack_nav.py`, `demo/spoof_scan.py`) **inside the closed loop** (attack + defense in
> one command). The same `demo/` scripts can also be run **standalone** against their matching
> sentinel defenders (`demo/kill_switch_sentinel.py`, `demo/scan_sentinel_secure.py`,
> `demo/mavlink_sentinel.py`) in separate terminals, matching the report's per-scenario
> attack/defense walkthrough.

## Documentation Map

| Document | Purpose |
| --- | --- |
| `agents/README.md` | AI agent layer architecture (attack replay + closed-loop defense orchestration). |
| `agents/VALIDATION.md` | Dry-run and live validation checklist for the AI agent layer. |
| `docs/README.md` | Overview of evidence folders. |
| `docs/architecture/two_layer_architecture.md` | Logical two-layer architecture, responsibilities, evidence mapping, and limits. |
| `docs/day1/README.md` | ROSbot simulation baseline evidence. |
| `docs/day2/README.md` | noVNC web UI integration evidence. |
| `docs/day3/README.md` | ROS2-MAVLink bridge MVP result. |
| `docs/day3/evidence_summary.md` | File-by-file Day3 evidence interpretation. |
| `docs/day3/odom_delta.md` | Odometry movement calculation proving the command path. |
| `docs/day4/README.md` | Mission audit implementation and accepted/rejected evidence. |
| `docs/day5/README.md` | GNSS integrity implementation and GPS_INPUT evidence. |
| `docs/day6/README.md` | Correlation engine hold/blocking evidence. |

## References

Official and technical documentation:

- DAH 2026 Preliminary Guide, 2026-06-15.
- MAVLink Developer Guide, Common Message Set.
- MAVLink Developer Guide, Mission Protocol.
- QGroundControl User Guide, Download and Install.
- Husarion Documentation, How to use Husarion Docker images.
- Docker Documentation, Compose file services reference.
- noVNC GitHub Repository, HTML VNC client library and application.

Project internal materials:

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

Research literature:

- Mayoral Vilches, V. et al., SROS2: Usable Cyber Security Tools for ROS 2, arXiv:2208.02615.
- Choton, J. C. et al., Formal Modeling and Verification of Publisher-Subscriber Paradigm in ROS 2, arXiv:2412.16186.
- Macenski, S. et al., Impact of ROS 2 Node Composition in Robotic Systems, arXiv:2305.09933.
- Clements, Z., Yoder, J. E., Humphreys, T. E., Carrier-phase and IMU based GNSS Spoofing Detection for Ground Vehicles, arXiv:2203.00140.
- Johansson, T., Spanghero, M., Papadimitratos, P., Consumer INS Coupled with Carrier Phase Measurements for GNSS Spoofing Detection, arXiv:2502.03870.
- Park, S., Cho, D. J., Son, P. W., Wide-Area GNSS Spoofing and Jamming Detection Using AIS-Derived Spatiotemporal Integrity Monitoring, arXiv:2603.11055.

## Current Status

The system is past the bridge-only MVP stage. The main control loop, mission audit, GNSS integrity, and correlation hold path are implemented and backed by Day3-Day6 evidence.

Recommended next steps:

- Capture QGroundControl screenshots for mission upload/rejection and operator-visible warning state.
- Add a repeatable evidence collection script for Day3-Day6 logs.
- Add regression tests that protect `MANUAL_CONTROL -> /cmd_vel`, mission audit, GNSS reject, and correlation hold.
- Extend GNSS response from rejection/warning to explicit trust downgrade and fallback behavior.
- Keep the existing Day3 `MANUAL_CONTROL -> /cmd_vel` and `CMD_TIMEOUT` watchdog behavior intact.
