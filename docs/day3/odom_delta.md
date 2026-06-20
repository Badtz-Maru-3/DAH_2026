# Day3 Odometry Delta

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

The ROSbot position changed after QGroundControl joystick input.
This indicates that MAVLink manual control was translated into ROS2 `/cmd_vel` and applied to the simulated UGV.

For the DAH 2026 testbed, this file is the motion proof for the command-control baseline. It does not prove attack detection by itself. It proves that the command path is live, measurable, and suitable for later command-injection and blocking experiments.

Day4-Day6 evidence should keep this movement proof as a regression baseline. Mission audit, GNSS integrity, and correlation changes must not break the existing `MANUAL_CONTROL -> /cmd_vel -> odometry` path or the `CMD_TIMEOUT` zero-command watchdog.
