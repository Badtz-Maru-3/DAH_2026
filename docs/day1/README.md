# Day1 - ROSbot Simulation Baseline

Day1 captures the baseline ROSbot Gazebo simulation state.

The purpose was to confirm that the UGV simulation container can run and expose the expected ROS2 topics before adding the web UI and MAVLink bridge layers.

The UGV launch supports `ROBOT_MODEL`. If the variable is omitted, the simulation uses `rosbot`; setting `ROBOT_MODEL=rosbot_xl` launches `rosbot_xl`.

## Evidence Files

| File | Meaning |
| --- | --- |
| `docker_ps.txt` | Container status during the baseline simulation run. |
| `ros2_topics.txt` | ROS2 topic list exposed by the ROSbot simulation. |
| `rosbot_sim.log` | Runtime log from the simulation container. |

## Interpretation

This day establishes the bottom layer of the system:

```text
ROSbot Gazebo
  -> ROS2 topics
  -> odometry, scan, TF, sensor data
```

The later Day2 and Day3 tests build on this baseline.
