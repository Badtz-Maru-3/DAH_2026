# Day1 - ROSbot Simulation Baseline

원본: `docs/day1/README.md`

Day1은 ROSbot Gazebo simulation의 baseline 상태를 캡처합니다.

목적은 web UI, MAVLink bridge, cyber-defense layer를 추가하기 전에 UGV simulation container가 실행되고 필요한 ROS2 topic을 노출하는지 확인하는 것입니다.

## Evidence Files

| File | Meaning |
| --- | --- |
| `docker_ps.txt` | baseline simulation run 중 container 상태 |
| `ros2_topics.txt` | ROSbot simulation이 노출한 ROS2 topic list |
| `rosbot_sim.log` | simulation container runtime log |

## What To Look For

- `docker_ps.txt`에서 simulation container가 살아 있었는지 확인합니다.
- `ros2_topics.txt`에서 command, odometry, scan, TF topic이 보이는지 확인합니다.
- `rosbot_sim.log`는 simulation startup issue 확인용 low-level runtime trace로 보존합니다.

## Interpretation

Day1은 logical two-layer architecture의 Simulation Layer baseline을 세웁니다.

```text
ROSbot Gazebo
  -> ROS2 topics
  -> odometry, scan, TF, sensor data
```

이 baseline은 이후 mission audit, GNSS integrity, command injection test에서 abnormal behavior를 해석하기 위한 known-good state입니다.

## Limitations

Day1은 QGroundControl connectivity, MAVLink handling, mission upload, attack injection, defense behavior를 증명하지 않습니다. simulated UGV layer가 available and observable하다는 것만 증명합니다.
