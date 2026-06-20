# Day1 - ROSbot Simulation Baseline

Day1 captures the baseline ROSbot Gazebo simulation state.

The purpose was to confirm that the UGV simulation container can run and expose the expected ROS2 topics before adding the web UI, MAVLink bridge, and cyber-defense layers.

The UGV launch supports `ROBOT_MODEL`. If the variable is omitted, the simulation uses `rosbot`; setting `ROBOT_MODEL=rosbot_xl` launches `rosbot_xl`.

## Evidence Files

| File | Meaning |
| --- | --- |
| `docker_ps.txt` | Container status during the baseline simulation run. |
| `ros2_topics.txt` | ROS2 topic list exposed by the ROSbot simulation. |
| `rosbot_sim.log` | Runtime log from the simulation container. |

## What To Look For

Use Day1 evidence to confirm that the simulation itself is not the source of later test failures.

- `docker_ps.txt` should show that the simulation container was alive during the capture.
- `ros2_topics.txt` should include the command, odometry, scan, and TF topics needed by later bridge and defense logic.
- `rosbot_sim.log` should be kept as the low-level runtime trace for simulation startup issues.

## Interpretation

This day establishes the physical/simulation layer of the testbed:

```text
ROSbot Gazebo
  -> ROS2 topics
  -> odometry, scan, TF, sensor data
```

For the attack-defense plan, Day1 matters because every later anomaly must eventually be observed against this baseline. Mission audit, GNSS integrity checks, and command injection tests all need a known-good simulation state before abnormal behavior can be interpreted.

This also makes Day1 the fallback check when later Day4-Day6 defense tests fail: first confirm that ROS2 discovery, odometry, scan, TF, and command topics still match the baseline before debugging MAVLink mission, GNSS, or correlation handling.

Baseline assumptions captured by Day1:

- ROSbot simulation can run in Docker.
- ROS2 discovery works in the configured `ROS_DOMAIN_ID`.
- Core topics such as odometry, scan, TF, and command interfaces are available.
- The robot model can be selected with `ROBOT_MODEL`; omitted means `rosbot`, while `ROBOT_MODEL=rosbot_xl` selects `rosbot_xl`.

## Limitations

Day1 does not prove QGroundControl connectivity, MAVLink handling, mission upload, attack injection, or defense behavior. It only proves that the simulated UGV layer is available and observable. Those higher layers are added in Day2 through Day6.
