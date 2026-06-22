# Day3 - ROS2-MAVLink Bridge MVP

원본: `docs/day3/README.md`

Day3는 QGroundControl과 ROSbot Gazebo simulation 사이의 첫 end-to-end control loop를 검증합니다.

목표는 custom bridge가 QGroundControl의 MAVLink joystick/control input을 받고, ROS2 `/cmd_vel`을 publish해 simulated ROSbot을 움직이며, odometry-derived telemetry를 QGroundControl로 되돌릴 수 있음을 증명하는 것입니다.

## Result

MVP validation passed.

Evidence는 다음을 보여줍니다.

- QGroundControl이 `dah-bridge`로 MAVLink traffic을 보냅니다.
- `dah-bridge`가 `MANUAL_CONTROL` message를 수신합니다.
- `dah-bridge`가 non-zero ROS2 `/cmd_vel`을 publish합니다.
- ROSbot drive controller가 `/cmd_vel`을 subscribe합니다.
- QGroundControl joystick input 이후 `/odometry/filtered`가 변합니다.
- measured planar movement는 약 `1.078 m`입니다.

## Layer Mapping

- Simulation Layer: QGroundControl noVNC, Gazebo/ROSbot, RViz, `/odometry/filtered`
- Software-Defined UGV Security Layer: MAVLink Bridge, `MANUAL_CONTROL -> /cmd_vel` translation, telemetry feedback

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

## Bridge Behavior

ROS2 side:

- `/cmd_vel`에 `geometry_msgs/msg/Twist` publish
- `/odometry/filtered`의 `nav_msgs/msg/Odometry` subscribe

MAVLink side:

- 기본 `BRIDGE_LOCAL_PORT=14551`에서 listen
- 기본 `QGC_IP:QGC_PORT=127.0.0.1:14550`으로 telemetry 전송
- heartbeat, status text, rover-like minimal parameter set 제공
- `MANUAL_CONTROL`, `RC_CHANNELS_OVERRIDE`, `COMMAND_LONG`, mission audit messages, `GPS_INPUT` 등을 처리

Control mapping:

- MAVLink forward axis -> `/cmd_vel.linear.x`
- MAVLink yaw/steer axis -> `/cmd_vel.angular.z`
- `MAX_LINEAR=0.5`
- `MAX_ANGULAR=1.2`
- `CMD_TIMEOUT=0.6`

## Evidence Files

| File | Meaning |
| --- | --- |
| `docker_ps.txt` | 네 container가 test 중 실행 중이었음을 확인 |
| `ros2_topics.txt` | simulation domain의 ROS2 topic snapshot |
| `cmd_vel_info.txt` | bridge publisher와 drive controller subscriber 확인 |
| `bridge_raw.log` | raw UDP/MAVLink receive evidence |
| `bridge_clean.log` | `MANUAL_CONTROL`, `/cmd_vel`, odometry update 요약 |
| `odom_before.txt` | movement 전 odometry sample |
| `odom_after.txt` | movement 후 odometry sample |
| `odom_delta.md` | odometry delta 계산 |
| `evidence_summary.md` | Day3 evidence set 해석 |

## Key Observations

```text
MAVLink RX: MANUAL_CONTROL
MANUAL_CONTROL -> /cmd_vel linear.x=0.500, angular.z=0.049
odom received: x=3.03, y=-0.58, z=0.00
odom received: x=3.73, y=-0.89, z=0.00
```

`cmd_vel_info.txt` 기준:

- Publisher: `ros2_mavlink_bridge`
- Subscriber: `drive_controller`

`odom_delta.md` 기준:

- Before: `x=2.768542`, `y=-0.436533`
- After: `x=3.743598`, `y=-0.896752`
- Planar distance: `1.078209 m`

## Conclusion

Day3는 QGroundControl input이 MAVLink와 ROS2를 거쳐 ROSbot simulation에 도달하고, resulting odometry가 실제 movement를 보여준다는 것을 증명합니다.

이는 production autopilot replacement나 최종 AI defense orchestrator가 아닙니다. command-attack injection, mission audit, GNSS integrity, correlation logic, report-ready evidence log를 위한 bridge baseline입니다.
