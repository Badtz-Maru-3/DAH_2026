# Day3 - ROS2-MAVLink Bridge MVP

Korean version: [`README_KR.md`](README_KR.md).

Day3 validates the first end-to-end control loop between QGroundControl and the ROSbot Gazebo simulation.

The goal was to prove that a custom bridge can receive MAVLink joystick/control input from QGroundControl, publish ROS2 `/cmd_vel`, move the simulated ROSbot, and send odometry-derived telemetry back to QGroundControl.

In the DAH 2026 plan, this is the first validated attack surface: a C2-like control-command path. It is not the final defense system yet, but it proves that injected or abnormal MAVLink control input can reach the simulated UGV and that resulting movement can be captured as evidence.

## Result

MVP validation passed.

The evidence shows that:

- QGroundControl sends MAVLink traffic to `dah-bridge`.
- `dah-bridge` receives `MANUAL_CONTROL` messages.
- `dah-bridge` publishes non-zero ROS2 `/cmd_vel`.
- The ROSbot drive controller subscribes to `/cmd_vel`.
- `/odometry/filtered` changes after QGroundControl joystick input.
- The measured planar movement was about `1.078 m`.

## Layer Mapping

- Simulation Layer: QGroundControl noVNC, Gazebo/ROSbot, RViz, `/odometry/filtered`
- Software-Defined UGV Security Layer: MAVLink Bridge, MANUAL_CONTROL to `/cmd_vel` translation, telemetry feedback

## Architecture

```text
QGroundControl noVNC
  -> MAVLink UDP / MANUAL_CONTROL
  -> dah-bridge
  -> ROS2 /cmd_vel
  -> ROSbot Gazebo
  -> ROS2 /odometry/filtered
  -> dah-bridge
  -> MAVLink telemetry
  -> QGroundControl map / HUD
```

## Services Under Test

The current default runtime path is the integrated `compose.webui.yml`, which launches all four services together. Use this path for the Day3 baseline unless you are intentionally debugging only the bridge.

| Container | Role |
| --- | --- |
| `dah-qgc-novnc` | QGroundControl web UI. |
| `dah-rosbot-sim-novnc` | ROSbot Gazebo simulation. |
| `dah-rviz-novnc` | RViz visualization. |
| `dah-bridge` | ROS2-MAVLink bridge. |

The integrated stack uses host networking and `restart: unless-stopped`. The bridge service depends on QGroundControl and ROSbot simulation, so the intended Day3 baseline can be launched from the root compose file.

Windows Docker Desktop note: host networking and `websockify 127.0.0.1:608x` can prevent noVNC from opening in the Windows host browser even when containers are healthy. See `docs/day2/README.md` before changing `compose.webui.yml`; a port-published Windows compose path must be revalidated against this Day3 command path.

`Bridge/compose.bridge.yml` remains available for bridge-only debugging, but the baseline stack now lives in the root compose file. Do not run both bridge paths at once because both use the `dah-bridge` container name. If `docker compose -f Bridge/compose.bridge.yml up -d` reports `Conflict. The container name "/dah-bridge" is already in use`, remove the integrated bridge container first:

