# Day2 - noVNC Web UI Stack

원본: `docs/day2/README.md`

Day2는 simulation environment의 browser-accessible visual stack을 캡처합니다.

목적은 QGroundControl, Gazebo, RViz가 Docker service로 실행되고 noVNC를 통해 browser에서 접근 가능한지 확인하는 것입니다. 이 계층은 이후 mission upload, abnormal-command observation, screenshot evidence에 필요합니다.

## Services

| Service | URL | Purpose |
| --- | --- | --- |
| QGroundControl | `http://localhost:6080/vnc.html` | Ground control UI |
| Gazebo | `http://localhost:6081/vnc_auto.html` | Simulation world and robot visualization |
| RViz | `http://localhost:6082/vnc_auto.html` | ROS2 visualization |

## Windows Docker Desktop Access Note

현재 captured stack은 `compose.webui.yml`의 `network_mode: host`를 기준으로 합니다. Windows Docker Desktop에서는 container가 healthy여도 Windows browser에서 `localhost:6080`, `6081`, `6082`가 열리지 않을 수 있습니다.

후보 수정은 다음과 같습니다.

- `websockify` bind를 `127.0.0.1`에서 `0.0.0.0`으로 변경
- noVNC service에서 `network_mode: host` 제거
- compose `ports`로 `6080:6080`, `6081:6081`, `6082:6082` publish

이 후보는 기본 Linux/WSL stack의 검증 완료 대체안이 아닙니다. host networking을 제거하면 ROS2 DDS discovery와 MAVLink bridge addressing이 달라질 수 있으므로 Day2-Day6 checks를 다시 수행해야 합니다.

## Evidence Files

| File | Meaning |
| --- | --- |
| `docker_ps_webui.txt` | web UI stack container 상태 |
| `ros2_topics_webui.txt` | web UI stack 실행 중 ROS2 topic list |
| `qgc_novnc.log` | QGroundControl noVNC service log |
| `gazebo_novnc.log` | Gazebo noVNC service log |
| `rviz_novnc.log` | RViz noVNC service log |

## Interpretation

Day2는 Simulation Layer의 operator-facing 부분을 세웁니다.

```text
Browser
  -> noVNC
  -> QGroundControl / Gazebo / RViz
```

Day3는 여기에 bridge를 추가해 QGroundControl이 ROSbot simulation을 실제로 제어할 수 있음을 검증합니다. Day4-Day6는 같은 UI/runtime layer 위에서 mission audit, GNSS integrity, correlation evidence를 수집합니다.

## Limitations

Day2는 QGroundControl이 robot을 제어하거나 bridge가 mission/GNSS input을 audit할 수 있음을 증명하지 않습니다. active MAVLink-to-ROS2 control path는 Day3, mission audit은 Day4, GNSS integrity는 Day5, correlation response는 Day6에서 검증됩니다.
