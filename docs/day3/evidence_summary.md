# Day3 Evidence Summary

Day3 proves that the custom ROS2-MAVLink bridge can connect QGroundControl control input to the ROSbot Gazebo simulation.

For the DAH 2026 plan, this evidence validates the first attack-defense surface: the command channel. Later Day4-Day6 evidence adds mission audit, GNSS integrity, and correlation blocking on top of this baseline.

## Verdict

The bridge MVP is validated.

The captured evidence supports this chain:

```text
QGroundControl joystick input
  -> MAVLink MANUAL_CONTROL
  -> dah-bridge
  -> ROS2 /cmd_vel
  -> drive_controller
  -> ROSbot movement
  -> /odometry/filtered change
```

## Container Evidence

`docker_ps.txt` shows the required services running together:

| Container | Evidence |
| --- | --- |
| `dah-bridge` | Bridge container was up. |
| `dah-qgc-novnc` | QGroundControl noVNC container was up. |
| `dah-rviz-novnc` | RViz noVNC container was up. |
| `dah-rosbot-sim-novnc` | ROSbot Gazebo simulation container was up. |

This confirms that the test was not isolated to one process; the full simulation/control stack was active.

Current runtime note: the default root `compose.webui.yml` now includes all four services, including `dah-bridge`. The separate `Bridge/compose.bridge.yml` remains useful for bridge-only debugging, but it should not be run at the same time as the integrated bridge service.

## ROS2 Topic Evidence

`ros2_topics.txt` includes the topics needed for the bridge MVP:

| Topic | Type | Role |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Velocity command input to the robot. |
| `/odometry/filtered` | `nav_msgs/msg/Odometry` | Robot pose/velocity feedback used for MAVLink telemetry. |
| `/scan` | `sensor_msgs/msg/LaserScan` | Laser scan visualization input. |
| `/tf`, `/tf_static` | `tf2_msgs/msg/TFMessage` | Robot frame transforms. |

## `/cmd_vel` Wiring Evidence

`cmd_vel_info.txt` confirms the critical ROS2 connection:

| Endpoint | Node | Meaning |
| --- | --- | --- |
| Publisher | `ros2_mavlink_bridge` | Bridge publishes velocity commands. |
| Subscriber | `drive_controller` | Robot controller receives velocity commands. |

This is the key ROS2-side proof that the bridge output is connected to the simulated robot.

## MAVLink Receive Evidence

`bridge_raw.log` confirms that the bridge receives UDP packets from QGroundControl:

```text
RAW UDP RX: 23 bytes from ('127.0.0.1', 14550)
MAVLink RX: MANUAL_CONTROL
MAVLink RX: HEARTBEAT
MAVLink RX: REQUEST_DATA_STREAM
MAVLink RX: COMMAND_LONG
```

This proves QGroundControl was communicating with the bridge over MAVLink UDP.

## Command Translation Evidence

`bridge_clean.log` shows MAVLink manual control being converted into ROS2 velocity commands:

```text
MANUAL_CONTROL -> /cmd_vel linear.x=0.302, angular.z=0.000
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.000
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.049
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.150
```

This proves the bridge is not only receiving MAVLink; it is producing non-zero robot commands.

## Motion Evidence

`odom_before.txt`, `odom_after.txt`, and `odom_delta.md` show that the robot position changed after QGroundControl input.

| Measurement | Value |
| --- | --- |
| Before `x` | `2.768542` |
| Before `y` | `-0.436533` |
| After `x` | `3.743598` |
| After `y` | `-0.896752` |
| Delta `x` | `0.975055` |
| Delta `y` | `-0.460219` |
| Planar distance | `1.078209 m` |

This is the final proof that the command path affected the simulated UGV.

## What This Proves

Day3 proves:

- QGroundControl can send MAVLink input to the custom bridge.
- The custom bridge can parse useful MAVLink control messages.
- The custom bridge can publish ROS2 `/cmd_vel`.
- The ROSbot simulation receives that command path.
- The robot moves in Gazebo.
- Odometry feedback is available for telemetry.
- The default compose path can now launch the full baseline testbed stack, including the bridge.

## What This Does Not Yet Prove

The current evidence does not yet prove:

- Long-duration stability.
- Full QGroundControl vehicle setup compatibility.
- Complete MAVLink parameter coverage.
- Mission execution by an autopilot.
- Long-duration GNSS fallback/dead-reckoning.
- Learned AI model behavior beyond the current rule/score-based correlation engine.
- Robust handling of network loss or container restarts beyond the current command timeout watchdog.
- Automated regression coverage or evidence collection scripts.

## Follow-on Evidence

Captured after Day3:

- `docs/day4/mission_audit.log` shows normal mission accepted and malicious mission rejected.
- `docs/day5/gnss_integrity.log` shows normal GPS_INPUT accepted and spoof/poor-fix inputs rejected.
- `docs/day6/correlation_mission_malicious.log` and `docs/day6/correlation_gnss_spoof.log` show hold engagement and command blocking.

Still useful to add:

- QGroundControl screenshots for mission upload, rejection, and operator-visible warning state.
- A repeatable script that captures container state, ROS2 topics, bridge logs, odometry deltas, and audit logs from a fresh run.
- A failure-mode test for command timeout and zero `/cmd_vel` publishing.