```bash
docker compose --env-file .env -f compose.webui.yml stop bridge
docker compose --env-file .env -f compose.webui.yml rm -f bridge
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

For a clean switch from the integrated baseline to bridge-only debugging:

```bash
docker compose --env-file .env -f compose.webui.yml down
docker compose --env-file .env -f Bridge/compose.bridge.yml up -d
```

To return from bridge-only debugging to the integrated baseline:

```bash
docker compose --env-file .env -f Bridge/compose.bridge.yml down
docker compose --env-file .env -f compose.webui.yml up -d
```

Robot model selection is controlled by `ROBOT_MODEL` in `.env`. If it is omitted, the stack launches `rosbot`. To use the XL model, add or edit this line in `.env` before starting the stack:

```bash
ROBOT_MODEL=rosbot_xl
```

To return to the default model, set `ROBOT_MODEL=rosbot` or remove the `ROBOT_MODEL` line from `.env`.

## Bridge Behavior

The bridge runs as ROS2 node `ros2_mavlink_bridge`.

ROS2 side:

- Publishes `geometry_msgs/msg/Twist` to `/cmd_vel`.
- Subscribes to `nav_msgs/msg/Odometry` from `/odometry/filtered`.

MAVLink side:

- Listens on `BRIDGE_LOCAL_PORT`, default `14551`.
- Sends telemetry to `QGC_IP:QGC_PORT`, default `127.0.0.1:14550`.
- Sends heartbeat and periodic status text to QGroundControl.
- Handles `MANUAL_CONTROL`, `RC_CHANNELS_OVERRIDE`, `COMMAND_LONG`, `PING`, mission audit messages, `GPS_INPUT`, `PARAM_REQUEST_LIST`, and `PARAM_REQUEST_READ`.
- Responds with a minimal rover-like parameter set so QGroundControl can complete basic parameter discovery.

Control mapping:

- MAVLink forward axis -> `/cmd_vel.linear.x`
- MAVLink yaw/steer axis -> `/cmd_vel.angular.z`
- `MAX_LINEAR=0.5`
- `MAX_ANGULAR=1.2`
- `CMD_TIMEOUT=0.6`

Telemetry mapping:

- ROS odometry local position is mapped to MAVLink local NED-like position.
- ROS odometry is also converted into approximate MAVLink global position using `BASE_LAT`, `BASE_LON`, and `BASE_ALT`.

Runtime behavior:

- The bridge publishes a zero `/cmd_vel` after `CMD_TIMEOUT` if manual control input stops.
- With `MAVLINK_DEBUG=1`, the bridge logs raw UDP receive events and MAVLink message types.

## Evidence Files

| File | Meaning |
| --- | --- |
| `docker_ps.txt` | Confirms all four containers were running during the test. |
| `ros2_topics.txt` | Captures ROS2 topics available in the simulation domain. |
| `cmd_vel_info.txt` | Confirms bridge publishes `/cmd_vel` and drive controller subscribes. |
| `bridge_raw.log` | Verbose bridge log with raw UDP/MAVLink receive evidence. |
| `bridge_clean.log` | Condensed bridge log showing `MANUAL_CONTROL`, `/cmd_vel`, and odometry updates. |
| `odom_before.txt` | Odometry sample before QGroundControl movement. |
| `odom_after.txt` | Odometry sample after QGroundControl movement. |
| `odom_delta.md` | Calculated odometry delta and interpretation. |
| `evidence_summary.md` | Human-readable summary of the Day3 evidence set. |

## Key Observations

From `bridge_clean.log`:

```text
Bridge up: ROS_DOMAIN_ID=17, MAVLink 0.0.0.0:14551 -> 127.0.0.1:14550, ROS /cmd_vel <-> /odometry/filtered
MAVLink RX: MANUAL_CONTROL
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.049
odom received: x=3.03, y=-0.58, z=0.00
odom received: x=3.73, y=-0.89, z=0.00
```

From `cmd_vel_info.txt`:

- Publisher: `ros2_mavlink_bridge`
- Subscriber: `drive_controller`

From `odom_delta.md`:

- Before: `x=2.768542`, `y=-0.436533`
- After: `x=3.743598`, `y=-0.896752`
- Delta: `dx=0.975055`, `dy=-0.460219`
- Planar distance: `1.078209 m`

## Conclusion

Day3 demonstrates a working bridge MVP. QGroundControl input reaches the ROSbot simulation through MAVLink and ROS2, and the robot's resulting odometry confirms actual movement.

This is not yet a production autopilot replacement or the final AI defense orchestrator. It is a successful prototype bridge that proves the integration path and gives the project a solid base for command-attack injection, mission audit mode, GNSS integrity checks, correlation logic, and report-ready evidence logs.

## Follow-on Alignment

After Day3, the bridge was extended with mission audit, GNSS integrity, and correlation hold:

- Day4 receives `MISSION_COUNT`, requests items with `MISSION_REQUEST_INT`, audits `MISSION_ITEM_INT`, and accepts/rejects with `MISSION_ACK`.
- Day5 receives `GPS_INPUT` and rejects spoofed or low-quality position input.
- Day6 converts mission/GNSS rejection into correlation hold and blocks manual commands during hold.

The Day3 bridge path must remain stable as those layers evolve. In particular, `MANUAL_CONTROL -> /cmd_vel`, odometry telemetry, and the `CMD_TIMEOUT` watchdog are existing evidence-backed behavior.
