# Day2 - noVNC Web UI Stack

Day2 captures the web-accessible visual stack for the simulation environment.

The purpose was to confirm that QGroundControl, Gazebo, and RViz can run as Docker services and be accessed through browser-based noVNC sessions. This creates the operator-facing layer needed for later mission upload, abnormal-command observation, and screenshot evidence.

In the current integrated stack, `compose.webui.yml` also starts `dah-bridge`. Day2 evidence still represents the web UI layer before the bridge MVP was validated.

## Services

| Service | URL | Purpose |
| --- | --- | --- |
| QGroundControl | `http://localhost:6080/vnc.html` | Ground control UI. |
| Gazebo | `http://localhost:6081/vnc_auto.html` | Simulation world and robot visualization. |
| RViz | `http://localhost:6082/vnc_auto.html` | ROS2 visualization. |

## Evidence Files

| File | Meaning |
| --- | --- |
| `docker_ps_webui.txt` | Container status for the web UI stack. |
| `ros2_topics_webui.txt` | ROS2 topic list while the web UI stack was running. |
| `qgc_novnc.log` | QGroundControl noVNC service log. |
| `gazebo_novnc.log` | Gazebo noVNC service log. |
| `rviz_novnc.log` | RViz noVNC service log. |

## What To Look For

Use Day2 evidence to confirm that the operator-facing surfaces are available before testing bridge control or attack scenarios.

- QGroundControl should be reachable through noVNC and later used for vehicle connection, joystick, and mission upload observations.
- Gazebo should show the simulated physical world, making movement or abnormal behavior visible.
- RViz should show ROS-side state such as TF, laser scan, odometry, and command topics.
- The service logs should help distinguish UI/display startup issues from bridge or ROS2 failures.

## Interpretation

This day establishes the operator-facing layer:

```text
Browser
  -> noVNC
  -> QGroundControl / Gazebo / RViz
```

Day3 then adds the bridge that lets QGroundControl actively control the ROSbot simulation.

Current runtime note: the bridge has since been folded into the default integrated `compose.webui.yml`, so the full baseline stack now starts from one compose file.

For the attack-defense plan, Day2 is not just UI plumbing. QGroundControl is the place where future mission attacks, waypoint uploads, operator alerts, and connection-state evidence will be observed. Gazebo shows the simulated physical effect, while RViz provides ROS-side confirmation through TF, laser scan, odometry, and command topics.

## Limitations

Day2 does not prove that QGroundControl can control the robot. It only proves that the web-accessible UI layer exists. The active MAVLink-to-ROS2 control path is validated in Day3.
