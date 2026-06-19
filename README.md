# DAH 2026

DAH 2026 is a Docker-based unmanned-systems cyber-defense testbed for the DAH 2026 Defense AI cyber attack-defense hackathon preliminary report package.

The current ROSbot UGV scenario is the first validated baseline. QGroundControl sends MAVLink manual-control messages, the bridge converts them to ROS2 `/cmd_vel`, Gazebo moves the simulated ROSbot, and odometry is sent back to QGroundControl as MAVLink telemetry.

The goal is not just to move one robot in simulation. This repository is intended to support repeatable evidence for the attack-defense loop: attack injection, abnormal behavior, AI-assisted detection, blocking, recovery, and logs that can be used as report evidence.

## Baseline Architecture

```text
QGroundControl noVNC
  -> MAVLink UDP
  -> dah-bridge
  -> ROS2 /cmd_vel
  -> ROSbot Gazebo
  -> ROS2 /odometry/filtered
  -> dah-bridge
  -> MAVLink telemetry
  -> QGroundControl HUD / map
```

## Components

| Component | Path | Role |
| --- | --- | --- |
| UGV simulation | `UGV/` | Runs the ROSbot Gazebo simulation and publishes ROS2 sensor/odometry topics. |
| GCS | `GCS/` | Runs QGroundControl through noVNC. |
| Bridge | `Bridge/` | Translates between MAVLink UDP and ROS2 topics. |
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
- Telemetry conversion path from ROS2 odometry to MAVLink local/global position messages.

Planned surfaces:

- Mission audit mode for waypoint/geofence validation.
- GNSS integrity monitoring using short-term residuals between odometry and position input.
- Correlation engine that combines command, mission, and GNSS symptoms.

## Runtime Services

`compose.webui.yml` is the default integrated stack. It starts QGroundControl, Gazebo, RViz, and the bridge together:

| Service | URL | Container | Purpose |
| --- | --- | --- | --- |
| QGroundControl | `http://localhost:6080/vnc.html` | `dah-qgc-novnc` | Ground control UI. |
| Gazebo | `http://localhost:6081/vnc_auto.html` | `dah-rosbot-sim-novnc` | ROSbot simulation UI. |
| RViz | `http://localhost:6082/vnc_auto.html` | `dah-rviz-novnc` | ROS2 visualization UI. |
| Bridge | N/A | `dah-bridge` | MAVLink/ROS2 control and telemetry bridge. |

Integrated services use host networking. QGroundControl persists its configuration under `GCS/data`, RViz waits for the ROSbot simulation service, and the bridge waits for QGroundControl and ROSbot simulation. The root stack uses `restart: unless-stopped` for the long-running services.

`Bridge/compose.bridge.yml` is kept for bridge-only debugging when QGroundControl and the simulation are started separately. Do not run it at the same time as the bridge service in `compose.webui.yml`, because both paths use the `dah-bridge` container name:

| Service | Container | Purpose |
| --- | --- | --- |
| bridge | `dah-bridge` | Starts only the MAVLink/ROS2 bridge from the `Bridge/` directory. |

## Environment

The project uses `.env` or `.env.example` for shared configuration.

| Variable | Default | Meaning |
| --- | --- | --- |
| `ROS_DOMAIN_ID` | `17` | Keeps UGV, RViz, and bridge in the same ROS2 DDS domain. |
| `ROBOT_MODEL` | `rosbot` | Selects the Gazebo robot model. If omitted from `.env`, the stack uses `rosbot`; set `ROBOT_MODEL=rosbot_xl` to launch `rosbot_xl`. |
| `QGC_IP` | `127.0.0.1` | QGroundControl MAVLink receiver address. |
| `QGC_PORT` | `14550` | QGroundControl MAVLink UDP port. |
| `BRIDGE_LOCAL_PORT` | `14551` | UDP port where the bridge listens for MAVLink packets. |
| `MAX_LINEAR` | `0.5` | Max linear velocity published to `/cmd_vel`. |
| `MAX_ANGULAR` | `1.2` | Max angular velocity published to `/cmd_vel`. |
| `CMD_TIMEOUT` | `0.6` | Time before the bridge publishes a zero command after input stops. |
| `BASE_LAT`, `BASE_LON`, `BASE_ALT` | Seoul defaults | Origin used to convert local odometry into MAVLink global position telemetry. |
| `LIBGL_ALWAYS_SOFTWARE` | `1` | Prefers software rendering for Gazebo/QGC stability. |
| `MAVLINK_DEBUG` | `0` | Enables verbose MAVLink receive logs when set to `1`. |

## Quick Start

Copy the example environment file if needed:

```bash
cp .env.example .env
```

Robot model selection:

```bash
# Default: ROBOT_MODEL is omitted, so rosbot is used.

# Optional:
ROBOT_MODEL=rosbot_xl
```

Start the integrated testbed stack:

```bash
docker compose --env-file .env -f compose.webui.yml up -d
```

Bridge-only debugging path, only when the integrated bridge is not already running:

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
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

## Documentation Map

| Document | Purpose |
| --- | --- |
| `docs/README.md` | Overview of evidence folders. |
| `docs/day1/README.md` | ROSbot simulation baseline evidence. |
| `docs/day2/README.md` | noVNC web UI integration evidence. |
| `docs/day3/README.md` | ROS2-MAVLink bridge MVP result. |
| `docs/day3/evidence_summary.md` | File-by-file Day3 evidence interpretation. |

## Current Status

The system is at a strong testbed MVP stage. The main control loop is demonstrated end to end, and evidence has been captured for container status, ROS2 topics, bridge logs, `/cmd_vel` wiring, and odometry movement.

Recommended next steps:

- Implement mission audit mode for `MISSION_COUNT` and `MISSION_ITEM_INT`.
- Log normal mission acceptance and malicious mission rejection evidence.
- Add GNSS integrity monitoring after the mission audit path is stable.
- Add correlation logic that links command, mission, and GNSS anomalies.
- Keep the existing Day3 `MANUAL_CONTROL -> /cmd_vel` and `CMD_TIMEOUT` watchdog behavior intact.
