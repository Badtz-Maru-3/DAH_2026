# Day3 Odometry Delta

원본: `docs/day3/odom_delta.md`

## Before

- x: 2.768542
- y: -0.436533
- z: 0.000000

## After

- x: 3.743598
- y: -0.896752
- z: 0.000000

## Delta

- dx: 0.975055
- dy: -0.460219
- dz: 0.000000
- planar_distance: 1.078209 m

## Interpretation

QGroundControl joystick input 이후 ROSbot position이 변했습니다.

이는 MAVLink manual control이 ROS2 `/cmd_vel`로 변환되어 simulated UGV에 적용되었음을 의미합니다.

DAH 2026 testbed에서 이 파일은 command-control baseline의 motion proof입니다. 이 파일만으로 attack detection을 증명하지는 않습니다. 대신 command path가 live, measurable하며 이후 command-injection 및 blocking experiment에 사용할 수 있음을 증명합니다.

Day4-Day6 evidence는 이 movement proof를 regression baseline으로 유지해야 합니다. Mission audit, GNSS integrity, correlation change가 기존 `MANUAL_CONTROL -> /cmd_vel -> odometry` path와 `CMD_TIMEOUT` zero-command watchdog을 깨면 안 됩니다.
