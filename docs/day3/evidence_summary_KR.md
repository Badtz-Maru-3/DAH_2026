# Day3 Evidence Summary

원본: `docs/day3/evidence_summary.md`

Day3는 custom ROS2-MAVLink bridge가 QGroundControl control input을 ROSbot Gazebo simulation에 연결할 수 있음을 증명합니다.

DAH 2026 계획에서 이 evidence는 첫 attack-defense surface인 command channel을 검증합니다. Day4-Day6 evidence는 이 baseline 위에 mission audit, GNSS integrity, correlation blocking을 추가합니다.

## Verdict

Bridge MVP is validated.

Captured evidence가 지지하는 chain:

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

`docker_ps.txt`는 다음 service가 함께 실행 중이었음을 보여줍니다.

| Container | Evidence |
| --- | --- |
| `dah-bridge` | Bridge container up |
| `dah-qgc-novnc` | QGroundControl noVNC container up |
| `dah-rviz-novnc` | RViz noVNC container up |
| `dah-rosbot-sim-novnc` | ROSbot Gazebo simulation container up |

## ROS2 Topic Evidence

| Topic | Type | Role |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | robot velocity command input |
| `/odometry/filtered` | `nav_msgs/msg/Odometry` | robot pose/velocity feedback |
| `/scan` | `sensor_msgs/msg/LaserScan` | laser scan visualization input |
| `/tf`, `/tf_static` | `tf2_msgs/msg/TFMessage` | robot frame transforms |

## `/cmd_vel` Wiring Evidence

`cmd_vel_info.txt`는 bridge output이 simulated robot에 연결되어 있음을 보여줍니다.

| Endpoint | Node | Meaning |
| --- | --- | --- |
| Publisher | `ros2_mavlink_bridge` | Bridge publishes velocity commands |
| Subscriber | `drive_controller` | Robot controller receives velocity commands |

## MAVLink Receive Evidence

```text
RAW UDP RX: 23 bytes from ('127.0.0.1', 14550)
MAVLink RX: MANUAL_CONTROL
MAVLink RX: HEARTBEAT
MAVLink RX: REQUEST_DATA_STREAM
MAVLink RX: COMMAND_LONG
```

## Command Translation Evidence

```text
MANUAL_CONTROL -> /cmd_vel linear.x=0.302, angular.z=0.000
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.000
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.049
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.150
```

## Motion Evidence

| Measurement | Value |
| --- | --- |
| Before `x` | `2.768542` |
| Before `y` | `-0.436533` |
| After `x` | `3.743598` |
| After `y` | `-0.896752` |
| Delta `x` | `0.975055` |
| Delta `y` | `-0.460219` |
| Planar distance | `1.078209 m` |

## What This Proves

- QGroundControl can send MAVLink input to the custom bridge.
- The bridge can parse useful MAVLink control messages.
- The bridge can publish ROS2 `/cmd_vel`.
- ROSbot simulation receives that command path.
- Robot movement is visible through odometry.
- Default compose path can launch the full baseline testbed stack.

## What This Does Not Yet Prove

- Long-duration stability
- full mission execution by an autopilot
- long-duration GNSS fallback/dead-reckoning
- learned AI model behavior beyond the current rule/score-based correlation engine
- automated regression coverage or evidence collection scripts
