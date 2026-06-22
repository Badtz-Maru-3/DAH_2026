# Day2 - noVNC Web UI Stack

Korean version: [`README_KR.md`](README_KR.md).

Day2 captures the web-accessible visual stack for the simulation environment.

The purpose was to confirm that QGroundControl, Gazebo, and RViz can run as Docker services and be accessed through browser-based noVNC sessions. This creates the operator-facing layer needed for later mission upload, abnormal-command observation, and screenshot evidence.

In the current integrated stack, `compose.webui.yml` also starts `dah-bridge`. Day2 evidence still represents the web UI layer before the bridge MVP was validated.

## Services

| Service | URL | Purpose |
| --- | --- | --- |
| QGroundControl | `http://localhost:6080/vnc.html` | Ground control UI. |
| Gazebo | `http://localhost:6081/vnc_auto.html` | Simulation world and robot visualization. |
| RViz | `http://localhost:6082/vnc_auto.html` | ROS2 visualization. |

## Windows Docker Desktop Access Note

The captured Day2 stack uses `compose.webui.yml` with `network_mode: host`, and each noVNC entrypoint currently starts `websockify` on container loopback:

| Service | Entrypoint | Current bind | Windows access candidate |
| --- | --- | --- | --- |
| QGroundControl | `GCS/entrypoint-novnc.sh` | `127.0.0.1:6080` | `0.0.0.0:6080` |
| Gazebo | `UGV/entrypoint-ugv-novnc.sh` | `127.0.0.1:6081` | `0.0.0.0:6081` |
| RViz | `UGV/entrypoint-rviz-novnc.sh` | `127.0.0.1:6082` | `0.0.0.0:6082` |

On Windows Docker Desktop, this can make the containers look healthy while the Windows browser still cannot open `localhost:6080`, `6081`, or `6082`. A candidate Windows workaround is:

- bind `websockify` to `0.0.0.0:6080`, `0.0.0.0:6081`, and `0.0.0.0:6082`;
- remove `network_mode: host` from the noVNC services;
- publish the browser ports with compose `ports: "6080:6080"`, `"6081:6081"`, and `"6082:6082"`.

This note is not yet a validated replacement for the default Linux/WSL stack. If host networking is removed, ROS2 DDS discovery and MAVLink bridge addressing can change, so rerun Day2-Day6 checks before documenting the Windows path as the default.

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
- Gazebo should show the simulated world, making movement or abnormal behavior visible.
- RViz should show ROS-side state such as TF, laser scan, odometry, and command topics.
- The service logs should help distinguish UI/display startup issues from bridge or ROS2 failures.

## Interpretation

This day establishes the operator-facing part of the Simulation Layer:

```text
Browser
  -> noVNC
  -> QGroundControl / Gazebo / RViz
```

Day3 then adds the bridge that lets QGroundControl actively control the ROSbot simulation. Day4-Day6 reuse this same operator and runtime layer for mission audit, GNSS integrity, and correlation evidence.

Current runtime note: the bridge has since been folded into the default integrated `compose.webui.yml`, so the full baseline stack now starts from one compose file.

For the attack-defense plan, Day2 is not just UI plumbing. QGroundControl is the place where future mission attacks, waypoint uploads, operator alerts, and connection-state evidence will be observed. Gazebo shows the simulated UGV effect, while RViz provides ROS-side confirmation through TF, laser scan, odometry, and command topics.

## Limitations

Day2 does not prove that QGroundControl can control the robot or that the bridge can audit missions/GNSS input. It only proves that the web-accessible UI layer exists. The active MAVLink-to-ROS2 control path is validated in Day3, mission audit in Day4, GNSS integrity in Day5, and correlation response in Day6.
